import importlib.util
from pathlib import Path

from backend.services.payload_normalization import normalize_ocr_summary_payload


def _real_medical_ocr_service_class():
    path = Path(__file__).resolve().parents[1] / "backend" / "services" / "ocr_service.py"
    spec = importlib.util.spec_from_file_location("real_ocr_service_for_regex_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MedicalOCRService


def test_regex_fallback_extracts_core_fields_without_urine_or_ecg_false_positives():
    text = "\n".join(
        [
            "\u59d3\u540d \u738b\u5f6c\u6865 \u6027\u522b \u7537 \u5e74\u9f84 21",
            "\u5c3f\u955c\u68c0\u767d\u7ec6\u80de \u672a\u89c1\u5f02\u5e38 0-3 \u4e2a/HP",
            "\u767d\u7ec6\u80de\u8ba1\u6570(WBC) 6.39 3.5-9.5 10^9/L",
            "\u8840\u7ea2\u86cb\u767d\u542b\u91cf\uff08HGB\uff09 165.00 130-175 g/L",
            "\u8840\u5c0f\u677f\u8ba1\u6570\uff08PLT\uff09 276.00 125-350 10^9/L",
            "\u4e19\u6c28\u9178\u6c28\u57fa\u8f6c\u79fb\u9176\uff08ALT\uff09 15.00 9-50 U/L",
            "\u95e8\u51ac\u6c28\u9178\u6c28\u57fa\u8f6c\u79fb\u9176\uff08AST\uff09 19.00 15-40 U/L",
            "\u78b1\u6027\u78f7\u9178\u9176(ALP) 90.00 40-125 U/L",
            "r-\u8c37\u6c28\u9170\u8f6c\u79fb\u9176(r-GGT) 12.00 10-60 U/L",
            "\u4e00\u822c\u68c0\u67e5 \u603b\u68c0 \u8eab\u9ad8(cm) 170 "
            "\u4f53\u91cd(Kg) 70 \u4f53\u91cd\u6307\u6570 24.22 "
            "\u6536\u7f29\u538b 105 \u8212\u5f20\u538b 60",
            "\u5fc3\u7387:68 \u6b21 Q-Tc:396 \u6beb\u79d2",
        ]
    )

    medical_ocr_service = _real_medical_ocr_service_class()
    extracted = medical_ocr_service()._extract_by_regex(text)
    normalized = normalize_ocr_summary_payload(extracted)

    assert normalized is not None, extracted
    assert normalized["patient_context"] == {
        "Age": 21,
        "Gender": 1,
        "Height": 170.0,
        "Weight": 70.0,
    }
    metrics = normalized["metrics"]
    assert metrics["BMI"]["value"] == 24.22
    assert metrics["SBP"]["value"] == 105
    assert metrics["DBP"]["value"] == 60
    assert metrics["WBC"]["value"] == 6.39
    assert metrics["HGB"]["value"] == 165.0
    assert metrics["Platelet"]["value"] == 276.0
    assert metrics["ALT"]["value"] == 15.0
    assert metrics["AST"]["value"] == 19.0
    assert metrics["ALP"]["value"] == 90.0
    assert metrics["GGT"]["value"] == 12.0
    assert "Cholesterol_Total" not in metrics
