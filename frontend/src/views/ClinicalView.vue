<template>
    <div class="p-6 h-full flex flex-col items-center">
        <div class="w-full max-w-4xl">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                临床体检 (Clinical Profile)
            </h1>

            <GlassCard :glowProximity="100">
                <template #header>
                    <div class="flex justify-between items-center text-sm text-slate-500 dark:text-slate-400">
                        <div class="flex items-center gap-4">
                            <span>请录入最新的体检报告数据</span>
                            <GlassButton size="sm" type="danger" @click="handleClearAll">
                                <el-icon class="mr-1">
                                    <Delete />
                                </el-icon> 清空数据
                            </GlassButton>
                        </div>
                        <div class="flex items-center gap-2">
                            <div data-testid="ocr-upload" class="upload-demo inline-block">
                                <input ref="ocrFileInput" data-testid="ocr-file-input" class="sr-only" type="file"
                                    accept=".jpg,.jpeg,.png,.pdf" @change="handleOcrFileSelection" />
                                <GlassButton size="sm" :loading="ocrLoading" @click="triggerOcrFileInput">
                                    <el-icon class="mr-2">
                                        <Camera />
                                    </el-icon> 智能识别体检单
                                </GlassButton>
                            </div>
                            <div data-testid="csv-upload" class="upload-demo inline-block">
                                <input ref="csvFileInput" data-testid="csv-file-input" class="sr-only" type="file"
                                    accept=".csv" @change="handleCsvFileSelection" />
                                <GlassButton size="sm" :loading="csvImportLoading" @click="triggerCsvFileInput">
                                    <el-icon class="mr-2">
                                        <Upload />
                                    </el-icon> 导入CSV健康数据
                                </GlassButton>
                            </div>
                        </div>
                    </div>
                </template>

                <!-- 任务 89：异常指标摘要 -->
                <div v-if="anomalySummary && anomalySummary.count > 0" class="mb-4 p-4 rounded-xl border-2"
                    :class="anomalySummary.status === 'alert' ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700' : 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'">
                    <div class="flex items-start gap-3">
                        <span class="text-2xl">{{ anomalySummary.status === 'alert' ? '警' : '查' }}</span>
                        <div class="flex-1">
                            <h4 class="font-bold text-slate-800 dark:text-white">健康警报摘要</h4>
                            <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{{ anomalySummary.message }}</p>
                            <div class="flex flex-wrap gap-2 mt-2">
                                <el-tag v-for="item in anomalySummary.items" :key="item" :type="getAnomalyTagType(item)"
                                    size="small" round>
                                    {{ getAnomalyLabel(item) }}
                                </el-tag>
                            </div>
                        </div>
                        <el-button size="small" type="primary" plain @click="runAnomalyDetection"
                            :loading="anomalyLoading">
                            重新检测
                        </el-button>
                    </div>
                </div>

                <div v-if="ocrDocumentStatus" data-testid="ocr-document-status-banner" class="mb-4 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
                    <div class="flex items-start justify-between gap-4">
                        <div>
                            <div class="font-bold text-slate-800 dark:text-white">{{ ocrDocumentStatus.title }}</div>
                            <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{{ ocrDocumentStatus.description }}</p>
                            <p v-if="ocrDocumentStatus.reason" class="text-xs text-slate-400 mt-1">{{ ocrDocumentStatus.reason }}</p>
                        </div>
                        <el-tag :type="ocrDocumentStatus.status === 'error' ? 'danger' : (ocrDocumentStatus.status === 'stored_unprocessed' ? 'warning' : 'success')" size="small" effect="dark">
                            {{ ocrDocumentStatus.status }}
                        </el-tag>
                    </div>
                </div>

                <div v-if="analysisContextDisplay" data-testid="analysis-context-banner" class="mb-4 p-4 rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50/80 dark:bg-blue-900/20">
                    <div class="flex items-start justify-between gap-4">
                        <div>
                            <div class="font-bold text-slate-800 dark:text-white" data-testid="analysis-context-mode">{{ analysisContextDisplay.modeLabel }}</div>
                            <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">
                                已识别 {{ analysisContextDisplay.counts?.recognized ?? 0 }} 项，已推导 {{ analysisContextDisplay.counts?.derived ?? 0 }} 项，待补充 {{ analysisContextDisplay.counts?.missing ?? 0 }} 项。
                            </p>
                            <p v-if="analysisContextDisplay.provisionalReasons.length" class="text-xs text-blue-700 dark:text-blue-300 mt-2">
                                {{ analysisContextDisplay.provisionalReasons.map(item => item.code || item).join(' · ') }}
                            </p>
                            <div v-if="analysisContextDisplay.blockingFields.length" class="flex flex-wrap gap-2 mt-2">
                                <el-tag v-for="field in analysisContextDisplay.blockingFields" :key="field" size="small" type="warning" effect="plain">
                                    {{ field }}
                                </el-tag>
                            </div>
                        </div>
                        <el-tag size="small" type="primary" effect="dark">{{ analysisContextDisplay.modeLabel }}</el-tag>
                    </div>
                </div>

                <el-form label-position="left" label-width="110px" size="default" class="clinical-form grid gap-6">

                    <!-- 基础信息 -->
                    <div class="p-4 rounded-xl bg-white/30 dark:bg-black/20 border border-gray-100 dark:border-white/5">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">基本信息 (Basic)</h3>
                        <div class="grid grid-cols-2 gap-6">
                            <el-form-item label="年龄 (Age)" :class="{ 'ocr-updated': isOcrUpdated('Age') }">
                                <el-input-number v-model="profile.Age" :min="0" :max="120" controls-position="right"
                                    class="w-full" placeholder="岁" />
                            </el-form-item>
                            <el-form-item label="性别 (Gender)" :class="{ 'ocr-updated': isOcrUpdated('Gender') }">
                                <el-select v-model="profile.Gender" class="w-full">
                                    <el-option label="男 (Male)" :value="1" />
                                    <el-option label="女 (Female)" :value="2" />
                                </el-select>
                            </el-form-item>
                        </div>
                    </div>

                    <!-- 身体指标 -->
                    <div class="p-4 rounded-xl bg-white/30 dark:bg-black/20 border border-gray-100 dark:border-white/5">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">身体指标 (Metrics)</h3>
                        <div class="grid grid-cols-2 gap-6">
                            <el-form-item label="身高 (cm)" :class="{ 'ocr-updated': isOcrUpdated('Height') }">
                                <el-input-number v-model="profile.Height" :min="30" :max="250" controls-position="right"
                                    class="w-full" placeholder="cm" />
                            </el-form-item>
                            <el-form-item label="体重 (kg)" :class="{ 'ocr-updated': isOcrUpdated('Weight') }">
                                <el-input-number v-model="profile.Weight" :min="1" :max="300" :precision="1"
                                    controls-position="right" class="w-full" placeholder="kg" />
                            </el-form-item>
                        </div>
                        <div class="grid grid-cols-2 gap-6 mt-2">
                            <el-form-item label="BMI" :class="{ 'ocr-updated': isOcrUpdated('BMI') }">
                                <el-input-number v-model="profile.BMI" :precision="1" disabled controls-position="right"
                                    class="w-full" />
                            </el-form-item>
                            <el-form-item label="腰围 (cm)">
                                <el-input-number v-model="profile.WaistCircum" :min="30" :max="200" :precision="1"
                                    controls-position="right" class="w-full" placeholder="cm" />
                            </el-form-item>
                        </div>
                        <div class="mt-4">
                            <el-form-item label="血压 (BP)"
                                :class="{ 'ocr-updated': isOcrUpdated('SBP') || isOcrUpdated('DBP') }">
                                <div class="flex gap-2 w-full">
                                    <el-input-number v-model="profile.SBP" :min="50" :max="300" placeholder="收缩压"
                                        controls-position="right" class="flex-1" />
                                    <span class="text-gray-400">/</span>
                                    <el-input-number v-model="profile.DBP" :min="30" :max="200" placeholder="舒张压"
                                        controls-position="right" class="flex-1" />
                                </div>
                            </el-form-item>
                        </div>
                    </div>

                    <!-- 生化指标 -->
                    <div class="p-4 rounded-xl bg-white/30 dark:bg-black/20 border border-gray-100 dark:border-white/5">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">生化指标 (Bio-Markers)
                        </h3>
                        <div class="grid grid-cols-2 gap-6">
                            <el-form-item label="空腹血糖"
                                :class="{ 'ocr-updated': isOcrUpdated('Glucose_Fasting'), 'guided-missing': isGuidedMissing('Glucose_Fasting') }">
                                <el-input-number v-model="profile.Glucose_Fasting" :min="1" :max="50" :precision="1"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Glucose_Fasting', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="糖化血红蛋白"
                                :class="{ 'ocr-updated': isOcrUpdated('HbA1c'), 'guided-missing': isGuidedMissing('HbA1c') }">
                                <el-input-number v-model="profile.HbA1c" :min="4" :max="15" :precision="1" :step="0.1"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('HbA1c', '%')" />
                            </el-form-item>
                            <el-form-item label="总胆固醇"
                                :class="{ 'ocr-updated': isOcrUpdated('Cholesterol_Total'), 'guided-missing': isGuidedMissing('Cholesterol_Total') }">
                                <el-input-number v-model="profile.Cholesterol_Total" :min="0" :max="20" :precision="2"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Cholesterol_Total', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="甘油三酯"
                                :class="{ 'ocr-updated': isOcrUpdated('Triglycerides'), 'guided-missing': isGuidedMissing('Triglycerides') }">
                                <el-input-number v-model="profile.Triglycerides" :min="0" :max="30" :precision="2"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Triglycerides', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="高密度脂蛋白"
                                :class="{ 'ocr-updated': isOcrUpdated('Cholesterol_HDL'), 'guided-missing': isGuidedMissing('Cholesterol_HDL') }">
                                <el-input-number v-model="profile.Cholesterol_HDL" :min="0" :max="5" :precision="2"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Cholesterol_HDL', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="睡眠时长(h)">
                                <el-input-number v-model="profile.Sleep_Hours" :min="0" :max="24" :step="0.5"
                                    controls-position="right" class="w-full" />
                            </el-form-item>
                            <el-form-item label="eGFR (肾)"
                                :class="{ 'ocr-updated': isOcrUpdated('eGFR'), 'guided-missing': isGuidedMissing('eGFR') }">
                                <el-input-number v-model="profile.eGFR" :min="0" controls-position="right"
                                    class="w-full" :placeholder="getPlaceholder('eGFR', 'mL/min')" />
                            </el-form-item>
                            <el-form-item label="ALT (肝)"
                                :class="{ 'ocr-updated': isOcrUpdated('ALT'), 'guided-missing': isGuidedMissing('ALT') }">
                                <el-input-number v-model="profile.ALT" :min="0" controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('ALT', 'U/L')" />
                            </el-form-item>
                        </div>

                        <!-- V10 新增指标 -->
                        <div class="grid grid-cols-2 gap-6 mt-6 border-t border-gray-100 dark:border-white/5 pt-6">
                            <el-form-item label="白细胞 (WBC)" :class="{ 'ocr-updated': isOcrUpdated('WBC') }">
                                <el-input-number v-model="profile.WBC" :min="0" :precision="1" :step="0.1"
                                    controls-position="right" class="w-full" placeholder="10^9/L" />
                            </el-form-item>
                            <el-form-item label="血小板 (PLT)" :class="{ 'ocr-updated': isOcrUpdated('Platelet') }">
                                <el-input-number v-model="profile.Platelet" :min="0" controls-position="right"
                                    class="w-full" placeholder="10^9/L" />
                            </el-form-item>
                            <el-form-item label="GGT (肝)" :class="{ 'ocr-updated': isOcrUpdated('GGT') }">
                                <el-input-number v-model="profile.GGT" :min="0" controls-position="right" class="w-full"
                                    placeholder="U/L" />
                            </el-form-item>
                            <el-form-item label="ALP (肝胆)"
                                :class="{ 'ocr-updated': isOcrUpdated('ALP'), 'guided-missing': isGuidedMissing('ALP') }">
                                <el-input-number v-model="profile.ALP" :min="0" controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('ALP', 'U/L')" />
                            </el-form-item>
                            <el-form-item label="肌酐 (Cr)"
                                :class="{ 'ocr-updated': isOcrUpdated('Creatinine'), 'guided-missing': isGuidedMissing('Creatinine') }">
                                <el-input-number v-model="profile.Creatinine" :min="0" :max="2000"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Creatinine', 'umol/L')" />
                            </el-form-item>
                        </div>
                    </div>

                    <!-- 任务 74：补充数据（非结构化） -->
                    <el-collapse v-if="profile.extra_data"
                        class="rounded-xl border border-gray-100 dark:border-white/5 overflow-hidden">
                        <el-collapse-item name="1">
                            <template #title>
                                <div class="px-4 font-bold text-slate-500 dark:text-slate-400 flex items-center gap-2">
                                    其他检测项 (Extra Findings)
                                    <el-tag v-if="Object.keys(profile.extra_data).length" size="small" type="info"
                                        round>
                                        {{ Object.keys(profile.extra_data).length }}
                                    </el-tag>
                                </div>
                            </template>
                            <div class="p-4 bg-white/30 dark:bg-black/20">
                                <div v-if="!Object.keys(profile.extra_data).length"
                                    class="text-sm text-center text-slate-400 py-4">
                                    暂无额外检测数据
                                </div>
                                <div v-else class="grid grid-cols-2 gap-4">
                                    <div v-for="(val, key) in profile.extra_data" :key="key"
                                        class="flex items-center justify-between p-2 bg-white/50 dark:bg-black/30 rounded border border-slate-100 dark:border-white/5">
                                        <div class="text-sm">
                                            <div class="text-slate-500 dark:text-slate-400 text-xs">{{ key }}</div>
                                            <div class="font-medium text-slate-700 dark:text-white">{{ val }}</div>
                                        </div>
                                        <el-button link type="danger" size="small" @click="removeExtraItem(key)">
                                            <el-icon>
                                                <Delete />
                                            </el-icon>
                                        </el-button>
                                    </div>
                                </div>
                                <!-- 手动添加（可选，后续增强） -->
                            </div>
                        </el-collapse-item>
                    </el-collapse>

                </el-form>

                <div class="mt-8 flex justify-end gap-3">
                    <GlassButton size="sm" @click="saveData">
                        <el-icon class="mr-2">
                            <Check />
                        </el-icon> 暂存数据
                    </GlassButton>
                    <GlassButton @click="saveToCloud" :disabled="saving">
                        {{ saving ? '保存中...' : '保存健康档案' }}
                    </GlassButton>
                    <GlassButton @click="$router.push('/genomics')">
                        下一步：基因组学 <el-icon class="ml-2">
                            <ArrowRight />
                        </el-icon>
                    </GlassButton>
                </div>
            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, nextTick, h } from 'vue'
