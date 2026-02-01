<template>
    <div class="p-6 h-full flex flex-col">
        <div class="w-full max-w-7xl mx-auto h-full flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    🎛️ 数据中心 (Administration)
                </h1>
                <el-tag type="danger" effect="dark" round>ADMIN ACCESS ONLY</el-tag>
            </div>

            <GlassCard class="flex-1 flex flex-col overflow-hidden" :glow="true">
                <div class="flex h-full">
                    <!-- Left: Control Panel (40%) -->
                    <div class="w-2/5 border-r border-gray-200 dark:border-white/10 p-6 flex flex-col overflow-y-auto">
                        <el-tabs v-model="activeTab" class="admin-tabs">

                            <!-- 1. Clinical Data Tab -->
                            <el-tab-pane label="🏥 临床数据" name="clinical">
                                <div class="space-y-4 mt-4">
                                    <!-- 上传区域 -->
                                    <div
                                        class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl border border-blue-100 dark:border-blue-800">
                                        <h3 class="font-bold text-blue-800 dark:text-blue-300 mb-2">NHANES 数据归档</h3>
                                        <p class="text-xs text-slate-500 mb-4">上传 .XPT 或 .CSV 文件到数据仓库，支持批量上传。</p>

                                        <el-upload class="upload-demo" drag action="#" :auto-upload="false"
                                            :on-change="handleClinicalFileChange" multiple accept=".xpt,.XPT,.csv,.CSV">
                                            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                                            <div class="el-upload__text">拖拽 XPT/CSV 文件到此处 (支持多选)</div>
                                            <template #tip>
                                                <div class="el-upload__tip text-blue-600">已选择 {{ clinicalFiles.length }}
                                                    个文件</div>
                                            </template>
                                        </el-upload>
                                    </div>

                                    <!-- 归档按钮 -->
                                    <GradientButton @click="uploadClinicalFiles()"
                                        :disabled="clinicalFiles.length === 0" :loading="clinicalUploading"
                                        class="w-full">
                                        📦 归档选中文件 ({{ clinicalFiles.length }})
                                    </GradientButton>

                                    <!-- 警告提示 -->
                                    <el-alert title="重要提示" type="warning" :closable="false" show-icon>
                                        <template #default>
                                            请确保相关 XPT 文件已全部上传更新后，再点击下方按钮。训练过程可能持续 1-2 分钟。
                                        </template>
                                    </el-alert>

                                    <!-- 训练按钮 -->
                                    <GradientButton @click="triggerClinicalTrain()" :loading="loading" class="w-full"
                                        style="background: linear-gradient(135deg, #f59e0b, #d97706);">
                                        🚀 重构临床模型 (ETL + 训练)
                                    </GradientButton>
                                </div>
                            </el-tab-pane>

                            <!-- 2. GWAS Data Tab -->
                            <el-tab-pane label="🧬 基因知识库" name="gwas">
                                <div class="space-y-6 mt-4">
                                    <div
                                        class="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-xl border border-purple-100 dark:border-purple-800">
                                        <h3 class="font-bold text-purple-800 dark:text-purple-300 mb-2">GWAS Raw Data
                                            Pipeline</h3>
                                        <p class="text-xs text-slate-500 mb-4">支持上传 GWAS Catalog 原始数据 (.tsv/.txt)
                                            或标准权重文件，系统将自动进行 ETL 清洗与 ID 映射。</p>

                                        <el-input v-model="extraMeta" placeholder="输入病种名称 (例如: T2D, Alzheimer)"
                                            class="mb-4" prefix-icon="Edit" />

                                        <el-upload class="upload-demo" drag action="#" :auto-upload="false"
                                            :on-change="(file) => handleGwasFileChange(file)" multiple
                                            accept=".csv,.txt,.tsv">
                                            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                                            <div class="el-upload__text">拖拽 .tsv / .txt / .csv 文件到此处 (支持批量)</div>
                                            <template #tip>
                                                <div class="el-upload__tip text-purple-600">文件名需以病种名称开头 (如 T2D_xxx.tsv)
                                                </div>
                                            </template>
                                        </el-upload>
                                    </div>
                                    <GradientButton @click="startGwasPipeline()"
                                        :disabled="gwasFiles.length === 0 || !extraMeta" :loading="loading"
                                        class="w-full">
                                        🧬 更新基因引擎 ({{ gwasFiles.length }} 个文件)
                                    </GradientButton>
                                </div>
                            </el-tab-pane>

                            <!-- 3. Pharmacy Tab -->
                            <el-tab-pane label="💊 药物规则" name="pharm">
                                <div class="space-y-6 mt-4">
                                    <div
                                        class="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-xl border border-orange-100 dark:border-orange-800">
                                        <h3 class="font-bold text-orange-800 dark:text-orange-300 mb-2">PharmGKB Update
                                        </h3>
                                        <p class="text-xs text-slate-500 mb-4">上传 PharmGKB 官方 ZIP 包，系统将自动解析 XML 并更新规则库。
                                        </p>

                                        <el-upload class="upload-demo" drag action="#" :auto-upload="false"
                                            :on-change="(file) => handleFileChange(file, 'pharm')" :limit="1">
                                            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                                            <div class="el-upload__text">拖拽 ZIP 包到此处</div>
                                        </el-upload>
                                    </div>
                                    <GradientButton @click="startPipeline('pharm')" :disabled="!selectedFile"
                                        :loading="loading" class="w-full">
                                        💊 刷新药房知识库
                                    </GradientButton>
                                </div>
                            </el-tab-pane>

                            <!-- 4. Vision Tab -->
                            <el-tab-pane label="📸 视觉模型" name="vision">
                                <div class="space-y-6 mt-4">
                                    <div
                                        class="bg-green-50 dark:bg-green-900/20 p-4 rounded-xl border border-green-100 dark:border-green-800">
                                        <h3 class="font-bold text-green-800 dark:text-green-300 mb-2">YOLO Fine-tuning
                                        </h3>
                                        <p class="text-xs text-slate-500 mb-4">上传标注好的图片数据集 (.zip)，触发 YOLOv8 增量训练。</p>

                                        <el-upload class="upload-demo" drag action="#" :auto-upload="false"
                                            :on-change="(file) => handleFileChange(file, 'vision')" :limit="1">
                                            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                                            <div class="el-upload__text">拖拽数据集 ZIP 到此处</div>
                                        </el-upload>
                                    </div>
                                    <GradientButton @click="startPipeline('vision')" :disabled="!selectedFile"
                                        :loading="loading" class="w-full">
                                        📸 启动视觉训练
                                    </GradientButton>
                                </div>
                            </el-tab-pane>

                        </el-tabs>
                    </div>

                    <!-- Right: Terminal Logs (60%) -->
                    <div class="w-3/5 bg-gray-900 flex flex-col">
                        <div class="p-3 border-b border-gray-700 bg-gray-800 flex justify-between items-center">
                            <div class="flex items-center gap-2">
                                <span class="text-gray-400 text-xs font-mono">Terminal Output</span>
                                <span v-if="isTaskRunning" class="text-yellow-400 text-xs animate-pulse">
                                    ● {{ currentTaskName || 'Running...' }}
                                </span>
                                <span v-else-if="logs.length > 0" class="text-green-400 text-xs">
                                    ● Idle
                                </span>
                            </div>
                            <div class="flex gap-2">
                                <div
                                    :class="['w-3 h-3 rounded-full', isTaskRunning ? 'bg-yellow-500 animate-pulse' : 'bg-red-500']">
                                </div>
                                <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                                <div
                                    :class="['w-3 h-3 rounded-full', !isTaskRunning && logs.length > 0 ? 'bg-green-500' : 'bg-gray-600']">
                                </div>
                            </div>
                        </div>
                        <div class="flex-1 p-4 overflow-y-auto font-mono text-sm leading-relaxed scrollbar-thin scrollbar-thumb-gray-700"
                            ref="logContainer">
                            <div v-if="logs.length === 0" class="text-gray-600 italic">Waiting for pipeline jobs...
                            </div>
                            <div v-for="(line, index) in logs" :key="index"
                                class="text-green-400 border-l-2 border-transparent hover:border-gray-600 pl-2">
                                {{ line }}
                            </div>
                            <div v-if="loading" class="text-blue-400 mt-2 animate-pulse">▐ Processing...</div>
                        </div>
                    </div>
                </div>
            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, onUnmounted, nextTick, onMounted } from 'vue'
