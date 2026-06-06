from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

RAG_SERVICE_PATH = Path(__file__).resolve().parents[1] / "backend" / "services" / "rag_service.py"
rag_service_spec = spec_from_file_location("rag_service_under_test", RAG_SERVICE_PATH)
rag_service_module = module_from_spec(rag_service_spec)
assert rag_service_spec.loader is not None
rag_service_spec.loader.exec_module(rag_service_module)
RAGService = rag_service_module.RAGService


class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


class FakeVectorStore:
    def __init__(self, documents):
        self._documents = documents

    def similarity_search(self, query, k=3):
        return self._documents[:k]


def test_search_context_with_quality_returns_internal_quality_summary(monkeypatch):
    service = RAGService()
    service.vectorstore = FakeVectorStore(
        [
            FakeDocument(
                "This guideline recommends routine monitoring and gradual lifestyle changes.",
                {
                    "source": "/kb/guideline-a.pdf",
                    "page": 1,
                    "chunk_index": 0,
                    "section_title": "Blood Sugar Guidance",
                    "page_range": "1-2",
                    "ocr_touched": True,
                },
            ),
            FakeDocument(
                "This report summary supports the same general advice with a second reference.",
                {
                    "source": "/kb/guideline-b.pdf",
                    "page": 4,
                    "chunk_index": 1,
                    "section_title": "Follow-up Advice",
                    "page_range": "4-5",
                },
            ),
        ]
    )
    service._initialized = True

    monkeypatch.setattr(
        rag_service_module,
        "describe_ocr_fallback_capability",
        lambda: {
            "available": True,
            "pdftoppm_available": True,
            "ocr_credentials_available": True,
            "network_assumption_state": "assumed_available",
            "missing_prerequisites": [],
        },
    )

    result = service.search_context_with_quality("blood sugar guidance", k=3)

    assert result["context"].startswith("[Ref 1 - guideline-a.pdf]")
    summary = result["rag_quality_summary"]
    assert summary["retrieval_status"] == "ok"
    assert summary["hit_count"] == 2
    assert summary["unique_source_count"] == 2
    assert summary["source_kind"] == "mixed"
    assert summary["density_status"] == "normal"
    assert summary["ocr_fallback_state"] == "available"
    assert summary["provenance_state"] == "full"
    assert summary["chunk_quality"] == "strong"


def test_search_context_with_quality_marks_unavailable_when_vectorstore_is_missing():
    service = RAGService()
    service.vectorstore = None
    service._initialized = True

    result = service.search_context_with_quality("blood sugar guidance", k=3)

    assert result["context"] == ""
    assert result["rag_quality_summary"]["retrieval_status"] == "unavailable"
    assert result["rag_quality_summary"]["hit_count"] == 0
    assert result["rag_quality_summary"]["source_kind"] == "unknown"
    assert result["rag_quality_summary"]["chunk_quality"] == "empty"
