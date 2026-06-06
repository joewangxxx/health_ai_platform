from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_showcase_entry_points_are_visible_from_readme():
    readme = _read_text("README.md")

    required_links = [
        "docs/showcase/project-one-page.md",
        "docs/showcase/demo-script.md",
        "docs/showcase/presentation-checklist.md",
        "docs/maintenance/presentation-polish-phase5.md",
    ]

    for link in required_links:
        assert link in readme
        assert (ROOT / link).exists()


def test_showcase_documents_have_required_presentation_sections():
    required_sections = {
        "docs/showcase/project-one-page.md": [
            "## 一句话定位",
            "## 展示亮点",
            "## 可量化证据",
            "## 边界声明",
        ],
        "docs/showcase/demo-script.md": [
            "## 演示目标",
            "## 演示动线",
            "## 讲解话术",
            "## 应急方案",
        ],
        "docs/showcase/presentation-checklist.md": [
            "## 展示前检查",
            "## 现场演示检查",
            "## 观感风险清单",
            "## 结束后归档",
        ],
    }

    for path, sections in required_sections.items():
        text = _read_text(path)
        for section in sections:
            assert section in text


def test_showcase_hygiene_files_are_utf8_without_bom_or_mojibake():
    checked_files = [
        ".gitignore",
        "README.md",
        "docs/maintenance/legacy-cleanup-phase4.md",
        "docs/maintenance/presentation-polish-phase5.md",
        "docs/showcase/project-one-page.md",
        "docs/showcase/demo-script.md",
        "docs/showcase/presentation-checklist.md",
    ]
    suspicious_fragments = ["鏁", "鍓", "绂", "涓", "\ufffd"]

    for path in checked_files:
        raw = (ROOT / path).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} should not contain a UTF-8 BOM"
        text = raw.decode("utf-8")
        for fragment in suspicious_fragments:
            assert fragment not in text, f"{path} contains suspicious mojibake fragment {fragment!r}"
