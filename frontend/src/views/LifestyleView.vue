<template>
    <div class="p-4 md:p-6 h-full flex flex-col items-center">
        <div class="w-full max-w-6xl">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                行为监测与饮食识别
            </h1>

            <GlassCard :glowProximity="100">
                <template #header>
                    <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between text-sm">
                        <div>
                            <div class="font-semibold text-slate-700 dark:text-slate-200">生活方式行为数据工作台</div>
                            <div class="text-xs text-slate-500 dark:text-slate-400">
                                蓝牙低功耗设备、饮食识别与平台标准行为时间线
                            </div>
                        </div>
                        <el-tag :type="activeScenario ? 'success' : 'info'" effect="plain" round>
                            {{ selectedScenario ? displayDataMode(selectedScenario.data_mode) : '等待上传' }}
                        </el-tag>
                    </div>
                </template>

                <div class="grid xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.82fr)] gap-6 py-4">
                    <section
                        class="flex flex-col gap-6 p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 relative overflow-hidden">
                        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between z-10">
                            <h3 class="text-sm font-bold uppercase text-slate-500 flex items-center gap-2">
                                <el-icon><Watch /></el-icon>
                                物联网实时监测（蓝牙）
                            </h3>
                            <div v-if="isConnected" class="flex items-center gap-2">
                                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                                <span class="text-xs text-green-600 font-bold">已连接（实时）</span>
                            </div>
                            <div v-else class="flex items-center gap-2">
                                <div class="w-2 h-2 rounded-full bg-slate-300"></div>
                                <span class="text-xs text-slate-400">离线</span>
                            </div>
                        </div>

                        <div v-if="!isConnected" class="z-10 py-6 flex flex-col items-center justify-center text-center">
                            <GlassButton @click="handleConnect" class="group">
                                <el-icon class="mr-2 group-hover:animate-pulse"><Connection /></el-icon>
                                扫描并连接设备
                            </GlassButton>
                            <span class="text-xs text-slate-400 mt-3 px-4">
                                支持标准蓝牙低功耗心率带。当前设备数据不会写入行为时间线。
                            </span>
                        </div>

                        <div v-else class="z-10 animate-in fade-in zoom-in duration-300 w-full">
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-0 min-h-64 overflow-hidden rounded-2xl border border-slate-200 dark:border-white/10 bg-white/40 dark:bg-black/20">
                                <div class="md:col-span-2 relative min-h-64 bg-slate-100/50 dark:bg-black/20 border-r border-slate-200 dark:border-white/5">
                                    <div ref="chartRef" class="w-full h-full min-h-64"></div>
                                    <div class="absolute top-4 left-4 flex flex-col">
                                        <span class="text-xs font-bold text-slate-400 uppercase">心率</span>
                                        <div class="flex items-end gap-2 text-red-500">
                                            <el-icon class="text-2xl animate-pulse"><Timer /></el-icon>
                                            <span class="text-4xl font-black leading-none tabular-nums">{{ iotData.hr }}</span>
                                            <span class="text-sm font-bold mb-1">次/分</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="flex flex-col justify-center gap-6 p-6 bg-white/40 dark:bg-white/5">
                                    <div>
                                        <div class="flex items-center gap-2 mb-1 text-orange-500">
                                            <el-icon><Bicycle /></el-icon>
                                            <span class="text-xs font-bold uppercase">步数</span>
                                        </div>
                                        <div class="flex items-baseline gap-2">
                                            <span class="text-3xl font-black text-slate-700 dark:text-white tabular-nums">{{ iotData.steps }}</span>
                                            <span class="text-xs text-slate-400">步</span>
                                        </div>
                                    </div>

                                    <div>
                                        <div class="flex items-center gap-2 mb-1 text-purple-500">
                                            <el-icon><Lightning /></el-icon>
                                            <span class="text-xs font-bold uppercase">热量</span>
                                        </div>
                                        <div class="flex items-baseline gap-2">
                                            <span class="text-3xl font-black text-slate-700 dark:text-white tabular-nums">{{ Math.floor(iotData.steps * 0.04) }}</span>
                                            <span class="text-xs text-slate-400">千卡</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section
                        class="flex flex-col gap-5 p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 relative overflow-hidden">
                        <h3 class="text-sm font-bold uppercase text-slate-500 flex items-center gap-2 z-10">
                            <el-icon><CameraFilled /></el-icon>
                            AI 饮食识别
                        </h3>

                        <el-upload class="upload-demo w-full z-10" drag action="#" :http-request="uploadAndAnalyzeFood"
                            :show-file-list="false">
                            <div class="flex flex-col items-center py-6">
                                <el-icon class="text-5xl text-slate-300 dark:text-slate-600 mb-4 transition-colors hover:text-purple-500">
                                    <Food />
                                </el-icon>
                                <div class="text-sm text-slate-500">点击拍摄或拖拽食物照片</div>
                            </div>
                        </el-upload>

                        <div class="z-10 grid grid-cols-2 sm:grid-cols-5 gap-3 mt-1">
                            <div class="nutrition-tile from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-red-100 dark:border-red-800/30">
                                <span class="text-xs text-red-600 dark:text-red-400 font-medium">热量</span>
                                <strong class="text-lg text-red-700 dark:text-red-300">{{ store.dietNutrition.calories }}</strong>
                                <span class="text-xs text-red-500">千卡</span>
                            </div>
                            <div class="nutrition-tile from-yellow-50 to-amber-50 dark:from-yellow-900/20 dark:to-amber-900/20 border-yellow-100 dark:border-yellow-800/30">
                                <span class="text-xs text-yellow-600 dark:text-yellow-400 font-medium">碳水</span>
                                <strong class="text-lg text-yellow-700 dark:text-yellow-300">{{ store.dietNutrition.carbs }}</strong>
                                <span class="text-xs text-yellow-500">克</span>
                            </div>
                            <div class="nutrition-tile from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-100 dark:border-blue-800/30">
                                <span class="text-xs text-blue-600 dark:text-blue-400 font-medium">蛋白</span>
                                <strong class="text-lg text-blue-700 dark:text-blue-300">{{ store.dietNutrition.protein }}</strong>
                                <span class="text-xs text-blue-500">克</span>
                            </div>
                            <div class="nutrition-tile from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-100 dark:border-green-800/30">
                                <span class="text-xs text-green-600 dark:text-green-400 font-medium">脂肪</span>
                                <strong class="text-lg text-green-700 dark:text-green-300">{{ store.dietNutrition.fat }}</strong>
                                <span class="text-xs text-green-500">克</span>
                            </div>
                            <div class="nutrition-tile from-sky-50 to-cyan-50 dark:from-sky-900/20 dark:to-cyan-900/20 border-sky-100 dark:border-sky-800/30 col-span-2 sm:col-span-1">
                                <span class="text-xs text-sky-600 dark:text-sky-400 font-medium">钠</span>
                                <strong class="text-lg text-sky-700 dark:text-sky-300">{{ store.dietNutrition.sodium_mg }}</strong>
                                <span class="text-xs text-sky-500">毫克</span>
                            </div>
                        </div>

                        <div class="z-10 flex flex-wrap items-center justify-between gap-2">
                            <el-tag v-if="analyzing" type="warning" effect="dark">分析中...</el-tag>
                            <el-tag v-else-if="store.dietNutrition.provenance?.source_type === 'simulated_demo'" type="info" effect="plain">
                                示例饮食识别
                            </el-tag>
                            <el-tag v-else-if="store.dietNutrition.calories > 0" type="success" effect="dark">已识别</el-tag>
                            <el-tag v-else type="info" effect="plain">待上传</el-tag>
                            <span class="text-xs text-slate-500 dark:text-slate-400">饮食识别不会自动上传图片原始文件。</span>
                        </div>
                    </section>
                </div>

                <section data-testid="behavior-day-timeline"
                    class="mt-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-800/50 p-5">
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div class="min-w-0">
                            <div class="flex flex-wrap items-center gap-2 mb-2">
                                <h2 class="text-lg font-black text-slate-800 dark:text-white">一天行为时间线</h2>
                                <el-tag :type="activeScenario ? 'success' : 'info'" effect="plain">
                                    {{ selectedScenario ? displayDataMode(selectedScenario.data_mode) : '等待上传' }}
                                </el-tag>
                            </div>
                            <p class="text-sm text-slate-500 dark:text-slate-400 max-w-3xl">
                                上传平台标准 CSV/JSON 行为日文件后，系统会解析为一天行为时间线，并用于本页预览与融合风险解释。
                            </p>
                        </div>
                    </div>

                    <div data-testid="behavior-upload-import" class="mt-5">
                        <el-upload
                            class="behavior-import-upload"
                            drag
                            action="#"
                            accept=".csv,.json,application/json,text/csv"
                            :http-request="handleBehaviorImport"
                            :show-file-list="false"
                            :disabled="behaviorImportLoading"
                        >
                            <div class="flex flex-col items-center py-5">
                                <el-icon class="text-4xl text-slate-300 dark:text-slate-600 mb-3">
                                    <Loading />
                                </el-icon>
                                <div class="text-sm font-bold text-slate-700 dark:text-slate-100">
                                    上传平台标准 CSV/JSON 行为日
                                </div>
                                <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                    成功后标记为 {{ displayDataMode('user_uploaded') }}，仅用于本页预览和风险解释上下文
                                </div>
                            </div>
                        </el-upload>
                    </div>

                    <div v-if="behaviorImportError" class="mt-4 text-sm text-red-600 dark:text-red-300">
                        {{ behaviorImportError }}
                    </div>

                    <div v-if="scenarioError" class="mt-4 text-sm text-red-600 dark:text-red-300">
                        {{ scenarioError }}
                    </div>

                    <div v-if="!activeScenario" class="mt-5 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/55 dark:bg-slate-900/20 p-6 text-center">
                        <div class="text-sm font-bold text-slate-700 dark:text-slate-100">等待上传行为日文件</div>
                        <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            上传成功后，这里会显示全天指标、时间线事件、事件详情和融合分析入口。
                        </div>
                    </div>

                    <div v-if="activeScenario" class="mt-6 grid lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] gap-6">
                        <div class="space-y-5 min-w-0">
                            <div class="flex flex-wrap gap-3">
                                <div v-for="metric in summaryMetrics" :key="metric.label"
                                    class="metric-chip">
                                    <span class="metric-chip-label">{{ metric.label }}</span>
                                    <strong class="metric-chip-value">{{ metric.value }}</strong>
                                    <span class="metric-chip-unit">{{ metric.unit }}</span>
                                </div>
                            </div>

                            <div class="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/50 dark:bg-black/10 p-4">
                                <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-4">
                                    <div>
                                        <div class="text-sm font-bold text-slate-700 dark:text-slate-100">
                                            {{ displayScenarioTitle(activeScenario) }}
                                        </div>
                                        <div class="text-xs text-slate-500">
                                            {{ displayScenarioSubject(selectedScenario) }} · {{ displayDataMode(selectedScenario.data_mode) }} · {{ currentTimelineTime }}
                                        </div>
                                    </div>
                                    <div class="flex flex-wrap gap-2">
                                        <GlassButton data-testid="behavior-play-toggle" size="sm" @click="togglePlayback">
                                            <el-icon><Timer /></el-icon>
                                            {{ isPlaying ? '暂停' : '播放' }}
                                        </GlassButton>
                                        <GlassButton data-testid="behavior-replay" size="sm" @click="replayScenario">
                                            <el-icon><Loading /></el-icon>
                                            重播
                                        </GlassButton>
                                    </div>
                                </div>

                                <el-slider
                                    data-testid="behavior-progress"
                                    v-model="timelineProgress"
                                    :min="0"
                                    :max="timelineMax"
                                    :step="1"
                                    :show-tooltip="false"
                                    @change="seekTimeline"
                                />

                                <div class="mt-4 space-y-3 max-h-[430px] overflow-auto pr-1">
                                    <button
                                        v-for="(event, index) in timelineEvents"
                                        :key="event.event_id"
                                        type="button"
                                        class="timeline-row"
                                        :class="{ 'timeline-row-active': index === currentEventIndex }"
                                        @click="selectTimelineEvent(index)"
                                    >
                                        <span class="timeline-time">{{ event.time }}</span>
                                        <span class="timeline-dot" :class="eventTypeColor(event.event_type)"></span>
                                        <span class="min-w-0 flex-1">
                                            <span class="block text-sm font-semibold text-slate-800 dark:text-white truncate">{{ displayEventLabel(event) }}</span>
                                            <span class="block text-xs text-slate-500 truncate">{{ displayEventType(event.event_type) }} · {{ displayDataMode(event.data_mode) }}</span>
                                        </span>
                                        <el-tag class="event-type-tag" size="small" effect="plain">{{ displayEventType(event.event_type) }}</el-tag>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <aside class="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/50 dark:bg-black/10 p-4 min-w-0">
                            <div class="flex flex-wrap items-center gap-2 mb-3">
                                <h3 class="text-sm font-black text-slate-700 dark:text-slate-100">事件详情</h3>
                                <el-tag size="small" :type="selectedEvent?.data_mode === 'user_uploaded' ? 'success' : 'info'" effect="plain">{{ displayDataMode(selectedEvent?.data_mode || 'user_uploaded') }}</el-tag>
                            </div>

                            <div v-if="selectedEvent" class="space-y-4">
                                <div>
                                    <div class="text-xl font-black text-slate-800 dark:text-white leading-tight">{{ selectedEvent.time }}</div>
                                    <div class="text-sm font-semibold text-slate-600 dark:text-slate-300">{{ displayEventLabel(selectedEvent) }}</div>
                                    <div class="text-xs text-slate-400 mt-1">事件结构版本：{{ displayPayloadValue(selectedEvent.schema_version) }}</div>
                                </div>

                                <div v-if="selectedEvent.event_type === 'diet_vision'" class="grid grid-cols-2 gap-2">
                                    <div v-for="metric in dietEventMetrics" :key="metric.label" class="detail-stat">
                                        <span>{{ metric.label }}</span>
                                        <strong>{{ metric.value }}</strong>
                                    </div>
                                </div>

                                <div v-if="selectedEvent.event_type === 'diet_vision'" class="text-xs text-slate-500 dark:text-slate-400">
                                    视觉识别来源：
                                    <span class="font-semibold">{{ displayDataMode(selectedEvent.payload?.vision_provenance?.source_type || selectedEvent.data_mode || 'user_uploaded') }}</span>
                                </div>

                                <dl class="payload-list">
                                    <div v-for="item in payloadPairs(selectedEvent.payload)" :key="item.key">
                                        <dt>{{ item.key }}</dt>
                                        <dd>{{ item.value }}</dd>
                                    </div>
                                </dl>

                                <div class="rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/40 p-3 text-xs text-amber-800 dark:text-amber-200">
                                    {{ eventProvenanceNotice(selectedEvent) }}
                                </div>
                            </div>
                        </aside>
                    </div>
                </section>

                <div class="mt-8 pt-6 border-t border-gray-200 dark:border-white/10 flex flex-col md:flex-row gap-4 md:items-center md:justify-between">
                    <GlassButton @click="$router.push('/genomics')">
                        <el-icon class="mr-2"><ArrowLeft /></el-icon>
                        上一步：基因组学
                    </GlassButton>

                    <div class="flex flex-col sm:flex-row gap-3">
                        <GradientButton v-if="!activeScenario" class="shadow-xl px-6" @click="runFusionAnalysis" :disabled="loading">
                            <span v-if="loading">正在进行多模态融合...</span>
                            <span v-else>启动融合计算</span>
                        </GradientButton>
                        <GradientButton v-else class="shadow-xl px-6" @click="runScenarioFusionAnalysis" :disabled="loading || !activeScenario">
                            {{ behaviorFusionCopy(activeScenario) }}
                        </GradientButton>
                    </div>
                </div>
            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
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
import { behaviorFusionCopy, importBehaviorDayFile } from '../utils/lifestyleBehaviorImport'
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

