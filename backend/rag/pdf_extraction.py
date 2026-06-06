from __future__ import annotations

import base64
import json
import logging
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.core.config import settings

logger = logging.getLogger(__name__)

# 中文注释：本模块负责 PDF 文本提取与 OCR 兜底，不承担向量化或检索逻辑。
DEFAULT_OCR_PAGE_LIMIT = 10
DEFAULT_OCR_DPI = 200
LOW_TEXT_DENSITY_PAGE_CHAR_THRESHOLD = 15
BAIDU_OCR_API_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
BAIDU_OCR_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"


def _import_langchain_pypdf_loader():
    from langchain_community.document_loaders import PyPDFLoader

    return PyPDFLoader


def _normalize_text(value: object) -> str:
    """中文说明：_normalize_text 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(value, str):
        return ""
    return value.replace("\x0c", "").strip()


_SECTION_TITLE_PATTERNS = (
    re.compile(r"^\s*#{1,6}\s*(?P<title>.+?)\s*$"),
    re.compile(
        r"^\s*第\s*[一二三四五六七八九十百千0-9]+(?:\.[一二三四五六七八九十百千0-9]+)*\s*[章节编部篇卷部分节]\s*[：:、.\-]?\s*(?P<title>.+?)\s*$"
    ),
    re.compile(r"^\s*[（(]?[一二三四五六七八九十百千]+[)）]?[、.．:：-]\s*(?P<title>.+?)\s*$"),
    re.compile(r"^\s*(?:chapter|section|part)\s+\d+(?:\.\d+)*\s*[：:、.\-]?\s*(?P<title>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:\d+(?:\.\d+){0,3}|[（(]?\d+[)）]?)\s*[：:、.\-]\s*(?P<title>.+?)\s*$"),
)


def _sanitize_section_title(value: object) -> Optional[str]:
    """中文说明：_sanitize_section_title 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    text = _normalize_text(value)
    if not text:
        return None

    cleaned = text.strip(" \t\r\n。！？；：:、,，.·-—")
    if not cleaned or len(cleaned) > 80:
        return None
    if any(ch in cleaned for ch in "\n\r\t"):
        return None
    if cleaned[-1] in "。！？；：:、,，.!?":
        return None
    return cleaned


