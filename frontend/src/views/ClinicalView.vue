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
                                <el-icon class="mr-1"><Delete /></el-icon> 清空数据
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
                <div v-if="anomalySummary && anomalySummary.count > 0" 
                    class="mb-4 p-4 rounded-xl border-2"
                    :class="anomalySummary.status === 'alert' ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700' : 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'">
                    <div class="flex items-start gap-3">
                        <span class="text-2xl">{{ anomalySummary.status === 'alert' ? '🚨' : '⚠️' }}</span>
                        <div class="flex-1">
                            <h4 class="font-bold text-slate-800 dark:text-white">健康警报摘要</h4>
                            <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{{ anomalySummary.message }}</p>
                            <div class="flex flex-wrap gap-2 mt-2">
                                <el-tag v-for="item in anomalySummary.items" :key="item" 
                                    :type="getAnomalyTagType(item)" size="small" round>
                                    {{ getAnomalyLabel(item) }}
                                </el-tag>
                            </div>
                        </div>
                        <el-button size="small" type="primary" plain @click="runAnomalyDetection" :loading="anomalyLoading">
                            重新检测
                        </el-button>
                    </div>
                </div>

                <el-form label-position="left" label-width="110px" size="default" class="clinical-form grid gap-6">

                    <!-- Basic Info -->
                    <div class="p-4 rounded-xl bg-white/30 dark:bg-black/20 border border-gray-100 dark:border-white/5">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">基本信息 (Basic)</h3>
                        <div class="grid grid-cols-2 gap-6">
                            <el-form-item label="年龄 (Age)">
                                <el-input-number v-model="profile.Age" :min="0" :max="120" controls-position="right"
                                    class="w-full" placeholder="岁" />
                            </el-form-item>
                            <el-form-item label="性别 (Gender)">
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
                            <el-form-item label="身高 (cm)">
                                <el-input-number v-model="profile.Height" :min="30" :max="250" controls-position="right"
                                    class="w-full" placeholder="cm" />
                            </el-form-item>
                            <el-form-item label="体重 (kg)">
                                <el-input-number v-model="profile.Weight" :min="1" :max="300" :precision="1"
                                    controls-position="right" class="w-full" placeholder="kg" />
                            </el-form-item>
                        </div>
                        <div class="grid grid-cols-2 gap-6 mt-2">
                            <el-form-item label="BMI">
                                <el-input-number v-model="profile.BMI" :precision="1" disabled controls-position="right"
                                    class="w-full" />
                            </el-form-item>
                            <el-form-item label="腰围 (cm)">
                                <el-input-number v-model="profile.WaistCircum" :min="30" :max="200" :precision="1"
                                    controls-position="right" class="w-full" placeholder="cm" />
                            </el-form-item>
                        </div>
                        <div class="mt-4">
                            <el-form-item label="血压 (BP)">
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
                            <el-form-item label="空腹血糖">
                                <el-input-number v-model="profile.Glucose_Fasting" :min="1" :max="50" :precision="1"
                                    controls-position="right" class="w-full" placeholder="mmol/L" />
                            </el-form-item>
                            <el-form-item label="糖化血红蛋白">
                                <el-input-number v-model="profile.HbA1c" :min="4" :max="15" :precision="1" :step="0.1"
                                    controls-position="right" class="w-full" />
                            </el-form-item>
                            <el-form-item label="总胆固醇">
                                <el-input-number v-model="profile.Cholesterol_Total" :min="0" :max="20" :precision="2"
                                    controls-position="right" class="w-full" placeholder="mmol/L" />
                            </el-form-item>
                            <el-form-item label="甘油三酯">
                                <el-input-number v-model="profile.Triglycerides" :min="0" :max="30" :precision="2"
                                    controls-position="right" class="w-full" placeholder="mmol/L" />
                            </el-form-item>
                            <el-form-item label="高密度脂蛋白">
                                <el-input-number v-model="profile.Cholesterol_HDL" :min="0" :max="5" :precision="2"
                                    controls-position="right" class="w-full" placeholder="mmol/L" />
                            </el-form-item>
                            <el-form-item label="睡眠时长(h)">
                                <el-input-number v-model="profile.Sleep_Hours" :min="0" :max="24" :step="0.5"
                                    controls-position="right" class="w-full" />
                            </el-form-item>
                            <el-form-item label="eGFR (肾)">
                                <el-input-number v-model="profile.eGFR" :min="0" controls-position="right"
                                    class="w-full" />
                            </el-form-item>
                            <el-form-item label="ALT (肝)">
                                <el-input-number v-model="profile.ALT" :min="0" controls-position="right"
                                    class="w-full" />
                            </el-form-item>
                        </div>

                        <!-- New V10 Indicators -->
                        <div class="grid grid-cols-2 gap-6 mt-6 border-t border-gray-100 dark:border-white/5 pt-6">
                            <el-form-item label="白细胞 (WBC)">
                                <el-input-number v-model="profile.WBC" :min="0" :precision="1" :step="0.1"
                                    controls-position="right" class="w-full" placeholder="10^9/L" />
                            </el-form-item>
                            <el-form-item label="血小板 (PLT)">
                                <el-input-number v-model="profile.Platelet" :min="0" controls-position="right"
                                    class="w-full" placeholder="10^9/L" />
                            </el-form-item>
                            <el-form-item label="GGT (肝)">
                                <el-input-number v-model="profile.GGT" :min="0" controls-position="right" class="w-full"
                                    placeholder="U/L" />
                            </el-form-item>
                            <el-form-item label="ALP (肝/骨)">
                                <el-input-number v-model="profile.ALP" :min="0" controls-position="right" class="w-full"
                                    placeholder="未检测(U/L)" />
                            </el-form-item>
                        </div>
                    </div>

                    <!-- Task 74: Extra Data (Unstructured) -->
                    <el-collapse v-if="profile.extra_data" class="rounded-xl border border-gray-100 dark:border-white/5 overflow-hidden">
                        <el-collapse-item name="1">
                            <template #title>
                                <div class="px-4 font-bold text-slate-500 dark:text-slate-400 flex items-center gap-2">
                                    📋 其他检测项 (Extra Findings) 
                                    <el-tag v-if="Object.keys(profile.extra_data).length" size="small" type="info" round>
                                        {{ Object.keys(profile.extra_data).length }}
                                    </el-tag>
                                </div>
                            </template>
                            <div class="p-4 bg-white/30 dark:bg-black/20">
                                <div v-if="!Object.keys(profile.extra_data).length" class="text-sm text-center text-slate-400 py-4">
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
                                            <el-icon><Delete /></el-icon>
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
import { ref, watch, onMounted } from 'vue'
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
        // Merge
        Object.assign(profile.value.extra_data, data.extra_findings)
    }

    let filledCount = 0
    for (const [key, val] of Object.entries(data)) {
        if (val === null || val === undefined || val === 'null') continue
        
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
        }
    }
    return filledCount
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
            
            // 🔥 Refactored to use shared function (Task 68/71)
            const filledCount = applyOcrDataToProfile(res.data)

            if (filledCount > 0) {
                // Success Notification
                ElNotification({
                    title: '识别成功',
                    message: `已更新 ${filledCount} 项数据，请核对。`,
                    type: 'success',
                    duration: 5000
                })
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
</style>