const { isConnected, error, heartRate, connectDevice, setSyncCallback } = useBluetooth()

const chartRef = ref(null)
let myChart = null
const hrHistory = ref([])

const behaviorScenarios = ref([])
const selectedScenarioId = ref('')
const selectedScenarioState = ref(null)
const selectedScenario = computed({
    get: () => selectedScenarioState.value || userProfile.value?.extra_data?.latest_behavior_day || null,
    set: (value) => {
        selectedScenarioState.value = value
    },
})
const activeScenario = selectedScenario
const scenarioListLoading = ref(false)
const scenarioDetailLoading = ref(false)
const scenarioError = ref('')
const behaviorImportLoading = ref(false)
const behaviorImportError = ref('')
const currentEventIndex = ref(0)
const timelineProgress = ref(0)
const isPlaying = ref(false)
let playbackTimer = null
let legacyTimer = null

const CLINICAL_ANALYSIS_FIELDS = new Set([
    'Age',
    'Gender',
    'BMI',
    'Height',
    'Weight',
    'WaistCircum',
    'SBP',
    'DBP',
    'Glucose_Fasting',
    'HbA1c',
    'Cholesterol_Total',
    'Triglycerides',
    'Cholesterol_HDL',
    'Cholesterol_LDL',
    'Sleep_Hours',
    'eGFR',
    'Creatinine',
    'ALT',
    'WBC',
    'GGT',
    'ALP',
    'Platelet',
])