import { storeToRefs } from 'pinia'
import { useHealthStore } from '../stores/healthStore'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import { ArrowRight, Check, Camera, Delete, Upload } from '@element-plus/icons-vue'
import axios from 'axios'
import { useToast } from '../composables/useToast'
import { ElNotification, ElMessageBox } from 'element-plus'

const store = useHealthStore()
const { userProfile: profile, importData, analysisContext } = storeToRefs(store)
const saving = ref(false)
const ocrLoading = ref(false)
const csvImportLoading = ref(false)
const ocrFileInput = ref(null)
const csvFileInput = ref(null)
const { showToast } = useToast()

const fieldStateSummary = computed(() => analysisContext.value?.field_state_summary || null)
const analysisMode = computed(() => analysisContext.value?.analysis_mode || null)
const provisionalReasons = computed(() => Array.isArray(analysisContext.value?.provisional_reasons) ? analysisContext.value.provisional_reasons : [])
const blockingFields = computed(() => Array.isArray(analysisContext.value?.blocking_fields) ? analysisContext.value.blocking_fields : [])
const fieldStateCounts = computed(() => {
    const summary = fieldStateSummary.value
    if (!summary) return null
    return {
        recognized: summary.recognized.length,
        derived: summary.derived.length,
        missing: summary.missing.length,
        user_confirmed: summary.user_confirmed.length,
        user_entered: summary.user_entered.length,
    }
})

