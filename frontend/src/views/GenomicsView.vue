<template>
    <div class="p-6 h-full flex flex-col items-center">
        <div class="w-full max-w-4xl">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                🧬 基因组学 (Genomics)
            </h1>

            <GlassCard :glowProximity="100">
                <template #header>
                    <div class="flex justify-between items-center text-sm text-slate-500 dark:text-slate-400">
                        <span>上传 23andMe 原始数据 txt 文件</span>
                        <span>Step 2/3</span>
                    </div>
                </template>

                <div class="flex flex-col items-center justify-center py-6">
                    <!-- Upload Area -->
                    <el-upload class="upload-demo w-full max-w-md" drag action="#" :http-request="uploadGeneFile"
                        :show-file-list="false">
                        <div class="flex flex-col items-center py-10">
                            <el-icon
                                class="el-icon--upload text-6xl mb-4 text-slate-400 dark:text-slate-500 transition-colors hover:text-blue-500">
                                <Document />
                            </el-icon>
                            <div class="el-upload__text text-slate-600 dark:text-slate-300 text-lg">
                                拖拽上传基因数据文件 (txt) <br>
                                <em class="text-xs text-slate-400">支持 23andMe 格式</em>
                            </div>
                        </div>
                    </el-upload>

                    <!-- Success Message -->
                    <div v-if="geneStats.loaded"
                        class="mt-8 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl flex items-center gap-4 w-full max-w-md animate-fade-in-up">
                        <el-icon class="text-3xl text-green-500">
                            <CircleCheckFilled />
                        </el-icon>
                        <div>
                            <div class="text-green-800 dark:text-green-300 font-bold text-lg">解析成功</div>
                            <div class="text-green-600 dark:text-green-400 text-sm">已提取 {{ geneStats.count }} 个有效位点
                                (SNPs)</div>
                        </div>
                    </div>

                    <!-- Cloud Sync Status -->
                    <div v-if="cloudSynced"
                        class="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl flex items-center gap-3 w-full max-w-md">
                        <span class="text-xl">☁️</span>
                        <span class="text-blue-600 dark:text-blue-400 text-sm font-medium">✅ 已同步到云端档案</span>
                    </div>
                </div>

                <!-- SNP Preview Table -->
                <div v-if="geneStats.loaded && displayedSnps.length > 0" class="mt-8">
                    <h3 class="text-sm font-bold text-slate-500 mb-3">🧬 数据预览 (Top 10 SNPs)</h3>
                    <div class="rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden">
                        <el-table :data="displayedSnps" style="width: 100%" size="small"
                            :header-cell-style="{ background: 'transparent' }"
                            :row-style="{ background: 'transparent' }">
                            <el-table-column prop="rsid" label="RSID" width="150" />
                            <el-table-column prop="chrom" label="Chr" width="80" />
                            <el-table-column prop="pos" label="Position" width="120" />
                            <el-table-column prop="genotype" label="Genotype" width="100" />
                            <el-table-column label="Status" width="80">
                                <template #default>
                                    <el-tag size="small" type="success" effect="plain">OK</el-tag>
                                </template>
                            </el-table-column>
                        </el-table>
                    </div>
                </div>

                <!-- Navigation -->
                <div class="mt-8 flex justify-between">
                    <GlassButton @click="$router.push('/clinical')">
                        <el-icon class="mr-2">
                            <ArrowLeft />
                        </el-icon> 上一步：临床体检
                    </GlassButton>
                    <GlassButton :disabled="!geneStats.loaded" @click="$router.push('/lifestyle')">
                        下一步：行为与 IoT <el-icon class="ml-2">
                            <ArrowRight />
                        </el-icon>
                    </GlassButton>
                </div>

            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Document, CircleCheckFilled, ArrowRight, ArrowLeft } from '@element-plus/icons-vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import { useHealthStore } from '../stores/healthStore'
import { storeToRefs } from 'pinia'
import axios from 'axios'
import { useToast } from '../composables/useToast'

const store = useHealthStore()
const { geneStats, geneData } = storeToRefs(store)
const cloudSynced = ref(false)
const { showToast } = useToast()

const uploadGeneFile = async (options) => {
    const formData = new FormData(); formData.append('file', options.file)
    try {
        const res = await axios.post('http://127.0.0.1:8000/analyze/genetics_file', formData)
        console.log('Gene API Response:', res.data)
        if (res.data.status === 'success') {
            // Store snps_dict for risk calculation, preview_list for table display
            store.setGeneData(res.data.snps_dict, res.data.parsed_count, res.data.preview_list)
            showToast(`基因分析完成！包含 ${res.data.parsed_count} 个位点`, 'success')

            // 🔥 V7: 自动同步到云端
            const synced = await store.saveProfileToCloud()
            if (synced) {
                cloudSynced.value = true
                showToast('☁️ 基因数据已自动同步到云端', 'success')
            }
        } else {
            showToast(res.data.message || "解析失败", 'error')
        }
    } catch (e) { showToast("基因解析服务连接失败", "error") }
}

// Use preview_list directly if available, otherwise fallback to geneData dict
const displayedSnps = computed(() => {
    // Check if genePreviewList exists
    if (store.genePreviewList && store.genePreviewList.length > 0) {
        return store.genePreviewList.slice(0, 10)
    }
    // Fallback for old data structure
    if (!geneData.value) return []
    return Object.entries(geneData.value).slice(0, 10).map(([k, v]) => ({
        rsid: k,
        chrom: '-',
        pos: '-',
        genotype: v
    }))
})
</script>

<style scoped>
/* Table transparency fix */
:deep(.el-table) {
    --el-table-bg-color: transparent !important;
    --el-table-tr-bg-color: transparent !important;
    --el-table-header-bg-color: rgba(100, 100, 100, 0.05) !important;
    --el-table-row-hover-bg-color: rgba(100, 100, 100, 0.1) !important;
    color: inherit;
    background-color: transparent !important;
    --el-table-border-color: rgba(100, 100, 100, 0.1) !important;
}

:deep(.el-table th),
:deep(.el-table tr) {
    background-color: transparent !important;
}

/* Ensure clean text color in dark mode */
.dark :deep(.el-table) {
    color: #e2e8f0;
}
</style>
