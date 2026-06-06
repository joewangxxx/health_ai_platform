<template>
    <!-- 中文注释：界面结构说明 -->
    <div class="p-6 h-full flex flex-col items-center overflow-auto">
        <div class="w-full max-w-5xl">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                🫁 个人档案 (Profile)
            </h1>

            <el-tabs v-model="activeTab" class="profile-tabs">
                <el-tab-pane label="账户信息" name="account">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
                        <GlassCard :glowProximity="100">
                            <template #header>
                                <div class="text-sm text-slate-500 dark:text-slate-400">账户信息</div>
                            </template>

                            <div class="flex flex-col items-center py-8">
                                <el-avatar :size="80" class="bg-linear-to-br from-blue-500 to-purple-600 text-white text-3xl font-bold shadow-lg">
                                    {{ authStore.user?.username?.charAt(0).toUpperCase() || '?' }}
                                </el-avatar>
                                <h2 class="mt-4 text-xl font-bold text-slate-800 dark:text-white">
                                    {{ authStore.user?.username || '加载中...' }}
                                </h2>
                                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                    {{ authStore.user?.email || '未设置邮箱' }}
                                </p>
                                <el-tag :type="authStore.user?.is_superuser ? 'danger' : 'info'" effect="dark" class="mt-3" round>
                                    {{ authStore.user?.is_superuser ? '管理员' : '普通用户' }}
                                </el-tag>
                                <div class="mt-6 px-4 py-2 bg-slate-100 dark:bg-slate-800/50 rounded-lg text-sm text-slate-600 dark:text-slate-300">
                                    欢迎回来，您的健康之旅从这里开始。
                                </div>
                            </div>
                        </GlassCard>

                        <GlassCard :glowProximity="100" v-if="!authStore.user?.is_superuser">
                            <template #header>
                                <div class="flex justify-between items-center">
                                    <span class="text-sm text-slate-500 dark:text-slate-400">健康档案摘要</span>
                                    <el-button size="small" type="primary" plain @click="$router.push('/clinical')">
                                        {{ hasProfile ? '编辑档案' : '建立档案' }}
                                    </el-button>
                                </div>
                            </template>

                            <div v-if="loading" class="flex items-center justify-center py-12">
                                <el-icon class="is-loading text-3xl text-blue-500"><Loading /></el-icon>
                            </div>
                            <div v-else-if="!hasProfile" class="flex flex-col items-center py-12">
                                <div class="text-6xl mb-4">🔍</div>
                                <p class="text-slate-500 dark:text-slate-400 text-center">
                                    暂无健康档案<br><span class="text-sm">请前往临床体检页面完善您的资料</span>
                                </p>
                            </div>
                            <div v-else class="py-4">
                                <el-descriptions :column="2" border size="small">
                                    <el-descriptions-item label="年龄">{{ profile.Age ? `${profile.Age} 岁` : '-' }}</el-descriptions-item>
                                    <el-descriptions-item label="性别">{{ profile.Gender === 1 ? '男' : profile.Gender === 2 ? '女' : '-' }}</el-descriptions-item>
                                    <el-descriptions-item label="身高">{{ profile.Height ? `${profile.Height} cm` : '-' }}</el-descriptions-item>
                                    <el-descriptions-item label="体重">{{ profile.Weight ? `${profile.Weight} kg` : '-' }}</el-descriptions-item>
                                    <el-descriptions-item label="BMI">
                                        <el-tag :type="getBmiType(profile.BMI)" size="small" v-if="profile.BMI">{{ profile.BMI }}</el-tag>
                                        <span v-else>-</span>
                                    </el-descriptions-item>
                                    <el-descriptions-item label="血压">{{ profile.SBP && profile.DBP ? `${profile.SBP}/${profile.DBP} mmHg` : '-' }}</el-descriptions-item>
                                </el-descriptions>
                            </div>
                        </GlassCard>
                    </div>
                </el-tab-pane>

                <el-tab-pane label="电子病历档案" name="documents" v-if="!authStore.user?.is_superuser">
                    <GlassCard class="mt-4">
                        <template #header>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-slate-500 dark:text-slate-400">📁 我的体检报告 ({{ documents.length }} 份)</span>
                                <GlassButton size="sm" @click="$router.push('/clinical')">
                                    📎 上传新报告
                                </GlassButton>
                            </div>
                        </template>

                        <div v-if="docsLoading" class="flex items-center justify-center py-12">
                            <el-icon class="is-loading text-3xl text-blue-500"><Loading /></el-icon>
                        </div>

                        <div v-else-if="documents.length === 0" class="flex flex-col items-center py-12">
                            <div class="text-6xl mb-4">🗂️</div>
                            <p class="text-slate-500 dark:text-slate-400 text-center">
                                暂无体检报告<br><span class="text-sm">前往临床体检页面上传您的首份报告</span>
                            </p>
                        </div>

                        <el-timeline v-else>
                            <el-timeline-item
                                v-for="doc in documents"
                                :key="doc.id"
                                :timestamp="formatDate(doc.upload_date)"
                                placement="top"
                            >
                                <div class="flex items-center justify-between bg-white/50 dark:bg-black/20 p-3 rounded-lg border border-slate-100 dark:border-white/5">
                                    <div class="flex items-center gap-3">
                                        <div class="w-10 h-10 flex items-center justify-center rounded-lg" :class="isPdf(doc.file_name) ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30'">
                                            <span class="text-xl">{{ isPdf(doc.file_name) ? '📄' : '🖼️' }}</span>
                                        </div>
                                        <div>
                                            <div class="font-medium text-slate-700 dark:text-white text-sm">{{ doc.file_name }}</div>
                                            <div class="text-xs text-slate-500 flex flex-wrap items-center gap-2 mt-1">
                                                <el-tag :data-testid="`document-ocr-status-${doc.id}`" :type="getDocumentStatusMeta(doc.ocr_processing_status?.status).type" size="small" effect="plain">
                                                    {{ getDocumentStatusMeta(doc.ocr_processing_status?.status).label }}
                                                </el-tag>
                                                <span v-if="doc.ocr_processing_status?.reason" class="text-slate-400">{{ doc.ocr_processing_status.reason }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="flex gap-2">
                                        <el-button size="small" @click="viewDocument(doc)">
                                            <el-icon><View /></el-icon>
                                        </el-button>
                                        <el-button :data-testid="`document-import-action-${doc.id}`" size="small" :type="canImportDocument(doc) ? 'success' : 'primary'" @click="loadToAnalysis(doc)">
                                            <el-icon class="mr-1"><DocumentCopy /></el-icon> {{ getDocumentActionLabel(doc) }}
                                        </el-button>
                                        <el-button size="small" type="danger" @click="deleteDocument(doc)">
                                            <el-icon><Delete /></el-icon>
                                        </el-button>
                                    </div>
                                </div>
                            </el-timeline-item>
                        </el-timeline>
                    </GlassCard>
                </el-tab-pane>
            </el-tabs>

            <div class="mt-6 flex justify-center gap-4">
                <GlassButton size="sm" @click="refreshData" :disabled="loading">
                    {{ loading ? '刷新中...' : '🔄 刷新数据' }}
                </GlassButton>
                <GlassButton @click="handleBack">🔙 返回仪表盘</GlassButton>
            </div>
        </div>

        <el-dialog v-model="showSummaryDialog" title="📓 提取数据预览" width="500px">
            <pre class="bg-slate-100 dark:bg-slate-800 p-4 rounded-lg text-sm overflow-auto max-h-96">{{ JSON.stringify(currentOcrSummary, null, 2) }}</pre>
        </el-dialog>
    </div>
</template>

<script setup>
// 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Loading, View, DocumentCopy, Delete } from '@element-plus/icons-vue'
import { ElNotification, ElMessageBox } from 'element-plus'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import { useAuthStore } from '../stores/authStore'
import { useHealthStore } from '../stores/healthStore'
import { useToast } from '../composables/useToast'
import axios from 'axios'
import { apiUrl } from '../utils/api'

const authStore = useAuthStore()
const healthStore = useHealthStore()
const router = useRouter()
const { userProfile: profile } = storeToRefs(healthStore)
const { showToast } = useToast()

const loading = ref(false)
const activeTab = ref('account')
const documents = ref([])
const docsLoading = ref(false)
const showSummaryDialog = ref(false)
const currentOcrSummary = ref(null)

// 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
const hasProfile = computed(() => {
    if (!profile.value) return false
    return profile.value.Age || profile.value.BMI || profile.value.Height || profile.value.Weight
})

const getBmiType = (bmi) => {
    if (!bmi) return 'info'
    if (bmi < 18.5) return 'warning'
    if (bmi < 24) return 'success'
    if (bmi < 28) return 'warning'
    return 'danger'
}

const isPdf = (filename) => filename?.toLowerCase().endsWith('.pdf')

const getDocumentStatusMeta = (status) => {
    const statusMap = {
        success: { label: '已提取结构化数据', type: 'success' },
        partial_success: { label: '部分识别', type: 'warning' },
        stored_unprocessed: { label: '已保存待识别', type: 'info' },
        error: { label: '识别失败', type: 'danger' },
    }
    return statusMap[status] || { label: '状态未知', type: 'info' }
}

// 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
const canImportDocument = (doc) => Boolean(doc?.ocr_summary && ['success', 'partial_success'].includes(doc?.ocr_processing_status?.status))

const getDocumentActionLabel = (doc) => {
    if (canImportDocument(doc)) return '导入到分析'
    if (doc?.ocr_processing_status?.status === 'stored_unprocessed') return '查看待识别状态'
    if (doc?.ocr_processing_status?.status === 'error') return '查看失败状态'
    return '查看状态'
}

const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    }).replace(/\//g, '-')
}