const SCENARIO_TITLE_CN = {
    'Uploaded behavior day': '上传行为日数据',
    'Metabolic and diabetes high-risk demo day': '代谢与糖尿病高风险行为日',
    'Cardiovascular and heart-failure monitoring demo day': '心血管与心衰监测行为日',
    'Younger cardiometabolic and respiratory improvement demo day': '年轻心代谢与呼吸改善行为日',
}

const EVENT_LABEL_CN = {
    'Short sleep window ended': '短睡眠时段结束',
    'High-carbohydrate breakfast recognition': '高碳水早餐识别',
    'Morning vitals replay': '晨间生命体征回放',
    'Long desk-sitting block': '长时间伏案久坐',
    'High-sodium lunch recognition': '高钠午餐识别',
    'Brief low-intensity walk': '短时低强度步行',
    'Evening screen time': '晚间屏幕久坐',
    'High-carbohydrate dinner recognition': '高碳水晚餐识别',
    'Daily behavior summary': '全天行为汇总',
    'Moderately short sleep ended': '中度睡眠不足结束',
    'Moderate breakfast recognition': '普通早餐识别',
    'Slow walk with limited tolerance': '耐量受限的慢走',
    'Rest after exertion': '活动后休息',
    'Sodium-risk lunch recognition': '钠摄入风险午餐识别',
    'Afternoon heart-rate fluctuation': '下午心率波动',
    'Lower-sodium dinner recovery choice': '低钠晚餐恢复选择',
    'Improved sleep window ended': '改善后的睡眠时段结束',
    'Balanced breakfast recognition': '均衡早餐识别',
    'Respiratory-aware brisk walk': '兼顾呼吸状态的快走',
    'Short work block with movement breaks': '含活动间歇的短时工作',
    'Lower-sodium lunch recognition': '低钠午餐识别',
    'Light mobility session': '轻量灵活性活动',
    'Heart-healthy dinner recognition': '护心晚餐识别',
}

