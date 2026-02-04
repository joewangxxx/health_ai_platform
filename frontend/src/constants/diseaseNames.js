/**
 * 疾病名称中英文映射表
 * =====================
 * 
 * 用于将后端返回的疾病英文代码转换为中文显示名称。
 * 支持30+种常见慢性病和健康风险。
 * 
 * 数据来源: 基于国际疾病分类(ICD-10)和中国疾病分类标准
 * 
 * @constant {Object} DISEASE_NAME_MAP
 */

export const DISEASE_NAME_MAP = {
    // ========================================
    // 代谢类疾病 (Metabolic Disorders)
    // 与糖代谢、脂代谢、能量代谢相关的疾病
    // ========================================

    'T2D': '糖尿病',                    // Type 2 Diabetes, 二型糖尿病
    'PreDiabetes': '糖尿病前期',        // 空腹血糖受损或糖耐量异常
    'Obesity': '肥胖症',                // BMI ≥ 28 (中国标准)
    'AbdominalObesity': '腹型肥胖',     // 腰围超标，内脏脂肪堆积
    'MetabolicSyndrome': '代谢综合征',  // 多种代谢异常的聚集
    'InsulinResist': '胰岛素抵抗',      // 细胞对胰岛素反应降低

    // ========================================
    // 心血管类疾病 (Cardiovascular Diseases)
    // 影响心脏和血管的疾病
    // ========================================

    'Hypertension': '高血压',           // 血压 ≥ 140/90 mmHg
    'HighLipid': '高血脂',              // 血脂异常 (TC/LDL/TG升高)
    'HeartFailure': '心力衰竭',         // 心脏泵血功能不足
    'CoronaryHeart': '冠心病',          // 冠状动脉粥样硬化性心脏病
    'HeartAttack': '心脏病发作',        // 急性心肌梗死
    'Stroke': '中风',                   // 脑卒中 (缺血性/出血性)
    'CVD': '综合心血管病',              // Cardiovascular Disease 总体风险

    // ========================================
    // 肾脏/代谢类 (Kidney & Uric Acid)
    // 与肾功能和尿酸代谢相关
    // ========================================

    'Gout': '痛风',                     // 尿酸盐结晶沉积导致的关节炎
    'Hyperuricemia': '高尿酸血症',      // 血尿酸 > 420μmol/L (男)
    'CKD': '慢性肾病',                  // Chronic Kidney Disease
    'KidneyStones': '肾结石',           // 泌尿系统结石

    // ========================================
    // 肝脏类 (Liver Diseases)
    // 影响肝脏功能的疾病
    // ========================================

    'LiverDisease': '肝损伤风险',       // 肝功能异常 (ALT/AST升高)
    'FattyLiver': '脂肪肝',             // 非酒精性脂肪性肝病(NAFLD)

    // ========================================
    // 血液/免疫类 (Blood & Immune)
    // 影响血液成分或免疫功能的疾病
    // ========================================

    'Anemia': '贫血',                   // 血红蛋白低于正常值
    'Inflammation': '慢性炎症',         // 低度慢性炎症状态
    'IronDef': '缺铁风险',              // 铁储备不足
    'IronOverload': '铁过载风险',       // 铁蛋白过高，可能损伤器官

    // ========================================
    // 骨骼/关节类 (Musculoskeletal)
    // 影响骨骼和关节的疾病
    // ========================================

    'Osteoporosis': '骨质疏松',         // 骨密度降低，骨折风险增加
    'Arthritis': '关节炎',              // 关节炎症性疾病

    // ========================================
    // 其他疾病 (Others)
    // ========================================

    'Asthma': '哮喘',                   // 气道慢性炎症性疾病
    'Psoriasis': '银屑病',              // 慢性自身免疫性皮肤病
    'GumDisease': '牙龈病',             // 牙周疾病
    'Depression': '抑郁风险',           // 情绪低落、兴趣丧失
    'HighLead': '重金属铅风险',         // 血铅超标
    'HighCadmium': '重金属镉风险'       // 血镉超标，损害肾脏和骨骼
}

/**
 * 获取疾病中文名称
 * 
 * @param {string} key - 疾病英文代码 (如 'T2D')
 * @returns {string} 中文名称，如未找到则返回原始代码
 * 
 * @example
 * getDiseaseName('T2D')  // 返回 '糖尿病'
 * getDiseaseName('Unknown')  // 返回 'Unknown'
 */
export function getDiseaseName(key) {
    return DISEASE_NAME_MAP[key] || key
}

/**
 * 雷达图默认显示的疾病列表
 * 选择了最常见的7种慢性病用于风险雷达可视化
 * 
 * @constant {Array<string>}
 */
export const RADAR_CHART_DISEASES = [
    'T2D',              // 糖尿病 - 代谢类代表
    'Hypertension',     // 高血压 - 心血管类代表
    'HighLipid',        // 高血脂 - 血脂异常
    'FattyLiver',       // 脂肪肝 - 肝脏类代表
    'CKD',              // 慢性肾病 - 肾脏类代表
    'Gout',             // 痛风 - 尿酸代谢
    'MetabolicSyndrome' // 代谢综合征 - 综合指标
]

