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
                        <el-upload data-testid="ocr-upload" class="upload-demo inline-block" action="#" :auto-upload="false"
                            :on-change="handleOcrUpload" :show-file-list="false" accept=".jpg,.jpeg,.png,.pdf">
                            <GlassButton size="sm" :loading="ocrLoading">
                                <el-icon class="mr-2">
                                    <Camera />
                                </el-icon> 智能识别体检单
                            </GlassButton>
                        </el-upload>
                    </div>
                </template>

                <!-- Task 89: Anomaly Alert Summary -->
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

                    <!-- Basic Info -->
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

                    <!-- Body Metrics -->
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

                    <!-- Biochemistry -->
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

                        <!-- New V10 Indicators -->
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

                    <!-- Task 74: Extra Data (Unstructured) -->
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
                                <!-- Manual Add (Optional, future enhancement) -->
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
import { ArrowRight, Check, Camera, Delete } from '@element-plus/icons-vue'
import axios from 'axios'
import { useToast } from '../composables/useToast'
import { ElNotification, ElMessageBox } from 'element-plus'

const store = useHealthStore()
const { userProfile: profile, importData, analysisContext } = storeToRefs(store)
const saving = ref(false)
const ocrLoading = ref(false)
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

// Task 126: OCR Updated Fields Highlight
const ocrUpdatedFields = ref(new Set())
const isOcrUpdated = (fieldName) => ocrUpdatedFields.value.has(fieldName)

// Task 131: OCR 鎾ら攢蹇収 - 淇濆瓨 OCR 鍓嶇殑琛ㄥ崟鐘舵€?
const lastProfileSnapshot = ref(null)

// OCR placeholders now prefer explicit guided-completion language.
const getPlaceholder = () => '待补充'

const isGuidedMissing = (fieldName) => {
    const summary = fieldStateSummary.value
    if (!summary) return false
    return Array.isArray(summary.missing) && summary.missing.includes(fieldName)
}

// ============================================
// Task 128: eGFR 鏅鸿兘濉厖绛栫暐 (CKD-EPI 2021)
// ============================================

/**
 * CKD-EPI 2021 鍏紡璁＄畻 eGFR (鏃犵鏃忔牎姝ｇ増)
 * @param {number} creatinine - 琛€娓呰倢閰?(umol/L)
 * @param {number} age - 骞撮緞 (宀?
 * @param {number} gender - 鎬у埆 (1=鐢? 2=濂?
 * @returns {number|null} eGFR (mL/min/1.73m虏) 鎴?null 鑻ヨ緭鍏ユ棤鏁?
 */
const calculateCKDEPI2021 = (creatinine, age, gender) => {
    // 鍙傛暟楠岃瘉
    if (!creatinine || !age || !gender) return null
    if (creatinine <= 0 || age <= 0) return null

    // 灏?umol/L 杞崲涓?mg/dL (鍏紡瑕佹眰)
    const Scr = creatinine / 88.4

    // 鎬у埆鍙傛暟
    const isFemale = gender === 2
    const kappa = isFemale ? 0.7 : 0.9
    const alpha = isFemale ? -0.241 : -0.302
    const sexMultiplier = isFemale ? 1.012 : 1.0

    // CKD-EPI 2021 鍏紡
    const ratio = Scr / kappa
    const minRatio = Math.min(ratio, 1)
    const maxRatio = Math.max(ratio, 1)

    const eGFR = 142 * Math.pow(minRatio, alpha) * Math.pow(maxRatio, -1.200) * Math.pow(0.9938, age) * sexMultiplier

    return parseFloat(eGFR.toFixed(1))
}

/**
 * Task 128: 鏅鸿兘璁＄畻 eGFR - 浠呭綋 eGFR 涓虹┖涓旀湁鑲岄厫鏃惰嚜鍔ㄨ绠?
 * OCR 浼樺厛: 濡傛灉 OCR 宸插～鍏?eGFR锛屼笉瑕嗙洊
 */