const fetchDocuments = async () => {
    docsLoading.value = true
    try {
        const res = await axios.get('/api/v1/user/documents')
        if (res.data.status === 'success') {
            documents.value = res.data.documents || []
        }
    } catch (e) {
        console.error('Failed to fetch documents:', e)
    } finally {
        docsLoading.value = false
    }
}

const viewDocument = (doc) => {
    window.open(apiUrl(doc.file_url), '_blank')
}

// 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
const loadToAnalysis = (doc) => {
    healthStore.setImportData({
        ocr_summary: doc.ocr_summary || null,
        ocr_processing_status: doc.ocr_processing_status || null,
        file_name: doc.file_name,
        file_url: doc.file_url,
    })

    if (doc.ocr_summary) {
        ElNotification.success({ title: '数据已准备', message: '正在跳转到临床页继续补全和分析...' })
    } else {
        ElNotification.warning({ title: '文档状态已带入', message: '当前文档暂无可导入的结构化数据，临床页会展示 OCR 状态。' })
    }
    router.push('/clinical')
}

const deleteDocument = async (doc) => {
    try {
        await ElMessageBox.confirm(
            `确定要永久删除 "${doc.file_name}" 吗？此操作不可恢复。`,
            '删除确认',
            { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
        )

        const res = await axios.delete(`/api/v1/user/documents/${doc.id}`)
        if (res.data.status === 'success') {
            showToast('文档已删除', 'success')
            await fetchDocuments()
        }
    } catch (e) {
        if (e !== 'cancel') {
            console.error('Delete failed:', e)
            showToast('删除失败: ' + (e.response?.data?.detail || e.message), 'error')
        }
    }
}

const refreshData = async () => {
    loading.value = true
    try {
        await authStore.fetchProfile()
        await fetchDocuments()
        showToast('数据已刷新', 'success')
    } catch (e) {
        showToast('刷新失败', 'error')
    } finally {
        loading.value = false
    }
}

const handleBack = () => {
    router.push(authStore.user?.is_superuser ? '/admin/dashboard' : '/')
}

onMounted(async () => {
    // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
    loading.value = true
    await healthStore.fetchRemoteProfile()
    await fetchDocuments()
    loading.value = false
})
</script>

<style scoped>
:deep(.el-descriptions__label) { font-weight: 600; color: #64748b; }
.dark :deep(.el-descriptions__label) { color: #94a3b8; }
:deep(.el-descriptions__content) { font-weight: 500; }
.profile-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
</style>
