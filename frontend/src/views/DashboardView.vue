<template>
    <div class="h-full flex flex-col p-4 overflow-hidden">

        <!-- Empty State -->
        <transition name="el-fade-in-linear">
            <div v-if="!store.riskReport || !store.userProfile.Age || !store.userProfile.BMI"
                class="empty-state p-10 rounded-3xl flex flex-col justify-center items-center h-full backdrop-blur-md transition-colors border border-dashed border-gray-400/30">
                <div class="bg-blue-50 p-6 rounded-full mb-6 animate-bounce-slow">
                    <el-icon size="60" class="text-blue-500">
                        <DataAnalysis />
                    </el-icon>
                </div>
                <h2 class="text-2xl font-bold text-slate-700 mb-2">👋 欢迎来到 HealthAI Platform</h2>
                <p class="text-lg font-light mb-8 max-w-md text-center text-slate-600">请先前往 <strong
                        class="text-blue-500">[临床体检]</strong> 页面完善您的健康档案，以获取精准的
                    AI 风险评估。</p>

                <div class="flex gap-4">
                    <GlassButton size="lg" @click="$router.push('/clinical')">
                        前往完善档案 <el-icon class="ml-2">
                            <ArrowRight />
                        </el-icon>
                    </GlassButton>
                </div>
            </div>
        </transition>

        <!-- Results Dashboard -->
        <div v-if="store.riskReport && store.userProfile.Age" class="h-full flex flex-col gap-5 min-h-0 relative">

            <!-- Header Actions (Right aligned above cards) -->
            <div class="flex justify-end mb-2">
                <GlassButton size="sm" class="gap-2" @click="refreshAnalysis" :disabled="loading">
                    <el-icon :class="{ 'is-loading': loading }">
                        <Refresh />
                    </el-icon>
                    更新报告
                </GlassButton>
            </div>

            <!-- 1. Top Cards: High Risks -->
            <div class="grid grid-cols-4 gap-3 shrink-0 h-32">
                <div v-for="risk in topRisks" :key="risk.name"
                    class="relative group rounded-2xl h-full w-full overflow-visible">
                    <GlowingEffect class="rounded-2xl" :spread="20" :glow="true" :disabled="false" :proximity="60"
                        :inactiveZone="0.01" :borderWidth="1">
                        <div
                            :class="['relative z-10 h-full rounded-2xl p-2 flex flex-col justify-center items-center shadow-lg backdrop-blur-md text-white border border-white/10 transition-all duration-300 hover:-translate-y-1', risk.level_class]">
                            <div class="text-xs opacity-90 mb-0.5 font-medium tracking-wide">{{ risk.name }}</div>
                            <div class="text-2xl font-black my-0.5 drop-shadow-md">{{ risk.prob }}%</div>
                            <div
                                class="bg-black/20 px-2 py-0.5 rounded-full text-[10px] backdrop-blur-sm border border-white/10">
                                {{ risk.level }}</div>
                        </div>
                    </GlowingEffect>
                </div>
            </div>

            <!-- 2. Charts Area -->
            <div class="grid grid-cols-2 gap-3 flex-1 min-h-0 items-stretch">

                <!-- Radar Chart -->
                <GlassCard class="h-full" :glowProximity="100" :glowSpread="40">
                    <div class="font-bold text-slate-700 mb-2 px-1 flex items-center gap-2 text-sm shrink-0">
                        <span class="w-1 h-3 bg-blue-500 rounded-full"></span>
                        🌐 全身系统风险雷达 (Systemic Risk Radar)
                    </div>
                    <div id="radarChart" class="flex-1 w-full min-h-[300px]"></div>
                </GlassCard>

                <!-- Attribution Table -->
                <GlassCard class="h-full" :glowProximity="100" :glowSpread="40">
                    <div class="font-bold text-slate-700 mb-2 px-1 flex items-center gap-2 text-sm shrink-0">
                        <span class="w-1 h-3 bg-purple-500 rounded-full"></span>
                        🧠 AI 决策归因 (Bayesian Inference)
                    </div>
                    <div class="flex-1 overflow-hidden rounded-xl border border-gray-500/10">
                        <el-table :data="attributionData" style="width: 100%; height: 100%;"
                            class="bg-transparent text-xs" size="small"
                            :header-cell-style="{ background: 'rgba(120,120,120,0.05)', color: 'inherit', fontWeight: 'bold' }"
                            :row-style="{ background: 'transparent' }">

                            <el-table-column prop="disease" label="病种 (Disease)" min-width="100"
                                show-overflow-tooltip />

                            <el-table-column label="基准 (Base)" min-width="80" align="center">
                                <template #default="scope">
                                    <div class="font-mono opacity-80">{{ scope.row.base }}%</div>
                                </template>
                            </el-table-column>

                            <el-table-column label="基因修正 (Gene)" min-width="90" align="center">
                                <template #default="scope">
                                    <el-tag :type="getModType(scope.row.gene)" effect="plain" size="small"
                                        class="scale-90 font-mono font-bold">
                                        {{ scope.row.gene }}
                                    </el-tag>
                                </template>
                            </el-table-column>

                            <el-table-column label="行为修正 (Life)" min-width="90" align="center">
                                <template #default="scope">
                                    <el-tag :type="getModType(scope.row.life)" effect="plain" size="small"
                                        class="scale-90 font-mono font-bold">
                                        {{ scope.row.life }}
                                    </el-tag>
                                </template>
                            </el-table-column>

                        </el-table>
                    </div>
                </GlassCard>

            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted, nextTick, watch, ref } from 'vue'
