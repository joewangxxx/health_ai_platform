<template>
    <div class="p-6 h-full flex flex-col items-center overflow-auto">
        <div class="w-full max-w-5xl">
            <!-- Header -->
            <div class="mb-8 flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold text-slate-800 dark:text-white flex items-center gap-3">
                        🥗 AI 智能食谱生成
                        <el-tag type="success" effect="dark" round size="small">Beta</el-tag>
                    </h1>
                    <p class="text-slate-500 dark:text-slate-400 mt-2">
                        基于您的健康档案与个性化需求，为您定制米其林级营养方案
                    </p>
                </div>
            </div>

            <!-- 1. Control Panel -->
            <GlassCard class="mb-8" :glowProximity="100">
                <template #header>
                    <div class="text-sm font-bold text-slate-500 uppercase tracking-wider">配置需求 (Configuration)</div>
                </template>

                <div class="py-4">
                    <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">
                        选择健康目标或限制条件：
                    </label>
                    <el-checkbox-group v-model="selectedConditions" size="large">
                        <el-checkbox-button value="hypertension">🩺 高血压 (Hypertension)</el-checkbox-button>
                        <el-checkbox-button value="diabetes">🍭 糖尿病 (Diabetes)</el-checkbox-button>
                        <el-checkbox-button value="weight_loss">🔥 减脂 (Fat Loss)</el-checkbox-button>
                        <el-checkbox-button value="muscle_gain">💪 增肌 (Muscle Gain)</el-checkbox-button>
                    </el-checkbox-group>
                </div>

                <div class="mt-6 flex justify-end">
                    <GlassButton size="lg" @click="handleGenerate" :disabled="loading" contentClass="font-bold text-lg">
                        <el-icon class="mr-2" :class="{ 'animate-spin': loading }">
                            <MagicStick />
                        </el-icon>
                        <span v-if="loading">生成中...</span>
                        <span v-else>✨ 生成今日食谱 (Generate Plan)</span>
                    </GlassButton>
                </div>
            </GlassCard>

            <!-- 2. Results Area -->
            <transition name="el-zoom-in-top">
                <div v-if="currentPlan" class="space-y-8 pb-12">

                    <!-- A. Recipe Card (AI Chef) -->
                    <div v-if="currentPlan.recipe_suggestion" class="relative group">
                        <!-- Decorative Glow -->
                        <div
                            class="absolute -inset-1 bg-linear-to-r from-pink-500 to-violet-500 rounded-2xl blur-sm opacity-30 group-hover:opacity-60 transition duration-500">
                        </div>

                        <el-card class="relative border-none shadow-xl rounded-2xl overflow-hidden dark:bg-slate-800">
                            <!-- Dish Title Header -->
                            <div
                                class="p-6 border-b border-gray-100 dark:border-gray-700 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <h2
                                        class="text-2xl font-black text-transparent bg-clip-text bg-linear-to-r from-slate-800 to-slate-600 dark:from-white dark:to-slate-300">
                                        {{ currentPlan.recipe_suggestion.dish_name }}
                                    </h2>
                                    <p class="text-slate-500 dark:text-slate-400 mt-1 italic">
                                        {{ currentPlan.recipe_suggestion.description }}
                                    </p>
                                    <!-- Task 112: Regenerate Button -->
                                    <el-button type="primary" link size="small" class="mt-2" @click="handleRegenerate" :disabled="loading">
                                        🔄 不满意？重新生成
                                    </el-button>
                                </div>
                                <div class="flex gap-2 flex-wrap">
                                    <el-tag v-for="tag in currentPlan.recipe_suggestion.tags" :key="tag" effect="light"
                                        round size="large" :type="getTagType(tag)">
                                        {{ tag }}
                                    </el-tag>
                                </div>
                            </div>

                            <div class="p-6 grid lg:grid-cols-2 gap-10">
                                <!-- Steps Timeline -->
                                <div>
                                    <h3 class="text-sm font-bold text-slate-400 uppercase mb-4 tracking-widest">烹饪步骤
                                        (Steps)</h3>
                                    <el-timeline>
                                        <el-timeline-item v-for="(step, index) in currentPlan.recipe_suggestion.steps"
                                            :key="index" :type="index === 0 ? 'primary' : ''" :hollow="index !== 0">
                                            <span class="text-slate-700 dark:text-slate-300 leading-relaxed">{{ step
                                                }}</span>
                                        </el-timeline-item>
                                    </el-timeline>
                                </div>

                                <!-- Tips & Quick Info -->
                                <div class="flex flex-col gap-6">
                                    <!-- Chef Tips -->
                                    <div
                                        class="bg-amber-50 dark:bg-amber-900/20 p-5 rounded-xl border border-amber-100 dark:border-amber-800">
                                        <h4
                                            class="font-bold text-amber-700 dark:text-amber-400 mb-2 flex items-center gap-2">
                                            <el-icon>
                                                <HotWater />
                                            </el-icon> 主厨贴士 (Chef's Tips)
                                        </h4>
                                        <p class="text-amber-800 dark:text-amber-200 text-sm leading-6">
                                            {{ currentPlan.recipe_suggestion.chef_tips }}
                                        </p>
                                    </div>

                                    <!-- Nutrition Highlight Small -->
                                    <div class="grid grid-cols-2 gap-4">
                                        <div class="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-xl text-center">
                                            <div class="text-xs text-slate-400">Total Calories</div>
                                            <div class="text-xl font-black text-slate-800 dark:text-white">
                                                {{ currentPlan.actual_calories }} <span
                                                    class="text-xs font-normal">kcal</span>
                                            </div>
                                        </div>
                                        <div class="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-xl text-center">
                                            <div class="text-xs text-slate-400">Protein Ratio</div>
                                            <div class="text-xl font-black text-blue-600">
                                                {{ ((currentPlan.macro_ratios?.protein || 0) * 100).toFixed(0) }}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </el-card>
                    </div>

                    <!-- B. Data Visualization Section -->
                    <div class="grid lg:grid-cols-2 gap-6">
                        <!-- Chart Card -->
                        <GlassCard :glowProximity="100">
                            <template #header>
                                <div class="text-sm font-bold text-slate-500">宏量营养素分布 (Macronutrients)</div>
                            </template>
                            <div class="h-64 flex items-center justify-center">
                                <div ref="chartContainer" class="w-full h-full"></div>
                            </div>
                        </GlassCard>

                        <!-- Ingredients Table Card -->
                        <GlassCard :glowProximity="100">
                            <template #header>
                                <div class="text-sm font-bold text-slate-500">食材清单 (Ingredients)</div>
                            </template>
                            <div class="h-64 overflow-auto">
                                <el-table :data="currentPlan.foods" style="width: 100%" size="small" :border="false">
                                    <el-table-column label="食材 (Ingredient)" min-width="140">
                                        <template #default="scope">
                                            <div class="flex flex-col">
                                                <span class="font-medium text-slate-700 dark:text-slate-200">
                                                    {{ scope.row.name }}
                                                </span>
                                            </div>
                                        </template>
                                    </el-table-column>

                                    <el-table-column label="份量 (Portion)" width="120">
                                        <template #default="scope">
                                            <span class="text-slate-600 dark:text-slate-400">
                                                {{ scope.row.amount_desc }}
                                            </span>
                                        </template>
                                    </el-table-column>

                                    <el-table-column label="热量" width="80" align="right">
                                        <template #default="scope">
                                            <span class="font-mono">{{ scope.row.calories }}</span>
                                        </template>
                                    </el-table-column>
                                </el-table>
                            </div>
                        </GlassCard>
                    </div>

                </div>
            </transition>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, onUnmounted, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MagicStick, HotWater } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useNutritionStore } from '../../stores/nutritionStore'