const DATA_MODE_CN = {
    simulated_demo: '示例数据',
    user_uploaded: '用户上传数据',
    real_device: '真实设备数据',
    demo_scenario: '示例场景',
    behavior_upload: '行为上传文件',
    'behavior_timeline_event.v1': '行为时间线事件结构 v1',
    'diet_vision_event.v1': '饮食视觉事件结构 v1',
    'platform_demo_profiles.v1': '平台示例患者画像 v1',
    'nhanes_lifestyle_supplement.v1': 'NHANES 生活方式补充数据 v1',
}

const EVENT_TYPE_CN = {
    sleep: '睡眠',
    vitals: '生命体征',
    activity: '活动',
    sedentary: '久坐',
    diet_vision: '饮食视觉',
    daily_summary: '全天汇总',
}

const PAYLOAD_KEY_CN = {
    active_minutes: '活动分钟',
    activity_type: '活动类型',
    baseline_profile_sleep_hours: '画像基线睡眠小时',
    breaks: '中断次数',
    breathing_note: '呼吸说明',
    calories: '热量',
    carbs: '碳水化合物',
    confidence: '置信度',
    demo_takeaway: '说明要点',
    diastolic_bp: '舒张压',
    diet_pattern: '饮食模式',
    duration_minutes: '持续分钟',
    estimated_calories: '估算热量',
    estimated_met_minutes: '估算代谢当量分钟',
    estimated_sodium_mg: '估算钠摄入',
    fasting_glucose_mmol_l: '空腹血糖',
    fat: '脂肪',
    food_items: '食物项目',
    hba1c_percent: '糖化血红蛋白',
    heart_rate_bpm: '心率',
    heart_rate_variability_ms: '心率变异性',
    image_ref: '图像引用',
    intensity: '强度',
    interpretation: '解读',
    meal_type: '餐次',
    model_name: '模型名称',
    night_awakenings: '夜间醒来次数',
    nutrition: '营养估算',
    oxygen_saturation_percent: '血氧饱和度',
    pacing_note: '节奏说明',
    peak_heart_rate_bpm: '峰值心率',
    posture: '姿势',
    protein: '蛋白质',
    recovery_context: '恢复背景',
    recovery_heart_rate_bpm_after_5_min: '5分钟后恢复心率',
    schema_version: '结构版本',
    sedentary_minutes: '久坐分钟',
    sleep_hours: '睡眠小时',
    sleep_quality: '睡眠质量',
    sodium_mg: '钠',
    source_type: '来源类型',
    steps: '步数',
    symptom_note: '症状说明',
    systolic_bp: '收缩压',
    vision_provenance: '视觉识别来源',
    weight_kg: '体重',
}

