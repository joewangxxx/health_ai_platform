import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.rag.pdf_extraction import (
    describe_ocr_fallback_capability,
    format_ocr_fallback_capability_summary,
    load_pdf_documents_with_ocr_fallback,
    resolve_pdf_loader_factory,
    resolve_page_range,
    resolve_section_title,
)
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Build PDF guidelines from backend/rag/docs into the Chroma vector store.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")
VECTOR_STORE_BACKUP_DIR = str(REPO_ROOT / ".tmp" / "rag-vector-store-backups")
RAG_CHUNK_SIZE = 800
RAG_CHUNK_OVERLAP = 120
RAG_CHUNK_SEPARATORS = ["\n\n", "\n", "\u3002", "\uff1b", "\uff1a", "\uff0c", " ", ""]


def _build_text_splitter() -> RecursiveCharacterTextSplitter:
    """Build the text splitter used for Chinese guideline chunks."""
    return RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        length_function=len,
        separators=RAG_CHUNK_SEPARATORS,
    )


_HEADING_PATTERNS = (
    re.compile(r"^\s*#{1,6}\s*(?P<title>.+?)\s*$"),
    re.compile(r"^\s*\u7b2c?[\u4e00-\u9fff\d]+[\u7ae0\u8282\u90e8\u5206\u7bc7\u5377]\s*[\u3001\u3002:\uff1a\-]?\s*(?P<title>.+?)\s*$"),
    re.compile(r"^\s*(?:[\uff08(]?[\u4e00-\u9fff\d]+[\uff09)]?|\d+(?:\.\d+){0,3})\s*[\u3001\u3002:\uff1a\-]?\s*(?P<title>.+?)\s*$"),
)


def _normalize_text(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _extract_section_title_from_text(page_content: str) -> Optional[str]:
    """Infer a short section title from the first heading-like line."""
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

            candidate = match.group("title").strip(" \t\r\n\u3002\uff1b:\uff1a-")
            if not candidate or len(candidate) > 80:
                continue
            if any(ch in candidate for ch in "\u3002\uff1b\uff01"):
                continue
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
    """Build bounded metadata for a persisted Chroma chunk."""
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
    else:
        chunk_metadata.pop("section_title", None)

    page_range = resolve_page_range(source_metadata)
    if page_range:
        chunk_metadata["page_range"] = page_range
    else:
        chunk_metadata.pop("page_range", None)

    return chunk_metadata


def _split_documents_with_metadata(documents: List) -> List:
    """Split documents while preserving source/page metadata."""
    text_splitter = _build_text_splitter()
    splits = []

    for document in documents:
        document_metadata = dict(getattr(document, "metadata", {}) or {})
        document_section_title = resolve_section_title(document_metadata, getattr(document, "page_content", ""))
        document_splits = text_splitter.split_documents([document])

        for chunk_index, chunk in enumerate(document_splits):
            chunk_metadata = dict(getattr(chunk, "metadata", {}) or {})
            resolved_metadata = _build_chunk_metadata(
                document_metadata,
                chunk_index,
                getattr(chunk, "page_content", ""),
                section_title=document_section_title,
            )
            chunk_metadata.update(resolved_metadata)
            if "section_title" not in resolved_metadata:
                chunk_metadata.pop("section_title", None)
            if "page_range" not in resolved_metadata:
                chunk_metadata.pop("page_range", None)
            chunk.metadata = chunk_metadata
            splits.append(chunk)

    return splits


def _prepare_vector_store_rebuild() -> Optional[Path]:
    """Move the existing vector store aside so rebuild starts from a clean index."""
    vector_store = Path(VECTOR_STORE_DIR)
    if not vector_store.exists() or not any(vector_store.iterdir()):
        return None

    backup_root = Path(VECTOR_STORE_BACKUP_DIR)
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / f"vector_store_{timestamp}"
    shutil.move(str(vector_store), str(backup_path))
    print(f"Existing vector store moved to backup: {backup_path}")
    return backup_path


def _restore_vector_store_backup(backup_path: Optional[Path]) -> None:
    """Restore the previous vector store if rebuild fails before completion."""
    if backup_path is None or not backup_path.exists():
        return

    vector_store = Path(VECTOR_STORE_DIR)
    if vector_store.exists():
        shutil.rmtree(vector_store)
    shutil.move(str(backup_path), str(vector_store))
    print(f"Restored previous vector store from backup: {backup_path}")


def build_knowledge_base():
    """Build the RAG knowledge base from backend/rag/docs."""
    ocr_fallback_capability = describe_ocr_fallback_capability()
    print(format_ocr_fallback_capability_summary(ocr_fallback_capability))
    print("Starting knowledge base build process...")
    print(f"Docs Dir: {DOCS_DIR}")
    print(f"Vector Store Dir: {VECTOR_STORE_DIR}")

    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print("Docs directory created. Please put PDF files in backend/rag/docs/")
        return False

    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print("No PDF files found in backend/rag/docs/. Skipping build.")
        return False

    documents = []
    print(f"Found {len(pdf_files)} PDF(s). Loading...")
    loader_factory = resolve_pdf_loader_factory()

    for pdf_file in pdf_files:
        # Keep processing the batch even if one PDF fails to load.
        file_path = os.path.join(DOCS_DIR, pdf_file)
        try:
            docs = load_pdf_documents_with_ocr_fallback(file_path, loader_factory=loader_factory)
            documents.extend(docs)
            print(f"Loaded: {pdf_file} ({len(docs)} pages)")
        except Exception as exc:
            print(f"Failed to load {pdf_file}: {exc}")

    if not documents:
        print("No documents loaded.")
        return False

    print("Splitting text...")
    splits = _split_documents_with_metadata(documents)
    print(f"Generated {len(splits)} chunks.")

    print("Initializing embeddings model (shibing624/text2vec-base-chinese)...")
    try:
        embeddings = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
    except Exception as exc:
        print(f"Failed to load HuggingFace model: {exc}")
        return False

    print("Creating Chroma vector store...")
    backup_path = _prepare_vector_store_rebuild()
    try:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=VECTOR_STORE_DIR,
        )
        print(f"Knowledge Base Built Successfully! Saved to {VECTOR_STORE_DIR}")
        print(f"Total Vectors: {vectorstore._collection.count()}")
        return True
    except Exception as exc:
        _restore_vector_store_backup(backup_path)
        print(f"Failed to create vector store: {exc}")
        print("Hint: Ensure the embedding model is supported by your API provider.")
        return False


if __name__ == "__main__":
    sys.exit(0 if build_knowledge_base() else 1)
