import json
import logging
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIStatusError, RateLimitError
from backend.core.config import settings
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.services.payload_normalization import has_structured_ocr_summary_data

# Initialize Logger
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    import filetype
    OCR_RUNTIME_AVAILABLE = True
except ImportError:
    fitz = None
    filetype = None
    OCR_RUNTIME_AVAILABLE = False

try:
    from aip import AipOcr
    BAIDU_OCR_AVAILABLE = True
except ImportError:
    AipOcr = None
    BAIDU_OCR_AVAILABLE = False

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

    class RetryError(Exception):
        pass

    def retry(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def stop_after_attempt(*args, **kwargs):
        return None

    def wait_exponential(*args, **kwargs):
        return None

    def retry_if_exception_type(*args, **kwargs):
        return None

_degraded_mode_warning_emitted = False


def _emit_degraded_mode_warning():
    global _degraded_mode_warning_emitted
    if _degraded_mode_warning_emitted:
        return
    logger.warning("Baidu OCR unavailable; OCR will run in degraded mode.")
    _degraded_mode_warning_emitted = True


class MedicalOCRService:
    def __init__(self):
        """
        Initialize MedicalOCRService with Baidu AIP and AsyncOpenAI client (Kimi).
        """
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL or "https://api.moonshot.cn/v1"
        self.model = settings.OPENAI_MODEL or "moonshot-v1-8k"
        
        # Initialize LLM Client
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None
            logger.debug("OPENAI_API_KEY missing. LLM semantic parsing will be disabled.")
            
        # Initialize Baidu OCR Client
        self.ocr_client = None
        self.ocr_ready = False
        try:
            if not BAIDU_OCR_AVAILABLE or AipOcr is None:
                _emit_degraded_mode_warning()
            elif settings.BAIDU_APP_ID and settings.BAIDU_API_KEY and settings.BAIDU_SECRET_KEY:
                self.ocr_client = AipOcr(
                    settings.BAIDU_APP_ID, 
                    settings.BAIDU_API_KEY, 
                    settings.BAIDU_SECRET_KEY
                )
                self.ocr_client.setConnectionTimeoutInMillis(settings.BAIDU_OCR_CONNECTION_TIMEOUT_MS)
                self.ocr_client.setSocketTimeoutInMillis(settings.BAIDU_OCR_SOCKET_TIMEOUT_MS)
                self.ocr_ready = True
            else:
                _emit_degraded_mode_warning()
        except Exception as e:
            logger.warning("Baidu OCR init unavailable; OCR will run in degraded mode (%s).", e)

    def _build_processing_status(
        self,
        *,
        status: str,
        reason: Optional[str],
        structured_data_present: bool,
        raw_text_present: bool,
    ) -> Dict[str, Any]:
        return {
            "schema_version": "ocr_processing_status.v1",
            "status": status,
            "reason": reason,
            "structured_data_present": structured_data_present,
            "raw_text_present": raw_text_present,
        }

    def _build_stored_unprocessed_result(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "status": "stored_unprocessed",
            "message": message,
            "raw_text": None,
            "extraction_method": None,
            "data": None,
            "ocr_processing_status": self._build_processing_status(
                status="stored_unprocessed",
                reason=reason,
                structured_data_present=False,
                raw_text_present=False,
            ),
        }

    def build_stored_unprocessed_result(self, reason: str, message: str) -> Dict[str, Any]:
        return self._build_stored_unprocessed_result(reason, message)

    def _pdf_to_images(self, pdf_bytes: bytes, max_pages: int = 5) -> List[bytes]:
        """
        Convert PDF pages to list of image bytes (PNG).
        Limits to first max_pages to save quota/time.
        """
        images = []
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                if doc.page_count < 1:
                    return []
                
                # Iterate pages
                for i in range(min(doc.page_count, max_pages)):
                    page = doc.load_page(i)
                    # Task 50: Render at 3x scale for better OCR on dense medical text
                    mat = fitz.Matrix(3.0, 3.0)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    images.append(img_bytes)
                    
                return images
        except Exception as e:
            logger.error(f"PDF Conversion Failed: {e}")
            return []

    def _get_ocr_text(self, image_bytes: bytes) -> str:
        """
        Run Baidu Cloud OCR on image bytes and return combined text.
        Handles PDF to Image conversion (multi-page).
        """
        if not self.ocr_ready or not self.ocr_client or not OCR_RUNTIME_AVAILABLE:
            logger.info("Baidu OCR client not ready; skipping OCR parse.")
            return ""

        try:
            # 1. Determine list of images to process
            kind = filetype.guess(image_bytes) if filetype else None
            images_to_process = []

            if kind and kind.mime == 'application/pdf':
                images = self._pdf_to_images(image_bytes)
                if images:
                    images_to_process = images
                else:
                    logger.warning("PDF conversion failed or empty. Trying raw bytes as fallback.")
                    images_to_process = [image_bytes]
            else:
                # Assume single image
                images_to_process = [image_bytes]

            # 2. Concurrent OCR Processing (Task 72/80)
            full_text_parts = [""] * len(images_to_process)
            options = {"detect_direction": "true"}
            
            def process_page(idx, img_data):
                try:
                    res = self.ocr_client.basicAccurate(img_data, options)
                    if "error_code" in res:
                        logger.error(f"Baidu OCR API Error (Page {idx}): {res}")
                        return f"--- Page {idx+1} [Error] ---\n"
                    
                    if "words_result" in res:
                        page_txt = "\n".join([item['words'] for item in res['words_result']])
                        return f"--- Page {idx+1} ---\n{page_txt}"
                    return f"--- Page {idx+1} [Empty] ---\n"
                except Exception as e:
                    logger.error(f"Page {idx} processing failed: {e}")
                    return f"--- Page {idx+1} [Exception] ---\n"

            # Task 80: Use ThreadPoolExecutor with 5 workers for faster multi-page OCR
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_idx = {executor.submit(process_page, i, img): i for i, img in enumerate(images_to_process)}
                
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        full_text_parts[idx] = future.result()
                    except Exception as exc:
                        logger.error(f"Page {idx} generated an exception: {exc}")
            
            full_text = "\n\n".join(full_text_parts)
            return full_text

        except Exception as e:
            logger.error(f"Baidu OCR Processing Error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _extract_by_regex(self, text: str) -> Dict[str, Any]:
        """
        Regex fallback used when semantic LLM parsing is unavailable.
        Patterns are kept ASCII-safe with Unicode escapes to avoid Windows
        console encoding corruption in Chinese labels.
        """
        result: Dict[str, Any] = {}

        def assign_number(key: str, value: str | None, *, as_int: bool = False) -> None:
            if value is None:
                return
            try:
                number = float(value)
            except (TypeError, ValueError):
                return
            result[key] = int(number) if as_int else number

        def first_number_after(label_pattern: str, *, max_gap: int = 18) -> str | None:
            pattern = rf"{label_pattern}\D{{0,{max_gap}}}(\d{{1,4}}(?:\.\d{{1,2}})?)"
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1) if match else None

        def gender_value() -> int | None:
            match = re.search(
                r"(?:\u6027\s*\u522b|\u6027\u522b)\D{0,12}(\u7537|\u5973|Male|Female|M|F)",
                text,
                re.IGNORECASE,
            )
            if not match:
                return None
            token = match.group(1).lower()
            if token in {"\u7537", "male", "m"}:
                return 1
            if token in {"\u5973", "female", "f"}:
                return 2
            return None

        patient_patterns = [
            ("Age", r"(?:\u5e74\s*\u9f84|\u5e74\u9f84)", True),
            ("Height", r"\u8eab\u9ad8\s*(?:\(|\uff08)?\s*cm\s*(?:\)|\uff09)?", False),
            ("Weight", r"\u4f53\u91cd\s*(?:\(|\uff08)?\s*(?:kg|Kg|KG)\s*(?:\)|\uff09)?", False),
            ("BMI", r"(?:\bBMI\b|\u4f53\u91cd\u6307\u6570|\u4f53\u8d28\u6307\u6570)", False),
            ("SBP", r"(?:\u6536\u7f29\u538b|\u9ad8\u538b|SBP)", True),
            ("DBP", r"(?:\u8212\u5f20\u538b|\u4f4e\u538b|DBP)", True),
        ]
        for key, pattern, as_int in patient_patterns:
            assign_number(key, first_number_after(pattern), as_int=as_int)

        gender = gender_value()
        if gender is not None:
            result["Gender"] = gender

        patterns = [
            ("BMI", r"(?:\bBMI\b|\u4f53\u91cd\u6307\u6570|\u4f53\u8d28\u6307\u6570)\D{0,10}(\d{2}\.\d{1,2}|\d{2})", 1),
            ("WBC", r"(?:\bWBC\b|\u767d\u7ec6\u80de\u8ba1\u6570\s*[\uff08(]?\s*WBC?\s*[\uff09)]?)\D{0,18}(\d{1,2}\.?\d{0,2})", 1),
            ("HGB", r"(?:\bHGB\b|\u8840\u7ea2\u86cb\u767d(?:\u542b\u91cf)?\s*[\uff08(]?\s*HGB?\s*[\uff09)]?)\D{0,18}(\d{2,3}\.?\d{0,2})", 1),
            ("PLT", r"(?:\bPLT\b|\u8840\u5c0f\u677f\u8ba1\u6570\s*[\uff08(]?\s*PLT?\s*[\uff09)]?)\D{0,18}(\d{2,3}\.?\d{0,2})", 1),
            ("ALT", r"(?:\bALT\b|\u8c37\u4e19\u8f6c\u6c28\u9176|\u4e19\u6c28\u9178\u6c28\u57fa\u8f6c\u79fb\u9176)\D{0,10}(\d{1,3}\.?\d{0,2})", 1),
            ("AST", r"(?:\bAST\b|\u8c37\u8349\u8f6c\u6c28\u9176|\u95e8\u51ac\u6c28\u9178\u6c28\u57fa\u8f6c\u79fb\u9176|\u5929\u95e8\u51ac\u6c28\u9178\u6c28\u57fa\u8f6c\u79fb\u9176)\D{0,10}(\d{1,3}\.?\d{0,2})", 1),
            ("GGT", r"(?:\bGGT\b|[\u03b3rR]-?\u8c37\u6c28\u9170\u8f6c\u79fb\u9176|[\u03b3rR]-?\u8c37\u6c28\u9170\u8f6c\u80bd\u9176|\u8c37\u6c28\u9170\u8f6c\u79fb\u9176|\u8c37\u6c28\u9170\u8f6c\u80bd\u9176)\D{0,10}(\d{1,3}\.?\d{0,2})", 1),
            ("ALP", r"(?:\bALP\b|\u78b1\u6027\u78f7\u9178\u9176)\D{0,10}(\d{1,3}\.?\d{0,2})", 1),
            ("Glu", r"(?:\bGLU\b|\bGlu\b|\u8461\u8404\u7cd6|\u8840\u7cd6|\u7a7a\u8179\u8840\u7cd6)\D{0,10}(\d{1,2}\.?\d{0,2})", 1),
            ("HbA1c", r"(?:\bHbA1c\b|\bHbA1C\b|\bA1c\b|\bA1C\b|\bGHb\b|\u7cd6\u5316\u8840\u7ea2\u86cb\u767d(?:A1c)?)\D{0,10}(\d{1,2}\.?\d{0,2})", 1),
            ("TC", r"(?:\u603b\u80c6\u56fa\u9187|(?<![A-Za-z-])TC(?![A-Za-z-]))\D{0,10}(\d{1,2}\.?\d{0,2})", 1),
            ("TG", r"(?:\bTG\b|\u7518\u6cb9\u4e09\u916f)\D{0,10}(\d{1,2}\.?\d{0,2})", 1),
            ("HDL", r"(?:\bHDL-C\b|\bHDL_C\b|\bHDLC\b|\bHDL\b|\u9ad8\u5bc6\u5ea6\u8102\u86cb\u767d\u80c6\u56fa\u9187|\u9ad8\u5bc6\u5ea6\u8102\u86cb\u767d)\D{0,10}(\d{1,2}\.?\d{0,2})", 1),
            ("LDL", r"(?:\bLDL-C\b|\bLDL_C\b|\bLDLC\b|\bLDL\b|\u4f4e\u5bc6\u5ea6\u8102\u86cb\u767d\u80c6\u56fa\u9187|\u4f4e\u5bc6\u5ea6\u8102\u86cb\u767d)\D{0,10}(\d{1,2}\.?\d{0,2})", 1),
            ("Creatinine", r"(?:\bCreatinine\b|\bCREA\b|\bScr\b|\bCr\b|\u808c\u9150|\u8840\u808c\u9150)\D{0,10}(\d{1,3}\.?\d{0,2})", 1),
            ("eGFR", r"(?:\beGFR\b|\bGFR\b|\u4f30\u7b97\u80be\u5c0f\u7403\u6ee4\u8fc7\u7387|\u80be\u5c0f\u7403\u6ee4\u8fc7\u7387)\D{0,10}(\d{1,3}\.?\d{0,2})", 1),
            ("UA", r"(?:\bUA\b|\u5c3f\u9178)\D{0,10}(\d{2,4}\.?\d{0,2})", 1),
        ]

        for key, pattern, group in patterns:
            if key in result:
                continue
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                assign_number(key, match.group(group))

        bp_match = re.search(r"(?:\bBP\b|Blood Pressure|\u8840\u538b)\D{0,10}(\d{2,3})\s*[/\uff0f]\s*(\d{2,3})", text, re.IGNORECASE)
        if bp_match:
            result["SBP"] = int(bp_match.group(1))
            result["DBP"] = int(bp_match.group(2))

        return result

    async def parse_medical_report(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Full Pipeline: Baidu OCR -> Text -> LLM -> JSON Structure
        With Regex Fallback if LLM fails (Task 64)
        """
        # 1. OCR Extraction
        if not OCR_RUNTIME_AVAILABLE:
            return self._build_stored_unprocessed_result(
                "ocr_runtime_unavailable",
                "Document saved, but OCR runtime is unavailable.",
            )

        if not self.ocr_ready or not self.ocr_client:
            return self._build_stored_unprocessed_result(
                "ocr_service_unavailable",
                "Document saved, but OCR provider is unavailable.",
            )

        raw_text = self._get_ocr_text(image_bytes)
        
        if not raw_text:
            return self._build_stored_unprocessed_result(
                "ocr_processing_failed",
                "Document saved, but OCR did not produce usable text.",
            )
        
        # 2. LLM Semantic Parsing with Fallback
        data = None
        extraction_method = "none"
        
        if self.client:
            try:
                logger.info("Sending OCR text to LLM for parsing...")
                data = await self._call_llm_for_parsing(raw_text)
                extraction_method = "llm"
            except (RetryError, RateLimitError, APIStatusError) as e:
                logger.warning(f"LLM extraction failed: {e}. Using regex fallback.")
                data = self._extract_by_regex(raw_text)
                extraction_method = "regex_fallback"
            except Exception as e:
                logger.error(f"LLM unexpected error: {e}. Using regex fallback.")
                data = self._extract_by_regex(raw_text)
                extraction_method = "regex_fallback"
        else:
            # No LLM configured, use regex directly
            logger.info("LLM not configured. Using regex extraction.")
            data = self._extract_by_regex(raw_text)
            extraction_method = "regex_only"
        
        # 3. Build Response
        if data and has_structured_ocr_summary_data(data):
            return {
                "status": "success",
                "message": f"Medical record parsed successfully via {extraction_method}.",
                "raw_text": raw_text,
                "extraction_method": extraction_method,
                "data": data,
                "ocr_processing_status": self._build_processing_status(
                    status="success",
                    reason=None,
                    structured_data_present=True,
                    raw_text_present=True,
                ),
            }
        else:
            return {
                "status": "partial_success",
                "message": "OCR completed but no structured data extracted.",
                "raw_text": raw_text,
                "extraction_method": extraction_method,
                "data": data or {},
                "ocr_processing_status": self._build_processing_status(
                    status="partial_success",
                    reason="structured_data_incomplete",
                    structured_data_present=bool(data),
                    raw_text_present=True,
                ),
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(APIStatusError),
        before_sleep=lambda retry_state: logger.warning(f"LLM API Error, retrying... (Attempt {retry_state.attempt_number})")
    )
    async def _call_llm_for_parsing(self, ocr_text: str) -> Dict[str, Any]:
        """
        Call Kimi/OpenAI to extract JSON structure.
        With retry mechanism for API errors (429 Engine Overloaded, etc.)
        """
        system_prompt = """
You are a medical-report structuring assistant. Extract structured health data from OCR text.
Return pure JSON only. Do not wrap the response in Markdown.

Core scalar fields, when present:
- Age, Gender, Height, Weight

Core metric fields, when present:
- BMI, SBP, DBP
- WBC, HGB, PLT
- ALT, AST, GGT, ALP
- Glu, HbA1c, TC, TG, HDL, LDL, UA, Creatinine, eGFR, KET

For Age/Gender/Height/Weight, return a simple value.
For every metric/lab/vital field, return an object:
{"value": number_or_string, "unit": string_or_null, "ref_range": string_or_null, "hospital_flag": string_or_null}

Use common aliases:
- SBP/DBP: systolic/diastolic or high/low blood pressure values.
- Glu: glucose, fasting glucose, blood glucose, GLU.
- HbA1c: HbA1c, HbA1C, A1c, glycosylated hemoglobin.
- HDL/LDL: HDL-C and LDL-C.
- Creatinine: creatinine, Cr, CREA, Scr.
- eGFR: eGFR or GFR.

Put detected non-core measurements under extra_findings using the same object shape.
Do not infer missing values. Use null when unavailable.
"""
        # [DEBUG] Print Full Prompt Context

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ocr_text}
            ]
            # Task 66: Removed temperature, response_format for Kimi k2.5 compatibility
        )

        content = response.choices[0].message.content.strip()
        
        # [DEBUG] Print Raw LLM Response

        # Task 66: Clean <think>...</think> tags (Kimi k2.5 Thinking Mode)
        content_cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

        # 1. Clean Markdown Code Blocks
        cleaned_content = content_cleaned.replace("```json", "").replace("```", "").strip()

        try:
            # 2. Try Direct Parsing
            parsed_json = json.loads(cleaned_content)
        except json.JSONDecodeError:
            # 3. Regex Fallback
            logger.warning("JSON Decode Failed for LLM response. Trying Regex Fallback...")
            match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
            if match:
                try:
                    parsed_json = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.error(f"Regex Fallback also failed for content: {cleaned_content}")
                    return {} # Return empty dict on total failure
            else:
                 logger.error(f"No JSON found in LLM response: {cleaned_content}")
                 return {} # Return empty on failure
            
        return parsed_json

_medical_ocr_service: Optional[MedicalOCRService] = None


def get_medical_ocr_service() -> MedicalOCRService:
    global _medical_ocr_service
    if _medical_ocr_service is None:
        _medical_ocr_service = MedicalOCRService()
    return _medical_ocr_service


class _MedicalOCRServiceProxy:
    def __getattr__(self, item):
        return getattr(get_medical_ocr_service(), item)


medical_ocr_service = _MedicalOCRServiceProxy()