def _contains_cjk_characters(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def _extract_section_title_from_text(page_content: str) -> Optional[str]:
    """中文说明：_extract_section_title_from_text 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not isinstance(page_content, str):
        return None

    lines = [line.strip() for line in page_content.splitlines() if line and line.strip()]
    if not lines:
        return None

    for candidate_line in lines[:3]:
        if len(candidate_line) > 120:
            continue

        for pattern in _SECTION_TITLE_PATTERNS:
            match = pattern.match(candidate_line)
            if not match:
                continue

            candidate = _sanitize_section_title(match.group("title"))
            if candidate:
                return candidate

    if len(lines) == 1:
        candidate = _sanitize_section_title(lines[0])
        if (
            candidate
            and len(candidate) <= 60
            and _contains_cjk_characters(candidate)
            and not any(punct in lines[0] for punct in "。！？；：:、,，.!?")
        ):
            return candidate

    return None


def resolve_section_title(source_metadata: dict, page_content: str) -> Optional[str]:
    """中文说明：resolve_section_title 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    for key in ("section_title", "title"):
        section_title = _sanitize_section_title(source_metadata.get(key))
        if section_title:
            return section_title

    return _extract_section_title_from_text(page_content)


def _normalize_page_bound(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if re.fullmatch(r"\d+", text):
            return int(text)
    return None


def resolve_page_range(source_metadata: dict) -> Optional[str]:
    """中文说明：resolve_page_range 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    page_range = source_metadata.get("page_range")
    if isinstance(page_range, (list, tuple)) and len(page_range) == 2:
        start_page = _normalize_page_bound(page_range[0])
        end_page = _normalize_page_bound(page_range[1])
        if start_page is None or end_page is None or end_page <= start_page:
            return None
        return f"{start_page}-{end_page}"

    if isinstance(page_range, str):
        normalized = page_range.strip()
        if not normalized:
            return None
        if "-" in normalized:
            start_page_text, end_page_text = [part.strip() for part in normalized.split("-", 1)]
            start_page = _normalize_page_bound(start_page_text)
            end_page = _normalize_page_bound(end_page_text)
            if start_page is not None and end_page is not None and end_page > start_page:
                return f"{start_page}-{end_page}"
        return None

    start_page = _normalize_page_bound(source_metadata.get("start_page"))
    end_page = _normalize_page_bound(source_metadata.get("end_page"))
    if start_page is not None and end_page is not None and end_page > start_page:
        return f"{start_page}-{end_page}"

    return None


def _has_meaningful_text(value: object) -> bool:
    return bool(_normalize_text(value))


def _is_low_text_density(value: object) -> bool:
    text = _normalize_text(value)
    if not text:
        return True
    return len("".join(text.split())) <= LOW_TEXT_DENSITY_PAGE_CHAR_THRESHOLD


def _resolve_page_number(document_index: int) -> int:
    return document_index + 1


def _build_pypdf_loader_factory() -> Callable[[str], Any]:
    """中文说明：_build_pypdf_loader_factory 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    def _loader_factory(file_path: str):
        try:
            from pypdf import PdfReader
        except Exception as exc:
            logger.error("No PDF loader available for %s: %s", file_path, exc)

            class _EmptyLoader:
                def load(self):
                    return []

            return _EmptyLoader()

        class _PypdfLoader:
            def __init__(self, file_path: str):
                self.file_path = file_path

            def load(self):
                reader = PdfReader(self.file_path)
                documents = []
                for page_index, page in enumerate(reader.pages, start=1):
                    documents.append(
                        SimpleNamespace(
                            page_content=page.extract_text() or "",
                            metadata={"source": self.file_path, "page": page_index},
                        )
                    )
                return documents

        return _PypdfLoader(file_path)

    return _loader_factory


@lru_cache(maxsize=1)
def resolve_pdf_loader_factory() -> Callable[[str], Any]:
    # 中文注释：优先使用 langchain loader；不可用时回退到 pypdf，避免硬依赖阻塞流程。
    """中文说明：resolve_pdf_loader_factory 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    try:
        loader_cls = _import_langchain_pypdf_loader()
    except Exception:
        logger.warning("PyPDFLoader unavailable; using pypdf fallback for this process.")
        return _build_pypdf_loader_factory()

    return lambda file_path, _loader=loader_cls: _loader(file_path)


def describe_ocr_fallback_capability() -> dict[str, Any]:
    # 中文注释：只描述当前进程能力，不在此处触发网络调用或重试副作用。
    """中文说明：describe_ocr_fallback_capability 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    pdftoppm_available = shutil.which("pdftoppm") is not None
    ocr_credentials_available = bool(
        settings.BAIDU_APP_ID and settings.BAIDU_API_KEY and settings.BAIDU_SECRET_KEY
    )
    missing_prerequisites = []
    if not pdftoppm_available:
        missing_prerequisites.append("pdftoppm")
    if not ocr_credentials_available:
        missing_prerequisites.append("baidu_ocr_credentials")

    return {
        "available": pdftoppm_available and ocr_credentials_available,
        "pdftoppm_available": pdftoppm_available,
        "ocr_credentials_available": ocr_credentials_available,
        "network_assumption_state": "assumed_available",
        "missing_prerequisites": missing_prerequisites,
    }


def format_ocr_fallback_capability_summary(summary: dict[str, Any]) -> str:
    missing_prerequisites = summary.get("missing_prerequisites") or []
    missing = ", ".join(str(item) for item in missing_prerequisites) if missing_prerequisites else "none"
    return (
        "OCR fallback capability: "
        f"available={summary.get('available', False)} "
        f"pdftoppm_available={summary.get('pdftoppm_available', False)} "
        f"ocr_credentials_available={summary.get('ocr_credentials_available', False)} "
        f"network_assumption_state={summary.get('network_assumption_state', 'assumed_available')} "
        f"missing_prerequisites={missing}"
    )


def _load_documents_with_pypdf(file_path: str) -> list[Any]:
    loader_factory = resolve_pdf_loader_factory()
    loader = loader_factory(file_path)
    return list(loader.load())


def _render_pdf_page_to_png_bytes(file_path: str, page_number: int, dpi: int = DEFAULT_OCR_DPI) -> bytes:
    """中文说明：_render_pdf_page_to_png_bytes 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        logger.info("pdftoppm is unavailable; skipping OCR render for %s page %s", file_path, page_number)
        return b""

    with tempfile.TemporaryDirectory() as temp_dir:
        output_prefix = Path(temp_dir) / "page"
        command = [
            pdftoppm,
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-singlefile",
            "-r",
            str(dpi),
            "-png",
            file_path,
            str(output_prefix),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning(
                "pdftoppm failed for %s page %s: %s",
                file_path,
                page_number,
                (result.stderr or result.stdout).strip(),
            )
            return b""

        image_path = output_prefix.with_suffix(".png")
        if not image_path.exists():
            logger.warning("pdftoppm did not produce an image for %s page %s", file_path, page_number)
            return b""

        return image_path.read_bytes()


def _build_baidu_access_token() -> Optional[str]:
    """中文说明：_build_baidu_access_token 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    if not (settings.BAIDU_APP_ID and settings.BAIDU_API_KEY and settings.BAIDU_SECRET_KEY):
        return None

    token_url = (
        f"{BAIDU_OCR_TOKEN_URL}?"
        + urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": settings.BAIDU_API_KEY,
                "client_secret": settings.BAIDU_SECRET_KEY,
            }
        )
    )
    request = Request(token_url, method="GET")
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("access_token")
    return token if isinstance(token, str) and token else None


