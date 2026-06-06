import importlib.util
import sys
import tempfile
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_KB_PATH = REPO_ROOT / "backend" / "rag" / "build_kb.py"


def load_real_build_kb_module(fake_loader_cls, fake_splitter_cls, fake_embeddings_cls, fake_chroma_cls):
    fake_document_loaders = types.ModuleType("langchain_community.document_loaders")
    fake_document_loaders.PyPDFLoader = fake_loader_cls

    fake_langchain_community = types.ModuleType("langchain_community")
    fake_langchain_community.document_loaders = fake_document_loaders

    fake_langchain_text_splitters = types.ModuleType("langchain_text_splitters")
    fake_langchain_text_splitters.RecursiveCharacterTextSplitter = fake_splitter_cls

    fake_langchain_huggingface = types.ModuleType("langchain_huggingface")
    fake_langchain_huggingface.HuggingFaceEmbeddings = fake_embeddings_cls

    fake_langchain_chroma = types.ModuleType("langchain_chroma")
    fake_langchain_chroma.Chroma = fake_chroma_cls

    module_name = "real_build_kb_for_test"
    spec = importlib.util.spec_from_file_location(module_name, BUILD_KB_PATH)
    module = importlib.util.module_from_spec(spec)

    originals = {
        "langchain_community": sys.modules.get("langchain_community"),
        "langchain_community.document_loaders": sys.modules.get("langchain_community.document_loaders"),
        "langchain_text_splitters": sys.modules.get("langchain_text_splitters"),
        "langchain_huggingface": sys.modules.get("langchain_huggingface"),
        "langchain_chroma": sys.modules.get("langchain_chroma"),
    }

    sys.modules["langchain_community"] = fake_langchain_community
    sys.modules["langchain_community.document_loaders"] = fake_document_loaders
    sys.modules["langchain_text_splitters"] = fake_langchain_text_splitters
    sys.modules["langchain_huggingface"] = fake_langchain_huggingface
    sys.modules["langchain_chroma"] = fake_langchain_chroma
    try:
        spec.loader.exec_module(module)
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    return module


def _install_fake_runtime(monkeypatch, module, loader_docs, captured, splitter_cls=None):
    class FakeDoc:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            docs = []
            for page_content, metadata in loader_docs:
                merged = dict(metadata)
                merged.setdefault("source", self.file_path)
                docs.append(FakeDoc(page_content, merged))
            return docs

    class FakeSplitter:
        def __init__(self, **kwargs):
            captured["splitter_kwargs"] = kwargs

        def split_documents(self, docs):
            split_docs = []
            for doc in docs:
                split_docs.append(FakeDoc(doc.page_content, dict(doc.metadata)))
            return split_docs

    class FakeEmbeddings:
        def __init__(self, *args, **kwargs):
            captured["embeddings_kwargs"] = kwargs

    class FakeCollection:
        def count(self):
            return len(captured["documents"])

    class FakeVectorstore:
        _collection = FakeCollection()

    class FakeChroma:
        @classmethod
        def from_documents(cls, documents, embedding, persist_directory):
            captured["documents"] = documents
            captured["persist_directory"] = persist_directory
            captured["embedding"] = embedding
            return FakeVectorstore()

    loaded = load_real_build_kb_module(FakeLoader, splitter_cls or FakeSplitter, FakeEmbeddings, FakeChroma)
    monkeypatch.setattr(loaded, "VECTOR_STORE_DIR", tempfile.mkdtemp(prefix="rag-build-kb-test-vector-"))
    monkeypatch.setattr(loaded, "VECTOR_STORE_BACKUP_DIR", tempfile.mkdtemp(prefix="rag-build-kb-test-backup-"))
    monkeypatch.setattr(loaded.os.path, "exists", lambda path: True)
    monkeypatch.setattr(loaded.os, "listdir", lambda path: ["guideline.pdf"])
    monkeypatch.setattr(loaded, "resolve_pdf_loader_factory", lambda: (lambda file_path: FakeLoader(file_path)))
    return loaded


def test_build_knowledge_base_uses_frozen_chunking_profile(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("首行标题\n正文内容。", {"page": 1, "title": "示例标题"})],
        captured,
    )

    module.build_knowledge_base()

    splitter_kwargs = captured["splitter_kwargs"]
    assert splitter_kwargs["chunk_size"] == 800
    assert splitter_kwargs["chunk_overlap"] == 120
    assert splitter_kwargs["length_function"] is len
    assert splitter_kwargs["separators"] == module.RAG_CHUNK_SEPARATORS


