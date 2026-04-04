<template>
    <div class="p-6 h-full flex flex-col items-center">
        <div class="w-full max-w-5xl">
            <!-- Title -->
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                💊 智能药房 (Smart Pharmacy)
            </h1>

            <GlassCard :glowProximity="100">
                <template #header>
                    <div class="flex justify-between items-center text-sm text-slate-500 dark:text-slate-400">
                        <span>多模态药物基因组学安全筛查</span>
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                            <span>AI Engine Ready</span>
                        </div>
                    </div>
                </template>

                <!-- 1. Search Bar -->
                <div
                    class="flex gap-4 mb-8 p-6 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-inner">
                    <el-autocomplete v-model="drugName" :fetch-suggestions="querySearch"
                        placeholder="输入药物名称 (例如: Metoprolol, Warfarin)" size="large" class="flex-1 text-lg w-full"
                        :trigger-on-focus="true" @select="handleSelect" clearable>
                        <template #prefix>
                            <el-icon class="text-gray-400">
                                <Search />
                            </el-icon>
                        </template>
                    </el-autocomplete>

                    <GlassButton @click="analyzeMedication" :disabled="analyzing">
                        <span class="font-bold">{{ analyzing ? '分析中...' : '安全分析 (Analyze)' }}</span>
                    </GlassButton>
                </div>

                <!-- 2. Result Area -->
                <transition name="el-zoom-in-top">
                    <div v-if="result" class="mt-2">

                        <!-- A. Score & Recommendation Header -->
                        <div class="flex flex-col md:flex-row gap-8 mb-8">
                            <!-- Score -->
                            <div
                                class="flex flex-col items-center justify-center p-6 bg-white dark:bg-black/20 rounded-2xl border border-slate-100 dark:border-white/5 shadow-sm min-w-[200px]">
                                <el-progress type="dashboard" :percentage="result.safety_score" :color="scoreColors"
                                    :width="140" :stroke-width="12">
                                    <template #default="{ percentage }">
                                        <span class="text-3xl font-black block">{{ percentage }}</span>
                                        <span class="text-xs text-slate-400 uppercase">Safety Score</span>
                                    </template>
                                </el-progress>
                            </div>

                            <!-- Recommendation -->
                            <div
                                class="flex-1 p-6 rounded-2xl bg-linear-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800 flex flex-col justify-center">
                                <h3
                                    class="text-sm font-bold uppercase tracking-wider text-blue-500 mb-2 flex items-center gap-2">
                                    <el-icon>
                                        <FirstAidKit />
                                    </el-icon> AI 最终建议 (Final Recommendation)
                                </h3>
                                <p
                                    class="text-lg md:text-xl font-bold text-slate-700 dark:text-slate-200 leading-relaxed">
                                    {{ result.recommendation }}
                                </p>
                            </div>
                        </div>

                        <!-- B. Multi-modal Breakdown -->
                        <h3 class="text-sm font-bold text-slate-500 mb-4 pl-1">🧬 多维风险归因 (Risk Factors Breakdown)</h3>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">

                            <!-- Genomic Card -->
                            <div
                                class="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-white/5 relative overflow-hidden group hover:border-blue-300 transition-colors">
                                <div class="flex items-center gap-3 mb-3">
                                    <div
                                        class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-xl">
                                        🧬</div>
                                    <h4 class="font-bold text-slate-700 dark:text-slate-300">基因组学<br><span
                                            class="text-[10px] font-normal opacity-60">Genomic Factor</span></h4>
                                </div>
                                <p class="text-sm text-slate-600 dark:text-slate-400 leading-6">{{
                                    result.analysis.genomic }}</p>
                            </div>

                            <!-- Clinical Card -->
                            <div
                                class="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-white/5 relative overflow-hidden group hover:border-orange-300 transition-colors">
                                <div class="flex items-center gap-3 mb-3">
                                    <div
                                        class="w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center text-xl">
                                        🩺</div>
                                    <h4 class="font-bold text-slate-700 dark:text-slate-300">临床表型<br><span
                                            class="text-[10px] font-normal opacity-60">Clinical Factor</span></h4>
                                </div>
                                <p class="text-sm text-slate-600 dark:text-slate-400 leading-6">{{
                                    result.analysis.clinical }}</p>
                            </div>

                            <!-- IoT Card -->
                            <div
                                class="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200 dark:border-white/5 relative overflow-hidden group hover:border-purple-300 transition-colors">
                                <div class="flex items-center gap-3 mb-3">
                                    <div
                                        class="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-xl">
                                        ⌚</div>
                                    <h4 class="font-bold text-slate-700 dark:text-slate-300">实时状态<br><span
                                            class="text-[10px] font-normal opacity-60">IoT Context</span></h4>
                                </div>
                                <p class="text-sm text-slate-600 dark:text-slate-400 leading-6">{{ result.analysis.iot
                                    }}</p>
                            </div>

                        </div>
                    </div>

                    <!-- Empty State -->
                    <div v-else
                        class="mt-12 mb-12 flex flex-col items-center justify-center opacity-40 p-10 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-3xl">
                        <div class="p-4 rounded-full bg-slate-100 dark:bg-white/10 mb-4 transition-colors">
                            <el-icon size="64" class="text-slate-400 dark:text-slate-200">
                                <FirstAidKit />
                            </el-icon>
                        </div>
                        <p class="text-base font-medium text-slate-500 dark:text-slate-300">请输入药物名称以开始安全筛查</p>
                        <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">支持检测药物基因相互作用、肝肾功能禁忌及实时状态预警</p>
                    </div>
                </transition>

            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search, FirstAidKit } from '@element-plus/icons-vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import { useHealthStore } from '../stores/healthStore'
