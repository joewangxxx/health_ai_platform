from __future__ import annotations

from statistics import mean
from typing import Any, Iterable


EXTREMELY_SHORT_CHUNK_THRESHOLD = 40
LOW_DENSITY_AVERAGE_CHUNK_SIZE_THRESHOLD = 40
LOW_DENSITY_BLANK_PAGE_RATIO_THRESHOLD = 0.5
LOW_DENSITY_SHORT_CHUNK_RATIO_THRESHOLD = 0.5


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _page_text(document: Any) -> str:
    return getattr(document, "page_content", "") or ""


def _page_metadata(document: Any) -> dict[str, Any]:
    return dict(getattr(document, "metadata", {}) or {})


def _is_blank_page(document: Any) -> bool:
    return not _normalize_text(_page_text(document))


def _is_ocr_touched(document: Any) -> bool:
    metadata = _page_metadata(document)
    return bool(metadata.get("ocr_touched"))


def _chunk_length(chunk: Any) -> int:
    return len(_page_text(chunk))


def _coverage(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def summarize_document_density(documents: Iterable[Any], chunks: Iterable[Any]) -> dict[str, Any]:
    document_list = list(documents)
    chunk_list = list(chunks)

    page_count = len(document_list)
    chunk_count = len(chunk_list)
    chunk_lengths = [_chunk_length(chunk) for chunk in chunk_list]

    blank_page_count = sum(1 for document in document_list if _is_blank_page(document))
    ocr_touched_page_count = sum(1 for document in document_list if _is_ocr_touched(document))
    extremely_short_chunk_count = sum(
        1
        for chunk_length in chunk_lengths
        if chunk_length <= EXTREMELY_SHORT_CHUNK_THRESHOLD
    )

    blank_page_ratio = _coverage(blank_page_count, page_count)
    extremely_short_chunk_ratio = _coverage(extremely_short_chunk_count, chunk_count)
    average_chunk_size = round(mean(chunk_lengths), 4) if chunk_lengths else 0.0

    density_reasons: list[str] = []
    if blank_page_ratio >= LOW_DENSITY_BLANK_PAGE_RATIO_THRESHOLD and blank_page_count > 0:
        density_reasons.append(f"blank_page_ratio>={LOW_DENSITY_BLANK_PAGE_RATIO_THRESHOLD}")
    if extremely_short_chunk_ratio >= LOW_DENSITY_SHORT_CHUNK_RATIO_THRESHOLD and extremely_short_chunk_count > 0:
        density_reasons.append(f"extremely_short_chunk_ratio>={LOW_DENSITY_SHORT_CHUNK_RATIO_THRESHOLD}")
    if not density_reasons and average_chunk_size < LOW_DENSITY_AVERAGE_CHUNK_SIZE_THRESHOLD:
        density_reasons.append(f"average_chunk_size<{LOW_DENSITY_AVERAGE_CHUNK_SIZE_THRESHOLD}")

    low_density = bool(density_reasons)

    return {
        "blank_page_count": blank_page_count,
        "blank_page_ratio": blank_page_ratio,
        "ocr_touched_page_count": ocr_touched_page_count,
        "extremely_short_chunk_count": extremely_short_chunk_count,
        "extremely_short_chunk_ratio": extremely_short_chunk_ratio,
        "density_status": "low_density" if low_density else "normal",
        "low_density": low_density,
        "density_reasons": density_reasons,
    }
