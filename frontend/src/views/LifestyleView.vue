<template>
    <div class="p-6 h-full flex flex-col items-center">
        <div class="w-full max-w-5xl">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                📸 行为监测与饮食识别 (Lifestyle & IoT)
            </h1>

            <GlassCard :glowProximity="100">
                <template #header>
                    <div class="flex justify-between items-center text-sm text-slate-500 dark:text-slate-400">
                        <span>实时设备数据同步与 AI 饮食分析</span>
                        <span>Step 3/3</span>
                    </div>
                </template>

                <div class="grid md:grid-cols-2 gap-8 py-4">

                    <!-- Left: IoT Monitor -->
                    <div
                        class="flex flex-col gap-6 p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 relative overflow-hidden">
                        <div class="flex justify-between items-center z-10">
                            <h3
                                class="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
                                <el-icon>
                                    <Watch />
                                </el-icon> IoT 实时监测 (Bluetooth)
                            </h3>
                            <div v-if="isConnected" class="flex items-center gap-2">
                                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                                <span class="text-xs text-green-600 font-bold">已连接 (Live)</span>
                            </div>
                            <div v-else class="flex items-center gap-2">
                                <div class="w-2 h-2 rounded-full bg-slate-300"></div>
                                <span class="text-xs text-slate-400">离线 (Offline)</span>
                            </div>
                        </div>

                        <!-- 1. Connection Button (If Not Connected) -->
                        <div v-if="!isConnected" class="z-10 py-8 flex flex-col items-center justify-center">
                            <GlassButton @click="handleConnect" class="group">
                                <el-icon class="mr-2 group-hover:animate-pulse"><Connection /></el-icon>
                                扫描并连接设备 (Scan & Connect)
                            </GlassButton>
                            <span class="text-xs text-slate-400 mt-3 text-center px-4">
                                支持标准 BLE 心率带 (UUID 0x180d)<br>请确保您的设备已开启广播
                            </span>
                        </div>

                        <!-- 2. Live Dashboard (When Connected) -->
                        <div v-else class="z-10 animate-in fade-in zoom-in duration-300 w-full">
                            <GlassCard class="!p-0 overflow-hidden border-0 shadow-none bg-transparent">
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-0 h-64">
                                    
                                    <!-- Left: Real-time Waveform (2 cols) -->
                                    <div class="md:col-span-2 relative bg-slate-100/50 dark:bg-black/20 border-r border-slate-200 dark:border-white/5">
                                         <div ref="chartRef" class="w-full h-full"></div>
                                         
                                         <!-- Floating HR Badge -->
                                         <div class="absolute top-4 left-4 flex flex-col">
                                            <span class="text-xs font-bold text-slate-400 uppercase">Heart Rate</span>
                                            <div class="flex items-end gap-2 text-red-500">
                                                <el-icon class="text-2xl animate-pulse"><Timer /></el-icon>
                                                <span class="text-4xl font-black leading-none tabular-nums">{{ iotData.hr }}</span>
                                                <span class="text-sm font-bold mb-1">BPM</span>
                                            </div>
                                         </div>
                                    </div>

                                    <!-- Right: Data Statistics (1 col) -->
                                    <div class="flex flex-col justify-center gap-6 p-6 bg-white/40 dark:bg-white/5">
                                         <!-- Steps -->
                                         <div>
                                            <div class="flex items-center gap-2 mb-1 text-orange-500">
                                                <el-icon><Bicycle /></el-icon>
                                                <span class="text-xs font-bold uppercase">Steps</span>
                                            </div>
                                            <div class="flex items-baseline gap-2">
                                                <span class="text-3xl font-black text-slate-700 dark:text-white tabular-nums">{{ iotData.steps }}</span>
                                                <span class="text-xs text-slate-400">步</span>
                                            </div>
                                            <div class="h-1.5 w-full bg-slate-200 dark:bg-white/10 rounded-full mt-2 overflow-hidden">
                                                <div class="h-full bg-orange-400 rounded-full" style="width: 45%"></div>
                                            </div>
                                         </div>

                                         <!-- Calories (Estimated) -->
                                         <div>
                                            <div class="flex items-center gap-2 mb-1 text-purple-500">
                                                <el-icon><Lightning /></el-icon>
                                                <span class="text-xs font-bold uppercase">Calories</span>
                                            </div>
                                            <div class="flex items-baseline gap-2">
                                                <span class="text-3xl font-black text-slate-700 dark:text-white tabular-nums">{{ Math.floor(iotData.steps * 0.04) }}</span>
                                                <span class="text-xs text-slate-400">kcal</span>
                                            </div>
                                             <div class="h-1.5 w-full bg-slate-200 dark:bg-white/10 rounded-full mt-2 overflow-hidden">
                                                <div class="h-full bg-purple-400 rounded-full" style="width: 30%"></div>
                                            </div>
                                         </div>
                                    </div>
                                </div>
                            </GlassCard>
                        </div>

                        <!-- Decor -->
                        <div class="absolute -bottom-10 -left-10 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl"></div>
                    </div>

                    <!-- Right: Food Vision -->
                    <div
                        class="flex flex-col gap-6 p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 relative overflow-hidden">
                        <h3
                            class="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2 z-10">
                            <el-icon>
                                <CameraFilled />
                            </el-icon> AI 饮食识别
                        </h3>

                        <el-upload class="upload-demo w-full z-10" drag action="#" :http-request="uploadAndAnalyzeFood"
                            :show-file-list="false">
                            <div class="flex flex-col items-center py-8">
                                <el-icon
                                    class="text-5xl text-slate-300 dark:text-slate-600 mb-4 transition-colors hover:text-purple-500">
                                    <Food />
                                </el-icon>
                                <div class="text-sm text-slate-500">点击拍摄或拖拽食物照片</div>
                            </div>
                        </el-upload>

                        <!-- 4D Nutrition Result Display -->
                        <div class="z-10 grid grid-cols-2 gap-3 mt-2">
                            <!-- Calories -->
                            <div
                                class="bg-linear-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 p-3 rounded-xl border border-red-100 dark:border-red-800/30">
                                <div class="flex items-center gap-2 mb-1">
                                    <span class="text-lg">🔥</span>
                                    <span class="text-xs text-red-600 dark:text-red-400 font-medium">热量</span>
                                </div>
                                <span class="text-xl font-bold text-red-700 dark:text-red-300">{{
                                    store.dietNutrition.calories }}</span>
                                <span class="text-xs text-red-500 ml-1">kcal</span>
                            </div>
                            <!-- Carbs -->
                            <div
                                class="bg-linear-to-br from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 p-3 rounded-xl border border-yellow-100 dark:border-yellow-800/30">
                                <div class="flex items-center gap-2 mb-1">
                                    <span class="text-lg">🍞</span>
                                    <span class="text-xs text-yellow-600 dark:text-yellow-400 font-medium">碳水</span>
                                </div>
                                <span class="text-xl font-bold text-yellow-700 dark:text-yellow-300">{{
                                    store.dietNutrition.carbs
                                }}</span>
                                <span class="text-xs text-yellow-500 ml-1">g</span>
                            </div>
                            <!-- Protein -->
                            <div
                                class="bg-linear-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-3 rounded-xl border border-blue-100 dark:border-blue-800/30">
                                <div class="flex items-center gap-2 mb-1">
                                    <span class="text-lg">🥩</span>
                                    <span class="text-xs text-blue-600 dark:text-blue-400 font-medium">蛋白质</span>
                                </div>
                                <span class="text-xl font-bold text-blue-700 dark:text-blue-300">{{
                                    store.dietNutrition.protein
                                }}</span>
                                <span class="text-xs text-blue-500 ml-1">g</span>
                            </div>
                            <!-- Fat -->
                            <div
                                class="bg-linear-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 p-3 rounded-xl border border-green-100 dark:border-green-800/30">
                                <div class="flex items-center gap-2 mb-1">
                                    <span class="text-lg">🥑</span>
                                    <span class="text-xs text-green-600 dark:text-green-400 font-medium">脂肪</span>
                                </div>
                                <span class="text-xl font-bold text-green-700 dark:text-green-300">{{
                                    store.dietNutrition.fat }}</span>
                                <span class="text-xs text-green-500 ml-1">g</span>
                            </div>
                        </div>
                        <!-- Status Tag -->
                        <div class="z-10 mt-3 flex justify-end">
                            <el-tag v-if="analyzing" type="warning" effect="dark">分析中...</el-tag>
                            <el-tag v-else-if="store.dietNutrition.calories > 0" type="success"
                                effect="dark">已识别</el-tag>
                            <el-tag v-else type="info" effect="plain">待上传</el-tag>
                        </div>

                        <!-- Decor -->
                        <div class="absolute -top-10 -right-10 w-40 h-40 bg-purple-500/10 rounded-full blur-3xl"></div>
                    </div>
                </div>

                <div class="mt-8 pt-6 border-t border-gray-200 dark:border-white/10 flex justify-between items-center">
                    <GlassButton @click="$router.push('/genomics')">
                        <el-icon class="mr-2">
                            <ArrowLeft />
                        </el-icon> 上一步：基因组学
                    </GlassButton>

                    <div class="flex gap-4">
                        <GradientButton class="shadow-xl px-8" @click="runFusionAnalysis" :disabled="loading">
                            <span v-if="loading">🧠 正在进行多模态融合...</span>
                            <span v-else> 启动融合计算 (Run Fusion)</span>
                        </GradientButton>
                    </div>
                </div>

            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { CameraFilled, Watch, Timer, Bicycle, Food, ArrowLeft, Connection, Loading, Lightning } from '@element-plus/icons-vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import GradientButton from '../components/ui/GradientButton.vue'
