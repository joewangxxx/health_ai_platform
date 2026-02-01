"""
Anomaly Detection Service (Task 88)
====================================
Analyzes clinical data and generates anomaly tags based on:
1. Hospital flags (H/L/↑/↓)
2. Extracted reference ranges
3. Standard medical reference database (fallback)
"""
import re
from typing import Dict, Any, List, Optional, Tuple

# ============================================================
# Standard Reference Ranges (China Medical Standards)
# ============================================================
STANDARD_RANGES = {
    # Basic Info (these don't have ranges, just for completeness)
    "Age": None,
    "Gender": None,
    "Height": None,
    "Weight": None,
    
    # Body Metrics
    "BMI": (18.5, 23.9, "体重指数"),
    "SBP": (90, 139, "收缩压"),
    "DBP": (60, 89, "舒张压"),
    
    # Blood Panel
    "WBC": (3.5, 9.5, "白细胞"),
    "NEUT_PERCENT": (40, 75, "中性粒细胞%"),
    "LYM_PERCENT": (20, 50, "淋巴细胞%"),
    "HGB": (120, 160, "血红蛋白"),  # Gender-specific in reality
    "PLT": (125, 350, "血小板"),
    
    # Liver Function
    "ALT": (0, 40, "谷丙转氨酶"),
    "AST": (0, 40, "谷草转氨酶"),
    "GGT": (0, 60, "γ-谷氨酰转肽酶"),
    "ALP": (45, 125, "碱性磷酸酶"),
    
    # Metabolism
    "Glu": (3.9, 6.1, "空腹血糖"),
    "Glucose_Fasting": (3.9, 6.1, "空腹血糖"),
    "TC": (0, 5.2, "总胆固醇"),
    "TG": (0, 1.7, "甘油三酯"),
    "HDL": (1.0, 999, "高密度脂蛋白"),  # Higher is better
    "LDL": (0, 3.4, "低密度脂蛋白"),
    "Cholesterol_Total": (0, 5.2, "总胆固醇"),
    "Triglycerides": (0, 1.7, "甘油三酯"),
    "Cholesterol_HDL": (1.0, 999, "高密度脂蛋白"),
    "Cholesterol_LDL": (0, 3.4, "低密度脂蛋白"),
    "UA": (150, 420, "尿酸"),  # Gender-specific
    "Creatinine": (44, 133, "肌酐"),
    "eGFR": (90, 999, "肾小球滤过率"),
    "HbA1c": (4.0, 6.0, "糖化血红蛋白"),
    
    # Qualitative Tests (special handling)
    "KET": "negative",  # Special: should be negative
}

# Tag Categories for different anomalies
ANOMALY_TAGS = {
    "BMI": "Metabolic_Alert",
    "SBP": "Cardiovascular_Risk",
    "DBP": "Cardiovascular_Risk",
    "Glu": "Diabetes_Risk",
    "Glucose_Fasting": "Diabetes_Risk",
    "HbA1c": "Diabetes_Risk",
    "TC": "Lipid_Abnormality",
    "TG": "Lipid_Abnormality",
    "HDL": "Lipid_Abnormality",
    "LDL": "Lipid_Abnormality",
    "ALT": "Liver_Alert",
    "AST": "Liver_Alert",
    "GGT": "Liver_Alert",
    "ALP": "Liver_Alert",
    "UA": "Kidney_Alert",
    "Creatinine": "Kidney_Alert",
    "eGFR": "Kidney_Alert",
    "WBC": "Blood_Abnormality",
    "HGB": "Blood_Abnormality",
    "PLT": "Blood_Abnormality",
    "KET": "Urinary_Abnormality",
}


