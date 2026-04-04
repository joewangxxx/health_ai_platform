from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Optional

from backend.rag.benchmark_diagnostics import summarize_document_density
from backend.rag.pdf_extraction import (
    describe_ocr_fallback_capability,
    format_ocr_fallback_capability_summary,
    load_pdf_documents_with_ocr_fallback,
    resolve_pdf_loader_factory,
    resolve_page_range,
    resolve_section_title,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent / "docs"
RAG_CHUNK_SIZE = 800
RAG_CHUNK_OVERLAP = 120
RAG_CHUNK_SEPARATORS = ["\n\n", "\n", "。", "；", "：", "，", " ", ""]

_HEADING_PATTERNS = (
    re.compile(r"^\s*#{1,6}\s*(?P<title>.+?)\s*$"),
    re.compile(r"^\s*(?:[一二三四五六七八九十百千0-9]+(?:[、.．])?)\s*(?P<title>.+?)\s*$"),
)


@dataclass
class ChunkRecord:
    source: str
    page: Optional[int]
    chunk_index: int
    text: str
    metadata: dict[str, Any]


def _normalize_text(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _extract_section_title_from_text(page_content: str) -> Optional[str]:
    if not isinstance(page_content, str):
        return None

    for raw_line in page_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if len(line) > 120:
            return None

        for pattern in _HEADING_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            candidate = match.group("title").strip(" \t\r\n。；：:-")
            if candidate and len(candidate) <= 80:
                return candidate
        break

    return None


def _resolve_section_title(source_metadata: dict, page_content: str) -> Optional[str]:
    for key in ("section_title", "title"):
        section_title = _normalize_text(source_metadata.get(key))
        if section_title:
            return section_title
    return _extract_section_title_from_text(page_content)


def _build_chunk_metadata(
    source_metadata: dict,
    chunk_index: int,
    page_content: str,
    *,
    section_title: Optional[str] = None,
) -> dict:
    chunk_metadata = {}

    source = source_metadata.get("source")
    if source is not None:
        chunk_metadata["source"] = source

    page = source_metadata.get("page")
    if page is not None:
        chunk_metadata["page"] = page

    chunk_metadata["chunk_index"] = chunk_index

    resolved_section_title = _normalize_text(section_title) or resolve_section_title(source_metadata, page_content)
    if resolved_section_title:
        chunk_metadata["section_title"] = resolved_section_title

    page_range = resolve_page_range(source_metadata)
    if page_range:
        chunk_metadata["page_range"] = page_range

    return chunk_metadata


def _split_text_by_rules(text: str) -> list[str]:
    normalized = text or ""
    if not normalized:
        return [""]
    if len(normalized) <= RAG_CHUNK_SIZE:
        return [normalized]

    for separator in RAG_CHUNK_SEPARATORS[:-1]:
        if separator and separator in normalized:
            parts = [part for part in normalized.split(separator) if part]
            if len(parts) > 1:
                merged: list[str] = []
                current = ""
                for part in parts:
                    candidate = part if not current else f"{current}{separator}{part}"
                    if len(candidate) <= RAG_CHUNK_SIZE:
                        current = candidate
                        continue
                    if current:
                        merged.append(current)
                    current = part
                if current:
                    merged.append(current)
                if merged:
                    return merged

    chunks = []
    start = 0
    step = max(1, RAG_CHUNK_SIZE - RAG_CHUNK_OVERLAP)
    while start < len(normalized):
        chunk = normalized[start : start + RAG_CHUNK_SIZE]
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks or [normalized]


def _split_documents_with_metadata(documents: Iterable[Any]) -> list[Any]:
    splits = []
    for document in documents:
        document_metadata = dict(getattr(document, "metadata", {}) or {})
        page_content = getattr(document, "page_content", "") or ""
        document_section_title = resolve_section_title(document_metadata, page_content)
        split_texts = _split_text_by_rules(page_content)
        for chunk_index, split_text in enumerate(split_texts):
            chunk_metadata = dict(document_metadata)
            chunk_metadata.update(
                _build_chunk_metadata(
                    document_metadata,
                    chunk_index,
                    split_text,
                    section_title=document_section_title,
                )
            )
            try:
                chunk = document.__class__(page_content=split_text, metadata=chunk_metadata)
            except Exception:
                try:
                    chunk = document.__class__(split_text, chunk_metadata)
                except Exception:
                    chunk = SimpleNamespace(page_content=split_text, metadata=chunk_metadata)
            splits.append(chunk)
    return splits


def iter_rag_corpus_pdf_files(corpus_dir: Path | str | None = None) -> list[Path]:
    corpus_path = Path(corpus_dir) if corpus_dir is not None else DEFAULT_CORPUS_DIR
    if not corpus_path.exists():
        return []
    return sorted((path for path in corpus_path.iterdir() if path.suffix.lower() == ".pdf"), key=lambda p: p.name.lower())


def _is_metadata_floor_present(metadata: dict[str, Any]) -> bool:
    return all(metadata.get(key) is not None for key in ("source", "page", "chunk_index"))


def _coverage(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _summarize_chunks(chunks: list[Any]) -> dict[str, Any]:
    chunk_lengths = [len(getattr(chunk, "page_content", "") or "") for chunk in chunks]
    metadata_list = [dict(getattr(chunk, "metadata", {}) or {}) for chunk in chunks]
    total_chunks = len(chunks)
    section_title_hits = sum(1 for metadata in metadata_list if metadata.get("section_title") is not None)
    page_range_hits = sum(1 for metadata in metadata_list if metadata.get("page_range") is not None)
    metadata_floor_hits = sum(1 for metadata in metadata_list if _is_metadata_floor_present(metadata))

    return {
        "chunk_count": total_chunks,
        "average_chunk_size": round(mean(chunk_lengths), 4) if chunk_lengths else 0.0,
        "max_chunk_size": max(chunk_lengths) if chunk_lengths else 0,
        "section_title_coverage": _coverage(section_title_hits, total_chunks),
        "page_range_coverage": _coverage(page_range_hits, total_chunks),
        "metadata_floor_coverage": _coverage(metadata_floor_hits, total_chunks),
    }


def _qa_usefulness_score(doc_summary: dict[str, Any], density_summary: dict[str, Any]) -> float:
    if doc_summary.get("chunk_count", 0) <= 0:
        return 0.0
    if doc_summary.get("metadata_floor_coverage", 0.0) <= 0.0:
        return 0.0

    score = 0.35
    score += 0.35 * float(doc_summary.get("section_title_coverage", 0.0))
    score += 0.15 * float(doc_summary.get("page_range_coverage", 0.0))

    if density_summary.get("low_density"):
        score -= 0.10
    else:
        score += 0.15

    if int(density_summary.get("ocr_touched_page_count") or 0) > 0:
        score += 0.10

    return round(max(0.0, min(1.0, score)), 4)


def _qa_usefulness_label(score: float) -> str:
    if score >= 0.75:
        return "strong"
    if score >= 0.45:
        return "mixed"
    if score > 0:
        return "weak"
    return "empty"


def build_rag_live_corpus_benchmark(
    corpus_dir: Path | str | None = None,
    loader_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    corpus_path = Path(corpus_dir) if corpus_dir is not None else DEFAULT_CORPUS_DIR
    ocr_fallback_capability = describe_ocr_fallback_capability()
    default_loader_factory = loader_factory or resolve_pdf_loader_factory()

    pdf_files = iter_rag_corpus_pdf_files(corpus_path)
    document_reports: list[dict[str, Any]] = []
    load_failures: list[dict[str, str]] = []
    loaded_documents: list[Any] = []
    all_chunks: list[Any] = []

    for pdf_path in pdf_files:
        try:
            documents = load_pdf_documents_with_ocr_fallback(
                str(pdf_path),
                loader_factory=default_loader_factory,
            )
        except Exception as exc:
            load_failures.append({"source": str(pdf_path), "error": str(exc)})
            continue

        loaded_documents.extend(documents)
        chunks = _split_documents_with_metadata(documents)
        all_chunks.extend(chunks)

        doc_summary = _summarize_chunks(chunks)
        density_summary = summarize_document_density(documents, chunks)
        qa_usefulness_score = _qa_usefulness_score(doc_summary, density_summary)
        document_reports.append(
            {
                "source": str(pdf_path),
                "page_count": len(documents),
                **doc_summary,
                **density_summary,
                "qa_usefulness_score": qa_usefulness_score,
                "qa_usefulness": _qa_usefulness_label(qa_usefulness_score),
            }
        )

    low_density_document_count = sum(1 for document in document_reports if document["low_density"])
    section_title_document_coverage = _coverage(
        sum(1 for document in document_reports if document["section_title_coverage"] > 0),
        len(document_reports),
    )
    page_range_document_coverage = _coverage(
        sum(1 for document in document_reports if document["page_range_coverage"] > 0),
        len(document_reports),
    )
    corpus_qa_usefulness_score = round(
        mean([document["qa_usefulness_score"] for document in document_reports]), 4
    ) if document_reports else 0.0
    report = {
        "corpus_dir": str(corpus_path),
        "document_count": len(document_reports),
        "page_count": len(loaded_documents),
        "chunk_count": len(all_chunks),
        "average_chunk_size": round(mean([len(getattr(chunk, "page_content", "") or "") for chunk in all_chunks]), 4)
        if all_chunks
        else 0.0,
        "max_chunk_size": max((len(getattr(chunk, "page_content", "") or "") for chunk in all_chunks), default=0),
        "section_title_coverage": _coverage(
            sum(1 for chunk in all_chunks if getattr(chunk, "metadata", {}).get("section_title") is not None),
            len(all_chunks),
        ),
        "section_title_document_coverage": section_title_document_coverage,
        "page_range_coverage": _coverage(
            sum(1 for chunk in all_chunks if getattr(chunk, "metadata", {}).get("page_range") is not None),
            len(all_chunks),
        ),
        "page_range_document_coverage": page_range_document_coverage,
        "metadata_floor_coverage": _coverage(
            sum(1 for chunk in all_chunks if _is_metadata_floor_present(dict(getattr(chunk, "metadata", {}) or {}))),
            len(all_chunks),
        ),
        "low_density_document_count": low_density_document_count,
        "qa_usefulness_score": corpus_qa_usefulness_score,
        "qa_usefulness": _qa_usefulness_label(corpus_qa_usefulness_score),
        "documents": document_reports,
        "load_failures": load_failures,
        "vector_store_writes": 0,
        "ocr_fallback_capability": ocr_fallback_capability,
        "split_profile": {
            "chunk_size": RAG_CHUNK_SIZE,
            "chunk_overlap": RAG_CHUNK_OVERLAP,
            "separators": RAG_CHUNK_SEPARATORS,
        },
    }
    return report


def main() -> None:
    print(format_ocr_fallback_capability_summary(describe_ocr_fallback_capability()), file=sys.stderr)
    report = build_rag_live_corpus_benchmark()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