import { UploadFilled, Edit } from '@element-plus/icons-vue'
import axios from 'axios'
import GlassCard from '../../components/ui/GlassCard.vue'
import GradientButton from '../../components/ui/GradientButton.vue'
import { useAuthStore } from '../../stores/authStore'
import { useToast } from '../../composables/useToast'

const authStore = useAuthStore()
const { showToast } = useToast()

// Refs
const activeTab = ref('clinical')
const clinicalFiles = ref([])
const clinicalUploading = ref(false)
const loading = ref(false)
const extraMeta = ref('')
const gwasFiles = ref([])
const selectedFile = ref(null)
const logs = ref([])
const currentTaskName = ref('')
const isTaskRunning = ref(false)
const logContainer = ref(null)
const pollInterval = ref(null)
const currentTaskId = ref(null)

const getAuthHeaders = () => ({ Authorization: `Bearer ${authStore.token}` })

// File Handlers
const handleClinicalFileChange = (uploadFile, uploadFiles) => {
    clinicalFiles.value = uploadFiles
}

const handleGwasFileChange = (uploadFile, uploadFiles) => {
    gwasFiles.value = uploadFiles
}

const handleFileChange = (uploadFile, type) => {
    selectedFile.value = uploadFile
}

// 1. Upload Clinical Files
const uploadClinicalFiles = async () => {
    if (clinicalFiles.value.length === 0) {
        showToast('请先选择文件', 'warning')
        return
    }

    clinicalUploading.value = true
    let successCount = 0

    try {
        for (const file of clinicalFiles.value) {
            const formData = new FormData()
            formData.append('file', file.raw)

            try {
                // Using generic upload endpoint assumption or sticking to what might be there
                const res = await axios.post('http://127.0.0.1:8000/admin/data/upload_clinical', formData, {
                    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
                })

                if (res.data.status === 'success') {
                    showToast(`${file.name} 已归档`, 'success')
                    successCount++
                }
            } catch (e) {
                showToast(`${file.name} 上传失败: ${e.response?.data?.detail || e.message}`, 'error')
            }
        }
        showToast(`已归档 ${successCount}/${clinicalFiles.value.length} 个文件`, 'info')
        // Clear files after successful upload?
        // clinicalFiles.value = [] 
    } finally {
        clinicalUploading.value = false
    }
}

