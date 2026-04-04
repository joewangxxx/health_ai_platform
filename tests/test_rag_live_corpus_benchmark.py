from pathlib import Path


class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


def test_iter_rag_corpus_pdf_files_returns_sorted_pdfs(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    (corpus_dir / "z.pdf").write_bytes(b"%PDF-1.4")
    (corpus_dir / "a.pdf").write_bytes(b"%PDF-1.4")
    (corpus_dir / "ignore.txt").write_text("not a pdf", encoding="utf-8")

    pdf_files = benchmark.iter_rag_corpus_pdf_files(corpus_dir)

    assert [path.name for path in pdf_files] == ["a.pdf", "z.pdf"]


def test_build_rag_live_corpus_benchmark_reports_live_loader_and_split_stats(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    alpha_pdf = corpus_dir / "alpha.pdf"
    beta_pdf = corpus_dir / "beta.pdf"
    alpha_pdf.write_bytes(b"%PDF-1.4")
    beta_pdf.write_bytes(b"%PDF-1.4")

    loaded_paths = []

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = Path(file_path)

        def load(self):
            loaded_paths.append(self.file_path.name)
            if self.file_path.name == "alpha.pdf":
                return [
                    FakeDocument("abcdefghij", {"source": str(self.file_path), "page": 1, "title": "诊断标准"}),
                    FakeDocument(
                        "klmnopqrst",
                        {"source": str(self.file_path), "page": 2, "start_page": 1, "end_page": 2},
                    ),
                ]
            return [
                FakeDocument("uvwxyz1234", {"source": str(self.file_path), "page": 9}),
            ]

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=FakeLoader,
    )

    assert loaded_paths == ["alpha.pdf", "beta.pdf"]
    assert report["corpus_dir"] == str(corpus_dir)
    assert report["document_count"] == 2
    assert report["page_count"] == 3
    assert report["chunk_count"] == 3
    assert report["average_chunk_size"] == 10.0
    assert report["max_chunk_size"] == 10
    assert report["section_title_coverage"] == 0.3333
    assert report["page_range_coverage"] == 0.3333
    assert report["metadata_floor_coverage"] == 1.0
    assert [item["source"] for item in report["documents"]] == [
        str(alpha_pdf),
        str(beta_pdf),
    ]
    assert report["documents"][0]["chunk_count"] == 2
    assert report["documents"][1]["chunk_count"] == 1
    assert report["documents"][0]["section_title_coverage"] == 0.5
    assert report["documents"][0]["page_range_coverage"] == 0.5


def test_build_rag_live_corpus_benchmark_resolves_loader_factory_once(tmp_path, monkeypatch):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    (corpus_dir / "alpha.pdf").write_bytes(b"%PDF-1.4")
    (corpus_dir / "beta.pdf").write_bytes(b"%PDF-1.4")

    calls = []

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = Path(file_path)

        def load(self):
            return [
                FakeDocument("abcdefghij", {"source": str(self.file_path), "page": 1}),
            ]

    monkeypatch.setattr(
        benchmark,
        "resolve_pdf_loader_factory",
        lambda: (calls.append("called") or (lambda file_path: FakeLoader(file_path))),
    )

    report = benchmark.build_rag_live_corpus_benchmark(corpus_dir=corpus_dir)

    assert calls == ["called"]
    assert report["document_count"] == 2
    assert report["page_count"] == 2


def test_build_rag_live_corpus_benchmark_reports_qa_usefulness_signals(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    strong_pdf = corpus_dir / "strong.pdf"
    weak_pdf = corpus_dir / "weak.pdf"
    strong_pdf.write_bytes(b"%PDF-1.4")
    weak_pdf.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = Path(file_path)

        def load(self):
            if self.file_path.name == "strong.pdf":
                return [
                    FakeDocument(
                        "Page 1\n# Chronic Care Plan\nThis document has enough body text to stay useful for QA.",
                        {"source": str(self.file_path), "page": 1, "title": "Chronic Care Plan"},
                    )
                ]
            return [
                FakeDocument("Short note", {"source": str(self.file_path), "page": 1, "ocr_touched": True}),
                FakeDocument("tiny", {"source": str(self.file_path), "page": 2}),
            ]

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=FakeLoader,
    )

    strong_document = next(item for item in report["documents"] if item["source"] == str(strong_pdf))
    weak_document = next(item for item in report["documents"] if item["source"] == str(weak_pdf))

    assert report["section_title_document_coverage"] == 0.5
    assert report["qa_usefulness_score"] > 0
    assert report["qa_usefulness"] in {"mixed", "weak", "strong"}
    assert strong_document["qa_usefulness"] == "strong"
    assert weak_document["qa_usefulness"] in {"weak", "mixed"}
    assert strong_document["qa_usefulness_score"] > weak_document["qa_usefulness_score"]


def test_build_rag_live_corpus_benchmark_includes_ocr_fallback_capability_summary(tmp_path, monkeypatch):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    (corpus_dir / "alpha.pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        benchmark,
        "describe_ocr_fallback_capability",
        lambda: {
            "available": False,
            "pdftoppm_available": False,
            "ocr_credentials_available": False,
            "network_assumption_state": "assumed_available",
            "missing_prerequisites": ["pdftoppm", "baidu_ocr_credentials"],
        },
    )

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=lambda file_path: type(
            "FakeLoader",
            (),
            {
                "load": lambda self: [
                    FakeDocument("example text", {"source": file_path, "page": 1}),
                ]
            },
        )(),
    )

    assert report["ocr_fallback_capability"] == {
        "available": False,
        "pdftoppm_available": False,
        "ocr_credentials_available": False,
        "network_assumption_state": "assumed_available",
        "missing_prerequisites": ["pdftoppm", "baidu_ocr_credentials"],
    }


