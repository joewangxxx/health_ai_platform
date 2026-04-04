import os
import re
from typing import List, Optional

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

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")
RAG_CHUNK_SIZE = 800
RAG_CHUNK_OVERLAP = 120
RAG_CHUNK_SEPARATORS = ["\n\n", "\n", "。", "；", "：", "，", " ", ""]


def _build_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        length_function=len,
        separators=RAG_CHUNK_SEPARATORS,
    )


_HEADING_PATTERNS = (
    re.compile(r"^\s*#{1,6}\s*(?P<title>.+?)\s*$"),
    re.compile(r"^\s*第?[一二三四五六七八九十百千\d]+[章节部分篇卷]\s*[、.．\-]?\s*(?P<title>.+?)\s*$"),
    re.compile(r"^\s*(?:[（(]?[一二三四五六七八九十百\d]+[）)]?|\d+(?:\.\d+){0,3})\s*[、.．\-:：]?\s*(?P<title>.+?)\s*$"),
)


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

            candidate = match.group("title").strip(" \t\r\n。！？.-")
            if not candidate or len(candidate) > 80:
                continue
            if any(ch in candidate for ch in "。！？"):
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


def build_knowledge_base():
    """
    Builds the RAG knowledge base from backend/rag/docs.
    """
    ocr_fallback_capability = describe_ocr_fallback_capability()
    print(format_ocr_fallback_capability_summary(ocr_fallback_capability))
    print("Starting knowledge base build process...")
    print(f"Docs Dir: {DOCS_DIR}")
    print(f"Vector Store Dir: {VECTOR_STORE_DIR}")

    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print("Docs directory created. Please put PDF files in backend/rag/docs/")
        return

    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print("No PDF files found in backend/rag/docs/. Skipping build.")
        return

    documents = []
    print(f"Found {len(pdf_files)} PDF(s). Loading...")
    loader_factory = resolve_pdf_loader_factory()

    for pdf_file in pdf_files:
        file_path = os.path.join(DOCS_DIR, pdf_file)
        try:
            docs = load_pdf_documents_with_ocr_fallback(file_path, loader_factory=loader_factory)
            documents.extend(docs)
            print(f"Loaded: {pdf_file} ({len(docs)} pages)")
        except Exception as exc:
            print(f"Failed to load {pdf_file}: {exc}")

    if not documents:
        print("No documents loaded.")
        return

    print("Splitting text...")
    splits = _split_documents_with_metadata(documents)
    print(f"Generated {len(splits)} chunks.")

    print("Initializing embeddings model (shibing624/text2vec-base-chinese)...")
    try:
        embeddings = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
    except Exception as exc:
        print(f"Failed to load HuggingFace model: {exc}")
        return

    print("Creating Chroma vector store...")
    try:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=VECTOR_STORE_DIR,
        )
        print(f"Knowledge Base Built Successfully! Saved to {VECTOR_STORE_DIR}")
        print(f"Total Vectors: {vectorstore._collection.count()}")
    except Exception as exc:
        print(f"Failed to create vector store: {exc}")
        print("Hint: Ensure the embedding model is supported by your API provider.")


if __name__ == "__main__":
    build_knowledge_base()