import { useAuthStore } from '../../stores/authStore'
import { storeToRefs } from 'pinia'
import GlassCard from '../../components/ui/GlassCard.vue'
import GlassButton from '../../components/ui/GlassButton.vue'
import * as echarts from 'echarts'
import { useToast } from '../../composables/useToast'

const store = useNutritionStore()
const authStore = useAuthStore()
const router = useRouter()
const { currentPlan, loading } = storeToRefs(store)
const { showToast } = useToast()

// State
const selectedConditions = ref([])
const chartContainer = ref(null)
let myChart = null

// Actions
const handleGenerate = async () => {
    // 1. Check for empty conditions
    if (selectedConditions.value.length === 0) {
        try {
            await ElMessageBox.confirm(
                '您未选择任何健康限制，系统将为您生成标准的均衡膳食方案。是否继续？',
                '确认生成',
                {
                    confirmButtonText: '继续生成',
                    cancelButtonText: '取消',
                    type: 'info',
                }
            )
        } catch (e) {
            return // User cancelled
        }
    }

    // 2. Proceed
    const conditions = Array.from(selectedConditions.value)
    await store.generatePlan(conditions)
}

// Task 112: Force Refresh - Regenerate Recipe
const handleRegenerate = async () => {
    const conditions = Array.from(selectedConditions.value)
    await store.generatePlan(conditions, true)  // force_refresh = true
}

// Helpers
const getTagType = (tag) => {
    if (tag.includes('低') || tag.includes('Low')) return 'success'
    if (tag.includes('高') || tag.includes('High')) return 'warning'
    return 'info'
}

// Charts Logic
const renderChart = () => {
    if (!currentPlan.value || !chartContainer.value) return

    if (myChart) myChart.dispose()
    myChart = echarts.init(chartContainer.value)

    const macros = currentPlan.value.macros

    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c}g ({d}%)'
        },
        legend: {
            bottom: '0%',
            left: 'center',
            icon: 'circle'
        },
        color: ['#3b82f6', '#10b981', '#f59e0b'],
        series: [
            {
                name: 'Macros',
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 20,
                        fontWeight: 'bold'
                    }
                },
                labelLine: {
                    show: false
                },
                data: [
                    { value: macros.protein_g, name: 'Protein (蛋白质)' },
                    { value: macros.carbs_g, name: 'Carbs (碳水)' },
                    { value: macros.fat_g, name: 'Fat (脂肪)' }
                ]
            }
        ]
    }

    myChart.setOption(option)
}

// Watchers
watch(currentPlan, async (newVal) => {
    if (newVal) {
        await nextTick()
        renderChart()
    }
})

// Resize handler
const handleResize = () => {
    myChart && myChart.resize()
}

// Lifecycle
onMounted(async () => {
    window.addEventListener('resize', handleResize)

    // Auth Check
    try {
        await authStore.fetchProfile()
        if (!authStore.isAuthenticated) {
            showToast('登录已过期，请重新登录', 'warning')
            router.push('/login')
            return
        }
    } catch (e) {
        if (e.response?.status === 401) {
            authStore.logout()
            router.push('/login')
        }
    }

    // If plan already exists (persistence), render it
    if (currentPlan.value) {
        nextTick(() => renderChart())
    }
})

onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    if (myChart) myChart.dispose()
})
</script>

<style scoped></style>