const ocrDocumentStatus = computed(() => {
    const status = importData.value?.ocr_processing_status?.status
    if (!status) return null

    const statusMap = {
        success: {
            title: '已提取结构化数据',
            description: '文档中的结构化字段已进入分析流程。',
        },
        partial_success: {
            title: '部分识别',
            description: '文档已保存，只有部分字段可用于自动回填。',
        },
        stored_unprocessed: {
            title: '已保存待识别',
            description: '文档已入库，但当前 OCR provider 不可用或尚未完成识别。',
        },
        error: {
            title: '识别失败',
            description: '文档已上传，但解析失败，需要稍后重试或人工处理。',
        },
    }

    return {
        status,
        ...statusMap[status],
        reason: importData.value?.ocr_processing_status?.reason || '',
    }
})

const analysisContextDisplay = computed(() => {
    if (!analysisContext.value) return null
    const modeMap = {
        final: '正式分析',
        provisional: '临时分析',
        blocked: '分析受阻',
    }

    return {
        mode: analysisMode.value || 'final',
        modeLabel: modeMap[analysisMode.value || 'final'] || '正式分析',
        counts: fieldStateCounts.value,
        provisionalReasons: provisionalReasons.value,
        blockingFields: blockingFields.value,
    }
})

// 任务 126：OCR 更新字段高亮
const ocrUpdatedFields = ref(new Set())
const isOcrUpdated = (fieldName) => ocrUpdatedFields.value.has(fieldName)

