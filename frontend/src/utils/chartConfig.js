/**
 * ECharts 图表配置工具
 * =====================
 * 
 * 提供通用的图表配置生成函数，支持主题切换。
 * 用于 DashboardView.vue 等视图组件的图表渲染。
 * 
 * @module utils/chartConfig
 * @requires constants/diseaseNames
 */

import { DISEASE_NAME_MAP, RADAR_CHART_DISEASES } from '../constants/diseaseNames'

// ============================================
// 主题配色常量
// ============================================

/** 浅色主题文字颜色 (Tailwind: slate-700) */
const LIGHT_TEXT_COLOR = '#334155'

/** 深色主题文字颜色 (Tailwind: slate-200) */
const DARK_TEXT_COLOR = '#e2e8f0'

/** 浅色主题分割线颜色 */
const LIGHT_SPLIT_LINE = 'rgba(0,0,0,0.1)'

/** 深色主题分割线颜色 */
const DARK_SPLIT_LINE = 'rgba(255,255,255,0.1)'

/** 主色调 - Element Plus 蓝色 */
const PRIMARY_COLOR = '#409EFF'

// ============================================
// 图表配置函数
// ============================================

/**
 * 生成雷达图配置
 * 
 * 创建一个展示多种疾病风险的雷达图配置对象。
 * 支持亮色/暗色主题切换。
 * 
 * @param {Object} riskReport - 风险报告数据对象
 * @param {Object} riskReport.T2D - 糖尿病风险数据
 * @param {number} riskReport.T2D.final_risk - 最终风险概率 (0-100)
 * @param {boolean} [isDark=false] - 是否为暗色主题
 * @returns {Object} ECharts 雷达图配置对象
 * 
 * @example
 * const option = createRadarOption(store.riskReport, isDark.value)
 * radarChart.setOption(option)
 */
export function createRadarOption(riskReport, isDark = false) {
    // 数据校验: 无风险报告时返回空配置
    if (!riskReport) return {}

    // 根据主题选择配色
    const textColor = isDark ? DARK_TEXT_COLOR : LIGHT_TEXT_COLOR
    const splitLineColor = isDark ? DARK_SPLIT_LINE : LIGHT_SPLIT_LINE

    // 从风险报告中提取指定疾病的风险值
    const keys = RADAR_CHART_DISEASES
    const values = keys.map(k => {
        // 安全取值: 如果疾病不存在则默认为0
        return riskReport[k] ? riskReport[k].final_risk : 0
    })

    // 返回 ECharts 雷达图配置
    return {
        // 雷达图坐标系配置
        radar: {
            center: ['50%', '55%'],    // 居中显示，略偏下
            radius: '70%',              // 占据容器70%的空间

            // 指示器配置: 每个疾病一个轴
            indicator: keys.map(k => ({
                name: DISEASE_NAME_MAP[k] || k,  // 显示中文名
                max: 100                          // 最大值100%
            })),

            // 分割区域样式: 透明背景
            splitArea: {
                areaStyle: { color: ['transparent'] }
            },

            // 轴名称样式
            axisName: {
                color: textColor,
                fontWeight: 'bold'
            },

            // 分割线样式
            splitLine: {
                lineStyle: { color: splitLineColor }
            },

            // 轴线样式
            axisLine: {
                lineStyle: { color: splitLineColor }
            }
        },

        // 数据系列配置
        series: [{
            type: 'radar',
            data: [{
                value: values,
                name: 'Risk Profile',

                // 填充区域样式: 半透明蓝色
                areaStyle: { color: 'rgba(64,158,255, 0.5)' },

                // 边框线样式: 实色蓝色
                lineStyle: { color: PRIMARY_COLOR, width: 3 },

                // 数据点样式
                itemStyle: { color: PRIMARY_COLOR }
            }]
        }]
    }
}

// ============================================
// 样式辅助函数
// ============================================

/**
 * 获取风险等级对应的样式类
 * 
 * 根据风险等级返回对应的 Tailwind CSS 渐变背景类。
 * 用于风险卡片的视觉区分。
 * 
 * @param {string} level - 风险等级文本 (包含 'Very High', 'High', 或其他)
 * @returns {string} Tailwind CSS 渐变背景类名
 * 
 * @example
 * getRiskLevelClass('Very High')  // 返回红色渐变
 * getRiskLevelClass('High')       // 返回橙色渐变
 * getRiskLevelClass('Low')        // 返回绿色渐变
 */
export function getRiskLevelClass(level) {
    // 🔥 防御性检查: level 为空时返回默认灰色样式
    if (!level || typeof level !== 'string') {
        return 'bg-linear-to-br from-gray-300 to-gray-400'
    }

    // Very High: 红色渐变 (最高风险)
    if (level.includes('Very High')) {
        return 'bg-linear-to-br from-red-600 to-rose-700'
    }

    // High: 橙色渐变 (高风险)
    if (level.includes('High')) {
        return 'bg-linear-to-br from-orange-400 to-red-500'
    }

    // Low/Medium: 绿色渐变 (低/中风险)
    return 'bg-linear-to-br from-emerald-400 to-teal-500'
}

/**
 * 获取修正系数标签类型
 * 
 * 根据基因/生活方式修正系数返回 Element Plus tag 组件的类型。
 * 用于 AI 决策归因表格中的视觉反馈。
 * 
 * @param {string} valStr - 修正系数字符串 (如 "x1.2", "x0.8", "x1.0")
 * @returns {string} Element Plus tag 类型 ('danger' | 'success' | 'info')
 * 
 * @example
 * getModifierTagType('x1.3')  // 返回 'danger' (增加风险)
 * getModifierTagType('x0.7')  // 返回 'success' (降低风险)
 * getModifierTagType('x1.0')  // 返回 'info' (无影响)
 */
export function getModifierTagType(valStr) {
    // 解析修正系数数值
    const val = parseFloat(String(valStr).replace('x', ''))

    // > 1.1: 风险增加 (红色警告)
    if (val > 1.1) return 'danger'

    // < 0.9: 风险降低 (绿色好)
    if (val < 0.9) return 'success'

    // 0.9 ~ 1.1: 基本无影响 (蓝色信息)
    return 'info'
}

