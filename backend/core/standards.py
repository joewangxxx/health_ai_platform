"""
China Medical Reference Ranges (Task 90)
=========================================
Based on《中国体检人群检验项目参考区间》(WS/T 767-2017) and common clinical standards.

This module provides authoritative fallback reference ranges for anomaly detection
when OCR extraction fails to capture the hospital's specific reference values.
"""

# Gender constants for gender-specific ranges
MALE = 1
FEMALE = 2

CHINA_REFERENCE_RANGES = {
    # ======================= 核心指标 =======================
    "BMI": {"min": 18.5, "max": 23.9, "unit": "kg/m²", "note": "中国成人标准"},
    "SBP": {"min": 90, "max": 139, "unit": "mmHg", "note": "收缩压"},
    "DBP": {"min": 60, "max": 89, "unit": "mmHg", "note": "舒张压"},
    
    # ======================= 血常规 =======================
    "WBC": {"min": 3.5, "max": 9.5, "unit": "10^9/L"},
    "RBC": {
        "Male": {"min": 4.3, "max": 5.8},
        "Female": {"min": 3.8, "max": 5.1},
        "unit": "10^12/L"
    },
    "HGB": {
        "Male": {"min": 130, "max": 175},
        "Female": {"min": 115, "max": 150},
        "unit": "g/L"
    },
    "PLT": {"min": 125, "max": 350, "unit": "10^9/L"},
    "Platelet": {"min": 125, "max": 350, "unit": "10^9/L"},  # Alias
    "NEUT_PERCENT": {"min": 40, "max": 75, "unit": "%"},
    "LYM_PERCENT": {"min": 20, "max": 50, "unit": "%"},
    
    # ======================= 肝功能 =======================
    "ALT": {
        "Male": {"min": 9, "max": 50},
        "Female": {"min": 7, "max": 40},
        "unit": "U/L"
    },
    "AST": {
        "Male": {"min": 15, "max": 40},
        "Female": {"min": 13, "max": 35},
        "unit": "U/L"
    },
    "GGT": {
        "Male": {"min": 10, "max": 60},
        "Female": {"min": 7, "max": 45},
        "unit": "U/L"
    },
    "ALP": {"min": 45, "max": 125, "unit": "U/L"},
    "TBil": {"min": 5.1, "max": 19.0, "unit": "μmol/L"},
    
    # ======================= 肾功能 =======================
    "Cr": {
        "Male": {"min": 57, "max": 97},
        "Female": {"min": 41, "max": 73},
        "unit": "μmol/L"
    },
    "Creatinine": {
        "Male": {"min": 57, "max": 97},
        "Female": {"min": 41, "max": 73},
        "unit": "μmol/L"
    },
    "UA": {
        "Male": {"min": 208, "max": 428},
        "Female": {"min": 155, "max": 357},
        "unit": "μmol/L"
    },
    "eGFR": {"min": 90, "max": 999, "unit": "mL/min/1.73m²", "note": "肾小球滤过率"},
    
    # ======================= 代谢指标 =======================
    "Glu": {"min": 3.9, "max": 6.1, "unit": "mmol/L", "note": "空腹血糖"},
    "Glucose_Fasting": {"min": 3.9, "max": 6.1, "unit": "mmol/L"},  # Alias
    "HbA1c": {"min": 0, "max": 6.0, "unit": "%", "note": "糖化血红蛋白"},
    "TC": {"min": 0, "max": 5.18, "unit": "mmol/L", "note": "总胆固醇"},
    "Cholesterol_Total": {"min": 0, "max": 5.18, "unit": "mmol/L"},  # Alias
    "TG": {"min": 0, "max": 1.70, "unit": "mmol/L", "note": "甘油三酯"},
    "Triglycerides": {"min": 0, "max": 1.70, "unit": "mmol/L"},  # Alias
    "LDL": {"min": 0, "max": 3.37, "unit": "mmol/L", "note": "低密度脂蛋白"},
    "LDL-C": {"min": 0, "max": 3.37, "unit": "mmol/L"},
    "Cholesterol_LDL": {"min": 0, "max": 3.37, "unit": "mmol/L"},  # Alias
    "HDL": {"min": 1.03, "max": 999, "unit": "mmol/L", "note": "高密度脂蛋白(越高越好)"},
    "HDL-C": {"min": 1.03, "max": 999, "unit": "mmol/L"},
    "Cholesterol_HDL": {"min": 1.03, "max": 999, "unit": "mmol/L"},  # Alias
    
    # ======================= 尿常规 (定性) =======================
    "KET": {"expect": ["-", "阴性", "Negative", "neg"], "note": "尿酮体"},
    "PRO": {"expect": ["-", "阴性", "Negative", "neg"], "note": "尿蛋白"},
    "GLU_U": {"expect": ["-", "阴性", "Normal", "neg"], "note": "尿糖"},
    "BLD": {"expect": ["-", "阴性", "Negative", "neg"], "note": "尿潜血"},
}


def get_range_for_indicator(indicator: str, gender: int = None) -> dict:
    """
    Get reference range for a specific indicator, considering gender if applicable.
    
    Args:
        indicator: The indicator key (e.g., "HGB", "ALT")
        gender: 1 for Male, 2 for Female (optional)
    
    Returns:
        Dict with min, max, unit keys, or None if not found
    """
    if indicator not in CHINA_REFERENCE_RANGES:
        return None
    
    ref = CHINA_REFERENCE_RANGES[indicator]
    
    # Check if gender-specific
    if "Male" in ref and "Female" in ref:
        if gender == MALE:
            return {
                "min": ref["Male"]["min"],
                "max": ref["Male"]["max"],
                "unit": ref.get("unit", "")
            }
        elif gender == FEMALE:
            return {
                "min": ref["Female"]["min"],
                "max": ref["Female"]["max"],
                "unit": ref.get("unit", "")
            }
        else:
            # Default to wider range if gender unknown
            return {
                "min": min(ref["Male"]["min"], ref["Female"]["min"]),
                "max": max(ref["Male"]["max"], ref["Female"]["max"]),
                "unit": ref.get("unit", "")
            }
    
    # Non-gender-specific
    if "min" in ref and "max" in ref:
        return {
            "min": ref["min"],
            "max": ref["max"],
            "unit": ref.get("unit", "")
        }
    
    # Qualitative test (has "expect" key)
    if "expect" in ref:
        return {"expect": ref["expect"], "note": ref.get("note", "")}
    
    return None


def is_qualitative_test(indicator: str) -> bool:
    """Check if an indicator is a qualitative (non-numeric) test."""
    if indicator not in CHINA_REFERENCE_RANGES:
        return False
    return "expect" in CHINA_REFERENCE_RANGES[indicator]