def test_build_rag_live_corpus_benchmark_flags_low_density_documents(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    low_density_pdf = corpus_dir / "scan-heavy.pdf"
    normal_pdf = corpus_dir / "normal.pdf"
    low_density_pdf.write_bytes(b"%PDF-1.4")
    normal_pdf.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = Path(file_path)

        def load(self):
            if self.file_path.name == "scan-heavy.pdf":
                return [
                    FakeDocument("", {"source": str(self.file_path), "page": 1, "ocr_touched": True}),
                    FakeDocument("   ", {"source": str(self.file_path), "page": 2}),
                    FakeDocument("tiny", {"source": str(self.file_path), "page": 3}),
                ]
            return [
                FakeDocument(
                    "This document has enough text to avoid a low-density flag.",
                    {"source": str(self.file_path), "page": 1},
                )
            ]

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=FakeLoader,
    )

    low_density_document = next(item for item in report["documents"] if item["source"] == str(low_density_pdf))
    normal_document = next(item for item in report["documents"] if item["source"] == str(normal_pdf))

    assert report["low_density_document_count"] == 1
    assert low_density_document["density_status"] == "low_density"
    assert low_density_document["low_density"] is True
    assert low_density_document["blank_page_count"] == 2
    assert low_density_document["blank_page_ratio"] == 0.6667
    assert low_density_document["ocr_touched_page_count"] == 1
    assert low_density_document["extremely_short_chunk_count"] == 3
    assert low_density_document["density_reasons"]
    assert normal_document["density_status"] == "normal"
    assert normal_document["low_density"] is False


def test_build_rag_live_corpus_benchmark_uses_ocr_enriched_documents(tmp_path, monkeypatch):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    scan_pdf = corpus_dir / "scan.pdf"
    scan_pdf.write_bytes(b"%PDF-1.4")

    class FakeDocument:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    def fake_load_pdf_documents_with_ocr_fallback(file_path, loader_factory=None):
        return [FakeDocument("# OCR extracted heading\nocr extracted body", {"source": file_path, "page": 1})]

    monkeypatch.setattr(benchmark, "load_pdf_documents_with_ocr_fallback", fake_load_pdf_documents_with_ocr_fallback)

    report = benchmark.build_rag_live_corpus_benchmark(corpus_dir=corpus_dir)

    assert report["document_count"] == 1
    assert report["chunk_count"] == 1
    assert report["average_chunk_size"] > 0
    assert report["section_title_coverage"] == 1.0


def test_build_rag_live_corpus_benchmark_rejects_decreasing_page_range(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    broken_pdf = corpus_dir / "broken-range.pdf"
    broken_pdf.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = Path(file_path)

        def load(self):
            return [
                FakeDocument(
                    "cross-page content",
                    {
                        "source": str(self.file_path),
                        "page": 7,
                        "start_page": 8,
                        "end_page": 7,
                    },
                ),
            ]

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=FakeLoader,
    )

    [document_report] = report["documents"]
    assert document_report["page_range_coverage"] == 0.0
    assert document_report["chunk_count"] == 1
    assert document_report["metadata_floor_coverage"] == 1.0
    assert report["page_range_coverage"] == 0.0


def test_build_rag_live_corpus_benchmark_propagates_page_level_section_title(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    titled_pdf = corpus_dir / "titled.pdf"
    titled_pdf.write_bytes(b"%PDF-1.4")

    class FakeLoader:
        def __init__(self, file_path):
            self.file_path = Path(file_path)

        def load(self):
            return [
                FakeDocument("一、预防策略\n" + ("正文A" * 360), {"source": str(self.file_path), "page": 1}),
            ]

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=FakeLoader,
    )

    [document_report] = report["documents"]
    assert document_report["chunk_count"] > 1
    assert document_report["section_title_coverage"] == 1.0
    assert report["section_title_coverage"] == 1.0


def test_build_rag_live_corpus_benchmark_records_load_failures_without_writing_vector_store(tmp_path):
    from backend.rag import benchmark

    corpus_dir = tmp_path / "docs"
    corpus_dir.mkdir()
    (corpus_dir / "broken.pdf").write_bytes(b"%PDF-1.4")

    class FailingLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            raise RuntimeError("pdf parse failed")

    report = benchmark.build_rag_live_corpus_benchmark(
        corpus_dir=corpus_dir,
        loader_factory=FailingLoader,
    )

    assert report["document_count"] == 0
    assert report["page_count"] == 0
    assert report["chunk_count"] == 0
    assert report["load_failures"] == [
        {
            "source": str(corpus_dir / "broken.pdf"),
            "error": "pdf parse failed",
        }
    ]
    assert report["vector_store_writes"] == 0