const tryAutoCalculateEGFR = () => {
    // 妫€鏌ュ綋鍓?eGFR 鏄惁涓虹┖ - 涓嶈鐩栧凡鏈夊€?
    const currentEGFR = profile.value.eGFR
    if (currentEGFR !== null && currentEGFR !== undefined && currentEGFR !== '') {
        console.log('鈴笍 eGFR 宸叉湁鍊硷紝璺宠繃鑷姩璁＄畻')
        return
    }

    // 妫€鏌ュ繀瑕佸弬鏁?
    const age = profile.value.Age
    const gender = profile.value.Gender
    const creatinine = profile.value.Creatinine

    if (!age || !gender || !creatinine) {
        return // 鍙傛暟涓嶅叏锛屾棤娉曡绠?
    }

    // 鎵ц璁＄畻
    const calculatedEGFR = calculateCKDEPI2021(creatinine, age, gender)
    if (calculatedEGFR !== null) {
        profile.value.eGFR = calculatedEGFR
        console.log(`馃М eGFR 鑷姩璁＄畻: Cr=${creatinine} 鈫?eGFR=${calculatedEGFR}`)
    }
}

// Task 128: 鐩戝惉骞撮緞銆佹€у埆銆佽倢閰愬彉鍖栵紝鑷姩瑙﹀彂 eGFR 璁＄畻
watch(
    [() => profile.value.Age, () => profile.value.Gender, () => profile.value.Creatinine],
    () => {
        tryAutoCalculateEGFR()
    },
    { immediate: false }
)

// Task 89: Anomaly Detection State
const anomalyLoading = ref(false)
const anomalies = ref([])
const anomalySummary = ref(null)
const anomalyMap = ref({}) // key -> anomaly object for quick lookup

// Task 89: Helper functions for anomaly display
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

// Task 89: Run anomaly detection
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

            // Build lookup map
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

// 馃敟 Task 59: Check for imported data on mount
onMounted(() => {
    if (importData.value && typeof importData.value === 'object') {
        console.log("馃摜 Detected importData, auto-filling form...")
        if (importData.value.ocr_summary) {
            applyOcrDataToProfile(importData.value.ocr_summary)
            ElNotification.success({
                title: '历史数据已载入',
                message: '已自动回填可识别字段，请核对后再继续分析。',
                duration: 5000
            })
        } else if (importData.value.ocr_processing_status) {
            ElNotification({
                title: '文档已保存，待识别',
                message: '当前文档还没有可用的结构化 OCR 数据，请稍后重试或继续手动补全。',
                type: 'warning',
                duration: 5000
            })
        }
        store.clearImportData()  // Prevent re-load on refresh
    }
})