import { storeToRefs } from 'pinia'
import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast'

const store = useHealthStore()
const router = useRouter()
const { userProfile, geneData, iotData } = storeToRefs(store)
const { showToast } = useToast()

const drugName = ref('')
const analyzing = ref(false)
const result = ref(null)
const allDrugs = ref([])

const scoreColors = [
    { color: '#f56c6c', percentage: 20 },
    { color: '#e6a23c', percentage: 60 },
    { color: '#67c23a', percentage: 100 },
]

onMounted(async () => {
    try {
        const res = await axios.get('/drugs/list')
        if (res.data.status === 'success') {
            allDrugs.value = res.data.drugs.map(d => ({ value: d }))
        }
    } catch (e) {
        console.error("Failed to load drug list", e)
    }
})

const querySearch = (queryString, cb) => {
    const results = queryString
        ? allDrugs.value.filter(createFilter(queryString))
        : allDrugs.value
    // limit results to avoid lagging
    cb(results.slice(0, 50))
}

const createFilter = (queryString) => {
    return (drug) => {
        return (drug.value.toLowerCase().indexOf(queryString.toLowerCase()) === 0)
    }
}

const handleSelect = (item) => {
    drugName.value = item.value
}

const analyzeMedication = async () => {
    if (!drugName.value) return showToast("请输入药物名称", "warning")

    // Check for missing profile (Cold Start Warning)
    if (!userProfile.value || !userProfile.value.Age) {
        showToast('提示：您尚未完善健康档案，分析结果仅供参考', 'info')
    }

    analyzing.value = true
    result.value = null

    try {
        const payload = {
            target_drug: drugName.value,
            clinical: userProfile.value,
            genetics: geneData.value || {},
            iot: iotData.value
        }

        const res = await axios.post('/analyze/medication', payload)
        if (res.data.status === 'success') {
            // Check for missing data status from service
            if (res.data.detail?.status === 'missing_data') {
                ElMessageBox.confirm(
                    '进行药物安全评估需要肝肾功能数据。检测到您尚未填写，是否立即前往补充？',
                    '数据缺失',
                    {
                        confirmButtonText: '去填写',
                        cancelButtonText: '取消',
                        type: 'warning',
                    }
                )
                    .then(() => {
                        router.push('/clinical')
                    })
                    .catch(() => {
                        // Canceled
                    })
                result.value = null // Do not show empty/partial result
                return
            }

            result.value = res.data
            showToast("分析完成", "success")
        } else {
            showToast(res.data.message, "error")
        }
    } catch (e) {
        showToast("分析服务连接异常", "error")
    } finally {
        analyzing.value = false
    }
}
</script>

<style scoped>
/* Ensure autocomplete width works in flex container */
:deep(.el-autocomplete) {
    display: flex;
    /* Helps to fill flex parent if needed, usually width:100% is enough */
}

/* Dark mode overrides for Element Plus Autocomplete */
:deep(.el-input__wrapper) {
    background-color: white;
    box-shadow: 0 0 0 1px #e2e8f0 inset;
}

:deep(html.dark .el-input__wrapper) {
    background-color: rgba(0, 0, 0, 0.3) !important;
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset !important;
}

:deep(html.dark .el-input__inner) {
    color: white !important;
}

:deep(html.dark .el-input__inner::placeholder) {
    color: rgba(255, 255, 255, 0.4);
}
</style>
