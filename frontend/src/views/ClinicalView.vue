<template>
    <div class="p-6 h-full flex flex-col items-center">
        <div class="w-full max-w-4xl">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                🩺 临床体检 (Clinical Profile)
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
                        <el-upload class="upload-demo inline-block" action="#" :auto-upload="false"
                            :on-change="handleOcrUpload" :show-file-list="false" accept=".jpg,.jpeg,.png,.pdf">
                            <GlassButton size="sm" :loading="ocrLoading">
                                <el-icon class="mr-2">
                                    <Camera />
                                </el-icon> 📷 智能识别体检单
                            </GlassButton>
                        </el-upload>
                    </div>
                </template>

                <!-- Task 89: Anomaly Alert Summary -->
                <div v-if="anomalySummary && anomalySummary.count > 0" class="mb-4 p-4 rounded-xl border-2"
                    :class="anomalySummary.status === 'alert' ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700' : 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'">
                    <div class="flex items-start gap-3">
                        <span class="text-2xl">{{ anomalySummary.status === 'alert' ? '🚨' : '⚠️' }}</span>
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
                                :class="{ 'ocr-updated': isOcrUpdated('Glucose_Fasting'), 'ocr-not-found': isOcrNotFound('Glucose_Fasting') }">
                                <el-input-number v-model="profile.Glucose_Fasting" :min="1" :max="50" :precision="1"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Glucose_Fasting', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="糖化血红蛋白"
                                :class="{ 'ocr-updated': isOcrUpdated('HbA1c'), 'ocr-not-found': isOcrNotFound('HbA1c') }">
                                <el-input-number v-model="profile.HbA1c" :min="4" :max="15" :precision="1" :step="0.1"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('HbA1c', '%')" />
                            </el-form-item>
                            <el-form-item label="总胆固醇"
                                :class="{ 'ocr-updated': isOcrUpdated('Cholesterol_Total'), 'ocr-not-found': isOcrNotFound('Cholesterol_Total') }">
                                <el-input-number v-model="profile.Cholesterol_Total" :min="0" :max="20" :precision="2"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Cholesterol_Total', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="甘油三酯"
                                :class="{ 'ocr-updated': isOcrUpdated('Triglycerides'), 'ocr-not-found': isOcrNotFound('Triglycerides') }">
                                <el-input-number v-model="profile.Triglycerides" :min="0" :max="30" :precision="2"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Triglycerides', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="高密度脂蛋白"
                                :class="{ 'ocr-updated': isOcrUpdated('Cholesterol_HDL'), 'ocr-not-found': isOcrNotFound('Cholesterol_HDL') }">
                                <el-input-number v-model="profile.Cholesterol_HDL" :min="0" :max="5" :precision="2"
                                    controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('Cholesterol_HDL', 'mmol/L')" />
                            </el-form-item>
                            <el-form-item label="睡眠时长(h)">
                                <el-input-number v-model="profile.Sleep_Hours" :min="0" :max="24" :step="0.5"
                                    controls-position="right" class="w-full" />
                            </el-form-item>
                            <el-form-item label="eGFR (肾)"
                                :class="{ 'ocr-updated': isOcrUpdated('eGFR'), 'ocr-not-found': isOcrNotFound('eGFR') }">
                                <el-input-number v-model="profile.eGFR" :min="0" controls-position="right"
                                    class="w-full" :placeholder="getPlaceholder('eGFR', 'mL/min')" />
                            </el-form-item>
                            <el-form-item label="ALT (肝)"
                                :class="{ 'ocr-updated': isOcrUpdated('ALT'), 'ocr-not-found': isOcrNotFound('ALT') }">
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
                            <el-form-item label="ALP (肝/骨)"
                                :class="{ 'ocr-updated': isOcrUpdated('ALP'), 'ocr-not-found': isOcrNotFound('ALP') }">
                                <el-input-number v-model="profile.ALP" :min="0" controls-position="right" class="w-full"
                                    :placeholder="getPlaceholder('ALP', 'U/L')" />
                            </el-form-item>
                            <!-- Task 128: 肌酐输入 (用于 eGFR 自动计算) -->
                            <el-form-item label="肌酐 (Cr)"
                                :class="{ 'ocr-updated': isOcrUpdated('Creatinine'), 'ocr-not-found': isOcrNotFound('Creatinine') }">
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
                                    📋 其他检测项 (Extra Findings)
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
                        {{ saving ? '保存中...' : '💾 保存健康档案' }}
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
import { ref, watch, onMounted, nextTick, h } from 'vue'
import { storeToRefs } from 'pinia'
import { useHealthStore } from '../stores/healthStore'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import { ArrowRight, Check, Camera, Delete } from '@element-plus/icons-vue'
import axios from 'axios'
import { useToast } from '../composables/useToast'
import { ElNotification, ElMessageBox } from 'element-plus'

