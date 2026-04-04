import importlib.util
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RAG_SERVICE_PATH = REPO_ROOT / "backend" / "services" / "rag_service.py"


def load_real_rag_service_module(fake_embeddings_cls, fake_chroma_cls):
    fake_langchain_huggingface = types.ModuleType("langchain_huggingface")
    fake_langchain_huggingface.HuggingFaceEmbeddings = fake_embeddings_cls

    fake_langchain_chroma = types.ModuleType("langchain_chroma")
    fake_langchain_chroma.Chroma = fake_chroma_cls

    module_name = "real_rag_service_for_test"
    spec = importlib.util.spec_from_file_location(module_name, RAG_SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)

    original_hf = sys.modules.get("langchain_huggingface")
    original_chroma = sys.modules.get("langchain_chroma")
    sys.modules["langchain_huggingface"] = fake_langchain_huggingface
    sys.modules["langchain_chroma"] = fake_langchain_chroma
    try:
        spec.loader.exec_module(module)
    finally:
        if original_hf is None:
            sys.modules.pop("langchain_huggingface", None)
        else:
            sys.modules["langchain_huggingface"] = original_hf

        if original_chroma is None:
            sys.modules.pop("langchain_chroma", None)
        else:
            sys.modules["langchain_chroma"] = original_chroma

    return module


def test_rag_service_initializes_embeddings_lazily(monkeypatch):
    calls = {"embeddings": 0, "chroma": 0}

    class FakeEmbeddings:
        def __init__(self, *args, **kwargs):
            calls["embeddings"] += 1

    class FakeChroma:
        def __init__(self, *args, **kwargs):
            calls["chroma"] += 1

        def similarity_search(self, query, k=3):
            return []

    module = load_real_rag_service_module(FakeEmbeddings, FakeChroma)
    monkeypatch.setattr(module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(module.os, "listdir", lambda path: ["index"])

    service = module.RAGService()

    assert calls["embeddings"] == 0
    assert calls["chroma"] == 0

    service.search_context("血糖高怎么办", k=2)

    assert calls["embeddings"] == 1
    assert calls["chroma"] == 1


def test_rag_service_uses_local_files_only_for_embeddings(monkeypatch):
    captured = {}

    class FakeEmbeddings:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

    class FakeChroma:
        def __init__(self, *args, **kwargs):
            pass

        def similarity_search(self, query, k=3):
            return []

    module = load_real_rag_service_module(FakeEmbeddings, FakeChroma)
    monkeypatch.setattr(module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(module.os, "listdir", lambda path: ["index"])

    service = module.RAGService()
    service.search_context("高血压指南", k=3)

    assert captured["model_kwargs"]["local_files_only"] is True
