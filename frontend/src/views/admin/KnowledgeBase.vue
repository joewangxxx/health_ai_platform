<template>
    <div class="p-6 h-full flex flex-col">
        <div class="w-full max-w-7xl mx-auto h-full flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    📚 医学指南管理 (RAG Knowledge Base)
                </h1>
                <div class="flex gap-3">
                    <el-upload class="upload-demo" action="#" :auto-upload="false" :on-change="handleUpload"
                        :show-file-list="false" accept=".pdf" :disabled="uploading">
                        <el-button type="primary" size="large" :loading="uploading">
                            <el-icon class="mr-2">
                                <Upload />
                            </el-icon> 上传 PDF 指南
                        </el-button>
                    </el-upload>

                    <el-button type="warning" size="large" @click="rebuildIndex" :loading="rebuilding">
                        <el-icon class="mr-2">
                            <Refresh />
                        </el-icon> 重建索引
                    </el-button>

                    <el-button @click="fetchFiles" circle>
                        <el-icon>
                            <RefreshRight />
                        </el-icon>
                    </el-button>
                </div>
            </div>

            <GlassCard class="flex-1 flex flex-col overflow-hidden" :glow="true">
                <!-- Info Alert -->
                <div class="p-4">
                    <el-alert title="知识库说明" type="info" show-icon :closable="false" class="mb-4">
                        系统会自动读取此处的 PDF 文件并构建向量索引。上传新文件后，建议点击"重建索引"以确保检索生效。
                        索引构建是后台任务，可能需要几分钟时间。
                    </el-alert>

                    <!-- File Table -->
                    <el-table :data="fileList" style="width: 100%" height="100%" v-loading="loading"
                        element-loading-text="加载文件列表中...">
                        <el-table-column prop="name" label="文件名" min-width="300">
                            <template #default="scope">
                                <div class="flex items-center gap-2">
                                    <el-icon class="text-red-500 text-xl">
                                        <Document />
                                    </el-icon>
                                    <span class="font-medium">{{ scope.row.name }}</span>
                                </div>
                            </template>
                        </el-table-column>

                        <el-table-column prop="size" label="大小" width="120">
                            <template #default="scope">
                                {{ formatSize(scope.row.size) }}
                            </template>
                        </el-table-column>

                        <el-table-column prop="uploaded_at" label="最后修改时间" width="200" />

                        <el-table-column label="操作" width="120" align="center">
                            <template #default="scope">
                                <el-button type="danger" size="small" circle @click="confirmDelete(scope.row.name)">
                                    <el-icon>
                                        <Delete />
                                    </el-icon>
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </div>
            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload, Refresh, RefreshRight, Document, Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import axios from 'axios'
import GlassCard from '../../components/ui/GlassCard.vue'
import { useAuthStore } from '../../stores/authStore'
import { useToast } from '../../composables/useToast'

const authStore = useAuthStore()
const { showToast } = useToast()
const fileList = ref([])
const loading = ref(false)
const uploading = ref(false)
const rebuilding = ref(false)

const getAuthHeaders = () => ({
    Authorization: 'Bearer ' + authStore.token
})

// Format Bytes
const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 1. Fetch Files
const fetchFiles = async () => {
    loading.value = true
    try {
        const res = await axios.get('/admin/knowledge/files', {
            headers: getAuthHeaders()
        })
        fileList.value = res.data
    } catch (e) {
        showToast('获取文件列表失败: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
        loading.value = false
    }
}

// 2. Upload File
const handleUpload = async (file) => {
    if (!file.raw) return

    // Validate PDF
    if (file.raw.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('仅支持 PDF 文件', 'warning')
        return
    }

    uploading.value = true
    const formData = new FormData()
    formData.append('file', file.raw)

    try {
        await axios.post('/admin/knowledge/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                ...getAuthHeaders()
            }
        })
        showToast(`文件 ${file.name} 上传成功`, 'success')
        fetchFiles() // Refresh list
    } catch (e) {
        showToast('上传失败: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
        uploading.value = false
    }
}

// 3. Delete File
const confirmDelete = (filename) => {
    ElMessageBox.confirm(
        `确定要删除 "${filename}" 吗？此操作不可恢复。`,
        '警告',
        {
            confirmButtonText: '确定删除',
            cancelButtonText: '取消',
            type: 'warning',
        }
    ).then(async () => {
        try {
        await axios.delete(`/admin/knowledge/files/${filename}`, {
                headers: getAuthHeaders()
            })
            showToast('文件已删除', 'success')
            fetchFiles()
        } catch (e) {
            showToast('删除失败', 'error')
        }
    })
}

// 4. Rebuild Index
const rebuildIndex = async () => {
    rebuilding.value = true
    try {
        const res = await axios.post('/admin/knowledge/rebuild', {}, {
            headers: getAuthHeaders()
        })
        showToast('索引重建任务已后台启动，请稍候...', 'success')
    } catch (e) {
        showToast('触发重建失败', 'error')
    } finally {
        // Just visual delay to prevent spam
        setTimeout(() => { rebuilding.value = false }, 2000)
    }
}

onMounted(() => {
    fetchFiles()
})
</script>

<style scoped>
/* Scoped styles can be added here if needed */
</style>