// 任务 131：OCR 撤销快照（保存 OCR 前的表单状态）
const lastProfileSnapshot = ref(null)

// OCR 占位文案优先采用“引导补全”语义，减少歧义。
const getPlaceholder = () => '待补充'

const isGuidedMissing = (fieldName) => {
    const summary = fieldStateSummary.value
    if (!summary) return false
    return Array.isArray(summary.missing) && summary.missing.includes(fieldName)
}

const refreshBackendAnalysisContext = async () => {
    store.updateProfile(profile.value)
    return store.fetchLatestRiskReport(profile.value)
}

// ============================================
// 任务 128：eGFR 智能填充策略（CKD-EPI 2021）
// ============================================

/**
 * CKD-EPI 2021 公式计算 eGFR（无种族校正版本）
 * @param {number} creatinine - 血清肌酐 (umol/L)
 * @param {number} age - 年龄 (岁)
 * @param {number} gender - 性别 (1=男, 2=女)
 * @returns {number|null} eGFR (mL/min/1.73m²) 或 null（若输入无效）
 */
const calculateCKDEPI2021 = (creatinine, age, gender) => {
    // 参数校验
    if (!creatinine || !age || !gender) return null
    if (creatinine <= 0 || age <= 0) return null

    // 将 umol/L 转换为 mg/dL（公式要求）
    const Scr = creatinine / 88.4

    // 性别参数
    const isFemale = gender === 2
    const kappa = isFemale ? 0.7 : 0.9
    const alpha = isFemale ? -0.241 : -0.302
    const sexMultiplier = isFemale ? 1.012 : 1.0

    // CKD-EPI 2021 计算公式
    const ratio = Scr / kappa
    const minRatio = Math.min(ratio, 1)
    const maxRatio = Math.max(ratio, 1)

    const eGFR = 142 * Math.pow(minRatio, alpha) * Math.pow(maxRatio, -1.200) * Math.pow(0.9938, age) * sexMultiplier

    return parseFloat(eGFR.toFixed(1))
}

/**
 * Task 128: 智能计算 eGFR - 仅当 eGFR 为空且有肌酐时自动计算
 * OCR 优先: 如果 OCR 已填入 eGFR，不覆盖
 */
const tryAutoCalculateEGFR = () => {
    // 检查当前 eGFR 是否为空，避免覆盖已有值
    const currentEGFR = profile.value.eGFR
    if (currentEGFR !== null && currentEGFR !== undefined && currentEGFR !== '') {
        console.log('eGFR 已有值，跳过自动计算')
        return
    }

    // 检查必要参数
    const age = profile.value.Age
    const gender = profile.value.Gender
    const creatinine = profile.value.Creatinine

    if (!age || !gender || !creatinine) {
        return // 参数不全，无法计算
    }

    // 执行计算
    const calculatedEGFR = calculateCKDEPI2021(creatinine, age, gender)
    if (calculatedEGFR !== null) {
        profile.value.eGFR = calculatedEGFR
        console.log(`eGFR 自动计算: Cr=${creatinine} -> eGFR=${calculatedEGFR}`)
    }
}