const store = useHealthStore()
const { userProfile: profile, importData } = storeToRefs(store)
const saving = ref(false)
const ocrLoading = ref(false)
const { showToast } = useToast()

// Task 126: OCR Updated Fields Highlight
const ocrUpdatedFields = ref(new Set())

// Task 131: OCR 撤销快照 - 保存 OCR 前的表单状态
const lastProfileSnapshot = ref(null)

// Task 127: Smart Placeholder - 记录 OCR 是否已完成
const ocrCompleted = ref(false)

// Helper to check if a field was just updated by OCR
const isOcrUpdated = (fieldName) => ocrUpdatedFields.value.has(fieldName)

// Task 127: 动态 Placeholder - 根据 OCR 状态显示不同提示
const getPlaceholder = (fieldName, defaultText = '请输入数值') => {
    // 如果 OCR 已完成且该字段不在更新列表中（即未识别到）
    if (ocrCompleted.value && !ocrUpdatedFields.value.has(fieldName)) {
        // 检查当前值是否为空
        const currentVal = profile.value[fieldName]
        if (currentVal === null || currentVal === undefined || currentVal === '') {
            return '报告中未找到此项'
        }
    }
    return defaultText
}

// Task 127: 检查字段是否为 OCR 未识别状态
const isOcrNotFound = (fieldName) => {
    if (!ocrCompleted.value) return false
    const currentVal = profile.value[fieldName]
    const isEmpty = currentVal === null || currentVal === undefined || currentVal === ''
    return isEmpty && !ocrUpdatedFields.value.has(fieldName)
}

// ============================================
// Task 128: eGFR 智能填充策略 (CKD-EPI 2021)
// ============================================

/**
 * CKD-EPI 2021 公式计算 eGFR (无种族校正版)
 * @param {number} creatinine - 血清肌酐 (umol/L)
 * @param {number} age - 年龄 (岁)
 * @param {number} gender - 性别 (1=男, 2=女)
 * @returns {number|null} eGFR (mL/min/1.73m²) 或 null 若输入无效
 */
const calculateCKDEPI2021 = (creatinine, age, gender) => {
    // 参数验证
    if (!creatinine || !age || !gender) return null
    if (creatinine <= 0 || age <= 0) return null

    // 将 umol/L 转换为 mg/dL (公式要求)
    const Scr = creatinine / 88.4

    // 性别参数
    const isFemale = gender === 2
    const kappa = isFemale ? 0.7 : 0.9
    const alpha = isFemale ? -0.241 : -0.302
    const sexMultiplier = isFemale ? 1.012 : 1.0

    // CKD-EPI 2021 公式
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
    // 检查当前 eGFR 是否为空 - 不覆盖已有值
    const currentEGFR = profile.value.eGFR
    if (currentEGFR !== null && currentEGFR !== undefined && currentEGFR !== '') {
        console.log('⏭️ eGFR 已有值，跳过自动计算')
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
        console.log(`🧮 eGFR 自动计算: Cr=${creatinine} → eGFR=${calculatedEGFR}`)
    }
}

// Task 128: 监听年龄、性别、肌酐变化，自动触发 eGFR 计算
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
                    message: '🎉 所有指标均在正常范围内！',
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

// 🔥 Task 59: Check for imported data on mount
onMounted(() => {
    if (importData.value && typeof importData.value === 'object') {
        console.log("📥 Detected importData, auto-filling form...")
        applyOcrDataToProfile(importData.value)
        ElNotification.success({
            title: '历史数据已载入',
            message: '已成功载入历史体检数据，请核对后提交。',
            duration: 5000
        })
        store.clearImportData()  // Prevent re-load on refresh
    }
})