// 2. Trigger Clinical Pipeline (Rename from triggerClinicalTrain to match user intent if needed, but binding to template)
const triggerClinicalTrain = async () => {
    loading.value = true
    showToast('临床模型训练流水线已启动', 'success')
    
    try {
        const res = await axios.post('http://127.0.0.1:8000/admin/train/clinical', {}, {
             headers: getAuthHeaders()
        })
        
        if (res.data.task_id) {
            currentTaskName.value = 'Clinical ETL & Train'
            isTaskRunning.value = true
            startPolling()
        }
    } catch (e) {
        showToast(e.response?.data?.detail || '启动训练失败', 'error')
        loading.value = false
    }
}

// 3. Generic Pipeline (Pharm/Vision)
const startPipeline = async (type) => {
    if (!selectedFile.value) return
    loading.value = true

    const formData = new FormData()
    formData.append('file', selectedFile.value.raw)
    
    try {
        let url = ''
        if (type === 'pharm') url = 'http://127.0.0.1:8000/admin/pipeline/pharm'
        if (type === 'vision') url = 'http://127.0.0.1:8000/admin/pipeline/vision'

        const res = await axios.post(url, formData, {
             headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
        })

        showToast(`Task Started: ${res.data.task_id}`, 'success')
        currentTaskId.value = res.data.task_id
        startPolling()
    } catch (e) {
        showToast(e.response?.data?.detail || "Task Start Failed", 'error')
        loading.value = false
    }
}

