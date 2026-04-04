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
        Task 64: Regex Fallback Extraction
        When LLM fails, extract core metrics using regex patterns.
        """
        result = {}
        
        # Define patterns: (key, regex_pattern, group_index)
        patterns = [
            ('BMI', r'(?:BMI|体重指数|体质指数)\D{0,6}(\d{2}\.?\d{0,2})', 1),
            ('WBC', r'(?:WBC|白细胞)\D{0,10}(\d{1,2}\.?\d{0,2})', 1),
            ('HGB', r'(?:HGB|血红蛋白)\D{0,10}(\d{2,3})', 1),
            ('PLT', r'(?:PLT|血小板)\D{0,10}(\d{2,3})', 1),
            ('ALT', r'(?:ALT|谷丙转氨酶|丙氨酸氨基转移酶)\D{0,10}(\d{1,3})', 1),
            ('AST', r'(?:AST|谷草转氨酶)\D{0,10}(\d{1,3})', 1),
            ('GGT', r'(?:GGT|谷氨酰转肽酶|r-谷氨酰转肽酶)\D{0,10}(\d{1,3})', 1),
            ('Glu', r'(?:Glu|GLU|葡萄糖|空腹血糖|血糖)\D{0,10}(\d{1,2}\.?\d{0,2})', 1),
            ('TC', r'(?:TC|总胆固醇)\D{0,10}(\d{1,2}\.?\d{0,2})', 1),
            ('TG', r'(?:TG|甘油三酯)\D{0,10}(\d{1,2}\.?\d{0,2})', 1),
            ('UA', r'(?:UA|尿酸)\D{0,10}(\d{2,4})', 1),
        ]
        
        for key, pattern, group in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result[key] = float(match.group(group))
                except:
                    pass
        
        # Blood Pressure: Extract SBP/DBP from format like "120/80"
        bp_match = re.search(r'血压\D{0,10}(\d{2,3})\s*[/／]\s*(\d{2,3})', text)
        if bp_match:
            try:
                result['SBP'] = int(bp_match.group(1))
                result['DBP'] = int(bp_match.group(2))
            except:
                pass
        
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
        before_sleep=lambda retry_state: logger.warning(f"⚠️ LLM API Error, retrying... (Attempt {retry_state.attempt_number})")
    )
    async def _call_llm_for_parsing(self, ocr_text: str) -> Dict[str, Any]:
        """
        Call Kimi/OpenAI to extract JSON structure.
        With retry mechanism for API errors (429 Engine Overloaded, etc.)
        """
        system_prompt = (
            "你是一个专业的医疗数据结构化助手。请根据 OCR 文本提取生理指标。\n"
            "\n"
            "**Task 87: 新输出格式**\n"
            "每个指标的 Value 不再是纯数字，而是一个对象：\n"
            "```json\n"
            "\"WBC\": {\n"
            "    \"value\": 6.39,\n"
            "    \"unit\": \"10^9/L\",\n"
            "    \"ref_range\": \"3.5-9.5\",\n"
            "    \"hospital_flag\": null\n"
            "}\n"
            "```\n"
            "- **value**: 检测值（数字或字符串，如酮体的'+/-'）\n"
            "- **unit**: 单位（如 mmol/L, g/L, %）\n"
            "- **ref_range**: 参考范围（如 '3.5-9.5', '0-40'），如未找到则为 null\n"
            "- **hospital_flag**: 如果体检单明确标记了 'H', 'L', '↑', '↓', '+', '阳性', '偏高', '偏低'，填在这里；否则为 null\n"
            "\n"
            "**关键映射规则 (必须严格遵守)**：\n"
            "请在文本中寻找以下中文指标，并提取其数值存入对应的 JSON Key：\n"
            "\n"
            "--- 基础信息 (这些仅返回简单值，不需要对象格式) ---\n"
            "*   **Age** <== 寻找 \"年龄\", \"Age\" (只返回数字，如 45)\n"
            "*   **Gender** <== 寻找 \"性别\", \"Gender\" (返回 1 表示男性, 2 表示女性)\n"
            "*   **Height** <== 寻找 \"身高\" (转换为 cm，只保留数字)\n"
            "*   **Weight** <== 寻找 \"体重\" (转换为 kg，只保留数字)\n"
            "\n"
            "--- 身体指标 (使用对象格式) ---\n"
            "*   **BMI** <== 寻找 \"体重指数\", \"BMI\", \"体质指数\"\n"
            "*   **SBP** <== 寻找 \"收缩压\", \"高压\" (通常在血压组的前面)\n"
            "*   **DBP** <== 寻找 \"舒张压\", \"低压\" (通常在血压组的后面)\n"
            "\n"
            "--- 血常规 (使用对象格式) ---\n"
            "*   **WBC** <== 寻找 \"白细胞\", \"白细胞计数\", \"WBC\"\n"
            "*   **NEUT_PERCENT** <== 寻找 \"中性粒细胞百分比\", \"中性粒细胞%\"\n"
            "*   **LYM_PERCENT** <== 寻找 \"淋巴细胞百分比\", \"淋巴细胞%\"\n"
            "*   **HGB** <== 寻找 \"血红蛋白\", \"HGB\"\n"
            "*   **PLT** <== 寻找 \"血小板\", \"PLT\"\n"
            "\n"
            "--- 肝功能 (使用对象格式) ---\n"
            "*   **ALT** <== 寻找 \"谷丙转氨酶\", \"丙氨酸氨基转移酶\"\n"
            "*   **AST** <== 寻找 \"谷草转氨酶\", \"天门冬氨酸氨基转移酶\"\n"
            "*   **GGT** <== 寻找 \"r-谷氨酰转肽酶\", \"GGT\", \"谷氨酰转移酶\"\n"
            "*   **ALP** <== 寻找 \"碱性磷酸酶\", \"ALP\"\n"
            "\n"
            "--- 代谢指标 (使用对象格式) ---\n"
            "*   **Glu** <== 寻找 \"葡萄糖\", \"血糖\", \"空腹血糖\", \"GLU\"\n"
            "*   **TC** <== 寻找 \"总胆固醇\", \"TC\"\n"
            "*   **TG** <== 寻找 \"甘油三酯\", \"TG\"\n"
            "*   **HDL** <== 寻找 \"高密度脂蛋白\", \"HDL-C\"\n"
            "*   **LDL** <== 寻找 \"低密度脂蛋白\", \"LDL-C\"\n"
            "*   **UA** <== 寻找 \"尿酸\", \"UA\"\n"
            "*   **Creatinine** <== 寻找 \"肌酐\", \"Cr\", \"CREA\"\n"
            "*   **eGFR** <== 寻找 \"肾小球滤过率\", \"eGFR\"\n"
            "*   **HbA1c** <== 寻找 \"糖化血红蛋白\", \"HbA1c\"\n"
            "*   **KET** <== 寻找 \"酮体\", \"尿酮体\", \"KET\"\n"
            "\n"
            "**输出要求**：\n"
            "1. 返回纯 JSON（不要 Markdown 代码块）。\n"
            "2. 基础信息 (Age, Gender, Height, Weight) 只返回简单值。\n"
            "3. 其他所有生化/血常规指标使用对象格式 {value, unit, ref_range, hospital_flag}。\n"
            "4. 如果未找到某项，对应 Key 的值为 null。\n"
            "5. **extra_findings**: 将文中提到但不在上述核心指标列表中的其他所有检测项，以对象格式存入此字段。\n"
        )

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