// 任务 128：监听年龄、性别、肌酐变化并自动触发 eGFR 计算
watch(
    [() => profile.value.Age, () => profile.value.Gender, () => profile.value.Creatinine],
    () => {
        tryAutoCalculateEGFR()
    },
    { immediate: false }
)

// 任务 89：异常检测状态
const anomalyLoading = ref(false)
const anomalies = ref([])
const anomalySummary = ref(null)
const anomalyMap = ref({}) // key -> anomaly object for quick lookup

// 任务 89：异常展示辅助函数
const getAnomalyTagType = (item) => {
    const a = anomalyMap.value[item]
    if (!a) return 'info'
    if (a.status === 'High') return 'danger'
    if (a.status === 'Low') return 'warning'
    if (a.status === 'Abnormal') return 'danger'
    return 'warning'
}

const getAnomalyLabel = (item) => {
    const a = anomalyMap.value[item]
    if (!a) return item
    return `${item}: ${a.msg || a.status}`
}

const isFieldAbnormal = (fieldName) => {
    return !!anomalyMap.value[fieldName]
}

const getFieldAnomaly = (fieldName) => {
    return anomalyMap.value[fieldName]
}

// 任务 89：执行异常检测
const runAnomalyDetection = async () => {
    anomalyLoading.value = true
    try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/analysis/detect_anomalies/profile', {
            headers: { Authorization: `Bearer ${token}` }
        })
        if (response.data.status === 'success') {
            anomalies.value = response.data.anomalies || []
            anomalySummary.value = response.data.summary

            // 构建指标查找映射
            const map = {}
            anomalies.value.forEach(a => { map[a.item] = a })
            anomalyMap.value = map

            if (anomalySummary.value?.count > 0) {
                ElNotification.warning({
                    title: '健康检测完成',
                    message: anomalySummary.value.message,
                    duration: 5000
                })
            } else {
                ElNotification.success({
                    title: '检测完成',
                    message: '所有指标均在正常范围内。',
                    duration: 3000
                })
            }
        }
    } catch (e) {
        console.error("Anomaly detection failed:", e)
    } finally {
        anomalyLoading.value = false
    }
}

// 🔥 任务 59：页面挂载时检查是否存在导入数据
onMounted(async () => {
    const importedContext = importData.value
    if (importedContext && typeof importedContext === 'object') {
        console.log("检测到 importData，正在自动回填表单...")
        const preserveAnalysisContext = Boolean(importedContext.analysis_context)
        store.clearImportData(preserveAnalysisContext)  // Prevent re-load on refresh

        if (importedContext.ocr_summary) {
            applyOcrDataToProfile(importedContext.ocr_summary)

            if (!preserveAnalysisContext) {
                await refreshBackendAnalysisContext()
            }

            ElNotification.success({
                title: '历史数据已载入',
                message: '已自动回填可识别字段，请核对后再继续分析。',
                duration: 5000
            })
        } else if (importedContext.ocr_processing_status) {
            ElNotification({
                title: '文档已保存，待识别',
                message: '当前文档还没有可用的结构化 OCR 数据，请稍后重试或继续手动补全。',
                type: 'warning',
                duration: 5000
            })
        }
    }
})