const PAYLOAD_VALUE_CN = {
    simulated_demo: '示例数据',
    fragmented: '片段化',
    restless: '睡眠不安',
    restorative: '恢复性较好',
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    seated: '坐姿',
    walking: '步行',
    brisk_walking: '快走',
    mobility_and_stretching: '灵活性与拉伸',
    light: '轻度',
    moderate: '中等',
    post_walk_rest: '步行后休息',
    high_sodium_high_carbohydrate: '高钠高碳水',
    high_sodium_moderate_carbohydrate: '高钠中等碳水',
    lower_sodium_high_fiber_balanced: '低钠高纤维均衡',
    'white rice porridge': '白米粥',
    'steamed bun': '馒头',
    'pickled vegetables': '腌菜',
    'sweetened soy milk': '甜豆浆',
    'white rice': '白米饭',
    'braised pork': '红烧肉',
    'salted soup': '咸汤',
    'stir-fried greens': '炒青菜',
    noodles: '面条',
    'fried egg': '煎蛋',
    'processed sausage': '加工香肠',
    'sweet tea': '甜茶',
    'whole-grain toast': '全麦吐司',
    'boiled egg': '水煮蛋',
    'fresh fruit': '新鲜水果',
    'plain yogurt': '原味酸奶',
    'noodle soup': '汤面',
    'salted side dish': '咸味配菜',
    'leafy greens': '绿叶蔬菜',
    'roast chicken': '烤鸡',
    'brown rice': '糙米',
    'steamed vegetables': '蒸蔬菜',
    oatmeal: '燕麦粥',
    berries: '浆果',
    'unsalted nuts': '无盐坚果',
    quinoa: '藜麦',
    'grilled chicken salad': '烤鸡沙拉',
    'olive oil vinaigrette': '橄榄油醋汁',
    'steamed salmon': '蒸三文鱼',
    'steamed fish': '清蒸鱼',
    'tomato soup': '番茄汤',
    'pickled radish': '腌萝卜',
    'mild fatigue after errands': '外出活动后轻度疲劳',
    'paced breathing and low-impact movement': '节奏呼吸与低冲击活动',
    'short pauses used to avoid breathlessness': '通过短暂停顿避免气促',
    'Below the profile baseline and consistent with the demo patient\'s metabolic-risk narrative.': '低于画像基线，并符合该患者的代谢风险叙事。',
    'Uses existing profile vitals and metabolic labs as simulated demo context.': '使用既有画像中的生命体征和代谢实验室指标作为示例上下文。',
    'Low movement block aligned with low physical activity supplement.': '低活动时段与低体力活动补充信息一致。',
    'Adds to total sedentary minutes for the metabolic-risk demo day.': '计入代谢风险行为日的总久坐时间。',
    'A behavior-heavy replay day that can explain why lifestyle context may worsen a metabolic-risk interpretation.': '该行为密集回放日可说明生活方式上下文为何会加重代谢风险解读。',
    'A slightly short night for a cardiovascular monitoring demo day.': '心血管监测行为日中的轻度睡眠不足。',
    'Shows activity tolerance pressure in a heart-failure monitoring demo.': '展示心衰监测中的活动耐量压力。',
    'Rest period added after low-tolerance activity.': '低耐量活动后加入休息时段。',
    'Uses profile blood pressure and a simulated wearable-style heart-rate point without claiming real device provenance.': '使用画像血压和示例穿戴式心率点，不宣称来自真实设备。',
    'The day highlights sodium exposure and limited activity tolerance with visible rest recovery.': '该日突出钠暴露、活动耐量受限以及可见的休息恢复。',
    'Healthier contrast day extends sleep beyond the baseline supplement.': '更健康的对照日中，睡眠时长高于基线补充信息。',
    'Uses profile cardiometabolic and respiratory context while preserving simulated-demo provenance.': '使用画像中的心代谢和呼吸背景，同时保留示例来源。',
    'Healthier contrast day avoids prolonged uninterrupted sitting.': '更健康的对照日避免长时间连续久坐。',
    'Simulated monitoring point for demo replay; not real device evidence.': '示例回放中的监测点，不是真实设备证据。',
    'A healthier contrast day showing how better sleep, lower sodium, and more movement can be replayed without claiming real-device evidence.': '更健康的对照日，用于展示更好睡眠、较低钠摄入和更多活动如何在不宣称真实设备证据的情况下回放。',
}

const timelineEvents = computed(() => selectedScenario.value?.timeline || [])
const timelineMax = computed(() => Math.max(timelineEvents.value.length - 1, 0))
const selectedEvent = computed(() => timelineEvents.value[currentEventIndex.value] || null)
const currentTimelineTime = computed(() => selectedEvent.value?.time || '--:--')

const summaryMetrics = computed(() => {
    const summary = selectedScenario.value?.lifestyle_context?.summary || dailySummaryPayload.value || {}
    return [
        { label: '步数', value: formatMetricNumber(summary.steps), unit: '步' },
        { label: '活动', value: formatMetricNumber(summary.active_minutes), unit: '分钟' },
        { label: '久坐', value: formatMetricNumber(summary.sedentary_minutes), unit: '分钟' },
        { label: '睡眠', value: formatMetricNumber(summary.sleep_hours), unit: '小时' },
        { label: '热量', value: formatMetricNumber(summary.estimated_calories), unit: '千卡' },
        { label: '钠', value: formatMetricNumber(summary.estimated_sodium_mg), unit: '毫克' },
    ]
})

const dailySummaryPayload = computed(() => {
    const event = timelineEvents.value.find((item) => item.event_type === 'daily_summary')
    return event?.payload || null
})

const dietEventMetrics = computed(() => {
    const nutrition = selectedEvent.value?.payload?.nutrition || {}
    return [
        { label: '热量', value: `${formatNumber(nutrition.calories)} 千卡` },
        { label: '碳水', value: `${formatNumber(nutrition.carbs)} 克` },
        { label: '蛋白质', value: `${formatNumber(nutrition.protein)} 克` },
        { label: '脂肪', value: `${formatNumber(nutrition.fat)} 克` },
        { label: '钠', value: `${formatNumber(nutrition.sodium_mg)} 毫克` },
    ]
})

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
            lineStyle: { width: 3, color: '#f87171' },
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

watch(heartRate, (newVal) => {
    if (newVal > 0) {
        store.iotData.hr = newVal
        hrHistory.value.push(newVal)
        if (hrHistory.value.length > 50) hrHistory.value.shift()
        updateChart()
    }
})

watch(error, (msg) => {
    if (msg) showToast(msg, 'error')
})

const handleBatchSync = async (batchData) => {
    try {
        const token = localStorage.getItem('auth_token')
        await axios.post('/api/v1/iot/sync/batch', batchData, {
            headers: { Authorization: `Bearer ${token}` }
        })
    } catch (e) {
        console.error('Batch sync failed', e)
    }
}

const handleConnect = async () => {
    await connectDevice()
    if (isConnected.value) {
        showToast('设备连接成功', 'success')
        setSyncCallback(handleBatchSync)
        setTimeout(initChart, 200)
    }
}