import { useHealthStore } from '../stores/healthStore'
import { storeToRefs } from 'pinia'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast'
import { useBluetooth } from '../composables/useBluetooth'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { echarts, ensureEChartsModules } from '../utils/echarts'

ensureEChartsModules([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const store = useHealthStore()
const { iotData, userProfile, geneData } = storeToRefs(store)
const router = useRouter()
const { showToast } = useToast()
const loading = ref(false)
const analyzing = ref(false)

// Bluetooth Composable
const { device, isConnected, error, heartRate, connectDevice, setSyncCallback } = useBluetooth()

// Chart Refs
const chartRef = ref(null)
let myChart = null
const hrHistory = ref([]) // For waveform

// Initialize EChart
const initChart = () => {
    if (chartRef.value && !myChart) {
        myChart = echarts.init(chartRef.value)
        updateChart()
    }
}

const updateChart = () => {
    if (!myChart) return
    const option = {
        grid: { top: 10, bottom: 20, left: 30, right: 10 },
        xAxis: { type: 'category', show: false, data: hrHistory.value.map((_, i) => i) },
        yAxis: { type: 'value', min: 40, max: 200, splitLine: { show: false } },
        series: [{
            data: hrHistory.value,
            type: 'line',
            smooth: true,
            lineStyle: { width: 3, color: '#f87171' }, // Red-400
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(248, 113, 113, 0.5)' },
                    { offset: 1, color: 'rgba(248, 113, 113, 0.0)' }
                ])
            },
            showSymbol: false,
            animationDuration: 100
        }]
    }
    myChart.setOption(option)
}

