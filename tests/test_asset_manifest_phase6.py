import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase6_asset_manifest_files_are_present_and_linked():
    manifest_json = ROOT / "docs/maintenance/asset-manifest-phase6.json"
    manifest_md = ROOT / "docs/maintenance/asset-manifest-phase6.md"
    acceptance_md = ROOT / "docs/maintenance/phase6-acceptance-report.md"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert manifest_json.exists()
    assert manifest_md.exists()
    assert acceptance_md.exists()
    assert "docs/maintenance/asset-manifest-phase6.md" in readme
    assert "docs/maintenance/phase6-acceptance-report.md" in readme


def test_phase6_manifest_has_required_asset_classes_and_policies():
    manifest = json.loads((ROOT / "docs/maintenance/asset-manifest-phase6.json").read_text(encoding="utf-8"))
    classes = {item["asset_class"] for item in manifest["assets"]}

    required_classes = {
        "raw_data",
        "processed_data",
        "model_artifacts",
        "rag_documents",
        "vector_store",
        "upload_samples",
        "runtime_databases",
        "thesis_artifacts",
    }

    assert manifest["phase"] == "maintenance_phase6_asset_acceptance"
    assert required_classes <= classes
    assert manifest["policy"]["direct_delete_allowed"] is False
    assert manifest["policy"]["requires_owner_review_before_archive"] is True

    for item in manifest["assets"]:
        assert item["path"]
        assert item["retention_decision"] in {"keep", "keep_with_manifest", "review_before_externalize"}
        assert item["externalization_strategy"]
        assert item["demo_boundary"]


def test_phase6_acceptance_report_records_no_contract_or_asset_deletion():
    report = (ROOT / "docs/maintenance/phase6-acceptance-report.md").read_text(encoding="utf-8")

    required_text = [
        "未删除数据、模型、PDF、向量库、数据库、上传资产或论文文件",
        "无 API 路由、请求/响应 envelope、数据库 schema、模型 I/O 或前端 API 契约变更",
        "python -m pytest tests/test_asset_manifest_phase6.py tests/test_showcase_hygiene.py -q",
        "python -m pytest tests -q",
        "npm.cmd run build",
    ]

    for text in required_text:
        assert text in report
