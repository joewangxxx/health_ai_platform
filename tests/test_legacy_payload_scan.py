from pathlib import Path


def test_legacy_payload_scan_script_exists():
    assert Path("E:/health_ai_platform_2.0/backend/scripts/scan_legacy_payload_shapes.py").exists()