import { DataAnalysis, ArrowRight, Refresh } from '@element-plus/icons-vue'
import { useToast } from '../composables/useToast'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import GlowingEffect from '../components/ui/GlowingEffect.vue'
import * as echarts from 'echarts'
import { useHealthStore } from '../stores/healthStore'
import { storeToRefs } from 'pinia'
import axios from 'axios'

const store = useHealthStore()
const { userProfile, geneData, iotData } = storeToRefs(store)
const loading = ref(false)
const isDark = ref(false)
const { showToast } = useToast()

// --- Logic: Refresh Analysis ---
const refreshAnalysis = async () => {
    loading.value = true
    try {
        // ... (Payload preparation omitted for brevity, logic unchanged) ...
        const cleanForm = { ...userProfile.value }
        Object.keys(cleanForm).forEach(k => {
            if (typeof cleanForm[k] === 'string' && !isNaN(cleanForm[k])) cleanForm[k] = parseFloat(cleanForm[k])
        })
        const payload = { ...cleanForm, user_snps: geneData.value || {} }

        const res = await axios.post('http://127.0.0.1:8000/analyze/comprehensive', payload)

        if (res.data.status === 'success') {
            store.setRiskReport(res.data.risk_report)
            showToast("报告已更新", "success")
            await nextTick()
            renderRadar()
        } else {
            showToast(res.data.message, "error")
        }
    } catch (e) {
        showToast("分析服务连接失败", "error")
    } finally {
        loading.value = false
    }
}

// --- Data Mapping & Computed ---
const nameMap = {
    'T2D': '糖尿病', 'PreDiabetes': '糖尿病前期', 'Obesity': '肥胖症', 'AbdominalObesity': '腹型肥胖',
    'Gout': '痛风', 'Hyperuricemia': '高尿酸血症', 'Hypertension': '高血压', 'HighLipid': '高血脂',
    'MetabolicSyndrome': '代谢综合征', 'InsulinResist': '胰岛素抵抗', 'HeartFailure': '心力衰竭',
    'CoronaryHeart': '冠心病', 'HeartAttack': '心脏病发作', 'Stroke': '中风', 'CVD': '综合心血管病',
    'CKD': '慢性肾病', 'KidneyStones': '肾结石', 'LiverDisease': '肝损伤风险', 'FattyLiver': '脂肪肝', 'Anemia': '贫血',
    'Inflammation': '慢性炎症', 'Osteoporosis': '骨质疏松', 'Arthritis': '关节炎', 'Asthma': '哮喘',
    'Psoriasis': '银屑病', 'GumDisease': '牙龈病', 'Depression': '抑郁风险', 'IronDef': '缺铁风险',
    'IronOverload': '铁过载风险', 'HighLead': '重金属铅风险', 'HighCadmium': '重金属镉风险'
}

