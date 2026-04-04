class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


def test_resolve_pdf_loader_factory_warns_once_when_langchain_loader_is_missing(monkeypatch, caplog):
    from backend.rag import pdf_extraction

    pdf_extraction.resolve_pdf_loader_factory.cache_clear()

    monkeypatch.setattr(
        pdf_extraction,
        "_import_langchain_pypdf_loader",
        lambda: (_ for _ in ()).throw(ImportError("missing langchain loader")),
    )

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            return [FakeDocument("fallback text", {"source": self.file_path, "page": 1})]

    monkeypatch.setattr(
        pdf_extraction,
        "_build_pypdf_loader_factory",
        lambda: (lambda file_path: FakeLoader(file_path)),
    )

    with caplog.at_level("WARNING"):
        loader_factory_one = pdf_extraction.resolve_pdf_loader_factory()
        loader_factory_two = pdf_extraction.resolve_pdf_loader_factory()

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]
    assert warning_messages == ["PyPDFLoader unavailable; using pypdf fallback for this process."]
    assert loader_factory_one is loader_factory_two

    loaded_documents = loader_factory_one("example.pdf").load()
    assert loaded_documents[0].metadata["source"] == "example.pdf"


def test_describe_ocr_fallback_capability_reflects_environment(monkeypatch):
    from backend.rag import pdf_extraction

    monkeypatch.setattr(pdf_extraction.shutil, "which", lambda executable: "/usr/bin/pdftoppm" if executable == "pdftoppm" else None)
    monkeypatch.setattr(pdf_extraction.settings, "BAIDU_APP_ID", "app-id")
    monkeypatch.setattr(pdf_extraction.settings, "BAIDU_API_KEY", "api-key")
    monkeypatch.setattr(pdf_extraction.settings, "BAIDU_SECRET_KEY", "secret-key")

    summary = pdf_extraction.describe_ocr_fallback_capability()

    assert summary == {
        "available": True,
        "pdftoppm_available": True,
        "ocr_credentials_available": True,
        "network_assumption_state": "assumed_available",
        "missing_prerequisites": [],
    }


def test_load_pdf_documents_with_ocr_fallback_replaces_blank_pages(tmp_path):
    from backend.rag import pdf_extraction

    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            return [
                FakeDocument("", {"source": str(self.file_path), "page": 1}),
                FakeDocument("already extracted", {"source": str(self.file_path), "page": 2}),
            ]

    calls = []

    def fake_ocr_text_extractor(file_path, page_number):
        calls.append((file_path, page_number))
        return "ocr extracted page one"

    documents = pdf_extraction.load_pdf_documents_with_ocr_fallback(
        str(pdf_path),
        loader_factory=FakeLoader,
        ocr_text_extractor=fake_ocr_text_extractor,
        ocr_page_limit=5,
    )

    assert [document.page_content for document in documents] == [
        "ocr extracted page one",
        "already extracted",
    ]
    assert documents[0].metadata["ocr_touched"] is True
    assert "ocr_touched" not in documents[1].metadata
    assert calls == [(str(pdf_path), 1)]


def test_resolve_section_title_prefers_loader_metadata_over_text():
    from backend.rag import pdf_extraction

    source_metadata = {
        "source": "example.pdf",
        "page": 1,
        "section_title": "Loader section title",
        "title": "Fallback title",
    }

    assert pdf_extraction.resolve_section_title(source_metadata, "第1章 OCR heading\n正文") == "Loader section title"


def test_resolve_section_title_supports_chapter_labels_and_isolated_title_lines():
    from backend.rag import pdf_extraction

    chapter_heading = pdf_extraction.resolve_section_title(
        {"source": "example.pdf", "page": 2},
        "第1章 总则\n正文内容",
    )
    isolated_title = pdf_extraction.resolve_section_title(
        {"source": "example.pdf", "page": 3},
        "中国高血压防治指南",
    )

    assert chapter_heading == "总则"
    assert isolated_title == "中国高血压防治指南"


def test_resolve_section_title_rejects_plain_body_text():
    from backend.rag import pdf_extraction

    assert (
        pdf_extraction.resolve_section_title(
            {"source": "example.pdf", "page": 4},
            "This is ordinary paragraph text without a stable heading.",
        )
        is None
    )


def test_resolve_section_title_scans_past_leading_noise_lines():
    from backend.rag import pdf_extraction

    source_metadata = {"source": "example.pdf", "page": 5}

    assert (
        pdf_extraction.resolve_section_title(
            source_metadata,
            "Page 5\n# Chronic Care Plan\nThis is the body text.",
        )
        == "Chronic Care Plan"
    )


def test_load_pdf_documents_with_ocr_fallback_enriches_short_pages(tmp_path):
    from backend.rag import pdf_extraction

    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            return [
                FakeDocument("Short note", {"source": str(self.file_path), "page": 1}),
                FakeDocument("Adequate extracted text with enough detail.", {"source": str(self.file_path), "page": 2}),
            ]

    calls = []

    def fake_ocr_text_extractor(file_path, page_number):
        calls.append((file_path, page_number))
        return "Chronic Care Plan\nExpanded OCR body text"

    documents = pdf_extraction.load_pdf_documents_with_ocr_fallback(
        str(pdf_path),
        loader_factory=FakeLoader,
        ocr_text_extractor=fake_ocr_text_extractor,
        ocr_page_limit=5,
    )

    assert [document.page_content for document in documents] == [
        "Chronic Care Plan\nExpanded OCR body text",
        "Adequate extracted text with enough detail.",
    ]
    assert documents[0].metadata["ocr_touched"] is True
    assert "ocr_touched" not in documents[1].metadata
    assert calls == [(str(pdf_path), 1)]


def test_resolve_section_title_scans_following_lines_for_headings():
    from backend.rag import pdf_extraction

    source_metadata = {"source": "example.pdf", "page": 5}

    assert (
        pdf_extraction.resolve_section_title(
            source_metadata,
            "Page 1\n# Stable heading\nBody text that follows the heading.",
        )
        == "Stable heading"
    )


def test_load_pdf_documents_with_ocr_fallback_replaces_short_low_density_pages(tmp_path):
    from backend.rag import pdf_extraction

    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            return [
                FakeDocument("abc", {"source": str(self.file_path), "page": 1}),
                FakeDocument("already extracted", {"source": str(self.file_path), "page": 2}),
            ]

    calls = []

    def fake_ocr_text_extractor(file_path, page_number):
        calls.append((file_path, page_number))
        return "ocr extracted page one"

    documents = pdf_extraction.load_pdf_documents_with_ocr_fallback(
        str(pdf_path),
        loader_factory=FakeLoader,
        ocr_text_extractor=fake_ocr_text_extractor,
        ocr_page_limit=5,
    )

    assert [document.page_content for document in documents] == [
        "ocr extracted page one",
        "already extracted",
    ]
    assert documents[0].metadata["ocr_touched"] is True
    assert "ocr_touched" not in documents[1].metadata
    assert calls == [(str(pdf_path), 1)]