const syncLegacyIoT = async () => {
    try {
        store.iotData.steps += Math.floor(Math.random() * 5)
    } catch (e) {
        console.error('Legacy IoT update failed', e)
    }
}

const fetchBehaviorScenarios = async () => {
    scenarioListLoading.value = true
    scenarioError.value = ''
    try {
        const res = await axios.get('/api/v1/demo/behavior-scenarios')
        const scenarios = res.data?.scenarios || []
        behaviorScenarios.value = Array.isArray(scenarios) ? scenarios : []
        if (!selectedScenarioId.value && behaviorScenarios.value.length) {
            selectedScenarioId.value = behaviorScenarios.value[0].scenario_id
            await loadBehaviorScenario(selectedScenarioId.value)
        }
    } catch (e) {
        scenarioError.value = e.response?.data?.detail || '示例数据列表加载失败'
    } finally {
        scenarioListLoading.value = false
    }
}

const loadBehaviorScenario = async (scenarioId) => {
    if (!scenarioId) return
    scenarioDetailLoading.value = true
    scenarioError.value = ''
    behaviorImportError.value = ''
    pausePlayback()
    try {
        const res = await axios.get(`/api/v1/demo/behavior-scenarios/${scenarioId}`)
        const scenario = res.data?.scenario
        if (!scenario || scenario.data_mode !== 'simulated_demo') {
            throw new Error('Scenario must be simulated_demo')
        }
        selectedScenario.value = scenario
        currentEventIndex.value = 0
        timelineProgress.value = 0
        applyDietVisionEvent(timelineEvents.value[0])
    } catch (e) {
        selectedScenario.value = null
        scenarioError.value = e.response?.data?.detail || e.message || '示例数据详情加载失败'
    } finally {
        scenarioDetailLoading.value = false
    }
}

const applySelectedScenario = (scenario) => {
    selectedScenario.value = scenario
    currentEventIndex.value = 0
    timelineProgress.value = 0
    applyDietVisionEvent(timelineEvents.value[0])
}

const syncBehaviorScenarioToProfile = (scenario) => {
    if (!scenario || scenario.data_mode !== 'user_uploaded') return
    store.updateProfile({
        extra_data: {
            ...(userProfile.value?.extra_data || {}),
            latest_behavior_day: scenario,
            latest_lifestyle_context: scenario.lifestyle_context || null,
        },
    })
}

const loadPersistedBehaviorScenario = async () => {
    let scenario = userProfile.value?.extra_data?.latest_behavior_day
    if (!scenario) {
        try {
            const res = await axios.get('/user/profile')
            const profile = res.data?.profile
            if (profile) {
                store.updateProfile(profile)
                scenario = profile.extra_data?.latest_behavior_day
            }
        } catch (e) {
            console.error('Failed to load persisted behavior day:', e)
        }
    }
    if (scenario?.timeline && scenario?.lifestyle_context) {
        selectedScenarioId.value = ''
        applySelectedScenario(scenario)
    }
}

watch(
    () => userProfile.value?.extra_data?.latest_behavior_day,
    (scenario) => {
        if (!selectedScenario.value && scenario?.timeline && scenario?.lifestyle_context) {
            selectedScenarioId.value = ''
            applySelectedScenario(scenario)
        }
    },
    { immediate: true, deep: true }
)

const handleBehaviorImport = async (options) => {
    behaviorImportLoading.value = true
    behaviorImportError.value = ''
    pausePlayback()
    try {
        const result = await importBehaviorDayFile({
            axiosClient: axios,
            file: options.file,
            onSuccess: (scenario) => {
                selectedScenarioId.value = ''
                applySelectedScenario(scenario)
                syncBehaviorScenarioToProfile(scenario)
            },
        })
        if (!result.ok) {
            behaviorImportError.value = result.error
            showToast(result.error, 'error')
            return
        }
        showToast('用户上传行为日解析完成，时间线已更新', 'success')
    } finally {
        behaviorImportLoading.value = false
    }
}

const togglePlayback = () => {
    if (!selectedScenario.value) return
    if (isPlaying.value) {
        pausePlayback()
        return
    }
    isPlaying.value = true
    playbackTimer = setInterval(advanceTimeline, 1400)
}

const pausePlayback = () => {
    isPlaying.value = false
    if (playbackTimer) {
        clearInterval(playbackTimer)
        playbackTimer = null
    }
}

const replayScenario = () => {
    if (!selectedScenario.value) return
    pausePlayback()
    selectTimelineEvent(0)
    togglePlayback()
}

const advanceTimeline = () => {
    if (currentEventIndex.value >= timelineMax.value) {
        pausePlayback()
        return
    }
    selectTimelineEvent(currentEventIndex.value + 1)
}

const seekTimeline = (index) => {
    selectTimelineEvent(Number(index) || 0)
}

const selectTimelineEvent = (index) => {
    const bounded = Math.min(Math.max(index, 0), timelineMax.value)
    currentEventIndex.value = bounded
    timelineProgress.value = bounded
    applyDietVisionEvent(timelineEvents.value[bounded])
}

const applyDietVisionEvent = (event) => {
    if (event?.event_type !== 'diet_vision') return
    const nutrition = event.payload?.nutrition
    if (!nutrition) return
    store.setDietNutrition({
        ...nutrition,
        provenance: event.payload?.vision_provenance || {
            source_type: event.data_mode || 'user_uploaded'
        }
    })
}