const topRisks = computed(() => {
    if (!store.riskReport) return []
    const arr = Object.entries(store.riskReport).map(([k, v]) => ({
        name: nameMap[k] || k, prob: v.final_risk, level: v.level,
        level_class: v.level.includes('Very High') ? 'bg-linear-to-br from-red-600 to-rose-700' : (v.level.includes('High') ? 'bg-linear-to-br from-orange-400 to-red-500' : 'bg-linear-to-br from-emerald-400 to-teal-500')
    }))
    return arr.sort((a, b) => b.prob - a.prob).slice(0, 4)
})

const attributionData = computed(() => {
    if (!store.riskReport) return []
    const formatMod = (val) => {
        if (!val) return 'x1.0'
        const num = parseFloat(String(val).replace('x', ''))
        if (isNaN(num)) return 'x1.0'
        return 'x' + num.toFixed(1)
    }
    return Object.entries(store.riskReport).map(([k, v]) => {
        const src = v.breakdown || v.sources || {}
        let rawBase = src.clinical || src.clinical_base || src.base_clinical || 0
        let baseVal = typeof rawBase === 'number' ? rawBase : parseFloat(String(rawBase).replace('%', ''))
        return {
            disease: nameMap[k] || k,
            base: baseVal || 0,
            gene: formatMod(src.gene_modifier || src.gene_mod),
            life: formatMod(src.lifestyle_modifier || src.life_mod)
        }
    }).slice(0, 10)
})

const getModType = (valStr) => {
    const val = parseFloat(String(valStr).replace('x', ''))
    if (val > 1.1) return 'danger'
    if (val < 0.9) return 'success'
    return 'info'
}

// --- Charts ---
let radarChart = null
const renderRadar = () => {
    if (!store.riskReport) return
    const chartDom = document.getElementById('radarChart')
    if (!chartDom) return
    if (radarChart) radarChart.dispose()

    // Theme colors
    const textColor = isDark.value ? '#e2e8f0' : '#334155'
    const splitLineColor = isDark.value ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'

    radarChart = echarts.init(chartDom)
    const keys = ['T2D', 'Hypertension', 'HighLipid', 'FattyLiver', 'CKD', 'Gout', 'MetabolicSyndrome']
    const values = keys.map(k => store.riskReport[k] ? store.riskReport[k].final_risk : 0)

    radarChart.setOption({
        radar: {
            center: ['50%', '55%'], radius: '70%',
            indicator: keys.map(k => ({ name: nameMap[k] || k, max: 100 })),
            splitArea: { areaStyle: { color: ['transparent'] } },
            axisName: { color: textColor, fontWeight: 'bold' },
            splitLine: { lineStyle: { color: splitLineColor } },
            axisLine: { lineStyle: { color: splitLineColor } }
        },
        series: [{
            type: 'radar',
            data: [{
                value: values,
                name: 'Risk Profile',
                areaStyle: { color: 'rgba(64,158,255, 0.5)' },
                lineStyle: { color: '#409EFF', width: 3 },
                itemStyle: { color: '#409EFF' }
            }]
        }]
    })
}

// Watchers and lifecycle
onMounted(() => {
    isDark.value = document.documentElement.classList.contains('dark')
    // Observe theme change
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class') {
                isDark.value = document.documentElement.classList.contains('dark')
                renderRadar()
            }
        })
    })
    observer.observe(document.documentElement, { attributes: true })

    if (store.riskReport) {
        nextTick(() => renderRadar())
    }
})

watch(() => store.riskReport, () => {
    nextTick(() => renderRadar())
})
</script>

<style scoped>
/* Tables in dark/light mode */
.dark :deep(.el-table) {
    color: #e2e8f0;
}

:deep(.el-table) {
    --el-table-border-color: rgba(128, 128, 128, 0.1);
}
</style>