// 复用函数：将 OCR/导入数据应用到当前档案
const applyOcrDataToProfile = (data, options = {}) => {
    const { overwrite = false } = options
    const isValidValue = (val) => {
        if (val === null || val === undefined) return false
        if (val === 'null' || val === 'undefined') return false
        if (typeof val === 'string' && val.trim() === '') return false
        if (typeof val === 'number' && isNaN(val)) return false
        return true
    }

    const flattenStructuredPayload = (source) => {
        if (!source || typeof source !== 'object') return {}

        const flattened = { ...source }
        const mergeSection = (section) => {
            if (!section || typeof section !== 'object' || Array.isArray(section)) return
            for (const [key, value] of Object.entries(section)) {
                flattened[key] = value && typeof value === 'object' && 'value' in value ? value.value : value
            }
        }

        if (source.schema_version === 'ocr_summary.v1') {
            mergeSection(source.metrics)
            mergeSection(source.patient_context)
            mergeSection(source.extra_findings)
        }

        return flattened
    }

    const sourceData = flattenStructuredPayload(data)

    // 任务 67/68：增强映射（年龄、性别、身高、体重）
    const mapping = {
        'Age': 'Age',
        'Gender': 'Gender',
        'Height': 'Height',
        'Weight': 'Weight',
        'BMI': 'BMI',
        'SBP': 'SBP',
        'DBP': 'DBP',
        'Glu': 'Glucose_Fasting',
        'Glucose': 'Glucose_Fasting',
        'HbA1c': 'HbA1c',
        'TC': 'Cholesterol_Total',
        'TG': 'Triglycerides',
        'HDL': 'Cholesterol_HDL',
        'LDL': 'Cholesterol_LDL',
        'ALT': 'ALT',
        'AST': 'AST',
        'GGT': 'GGT',
        'ALP': 'ALP',
        'eGFR': 'eGFR',
        'Creatinine': 'Creatinine',
        'Cr': 'Creatinine',
        'CREA': 'Creatinine',
        'WBC': 'WBC',
        'PLT': 'Platelet',
        'Platelet': 'Platelet',
        'HGB': 'HGB'
    }

    let filledCount = 0
    let skippedCount = 0

    if (sourceData.extra_findings && typeof sourceData.extra_findings === 'object') {
        console.log("发现 Extra Findings:", sourceData.extra_findings)
        if (!profile.value.extra_data) profile.value.extra_data = {}
        for (const [k, v] of Object.entries(sourceData.extra_findings)) {
            if (isValidValue(v)) {
                profile.value.extra_data[k] = v
            }
        }
    }

    const skipKeys = new Set(['schema_version', 'metrics', 'patient_context', 'extra_findings', 'raw_text', 'confidence', 'page', 'pages', 'status'])

    for (const [key, val] of Object.entries(sourceData)) {
        if (skipKeys.has(key)) continue
        if (!isValidValue(val)) {
            skippedCount++
            continue
        }

        const profileKey = mapping[key] || (profile.value.hasOwnProperty(key) ? key : null)
        if (!profileKey || !profile.value.hasOwnProperty(profileKey)) continue

        const currentVal = profile.value[profileKey]
        const isEmpty = currentVal === null || currentVal === undefined || currentVal === ''
        if (!overwrite && !isEmpty) continue

        if (profileKey === 'Gender') {
            if (val === '男' || val === '男性' || val === 'Male' || val === 'M' || val === 1 || val === '1') {
                profile.value[profileKey] = 1
            } else if (val === '女' || val === '女性' || val === 'Female' || val === 'F' || val === 2 || val === '2') {
                profile.value[profileKey] = 2
            } else {
                continue
            }
        } else {
            const numVal = parseFloat(val)
            if (!isNaN(numVal)) {
                profile.value[profileKey] = numVal
            } else if (typeof val === 'string') {
                profile.value[profileKey] = val
            } else {
                continue
            }
        }

        filledCount++
        ocrUpdatedFields.value.add(profileKey)
    }

    if (skippedCount > 0) {
        console.log(`Smart Merge: Skipped ${skippedCount} empty/null fields (preserved existing data)`)
    }

    if (ocrUpdatedFields.value.size > 0) {
        console.log(`Highlighting ${ocrUpdatedFields.value.size} OCR-updated fields`)
        setTimeout(() => {
            ocrUpdatedFields.value.clear()
        }, 2500)
    }

    return filledCount
}

const formatUploadErrorMessage = (error, fallback) => {
    const detail = error.response?.data?.detail
    const message = error.response?.data?.message
    if (Array.isArray(detail)) {
        return detail.map(item => item?.msg || JSON.stringify(item)).join('；')
    }
    if (detail && typeof detail === 'object') {
        return detail.message || detail.msg || JSON.stringify(detail)
    }
    return detail || message || error.message || fallback
}

// ============================================
// 任务 131：OCR 撤销功能（撤销）
// ============================================
const handleUndoOcr = async () => {
    // 检查是否存在可用快照
    if (!lastProfileSnapshot.value) {
        showToast('没有可撤销的操作', 'warning')
        return
    }

    try {
        // 恢复快照数据到当前档案
        Object.keys(lastProfileSnapshot.value).forEach(key => {
            profile.value[key] = lastProfileSnapshot.value[key]
        })

        // 更新状态仓库并保存到云端
        store.updateProfile(profile.value)
        const saveSuccess = await store.saveProfileToCloud()

        if (saveSuccess) {
            ElNotification({
                title: '已撤销 OCR 变更',
                message: '已恢复到识别前的数据状态并同步到云端。',
                type: 'success',
                duration: 4000
            })
        } else {
            showToast('撤销成功但同步失败，请手动保存', 'warning')
        }

        // 清空快照
        lastProfileSnapshot.value = null

        // 清除 OCR 相关状态
        ocrUpdatedFields.value.clear()

    } catch (e) {
        console.error('Undo failed:', e)
        showToast('撤销失败: ' + e.message, 'error')
    }
}

const makeUploadFile = (file) => file ? { name: file.name, raw: file } : null

const triggerOcrFileInput = () => {
    ocrFileInput.value?.click()
}

const triggerCsvFileInput = () => {
    csvFileInput.value?.click()
}

const handleOcrFileSelection = async (event) => {
    const input = event.target
    const file = input?.files?.[0]
    await handleOcrUpload(makeUploadFile(file))
    if (input) input.value = ''
}

const handleCsvFileSelection = async (event) => {
    const input = event.target
    const file = input?.files?.[0]
    await handleCsvImport(makeUploadFile(file))
    if (input) input.value = ''
}