// Watch Bluetooth HR to update Chart & IoTStore
watch(heartRate, (newVal) => {
    if (newVal > 0) {
        // Update Store Display
        store.iotData.hr = newVal
        
        // Update Chart History (keep last 50 points)
        hrHistory.value.push(newVal)
        if (hrHistory.value.length > 50) hrHistory.value.shift()
        updateChart()
    }
})

// Batch Sync Callback
const handleBatchSync = async (batchData) => {
    try {
        const token = localStorage.getItem('auth_token')
        await axios.post('/api/v1/iot/sync/batch', batchData, {
             headers: { Authorization: `Bearer ${token}` }
        })
        console.log(`Synced ${batchData.length} data points to cloud.`)
    } catch (e) {
        console.error("Batch sync failed", e)
    }
}

// Bluetooth Error Handling
watch(error, (msg) => {
    if (msg) showToast(msg, 'error')
})

const handleConnect = async () => {
    await connectDevice()
    if (isConnected.value) {
        showToast("设备连接成功！", "success")
        setSyncCallback(handleBatchSync)
        // Init chart after a slight delay to ensure DOM readiness if hidden
        setTimeout(initChart, 200)
    }
}

// Legacy polling for steps (Mock or other API)
let legacyTimer = null
const syncLegacyIoT = async () => {
    // Only mock steps if not real device connected (or keep distinct)
    // For now keep current logic for steps
    try {
        // Mock steps update
        store.iotData.steps += Math.floor(Math.random() * 5)
    } catch (e) {}
}

onMounted(() => {
    legacyTimer = setInterval(syncLegacyIoT, 3000)
})

onUnmounted(() => {
    if (legacyTimer) clearInterval(legacyTimer)
    myChart?.dispose()
})

// --- Food Analysis Logic (Unchanged) ---
const uploadAndAnalyzeFood = async (options) => {
    analyzing.value = true
    const formData = new FormData(); formData.append('file', options.file)
    try {
        const res = await axios.post('/analyze/food_image', formData)
        if (res.data.status === 'success' && res.data.nutrition) {
            store.setDietNutrition(res.data.nutrition)
            showToast(res.data.message || `识别成功！热量: ${res.data.nutrition.calories} kcal`, 'success')
        } else if (res.data.nutrition?.status === 'success') {
            store.setDietNutrition(res.data.nutrition)
            showToast(res.data.message || `识别成功！热量: ${res.data.nutrition.calories} kcal`, 'success')
        } else {
            showToast(res.data.message || "识别失败，请尝试其他图片", 'warning')
        }
    } catch (e) {
        const errorDetail = e.response?.data?.detail || e.response?.data?.message || e.message || '网络异常'
        showToast(`识别失败: ${errorDetail}`, 'error')
    } finally { analyzing.value = false }
}

const runFusionAnalysis = async () => {
    loading.value = true
    try {
        const cleanForm = { ...userProfile.value }
        Object.keys(cleanForm).forEach(k => {
            if (typeof cleanForm[k] === 'string' && !isNaN(cleanForm[k])) cleanForm[k] = parseFloat(cleanForm[k])
        })
        const payload = { ...cleanForm, user_snps: geneData.value || {} }
        const res = await axios.post('/analyze/comprehensive', payload)
        if (res.data.status === 'success') {
            store.setRiskReport(res.data.risk_report)
            showToast("融合计算完成！", "success")
            setTimeout(() => { router.push('/') }, 500)
        } else {
            showToast(res.data.message, "error")
        }
    } catch (e) {
        showToast("分析服务连接失败", "error")
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
/* Scoped overrides if necessary */
</style>