// Shared function to apply OCR/imported data to profile
const applyOcrDataToProfile = (data) => {
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

    // Task 67/68: Enhanced mapping with Age, Gender, Height, Weight
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
        console.log("馃敟 Found Extra Findings:", sourceData.extra_findings)
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
        if (!isEmpty) continue

        if (profileKey === 'Gender') {
            if (val === '男' || val === 'Male' || val === 1 || val === '鐢?') {
                profile.value[profileKey] = 1
            } else if (val === '女' || val === 'Female' || val === 2 || val === '濂?') {
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
        console.log(`鈴笍 Smart Merge: Skipped ${skippedCount} empty/null fields (preserved existing data)`)
    }

    if (ocrUpdatedFields.value.size > 0) {
        console.log(`鉁?Highlighting ${ocrUpdatedFields.value.size} OCR-updated fields`)
        setTimeout(() => {
            ocrUpdatedFields.value.clear()
        }, 2500)
    }

    return filledCount
}

// ============================================
// Task 131: OCR 鎾ら攢鍔熻兘 (Undo)
// ============================================
const handleUndoOcr = async () => {
    // 妫€鏌ユ槸鍚︽湁蹇収鍙敤
    if (!lastProfileSnapshot.value) {
        showToast('没有可撤销的操作', 'warning')
        return
    }

    try {
        // 鎭㈠蹇収鏁版嵁鍒板綋鍓?profile
        Object.keys(lastProfileSnapshot.value).forEach(key => {
            profile.value[key] = lastProfileSnapshot.value[key]
        })

        // 鏇存柊 store 骞朵繚瀛樺埌浜戠
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

        // 娓呯┖蹇収
        lastProfileSnapshot.value = null

        // 娓呴櫎 OCR 鐩稿叧鐘舵€?
        ocrUpdatedFields.value.clear()

    } catch (e) {
        console.error('Undo failed:', e)
        showToast('撤销失败: ' + e.message, 'error')
    }
}

// 馃摲 OCR Upload Handler
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
                    store.updateProfile(profile.value)
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

// Task 71: Clear All Data
const handleClearAll = async () => {
    try {
        await ElMessageBox.confirm(
            '确定要清空当前页面上的所有已录入数据吗？此操作不可撤销。',
            '清空确认',
            { confirmButtonText: '清空', cancelButtonText: '取消', type: 'warning' }
        )

        // Reset all fields to null
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

// Auto-calculate BMI
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

// 馃敟 V7: 淇濆瓨鍒颁簯绔?
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
/* Reuse styles from App.vue for consistent look */
.clinical-form :deep(.el-input__wrapper) {
    background-color: rgba(255, 255, 255, 0.5);
    box-shadow: none;
    border: 1px solid rgba(0, 0, 0, 0.1);
}

.clinical-form :deep(.el-input__inner) {
    color: inherit;
    font-weight: 600;
}

.dark .clinical-form :deep(.el-input__wrapper) {
    background-color: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: white;
}

/* Task 126: OCR 鏁版嵁濉叆鏃剁殑"楂樹寒鍛煎惛"鐗规晥 */
@keyframes flash-green {
    0% {
        background-color: rgba(16, 185, 129, 0.25);
        /* Emerald-500 with opacity */
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3);
        border-color: rgba(16, 185, 129, 0.6);
    }

    50% {
        background-color: rgba(16, 185, 129, 0.15);
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }

    100% {
        background-color: transparent;
        box-shadow: none;
        border-color: inherit;
    }
}

/* 搴旂敤浜?Element Plus 杈撳叆妗嗗唴閮?wrapper */
.ocr-updated :deep(.el-input__wrapper),
.ocr-updated :deep(.el-input-number__decrease),
.ocr-updated :deep(.el-input-number__increase),
.ocr-updated :deep(.el-select__wrapper),
.ocr-updated :deep(.el-textarea__inner) {
    animation: flash-green 2.5s ease-out forwards;
}

/* Task 127: OCR 鏈壘鍒扮殑瀛楁鏍峰紡 - 鐏拌壊铏氱嚎杈规 */
.guided-missing :deep(.el-input__wrapper),
.guided-missing :deep(.el-input-number__decrease),
.guided-missing :deep(.el-input-number__increase),
.guided-missing :deep(.el-select__wrapper) {
    background-color: rgba(148, 163, 184, 0.08);
    /* Slate-400 with low opacity */
    border: 1.5px dashed rgba(148, 163, 184, 0.4);
    transition: all 0.3s ease;
}

.guided-missing :deep(.el-input__inner)::placeholder,
.guided-missing :deep(.el-input-number .el-input__inner)::placeholder {
    color: rgba(148, 163, 184, 0.7);
    font-style: italic;
}

/* 鎮仠鏃舵仮澶嶆甯告牱寮忥紝鎻愮ず鍙互鎵嬪～ */
.guided-missing:hover :deep(.el-input__wrapper),
.guided-missing:hover :deep(.el-input-number__decrease),
.guided-missing:hover :deep(.el-input-number__increase) {
    background-color: rgba(255, 255, 255, 0.5);
    border-style: solid;
    border-color: rgba(59, 130, 246, 0.5);
    /* Blue hint */
}

.dark .guided-missing :deep(.el-input__wrapper),
.dark .guided-missing :deep(.el-input-number__decrease),
.dark .guided-missing :deep(.el-input-number__increase) {
    background-color: rgba(30, 41, 59, 0.3);
    border-color: rgba(148, 163, 184, 0.3);
}
</style>