// Shared function to apply OCR/imported data to profile
const applyOcrDataToProfile = (data) => {
    // Task 125: Smart Merge - 只有当 OCR 数据有效时才覆盖，保留用户手填数据
    const isValidValue = (val) => {
        if (val === null || val === undefined) return false
        if (val === 'null' || val === 'undefined') return false
        if (typeof val === 'string' && val.trim() === '') return false
        if (typeof val === 'number' && isNaN(val)) return false
        return true
    }

    // Task 67/68: Enhanced mapping with Age, Gender, Height, Weight
    const mapping = {
        // Basic Info
        'Age': 'Age',
        'Gender': 'Gender',
        'Height': 'Height',
        'Weight': 'Weight',
        'BMI': 'BMI',
        'SBP': 'SBP',
        'DBP': 'DBP',
        // Biochemistry
        'Glu': 'Glucose_Fasting',
        'Glucose': 'Glucose_Fasting',
        'HbA1c': 'HbA1c',
        'TC': 'Cholesterol_Total',
        'TG': 'Triglycerides',
        'HDL': 'Cholesterol_HDL',
        'LDL': 'Cholesterol_LDL',
        // Liver / Kidney
        'ALT': 'ALT',
        'AST': 'AST',
        'GGT': 'GGT',
        'ALP': 'ALP',
        'eGFR': 'eGFR',
        'Creatinine': 'Creatinine',  // Task 128: 肌酐映射
        'Cr': 'Creatinine',           // 常见缩写
        'CREA': 'Creatinine',         // 体检单缩写
        // Blood
        'WBC': 'WBC',
        'PLT': 'Platelet',
        'Platelet': 'Platelet',
        'HGB': 'HGB'
    }

    // Task 74: Map extra_findings to extra_data
    if (data.extra_findings && typeof data.extra_findings === 'object') {
        console.log("🔥 Found Extra Findings:", data.extra_findings)
        // Initialize if undefined
        if (!profile.value.extra_data) profile.value.extra_data = {}
        // Merge (only valid values)
        for (const [k, v] of Object.entries(data.extra_findings)) {
            if (isValidValue(v)) {
                profile.value.extra_data[k] = v
            }
        }
    }

    let filledCount = 0
    let skippedCount = 0

    for (const [key, val] of Object.entries(data)) {
        // Task 125: Smart Merge - 如果 OCR 没读到这个数据，直接跳过，保留表单里原本可能存在的手填数据
        if (!isValidValue(val)) {
            skippedCount++
            continue
        }

        const profileKey = mapping[key] || (profile.value.hasOwnProperty(key) ? key : null)
        if (profileKey && profile.value.hasOwnProperty(profileKey)) {
            console.log(`✅ Updating ${profileKey}: ${profile.value[profileKey]} -> ${val}`)

            // Handle Gender specially (might come as string "男"/"女" or int 1/2)
            if (profileKey === 'Gender') {
                if (val === '男' || val === 'Male' || val === 1) {
                    profile.value[profileKey] = 1
                } else if (val === '女' || val === 'Female' || val === 2) {
                    profile.value[profileKey] = 2
                }
            } else {
                // Parse as float for numeric values
                const numVal = parseFloat(val)
                if (!isNaN(numVal)) {
                    profile.value[profileKey] = numVal
                }
            }
            filledCount++

            // Task 126: Track this field for highlight animation
            ocrUpdatedFields.value.add(profileKey)
        }
    }

    if (skippedCount > 0) {
        console.log(`⏭️ Smart Merge: Skipped ${skippedCount} empty/null fields (preserved existing data)`)
    }

    // Task 126: Clear highlights after animation duration (2.5s)
    if (ocrUpdatedFields.value.size > 0) {
        console.log(`✨ Highlighting ${ocrUpdatedFields.value.size} OCR-updated fields`)
        setTimeout(() => {
            ocrUpdatedFields.value.clear()
        }, 2500)
    }

    return filledCount
}

// ============================================
// Task 131: OCR 撤销功能 (Undo)
// ============================================
const handleUndoOcr = async () => {
    // 检查是否有快照可用
    if (!lastProfileSnapshot.value) {
        showToast('没有可撤销的操作', 'warning')
        return
    }

    try {
        // 恢复快照数据到当前 profile
        Object.keys(lastProfileSnapshot.value).forEach(key => {
            profile.value[key] = lastProfileSnapshot.value[key]
        })

        // 更新 store 并保存到云端
        store.updateProfile(profile.value)
        const saveSuccess = await store.saveProfileToCloud()

        if (saveSuccess) {
            ElNotification({
                title: '↩️ 已撤销 OCR 更改',
                message: '已恢复到识别前的数据状态并同步至云端。',
                type: 'success',
                duration: 4000
            })
        } else {
            showToast('撤销成功但同步失败，请手动保存', 'warning')
        }

        // 清空快照
        lastProfileSnapshot.value = null

        // 清除 OCR 相关状态
        ocrCompleted.value = false
        ocrUpdatedFields.value.clear()

    } catch (e) {
        console.error('Undo failed:', e)
        showToast('撤销失败: ' + e.message, 'error')
    }
}