def test_build_knowledge_base_resolves_loader_factory_once(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("Fallback text", {"page": 1})],
        captured,
    )
    monkeypatch.setattr(module.os, "listdir", lambda path: ["one.pdf", "two.pdf"])

    calls = []

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            return [FakeDocument("fallback text", {"source": self.file_path, "page": 1})]

    monkeypatch.setattr(
        module,
        "resolve_pdf_loader_factory",
        lambda: (calls.append("called") or (lambda file_path: FakeLoader(file_path))),
    )

    module.build_knowledge_base()

    assert calls == ["called"]


def test_build_knowledge_base_announces_ocr_fallback_capability_once(monkeypatch, capsys):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("Example heading\nNormal body", {"page": 1, "title": "Example title"})],
        captured,
    )
    from backend.rag import pdf_extraction

    monkeypatch.setattr(pdf_extraction.shutil, "which", lambda executable: "/usr/bin/pdftoppm" if executable == "pdftoppm" else None)
    monkeypatch.setattr(pdf_extraction.settings, "BAIDU_APP_ID", "app-id")
    monkeypatch.setattr(pdf_extraction.settings, "BAIDU_API_KEY", "api-key")
    monkeypatch.setattr(pdf_extraction.settings, "BAIDU_SECRET_KEY", "secret-key")

    module.build_knowledge_base()

    output_lines = capsys.readouterr().out.splitlines()
    capability_lines = [line for line in output_lines if line.startswith("OCR fallback capability:")]

    assert len(capability_lines) == 1
    assert "available=True" in capability_lines[0]
    assert "pdftoppm_available=True" in capability_lines[0]
    assert "ocr_credentials_available=True" in capability_lines[0]


def test_build_knowledge_base_keeps_single_page_metadata_minimal(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("单页正文，只有内容，没有标题线索。", {"page": 7, "page_range": "7-7"})],
        captured,
    )

    module.build_knowledge_base()

    [chunk] = captured["documents"]
    assert chunk.metadata["source"].endswith("guideline.pdf")
    assert chunk.metadata["page"] == 7
    assert chunk.metadata["chunk_index"] == 0
    assert "section_title" not in chunk.metadata
    assert "page_range" not in chunk.metadata


def test_build_knowledge_base_emits_page_range_for_cross_page_chunk(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("跨页内容，来自连续两页。", {"page": 7, "start_page": 7, "end_page": 8})],
        captured,
    )

    module.build_knowledge_base()

    [chunk] = captured["documents"]
    assert chunk.metadata["page"] == 7
    assert chunk.metadata["page_range"] == "7-8"


def test_build_knowledge_base_rejects_decreasing_page_range(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("cross-page content", {"page": 7, "start_page": 8, "end_page": 7})],
        captured,
    )

    module.build_knowledge_base()

    [chunk] = captured["documents"]
    assert chunk.metadata["page"] == 7
    assert "page_range" not in chunk.metadata


def test_build_knowledge_base_ignores_missing_title_without_heading(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("这是一段普通正文，没有稳定标题。", {"page": 3})],
        captured,
    )

    module.build_knowledge_base()

    [chunk] = captured["documents"]
    assert "section_title" not in chunk.metadata
    assert "page_range" not in chunk.metadata


def test_build_knowledge_base_uses_explicit_loader_title(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("没有章节标题的正文内容。", {"page": 11, "title": "糖尿病指南"})],
        captured,
    )

    module.build_knowledge_base()

    [chunk] = captured["documents"]
    assert chunk.metadata["section_title"] == "糖尿病指南"
    assert "page_range" not in chunk.metadata


def test_build_knowledge_base_infers_heading_from_lightweight_rules(monkeypatch):
    captured = {}
    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("一、诊断标准\n这是章节正文。", {"page": 9})],
        captured,
    )

    module.build_knowledge_base()

    [chunk] = captured["documents"]
    assert chunk.metadata["section_title"] == "诊断标准"
    assert "page_range" not in chunk.metadata


def test_build_knowledge_base_propagates_page_level_section_title_to_all_chunks(monkeypatch):
    captured = {}

    class MultiChunkSplitter:
        def __init__(self, **kwargs):
            captured["splitter_kwargs"] = kwargs

        def split_documents(self, docs):
            split_docs = []
            for doc in docs:
                split_docs.append(doc.__class__("一、预防策略\n正文A", dict(doc.metadata)))
                split_docs.append(doc.__class__("正文B", dict(doc.metadata)))
            return split_docs

    module = _install_fake_runtime(
        monkeypatch,
        None,
        [("一、预防策略\n正文A正文B", {"page": 12})],
        captured,
        splitter_cls=MultiChunkSplitter,
    )

    module.build_knowledge_base()

    assert [chunk.metadata["section_title"] for chunk in captured["documents"]] == [
        "预防策略",
        "预防策略",
    ]