// 📷 OCR 上传处理流程
const handleOcrUpload = async (uploadFile) => {
    if (!uploadFile || !uploadFile.raw) return

    ocrLoading.value = true
    const formData = new FormData()
    formData.append('file', uploadFile.raw)

    try {
        showToast('正在识别体检单，请稍候...', 'info')
        const response = await axios.post('/api/v1/ocr/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })

        const res = response.data || {}
        const ocrStatus = res.ocr_processing_status || res.document?.ocr_processing_status || res.data?.ocr_processing_status || null
        const structuredData = res.ocr_summary
            || res.document?.ocr_summary
            || res.data?.ocr_summary
            || (res.data && !res.data.status ? res.data : null)
            || (res.schema_version ? res : null)
        const documentContext = {
            ocr_summary: structuredData,
            ocr_processing_status: ocrStatus,
            file_name: res.document?.file_name || res.file_name || uploadFile.raw?.name || '',
            file_url: res.document?.file_url || res.file_url || '',
            analysis_context: res.analysis_context || null,
        }

        if (documentContext.ocr_processing_status || documentContext.ocr_summary) {
            store.setImportData(documentContext)
        }

        const status = ocrStatus?.status || res.status
        const hasStructuredData = Boolean(structuredData && typeof structuredData === 'object')

        if (res.status === 'error' || status === 'error') {
            showToast(res.message || ocrStatus?.reason || '识别失败', 'error')
            return
        }

        if (hasStructuredData) {
            lastProfileSnapshot.value = JSON.parse(JSON.stringify(profile.value))
            const filledCount = applyOcrDataToProfile(structuredData)
            await nextTick()

            if (filledCount > 0) {
                try {
                    const refreshedAnalysis = await refreshBackendAnalysisContext()
                    const saveSuccess = await store.saveProfileToCloud()

                    if (saveSuccess) {
                        ElNotification({
                            title: status === 'partial_success' ? '已保存并部分识别' : '识别完成并已自动保存',
                            message: h('div', { style: 'line-height: 1.6' }, [
                                h('span', null, `已回填 ${filledCount} 项结构化数据。`),
                                h('br'),
                                h('button', {
                                    class: 'el-button el-button--primary is-link',
                                    style: 'padding: 0; margin-top: 8px; font-size: 13px;',
                                    onClick: handleUndoOcr
                                }, '↩ 撤销本次回填')
                            ]),
                            type: 'success',
                            duration: 8000,
                        })
                    } else if (refreshedAnalysis) {
                        ElNotification({
                            title: status === 'partial_success' ? '已部分识别' : '识别完成',
                            message: `已回填 ${filledCount} 项数据，但自动保存失败。当前缺失字段引导已按最新分析结果更新，请手动点击"保存到云端"。`,
                            type: 'warning',
                            duration: 6000,
                        })
                    } else {
                        ElNotification({
                            title: '提取成功但自动保存失败',
                            message: `已回填 ${filledCount} 项数据，请手动点击"保存到云端"。`,
                            type: 'warning',
                            duration: 6000,
                        })
                    }
                } catch (saveError) {
                    console.error('Auto-save failed:', saveError)
                    ElNotification({
                        title: '提取成功但自动保存失败',
                        message: `已回填 ${filledCount} 项数据，请手动点击"保存到云端"。`,
                        type: 'warning',
                        duration: 6000,
                    })
                }
            } else {
                showToast(status === 'partial_success' ? '已保存并识别到少量字段，建议继续补全' : '识别成功，但未匹配到有效指标数据', 'warning')
            }
            return
        }

        if (status === 'stored_unprocessed') {
            showToast('文档已保存，当前 OCR 不可用，已进入待识别状态', 'warning')
            return
        }

        if (status === 'partial_success') {
            showToast('文档已保存，已识别部分结构化数据', 'warning')
            return
        }

        showToast(res.message || '上传完成，但未返回可用 OCR 结果', 'warning')
    } catch (e) {
        console.error(e)
        showToast('识别失败: ' + (e.response?.data?.detail || e.response?.data?.message || e.message), 'error')
    } finally {
        ocrLoading.value = false
    }
}

const handleCsvImport = async (uploadFile) => {
    if (!uploadFile || !uploadFile.raw) return

    csvImportLoading.value = true
    const formData = new FormData()
    formData.append('file', uploadFile.raw)

    try {
        showToast('正在导入CSV健康数据，请稍候...', 'info')
        const response = await axios.post('/api/v1/profile/import-csv', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })

        const res = response.data || {}
        const importedProfile = res.profile

        if (!importedProfile || typeof importedProfile !== 'object' || Array.isArray(importedProfile)) {
            showToast(res.message || 'CSV导入完成，但未返回可填充的 profile 数据', 'warning')
            return
        }

        lastProfileSnapshot.value = JSON.parse(JSON.stringify(profile.value))
        const filledCount = applyOcrDataToProfile(importedProfile, { overwrite: true })

        if (filledCount > 0) {
            ElNotification({
                title: 'CSV健康数据已导入',
                message: `已回填 ${filledCount} 项字段，请核对后再手动保存健康档案。`,
                type: 'success',
                duration: 6000,
            })
        } else {
            showToast('CSV导入完成，但没有匹配到可填充的非空字段', 'warning')
        }
    } catch (e) {
        console.error(e)
        showToast('CSV导入失败: ' + formatUploadErrorMessage(e, '请检查文件或选择 demo_patient_id 后重试'), 'error')
    } finally {
        csvImportLoading.value = false
    }
}