// 📷 OCR Upload Handler
const handleOcrUpload = async (uploadFile) => {
    if (!uploadFile || !uploadFile.raw) return

    ocrLoading.value = true
    const formData = new FormData()
    formData.append('file', uploadFile.raw)

    try {
        showToast('正在识别体检单，请稍候...', 'info')
        const response = await axios.post('http://127.0.0.1:8000/api/v1/ocr/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })

        const res = response.data
        if (res.status === 'success' && res.data) {
            const data = res.data

            // Task 131: 在修改前保存快照 (用于撤销)
            lastProfileSnapshot.value = JSON.parse(JSON.stringify(profile.value))

            // 🔥 Refactored to use shared function (Task 68/71)
            const filledCount = applyOcrDataToProfile(res.data)

            // Task 127: 标记 OCR 已完成
            ocrCompleted.value = true

            // Task 130: 等待 Vue 响应式更新 (让 eGFR watcher 生效)
            await nextTick()

            if (filledCount > 0) {
                // Task 130: 自动保存到云端
                try {
                    store.updateProfile(profile.value)
                    const saveSuccess = await store.saveProfileToCloud()

                    if (saveSuccess) {
                        // Task 131: 自动保存成功 - 显示带撤销按钮的通知
                        ElNotification({
                            title: '✅ 识别成功且已自动保存',
                            message: h('div', { style: 'line-height: 1.6' }, [
                                h('span', null, `已提取 ${filledCount} 项数据并同步至健康档案。`),
                                h('br'),
                                h('button', {
                                    class: 'el-button el-button--primary is-link',
                                    style: 'padding: 0; margin-top: 8px; font-size: 13px;',
                                    onClick: handleUndoOcr
                                }, '↩️ 撤销更改 (Undo)')
                            ]),
                            type: 'success',
                            duration: 8000  // 给用户足够时间反应
                        })
                    } else {
                        // 识别成功但保存失败
                        ElNotification({
                            title: '⚠️ 提取成功但自动保存失败',
                            message: `已提取 ${filledCount} 项数据，请检查后手动点击"保存到云端"按钮。`,
                            type: 'warning',
                            duration: 6000
                        })
                    }
                } catch (saveError) {
                    console.error('Auto-save failed:', saveError)
                    ElNotification({
                        title: '⚠️ 提取成功但自动保存失败',
                        message: `已提取 ${filledCount} 项数据，请检查后手动点击"保存到云端"按钮。`,
                        type: 'warning',
                        duration: 6000
                    })
                }
            } else {
                showToast('识别成功，但未匹配到有效指标数据', 'warning')
            }
        }
    } catch (e) {
        console.error(e)
        showToast('识别失败: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
        ocrLoading.value = false
    }
}

// Task 71: Clear All Data
const handleClearAll = async () => {
    try {
        await ElMessageBox.confirm(
            '确定要清空当前页面的所有已录入数据吗？此操作不可撤销。',
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
    if (h && w && h > 0) {
        const bmi = w / ((h / 100) * (h / 100))
        profile.value.BMI = parseFloat(bmi.toFixed(1))
    }
})

const saveData = () => {
    store.updateProfile(profile.value)
    showToast('临床数据已更新并暂存 (State Updated)', 'success')
}

// 🔥 V7: 保存到云端
const saveToCloud = async () => {
    saving.value = true
    try {
        store.updateProfile(profile.value)
        const success = await store.saveProfileToCloud()
        if (success) {
            showToast('💾 健康档案已云端同步', 'success')
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

/* Task 126: OCR 数据填入时的"高亮呼吸"特效 */
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

/* 应用于 Element Plus 输入框内部 wrapper */
.ocr-updated :deep(.el-input__wrapper),
.ocr-updated :deep(.el-input-number__decrease),
.ocr-updated :deep(.el-input-number__increase),
.ocr-updated :deep(.el-select__wrapper),
.ocr-updated :deep(.el-textarea__inner) {
    animation: flash-green 2.5s ease-out forwards;
}

/* Task 127: OCR 未找到的字段样式 - 灰色虚线边框 */
.ocr-not-found :deep(.el-input__wrapper),
.ocr-not-found :deep(.el-input-number__decrease),
.ocr-not-found :deep(.el-input-number__increase),
.ocr-not-found :deep(.el-select__wrapper) {
    background-color: rgba(148, 163, 184, 0.08);
    /* Slate-400 with low opacity */
    border: 1.5px dashed rgba(148, 163, 184, 0.4);
    transition: all 0.3s ease;
}

.ocr-not-found :deep(.el-input__inner)::placeholder,
.ocr-not-found :deep(.el-input-number .el-input__inner)::placeholder {
    color: rgba(148, 163, 184, 0.7);
    font-style: italic;
}

/* 悬停时恢复正常样式，提示可以手填 */
.ocr-not-found:hover :deep(.el-input__wrapper),
.ocr-not-found:hover :deep(.el-input-number__decrease),
.ocr-not-found:hover :deep(.el-input-number__increase) {
    background-color: rgba(255, 255, 255, 0.5);
    border-style: solid;
    border-color: rgba(59, 130, 246, 0.5);
    /* Blue hint */
}

.dark .ocr-not-found :deep(.el-input__wrapper),
.dark .ocr-not-found :deep(.el-input-number__decrease),
.dark .ocr-not-found :deep(.el-input-number__increase) {
    background-color: rgba(30, 41, 59, 0.3);
    border-color: rgba(148, 163, 184, 0.3);
}
</style>