const uploadAndAnalyzeFood = async (options) => {
    analyzing.value = true
    const formData = new FormData()
    formData.append('file', options.file)
    try {
        const res = await axios.post('/analyze/food_image', formData)
        if (res.data.status === 'success' && res.data.nutrition) {
            store.setDietNutrition(res.data.nutrition)
            showToast(res.data.message || `识别成功，热量 ${res.data.nutrition.calories} kcal`, 'success')
        } else if (res.data.nutrition?.status === 'success') {
            store.setDietNutrition(res.data.nutrition)
            showToast(res.data.message || `识别成功，热量 ${res.data.nutrition.calories} kcal`, 'success')
        } else {
            showToast(res.data.message || '识别失败，请尝试其他图片', 'warning')
        }
    } catch (e) {
        const errorDetail = e.response?.data?.detail || e.response?.data?.message || e.message || '网络异常'
        showToast(`识别失败: ${errorDetail}`, 'error')
    } finally {
        analyzing.value = false
    }
}

const buildClinicalPayload = () => {
    const cleanClinical = {}
    Object.entries(userProfile.value || {}).forEach(([key, value]) => {
        if (!CLINICAL_ANALYSIS_FIELDS.has(key)) {
            return
        }
        if (value === null || value === undefined || value === '') {
            return
        }
        cleanClinical[key] = typeof value === 'string' && !Number.isNaN(Number(value))
            ? Number(value)
            : value
    })
    return cleanClinical
}

const buildAnalysisPayload = (extraPayload = {}) => {
    const cleanClinical = buildClinicalPayload()
    const payload = {
        user_snps: geneData.value || {},
        ...extraPayload,
    }
    if (Object.keys(cleanClinical).length) {
        payload.clinical = cleanClinical
    }
    return payload
}

const runFusionAnalysis = async () => {
    loading.value = true
    try {
        const payload = buildAnalysisPayload()
        const res = await axios.post('/analyze/comprehensive', payload)
        handleAnalysisResponse(res)
    } catch (e) {
        showToast('分析服务连接失败', 'error')
    } finally {
        loading.value = false
    }
}

const runScenarioFusionAnalysis = async () => {
    if (!selectedScenario.value?.lifestyle_context) {
        showToast('请先上传行为日文件', 'warning')
        return
    }
    loading.value = true
    try {
        const payload = buildAnalysisPayload({
            lifestyle_context: selectedScenario.value.lifestyle_context
        })
        const res = await axios.post('/analyze/comprehensive', payload)
        handleAnalysisResponse(res, behaviorFusionCopy(selectedScenario.value))
    } catch (e) {
        showToast(e.response?.data?.detail || '生活方式融合分析失败', 'error')
    } finally {
        loading.value = false
    }
}

const runDemoFusionAnalysis = runScenarioFusionAnalysis

const handleAnalysisResponse = (res, successMessage = '融合计算完成') => {
    if (res.data.status === 'success') {
        store.setRiskReport(res.data.risk_report)
        showToast(successMessage, 'success')
        setTimeout(() => { router.push('/') }, 500)
    } else {
        showToast(res.data.message || '分析失败', 'error')
    }
}

const formatNumber = (value) => {
    if (value === null || value === undefined || value === '') return '--'
    if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1)
    return value
}

const formatMetricNumber = (value) => {
    if (value === null || value === undefined || value === '') return '--'
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(1)
    return value
}

const displayScenarioTitle = (scenario) => SCENARIO_TITLE_CN[scenario?.title] || scenario?.title || '行为日数据'

const displayScenarioSubject = (scenario) => scenario?.demo_patient_id || scenario?.patient_id || '行为日'

const displayEventLabel = (event) => EVENT_LABEL_CN[event?.label] || event?.label || '行为事件'

const displayDataMode = (dataMode) => DATA_MODE_CN[dataMode] || dataMode || '用户上传数据'

const displayEventType = (eventType) => EVENT_TYPE_CN[eventType] || eventType || '事件'

const displayPayloadKey = (key) => PAYLOAD_KEY_CN[key] || key

const displayPayloadValue = (value) => {
    if (value === null || value === undefined || value === '') return '--'
    if (typeof value === 'number') return formatNumber(value)
    if (typeof value === 'string') return PAYLOAD_VALUE_CN[value] || DATA_MODE_CN[value] || value
    if (Array.isArray(value)) {
        return value.map(displayPayloadValue).join('、')
    }
    if (typeof value === 'object') {
        return Object.entries(value)
            .map(([key, nestedValue]) => `${displayPayloadKey(key)}：${displayPayloadValue(nestedValue)}`)
            .join('；')
    }
    return String(value)
}

const payloadPairs = (payload) => {
    if (!payload || typeof payload !== 'object') return []
    return Object.entries(payload).map(([key, value]) => ({
        key: displayPayloadKey(key),
        value: displayPayloadValue(value),
    }))
}

const provenanceLabel = (sourceProvenance) => {
    if (!sourceProvenance) return '未知来源'
    if (sourceProvenance.source_type === 'user_uploaded') {
        return '用户上传文件'
    }
    const generatedFrom = Array.isArray(sourceProvenance.generated_from)
        ? sourceProvenance.generated_from.map((item) => PAYLOAD_VALUE_CN[item] || item).join('、')
        : '示例场景'
    const sourceType = displayDataMode(sourceProvenance.source_type || 'simulated_demo')
    return `${sourceType}（${generatedFrom}）`
}

const eventProvenanceNotice = (event) => {
    if (!event) return ''
    const base = `该事件来自${provenanceLabel(event.source_provenance)}，属于${displayDataMode(event.data_mode)}。`
    if (event.data_mode === 'user_uploaded' || event.data_mode === 'real_device') {
        return base
    }
    return `${base}不作为真实设备证据。`
}

const eventTypeColor = (eventType) => {
    const colors = {
        sleep: 'bg-indigo-400',
        vitals: 'bg-rose-400',
        activity: 'bg-emerald-400',
        sedentary: 'bg-amber-400',
        diet_vision: 'bg-sky-400',
        daily_summary: 'bg-violet-400',
    }
    return colors[eventType] || 'bg-slate-400'
}

