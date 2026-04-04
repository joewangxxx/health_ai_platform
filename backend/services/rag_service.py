import logging
import os
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.rag.benchmark_diagnostics import summarize_document_density
from backend.rag.pdf_extraction import describe_ocr_fallback_capability

logger = logging.getLogger(__name__)

try:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    RAG_DEPENDENCIES_AVAILABLE = True
except ImportError:
    Chroma = None
    HuggingFaceEmbeddings = None
    RAG_DEPENDENCIES_AVAILABLE = False


class RAGService:
    def __init__(self):
        """
        Initialize RAG Service with ChromaDB and Local HuggingFace Embeddings.
        """
        root = settings.PROJECT_ROOT
        if root.endswith("backend"):
            base = root
        else:
            base = os.path.join(root, "backend")

        self.vector_store_dir = os.path.join(base, "rag", "vector_store")
        self.embeddings = None
        self.vectorstore = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        self._init_vectorstore()
        self._initialized = True

    def _init_vectorstore(self):
        if not RAG_DEPENDENCIES_AVAILABLE:
            self.embeddings = None
            self.vectorstore = None
            return

        try:
            # Prefer local-only model loading in runtime containers.
            # If the embedding model is not cached, fall back to an empty RAG context
            # instead of blocking API startup on a remote model download.
            self.embeddings = HuggingFaceEmbeddings(
                model_name="shibing624/text2vec-base-chinese",
                model_kwargs={"local_files_only": True},
            )

            if os.path.exists(self.vector_store_dir) and os.listdir(self.vector_store_dir):
                self.vectorstore = Chroma(
                    persist_directory=self.vector_store_dir,
                    embedding_function=self.embeddings,
                )
                logger.info("RAGService: Vector Store loaded from %s", self.vector_store_dir)
            else:
                logger.info("RAGService: Vector Store empty or not found at %s", self.vector_store_dir)
        except Exception as exc:
            logger.warning("RAGService initialization error: %s", exc)

    def search_context_with_quality(self, query: str, k: int = 3) -> Dict[str, Any]:
        """
        Search for relevant context and return bounded query-time quality metadata.
        """
        self._ensure_initialized()
        if not self.vectorstore:
            return self._build_rag_search_result([], retrieval_status="unavailable")

        try:
            docs = self.vectorstore.similarity_search(query, k=k)
        except Exception as exc:
            logger.warning("RAG Search Error: %s", exc)
            return self._build_rag_search_result([], retrieval_status="unavailable")

        if not docs:
            return self._build_rag_search_result([], retrieval_status="empty")

        return self._build_rag_search_result(list(docs), retrieval_status="ok")

    def search_context(self, query: str, k: int = 3) -> str:
        """
        Backwards-compatible string-only wrapper for existing callers.
        """
        return self.search_context_with_quality(query, k=k)["context"]

    def _build_rag_search_result(self, docs: List[Any], *, retrieval_status: str) -> Dict[str, Any]:
        context = self._format_context(docs)
        quality_summary = self._build_rag_quality_summary(docs, retrieval_status=retrieval_status)
        return {
            "context": context,
            "rag_quality_summary": quality_summary,
        }

    def _format_context(self, docs: List[Any]) -> str:
        if not docs:
            return ""

        context_parts = []
        for index, doc in enumerate(docs):
            metadata = dict(getattr(doc, "metadata", {}) or {})
            source = os.path.basename(str(metadata.get("source", "Unknown")))
            context_parts.append(f"[Ref {index + 1} - {source}]: {getattr(doc, 'page_content', '')}")
        return "\n\n".join(context_parts)

    def _build_rag_quality_summary(self, docs: List[Any], *, retrieval_status: str) -> Dict[str, Any]:
        if retrieval_status != "ok" or not docs:
            return {
                "retrieval_status": retrieval_status,
                "hit_count": 0,
                "unique_source_count": 0,
                "source_kind": "unknown",
                "density_status": "unknown",
                "ocr_fallback_state": "unknown",
                "provenance_state": "missing",
                "chunk_quality": "empty",
            }

        metadata_list = [dict(getattr(doc, "metadata", {}) or {}) for doc in docs]
        source_values = {
            str(metadata.get("source")).strip()
            for metadata in metadata_list
            if metadata.get("source") is not None and str(metadata.get("source")).strip()
        }
        source_kind = self._infer_source_kind(metadata_list)
        density_status = self._infer_density_status(docs)
        ocr_fallback_state = self._infer_ocr_fallback_state(metadata_list)
        provenance_state = self._infer_provenance_state(metadata_list)
        chunk_quality = self._infer_chunk_quality(
            hit_count=len(docs),
            source_kind=source_kind,
            density_status=density_status,
            ocr_fallback_state=ocr_fallback_state,
            provenance_state=provenance_state,
        )

        return {
            "retrieval_status": "ok",
            "hit_count": len(docs),
            "unique_source_count": len(source_values),
            "source_kind": source_kind,
            "density_status": density_status,
            "ocr_fallback_state": ocr_fallback_state,
            "provenance_state": provenance_state,
            "chunk_quality": chunk_quality,
        }

    def _infer_source_kind(self, metadata_list: List[Dict[str, Any]]) -> str:
        if not metadata_list:
            return "unknown"

        has_ocr_text = any(bool(metadata.get("ocr_touched")) for metadata in metadata_list)
        has_pdf_text = any(not bool(metadata.get("ocr_touched")) for metadata in metadata_list)

        if has_ocr_text and has_pdf_text:
            return "mixed"
        if has_ocr_text:
            return "ocr_text"
        if has_pdf_text:
            return "pdf_text"
        return "unknown"

    def _infer_density_status(self, docs: List[Any]) -> str:
        if not docs:
            return "unknown"

        try:
            density_summary = summarize_document_density(docs, docs)
        except Exception as exc:
            logger.warning("RAG density summary unavailable: %s", exc)
            return "unknown"

        return density_summary.get("density_status", "unknown")

    def _infer_ocr_fallback_state(self, metadata_list: List[Dict[str, Any]]) -> str:
        capability = describe_ocr_fallback_capability()
        if not metadata_list:
            return "unknown"

        has_ocr_touched = any(bool(metadata.get("ocr_touched")) for metadata in metadata_list)
        capability_available = bool(capability.get("available"))
        missing_prerequisites = capability.get("missing_prerequisites") or []

        if capability_available:
            return "available"
        if has_ocr_touched:
            return "degraded"
        if missing_prerequisites:
            return "unavailable"
        return "unknown"

    def _infer_provenance_state(self, metadata_list: List[Dict[str, Any]]) -> str:
        if not metadata_list:
            return "missing"

        has_full_floor = all(
            metadata.get("source") is not None
            and metadata.get("page") is not None
            and metadata.get("chunk_index") is not None
            for metadata in metadata_list
        )
        if not has_full_floor:
            return "missing"

        has_optional_hints = all(
            metadata.get("section_title") is not None and metadata.get("page_range") is not None
            for metadata in metadata_list
        )
        return "full" if has_optional_hints else "partial"

    def _infer_chunk_quality(
        self,
        *,
        hit_count: int,
        source_kind: str,
        density_status: str,
        ocr_fallback_state: str,
        provenance_state: str,
    ) -> str:
        if hit_count <= 0:
            return "empty"
        if provenance_state == "missing":
            return "weak"

        severity = 0
        if density_status == "low_density":
            severity += 1
        if provenance_state == "partial":
            severity += 1
        if source_kind == "unknown":
            severity += 1
        if ocr_fallback_state in {"degraded", "unavailable"}:
            severity += 1
        if hit_count == 1:
            severity += 1

        if severity >= 3:
            return "weak"
        if severity >= 1:
            return "mixed"
        return "strong"


# Singleton Instance
rag_service = RAGService()