@lru_cache(maxsize=1)
def _get_baidu_access_token() -> Optional[str]:
    try:
        return _build_baidu_access_token()
    except Exception as exc:
        logger.warning("Baidu OCR access token unavailable: %s", exc)
        return None


def _ocr_page_with_baidu(file_path: str, page_number: int) -> str:
    """中文说明：_ocr_page_with_baidu 的职责与边界以当前实现为准，调用方应遵循现有输入输出约定。"""
    image_bytes = _render_pdf_page_to_png_bytes(file_path, page_number)
    if not image_bytes:
        return ""

    access_token = _get_baidu_access_token()
    if not access_token:
        return ""

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    request = Request(
        f"{BAIDU_OCR_API_URL}?access_token={access_token}",
        data=urlencode(
            {
                "image": image_b64,
                "detect_direction": "true",
            }
        ).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error_code"):
        logger.warning(
            "Baidu OCR returned an error for %s page %s: %s",
            file_path,
            page_number,
            payload,
        )
        return ""

    words_result = payload.get("words_result") or []
    if not isinstance(words_result, list):
        return ""

    lines: list[str] = []
    for item in words_result:
        if not isinstance(item, dict):
            continue
        word = item.get("words")
        if isinstance(word, str) and word.strip():
            lines.append(word.strip())
    return "\n".join(lines).strip()


def _default_ocr_text_extractor(file_path: str, page_number: int) -> str:
    return _ocr_page_with_baidu(file_path, page_number)


def load_pdf_documents_with_ocr_fallback(
    file_path: str,
    *,
    loader_factory: Callable[[str], Any] | None = None,
    ocr_text_extractor: Callable[[str, int], str] | None = None,
    ocr_page_limit: int = DEFAULT_OCR_PAGE_LIMIT,
) -> list[Any]:
    # 中文注释：仅对前 N 页执行 OCR 兜底，控制耗时并避免大文件放大延迟。
    loader = loader_factory(file_path) if loader_factory is not None else None
    documents = list(loader.load()) if loader is not None else _load_documents_with_pypdf(file_path)

    if not documents:
        return documents

    text_extractor = ocr_text_extractor or _default_ocr_text_extractor
    if text_extractor is None:
        return documents

    for document_index, document in enumerate(documents):
        if document_index >= ocr_page_limit:
            break

        page_content = getattr(document, "page_content", "")
        # 中文注释：页面已有足量文本时跳过 OCR，避免重复识别与额外成本。
        if _has_meaningful_text(page_content) and not _is_low_text_density(page_content):
            continue

        page_number = _resolve_page_number(document_index)
        extracted_text = _normalize_text(text_extractor(file_path, page_number))
        if extracted_text:
            document.page_content = extracted_text
            metadata = getattr(document, "metadata", None)
            if isinstance(metadata, dict):
                metadata["ocr_touched"] = True

    return documents