// 任务 71：清空全部数据
const handleClearAll = async () => {
    try {
        await ElMessageBox.confirm(
            '确定要清空当前页面上的所有已录入数据吗？此操作不可撤销。',
            '清空确认',
            { confirmButtonText: '清空', cancelButtonText: '取消', type: 'warning' }
        )

        // 将所有字段重置为空值（null）
        Object.keys(profile.value).forEach(key => {
            profile.value[key] = null
        })

        showToast('表单已清空', 'success')
    } catch (e) {
        // Cancelled
    }
}

// Remove extra item logic
const removeExtraItem = (key) => {
    if (profile.value.extra_data && profile.value.extra_data[key] !== undefined) {
        delete profile.value.extra_data[key]
    }
}

// 自动计算 BMI
watch([() => profile.value.Height, () => profile.value.Weight], ([h, w]) => {
    const bmiIsEmpty = profile.value.BMI === null || profile.value.BMI === undefined || profile.value.BMI === ''
    if (bmiIsEmpty && h && w && h > 0) {
        const bmi = w / ((h / 100) * (h / 100))
        profile.value.BMI = parseFloat(bmi.toFixed(1))
    }
})

const saveData = () => {
    store.updateProfile(profile.value)
    showToast('临床数据已更新并暂存', 'success')
}

// 🔥 V7：保存到云端
const saveToCloud = async () => {
    saving.value = true
    try {
        store.updateProfile(profile.value)
        const success = await store.saveProfileToCloud()
        if (success) {
            showToast('健康档案已云端同步', 'success')
        } else {
            showToast('保存失败，请重试', 'warning')
        }
    } catch (e) {
        showToast('云端同步失败', 'error')
    } finally {
        saving.value = false
    }
}
</script>

<style scoped>
/* 复用 App.vue 的输入框风格，保持视觉一致性 */
.clinical-form :deep(.el-input__wrapper),
.clinical-form :deep(.el-select__wrapper),
.clinical-form :deep(.el-textarea__inner) {
    background-color: rgba(255, 255, 255, 0.92) !important;
    box-shadow: none;
    border: 1px solid rgba(148, 163, 184, 0.35);
}

.clinical-form :deep(.el-input-number__decrease),
.clinical-form :deep(.el-input-number__increase) {
    background-color: rgba(248, 250, 252, 0.96) !important;
    border-color: rgba(148, 163, 184, 0.35);
    color: #64748b;
}

.clinical-form :deep(.el-input__inner),
.clinical-form :deep(.el-select__selected-item),
.clinical-form :deep(.el-textarea__inner) {
    color: #334155;
    font-weight: 600;
    -webkit-text-fill-color: #334155;
}

.clinical-form :deep(.el-input.is-disabled .el-input__wrapper) {
    background-color: rgba(248, 250, 252, 0.95) !important;
}

.clinical-form :deep(.el-input.is-disabled .el-input__inner) {
    color: #64748b;
    -webkit-text-fill-color: #64748b;
}

/* 任务 126：OCR 数据填入时的“高亮呼吸”特效 */
@keyframes flash-green {
    0% {
        background-color: rgba(16, 185, 129, 0.25);
        /* Emerald-500 带透明度 */
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3);
        border-color: rgba(16, 185, 129, 0.6);
    }

    50% {
        background-color: rgba(16, 185, 129, 0.15);
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }

    100% {
        background-color: rgba(255, 255, 255, 0.92);
        box-shadow: none;
        border-color: inherit;
    }
}

/* 应用于 Element Plus 输入组件内部 wrapper */
.ocr-updated :deep(.el-input__wrapper),
.ocr-updated :deep(.el-input-number__decrease),
.ocr-updated :deep(.el-input-number__increase),
.ocr-updated :deep(.el-select__wrapper),
.ocr-updated :deep(.el-textarea__inner) {
    animation: flash-green 2.5s ease-out forwards;
}

/* 任务 127：OCR 未找到字段样式 - 灰色虚线边框 */
.guided-missing :deep(.el-input__wrapper),
.guided-missing :deep(.el-input-number__decrease),
.guided-missing :deep(.el-input-number__increase),
.guided-missing :deep(.el-select__wrapper) {
    background-color: rgba(148, 163, 184, 0.08);
    /* Slate-400 低透明度 */
    border: 1.5px dashed rgba(148, 163, 184, 0.4);
    transition: all 0.3s ease;
}

.guided-missing :deep(.el-input__inner)::placeholder,
.guided-missing :deep(.el-input-number .el-input__inner)::placeholder {
    color: rgba(148, 163, 184, 0.7);
    font-style: italic;
}

/* 悬停时恢复正常样式，提示可以手填 */
.guided-missing:hover :deep(.el-input__wrapper),
.guided-missing:hover :deep(.el-input-number__decrease),
.guided-missing:hover :deep(.el-input-number__increase) {
    background-color: rgba(255, 255, 255, 0.5);
    border-style: solid;
    border-color: rgba(59, 130, 246, 0.5);
    /* 蓝色提示边框 */
}

.dark .guided-missing :deep(.el-input__wrapper),
.dark .guided-missing :deep(.el-input-number__decrease),
.dark .guided-missing :deep(.el-input-number__increase) {
    background-color: rgba(255, 255, 255, 0.92) !important;
    border-color: rgba(148, 163, 184, 0.3);
}
</style>