// 4. GWAS Pipeline
const startGwasPipeline = async () => {
    if (!extraMeta.value) {
        showToast('请先输入病种名称', 'warning')
        return
    }
    if (gwasFiles.value.length === 0) {
        showToast('请先选择文件', 'warning')
        return
    }

    loading.value = true
    let successCount = 0
    let skipCount = 0

    try {
        for (const file of gwasFiles.value) {
            // Check filename matches disease
            if (!file.name.toLowerCase().includes(extraMeta.value.toLowerCase())) {
                 showToast(`文件 ${file.name} 似乎不包含 ${extraMeta.value}，已跳过`, 'warning')
                 skipCount++
                 continue
            }

            const formData = new FormData()
            formData.append('file', file.raw)
            formData.append('disease', extraMeta.value)

            try {
                const res = await axios.post('http://127.0.0.1:8000/admin/pipeline/gwas', formData, {
                    headers: { ...getAuthHeaders(), 'Content-Type': 'multipart/form-data' }
                })

                if (res.data.status === 'queued') {
                    showToast(`任务已启动: ${file.name}`, 'success')
                    successCount++
                }
            } catch (e) {
                showToast(`${file.name} 上传失败: ${e.message}`, 'error')
            }
        }
        
        if (successCount > 0) {
            startPolling()
            showToast(`已提交 ${successCount} 个文件，跳过 ${skipCount} 个`, 'info')
        } else {
            loading.value = false
        }
    } catch (err) {
        loading.value = false
        showToast('GWAS Pipeline Error', 'error')
    }
}

// Polling Logic
const startPolling = () => {
    if (!pollInterval.value) {
        pollInterval.value = setInterval(checkTaskStatus, 2000)
    }
}

const checkTaskStatus = async () => {
    try {
        const res = await axios.get('http://127.0.0.1:8000/admin/task/status', {
            headers: getAuthHeaders()
        })

        const { is_running, logs: taskLogs, current_task } = res.data

        isTaskRunning.value = is_running
        currentTaskName.value = current_task || ''

        if (taskLogs && taskLogs.length > 0) {
            logs.value = taskLogs
            scrollToBottom()
        }

        if (!is_running && loading.value) {
             // Task finished
             loading.value = false
             if (pollInterval.value) {
                 clearInterval(pollInterval.value)
                 pollInterval.value = null
             }
             showToast("流水线执行完成", "info")
        }
    } catch (e) {
        console.error("Status check failed", e)
    }
}

const scrollToBottom = () => {
    nextTick(() => {
        if (logContainer.value) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
    })
}

onMounted(async () => {
    await checkTaskStatus()

    // Tab Scroll Logic
    const slider = document.querySelector('.el-tabs__nav-scroll')
    let isDown = false
    let startX
    let scrollLeft

    if (slider) {
        slider.addEventListener('mousedown', (e) => {
            isDown = true
            slider.style.cursor = 'grabbing'
            startX = e.pageX - slider.offsetLeft
            scrollLeft = slider.scrollLeft
        })
        slider.addEventListener('mouseleave', () => {
            isDown = false
            slider.style.cursor = 'grab'
        })
        slider.addEventListener('mouseup', () => {
            isDown = false
            slider.style.cursor = 'grab'
        })
        slider.addEventListener('mousemove', (e) => {
            if (!isDown) return
            e.preventDefault()
            const x = e.pageX - slider.offsetLeft
            const walk = (x - startX) * 2 // Scroll-fast
            slider.scrollLeft = scrollLeft - walk
        })
    }
})

onUnmounted(() => {
    if (pollInterval.value) clearInterval(pollInterval.value)
})
</script>

<style scoped>
.admin-tabs :deep(.el-tabs__item) {
    font-size: 16px;
    font-weight: 600;
    -webkit-user-select: none;
    /* Safari */
    -ms-user-select: none;
    /* IE 10 and IE 11 */
    user-select: none;
    /* Standard syntax */
}

/* Drag Scroll Bar */
.admin-tabs :deep(.el-tabs__nav-scroll) {
    overflow-x: auto;
    cursor: grab;
    scrollbar-width: none;
    /* Firefox */
    padding-bottom: 5px;
    /* Avoiding clipping */
}

.admin-tabs :deep(.el-tabs__nav-scroll::-webkit-scrollbar) {
    display: none;
    /* Chrome, Safari, Opera */
}
</style>