onMounted(async () => {
    legacyTimer = setInterval(syncLegacyIoT, 3000)
    await loadPersistedBehaviorScenario()
    setTimeout(loadPersistedBehaviorScenario, 1000)
})

onUnmounted(() => {
    if (legacyTimer) clearInterval(legacyTimer)
    pausePlayback()
    myChart?.dispose()
})
</script>

<style scoped>
.nutrition-tile {
    display: flex;
    min-height: 86px;
    flex-direction: column;
    justify-content: center;
    border-width: 1px;
    border-radius: 0.75rem;
    padding: 0.75rem;
    background-image: linear-gradient(to bottom right, var(--tw-gradient-stops));
}

.demo-scenario-controls {
    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 0.75rem;
}

.demo-scenario-select {
    width: 100%;
}

.demo-scenario-select :deep(.el-select__wrapper) {
    min-height: 2.25rem;
    border-radius: 0.75rem;
    border-color: rgba(148, 163, 184, 0.32);
    background: rgba(255, 255, 255, 0.68);
    box-shadow: 0 10px 24px -18px rgba(15, 23, 42, 0.24);
}

.demo-scenario-select :deep(.el-select__selected-item) {
    min-width: 0;
    font-size: 0.8125rem;
    font-weight: 600;
    color: #334155;
}

.demo-scenario-load-button {
    flex: none;
}

.behavior-import-upload :deep(.el-upload-dragger) {
    border-radius: 1rem;
    border-color: rgba(59, 130, 246, 0.26);
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(239, 246, 255, 0.58));
    box-shadow: 0 18px 36px -28px rgba(37, 99, 235, 0.38);
}

:global(.dark) .demo-scenario-select :deep(.el-select__wrapper) {
    border-color: rgba(148, 163, 184, 0.28);
    background: rgba(15, 23, 42, 0.48);
}

:global(.dark) .demo-scenario-select :deep(.el-select__selected-item) {
    color: #e2e8f0;
}

:global(.dark) .behavior-import-upload :deep(.el-upload-dragger) {
    border-color: rgba(96, 165, 250, 0.26);
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.56), rgba(30, 41, 59, 0.42));
}

@media (min-width: 640px) {
    .demo-scenario-controls {
        flex-direction: row;
        align-items: center;
        justify-content: flex-end;
    }

    .demo-scenario-select {
        flex: 1 1 22rem;
        min-width: 22rem;
        max-width: 24rem;
    }
}

@media (min-width: 1024px) {
    .demo-scenario-controls {
        flex: 0 0 auto;
        min-width: 32rem;
        max-width: 36rem;
    }
}

.metric-chip {
    display: flex;
    min-width: 132px;
    flex: 1 1 132px;
    align-items: baseline;
    gap: 0.25rem;
    border-radius: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.28);
    background: rgba(255, 255, 255, 0.48);
    padding: 0.75rem;
}

.metric-chip-label {
    font-size: 0.75rem;
    color: #64748b;
}

.metric-chip-value {
    font-size: 1.125rem;
    line-height: 1.5rem;
    color: #1e293b;
}

.metric-chip-unit {
    font-size: 0.75rem;
    color: #94a3b8;
}

:global(.dark) .metric-chip {
    background: rgba(15, 23, 42, 0.34);
}

:global(.dark) .metric-chip-label {
    color: #94a3b8;
}

:global(.dark) .metric-chip-value {
    color: #f8fafc;
}

.timeline-row {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 0.75rem;
    border-radius: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.24);
    background: rgba(255, 255, 255, 0.54);
    padding: 0.75rem;
    text-align: left;
    transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.timeline-row:hover,
.timeline-row-active {
    border-color: rgba(59, 130, 246, 0.52);
    background: rgba(239, 246, 255, 0.86);
    transform: translateY(-1px);
}

:global(.dark) .timeline-row {
    background: rgba(15, 23, 42, 0.34);
}

:global(.dark) .timeline-row:hover,
:global(.dark) .timeline-row-active {
    background: rgba(30, 41, 59, 0.78);
}

.timeline-time {
    width: 3.25rem;
    flex: none;
    font-variant-numeric: tabular-nums;
    font-size: 0.875rem;
    font-weight: 800;
    color: #475569;
}

:global(.dark) .timeline-time {
    color: #cbd5e1;
}

.timeline-dot {
    width: 0.75rem;
    height: 0.75rem;
    flex: none;
    border-radius: 9999px;
    box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.16);
}

.event-type-tag {
    max-width: 6.75rem;
}

.event-type-tag :deep(.el-tag__content) {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.detail-stat {
    border-radius: 0.75rem;
    border: 1px solid rgba(148, 163, 184, 0.24);
    background: rgba(248, 250, 252, 0.74);
    padding: 0.625rem;
}

:global(.dark) .detail-stat {
    background: rgba(15, 23, 42, 0.44);
}

.detail-stat span {
    display: block;
    font-size: 0.7rem;
    color: #64748b;
}

.detail-stat strong {
    display: block;
    margin-top: 0.125rem;
    font-size: 0.875rem;
    color: #0f172a;
}

:global(.dark) .detail-stat strong {
    color: #f8fafc;
}

.payload-list {
    display: grid;
    gap: 0.5rem;
    font-size: 0.75rem;
}

.payload-list div {
    display: grid;
    grid-template-columns: minmax(92px, 0.36fr) minmax(0, 1fr);
    gap: 0.625rem;
    border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    padding-bottom: 0.5rem;
}

.payload-list dt {
    color: #64748b;
    font-weight: 700;
    overflow-wrap: anywhere;
}

.payload-list dd {
    color: #334155;
    overflow-wrap: anywhere;
}

:global(.dark) .payload-list dd {
    color: #cbd5e1;
}

@media (max-width: 640px) {
    .event-type-tag {
        max-width: 4.5rem;
    }

    .payload-list div {
        grid-template-columns: 1fr;
    }
}
</style>