class AnomalyDetectionService:
    """
    Detects anomalies in clinical data using multi-tier logic.
    """
    
    def __init__(self):
        self.standard_ranges = STANDARD_RANGES
        self.anomaly_tags = ANOMALY_TAGS
    
    def detect_anomalies(self, clinical_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main detection method.
        
        Args:
            clinical_data: Dict with indicator names as keys.
                          Values can be:
                          - Simple number/string
                          - Object with {value, unit, ref_range, hospital_flag}
        
        Returns:
            List of anomaly dicts: [{item, value, status, tag, msg}, ...]
        """
        anomalies = []
        
        for key, data in clinical_data.items():
            if data is None:
                continue
            
            # Skip non-medical fields
            if key in ["id", "user_id", "extra_findings", "extra_data"]:
                continue
            
            anomaly = self._check_single_indicator(key, data)
            if anomaly:
                anomalies.append(anomaly)
        
        # Also check extra_findings if present
        extra = clinical_data.get("extra_findings") or clinical_data.get("extra_data")
        if extra and isinstance(extra, dict):
            for key, data in extra.items():
                if data is None:
                    continue
                anomaly = self._check_single_indicator(key, data, is_extra=True)
                if anomaly:
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _check_single_indicator(
        self, 
        key: str, 
        data: Any, 
        is_extra: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Check a single indicator for anomalies.
        
        Priority:
        1. hospital_flag (H/L/↑/↓/+)
        2. ref_range from OCR
        3. STANDARD_RANGES fallback
        """
        # Normalize data structure
        if isinstance(data, dict):
            value = data.get("value")
            unit = data.get("unit", "")
            ref_range = data.get("ref_range")
            hospital_flag = data.get("hospital_flag")
        else:
            value = data
            unit = ""
            ref_range = None
            hospital_flag = None
        
        if value is None:
            return None
        
        # Priority 1: Hospital Flag
        if hospital_flag:
            status, msg = self._parse_hospital_flag(hospital_flag, key)
            if status:
                return {
                    "item": key,
                    "value": value,
                    "unit": unit,
                    "status": status,
                    "tag": self.anomaly_tags.get(key, "Clinical_Alert"),
                    "msg": msg,
                    "source": "hospital_flag"
                }
        
        # Priority 2: Extracted ref_range
        if ref_range:
            status, msg = self._check_against_range(key, value, ref_range)
            if status:
                return {
                    "item": key,
                    "value": value,
                    "unit": unit,
                    "status": status,
                    "tag": self.anomaly_tags.get(key, "Clinical_Alert"),
                    "msg": msg,
                    "ref_range": ref_range,
                    "source": "extracted_range"
                }
        
        # Priority 3: Standard ranges fallback
        std_range = self.standard_ranges.get(key)
        if std_range:
            status, msg = self._check_against_standard(key, value, std_range)
            if status:
                return {
                    "item": key,
                    "value": value,
                    "unit": unit,
                    "status": status,
                    "tag": self.anomaly_tags.get(key, "Clinical_Alert"),
                    "msg": msg,
                    "source": "standard_range"
                }
        
        return None
    
    def _parse_hospital_flag(self, flag: str, key: str) -> Tuple[Optional[str], str]:
        """Parse hospital abnormality flags."""
        flag = str(flag).strip().upper()
        
        # Map flag to status
        if flag in ["H", "HIGH", "↑", "偏高"]:
            return "High", f"{key} 偏高"
        elif flag in ["L", "LOW", "↓", "偏低"]:
            return "Low", f"{key} 偏低"
        elif flag in ["+", "++", "+++", "阳性", "弱阳性", "POSITIVE"]:
            return "Abnormal", f"{key} 阳性"
        elif flag in ["-", "阴性", "NEGATIVE"]:
            return None, ""  # Normal
        
        return None, ""
    
    def _check_against_range(
        self, 
        key: str, 
        value: Any, 
        ref_range: str
    ) -> Tuple[Optional[str], str]:
        """Check value against extracted reference range."""
        try:
            # Parse range string like "3.5-9.5" or "0~40"
            value_num = float(value)
            
            # Handle different range formats
            match = re.match(r'([\d.]+)\s*[-~]\s*([\d.]+)', str(ref_range))
            if match:
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                
                if value_num < min_val:
                    return "Low", f"{key} 偏低 (参考: {ref_range})"
                elif value_num > max_val:
                    return "High", f"{key} 偏高 (参考: {ref_range})"
            
            # Handle single bound (e.g., "<40", ">90")
            match_lt = re.match(r'<\s*([\d.]+)', str(ref_range))
            match_gt = re.match(r'>\s*([\d.]+)', str(ref_range))
            
            if match_lt and value_num >= float(match_lt.group(1)):
                return "High", f"{key} 偏高 (参考: {ref_range})"
            if match_gt and value_num <= float(match_gt.group(1)):
                return "Low", f"{key} 偏低 (参考: {ref_range})"
                
        except (ValueError, TypeError):
            # Non-numeric value (e.g., KET = "+-")
            pass
        
        return None, ""
    
    def _check_against_standard(
        self, 
        key: str, 
        value: Any, 
        std_range: Any
    ) -> Tuple[Optional[str], str]:
        """Check value against standard reference database."""
        # Special handling for qualitative tests
        if std_range == "negative":
            val_str = str(value).strip().lower()
            if val_str not in ["-", "阴性", "negative", "neg", "0"]:
                return "Abnormal", f"{key} 异常 (应为阴性)"
            return None, ""
        
        # Numeric range check
        if isinstance(std_range, tuple) and len(std_range) >= 2:
            try:
                value_num = float(value)
                min_val, max_val = std_range[0], std_range[1]
                display_name = std_range[2] if len(std_range) > 2 else key
                
                if value_num < min_val:
                    return "Low", f"{display_name} 偏低 ({value_num} < {min_val})"
                elif value_num > max_val:
                    return "High", f"{display_name} 偏高 ({value_num} > {max_val})"
            except (ValueError, TypeError):
                pass
        
        return None, ""
    
    def generate_summary(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of all anomalies for display.
        """
        if not anomalies:
            return {
                "status": "healthy",
                "count": 0,
                "message": "🎉 所有检测指标均在正常范围内",
                "categories": {}
            }
        
        # Group by tag category
        categories = {}
        for a in anomalies:
            tag = a.get("tag", "Other")
            if tag not in categories:
                categories[tag] = []
            categories[tag].append(a)
        
        # Generate summary message
        high_priority = ["Diabetes_Risk", "Cardiovascular_Risk", "Liver_Alert", "Kidney_Alert"]
        priority_items = [a for a in anomalies if a.get("tag") in high_priority]
        
        if priority_items:
            msg = f"⚠️ 发现 {len(anomalies)} 项指标异常，其中 {len(priority_items)} 项需重点关注"
        else:
            msg = f"⚠️ 发现 {len(anomalies)} 项指标轻度异常，建议复查"
        
        return {
            "status": "warning" if len(anomalies) < 3 else "alert",
            "count": len(anomalies),
            "message": msg,
            "categories": categories,
            "items": [a["item"] for a in anomalies]
        }

    def assess_inflammatory_depression(
        self, 
        clinical_data: Dict[str, Any], 
        psych_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Task 97: 心身炎症关联分析 (Psycho-Immunology)
        
        根据炎症指标 (CRP/WBC) 和心理状态 (PHQ-9) 进行精准干预分类。
        
        Args:
            clinical_data: 临床数据，包含 CRP, WBC, HS_CRP 等
            psych_data: 心理评估数据，包含 PHQ9_Score (若无则默认为 0)
        
        Returns:
            dict: 包含亚型诊断、饮食建议、补充剂建议
        """
        psych_data = psych_data or {}
        
        # ============= 1. 提取指标 =============
        # 炎症标志物
        crp = clinical_data.get("CRP") or clinical_data.get("HS_CRP")
        wbc = clinical_data.get("WBC")
        
        # 心理评分 (PHQ-9: 0-27, ≥10 为中度抑郁)
        phq9_score = psych_data.get("PHQ9_Score", 0)
        
        # 其他辅助指标
        vit_d = clinical_data.get("Lab_VitD") or clinical_data.get("LBXVIDMS")
        omega3_ratio = psych_data.get("Omega3_Ratio")  # 可选
        
        # ============= 2. 状态判定 =============
        # 炎症状态判定 (排除急性感染)
        has_inflammation = False
        inflammation_markers = []
        
        if crp is not None and crp > 3.0:
            has_inflammation = True
            inflammation_markers.append(f"CRP = {crp} mg/L (> 3.0)")
        
        if wbc is not None and wbc > 9.5:
            has_inflammation = True
            inflammation_markers.append(f"WBC = {wbc} (> 9.5)")
        
        # 抑郁状态判定
        has_depression = phq9_score >= 10
        depression_level = "无"
        if phq9_score >= 20:
            depression_level = "重度"
        elif phq9_score >= 15:
            depression_level = "中重度"
        elif phq9_score >= 10:
            depression_level = "中度"
        elif phq9_score >= 5:
            depression_level = "轻度"
        
        # 维生素D缺乏
        vit_d_deficient = vit_d is not None and vit_d < 50  # nmol/L
        
        # ============= 3. 分支判定 =============
        if has_inflammation and has_depression:
            # 炎症性情绪低落
            subtype = "Inflammatory_Depression"
            subtype_cn = "炎症性情绪低落"
            description = (
                "🔬 检测到低度慢性炎症合并情绪低落。\n"
                "这种亚型对传统抗抑郁药物反应可能较差，"
                "但对抗炎干预和生活方式调整效果更好。"
            )
            dietary_advice = [
                "🥗 采用抗炎饮食 (Anti-Inflammatory Diet)",
                "🐟 增加 Omega-3 脂肪酸摄入 (深海鱼、亚麻籽)",
                "🍵 姜黄素、绿茶等天然抗炎食物",
                "🚫 减少加工食品、精制糖、反式脂肪",
                "🥬 增加叶酸和B族维生素 (深绿色蔬菜)",
            ]
            supplement_advice = [
                "💊 Omega-3 鱼油 (EPA 1000mg/天)",
                "🧡 姜黄素 (Curcumin 500-1000mg/天)",
                "☀️ 维生素D3 (若缺乏，2000-4000 IU/天)",
                "🧬 益生菌 (肠脑轴调节)",
            ]
            lifestyle_advice = [
                "🏃 规律有氧运动 (每周 150 分钟)",
                "😴 保证充足睡眠 (7-9 小时)",
                "🧘 冥想或正念练习",
            ]
            priority = "high"
            
        elif not has_inflammation and has_depression:
            # 非炎症性情绪低落
            subtype = "Non_Inflammatory_Depression"
            subtype_cn = "非炎症性情绪低落"
            description = (
                "🧠 情绪低落但无明显炎症标志。\n"
                "建议优先考虑生活方式调整和心理干预。"
            )
            dietary_advice = [
                "🍌 增加色氨酸食物 (香蕉、坚果、火鸡)",
                "🥬 富含叶酸的食物 (菠菜、豆类)",
                "🫐 抗氧化食物 (蓝莓、黑巧克力)",
            ]
            supplement_advice = [
                "☀️ 维生素D3 (若缺乏)",
                "💛 B族维生素复合剂",
                "🌿 SAMe 或 圣约翰草 (需医生指导)",
            ]
            lifestyle_advice = [
                "🏃 每日户外运动 (光照疗法)",
                "😴 睡眠卫生调整",
                "👥 社交活动增加",
                "📝 认知行为治疗 (CBT) 推荐",
            ]
            priority = "medium"
            
        elif has_inflammation and not has_depression:
            # 炎症状态但无情绪问题
            subtype = "Subclinical_Inflammation"
            subtype_cn = "亚临床炎症状态"
            description = (
                "⚠️ 检测到低度慢性炎症，目前无明显情绪症状。\n"
                "建议积极抗炎预防，避免发展为炎症性抑郁。"
            )
            dietary_advice = [
                "🐟 Omega-3 丰富的食物",
                "🍵 抗炎香料 (姜黄、生姜)",
                "🥗 地中海饮食模式",
            ]
            supplement_advice = [
                "💊 Omega-3 鱼油",
                "☀️ 维生素D (若缺乏)",
            ]
            lifestyle_advice = [
                "🏃 规律运动",
                "😴 充足睡眠",
                "🚭 戒烟限酒",
            ]
            priority = "low"
            
        else:
            # 健康状态
            subtype = "Healthy"
            subtype_cn = "心身健康状态"
            description = "✅ 炎症指标和心理状态均正常，继续保持健康生活方式。"
            dietary_advice = ["🥗 维持均衡饮食"]
            supplement_advice = ["💊 无需额外补充"]
            lifestyle_advice = ["🏃 保持规律运动和良好睡眠"]
            priority = "normal"
        
        return {
            "subtype": subtype,
            "subtype_cn": subtype_cn,
            "description": description,
            "priority": priority,
            "markers": {
                "inflammation": {
                    "status": "elevated" if has_inflammation else "normal",
                    "details": inflammation_markers
                },
                "depression": {
                    "status": depression_level,
                    "phq9_score": phq9_score
                },
                "vitamin_d": {
                    "status": "deficient" if vit_d_deficient else "adequate",
                    "value": vit_d
                }
            },
            "recommendations": {
                "dietary": dietary_advice,
                "supplements": supplement_advice,
                "lifestyle": lifestyle_advice
            }
        }


# Singleton instance
anomaly_service = AnomalyDetectionService()

