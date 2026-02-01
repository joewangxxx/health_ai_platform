<template>
    <div class="p-6 h-full flex flex-col">
        <div class="w-full max-w-7xl mx-auto h-full flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    👥 用户管理 (User Management)
                </h1>

                <GlassButton @click="fetchUsers" :loading="loading">
                    <el-icon class="mr-1">
                        <Refresh />
                    </el-icon> 刷新列表
                </GlassButton>
            </div>

            <!-- Table Card -->
            <GlassCard class="flex-1 overflow-hidden flex flex-col" :glow="false">
                <div class="flex-1 overflow-auto">
                    <el-table :data="users" style="width: 100%; height: 100%;" stripe>
                        <el-table-column prop="id" label="ID" width="80" align="center" />

                        <el-table-column prop="username" label="用户名 (Username)" min-width="150">
                            <template #default="scope">
                                <div class="font-bold flex items-center gap-2">
                                    {{ scope.row.username }}
                                    <div v-if="scope.row.is_superuser"
                                        class="text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded border border-red-200">
                                        ADMIN
                                    </div>
                                </div>
                            </template>
                        </el-table-column>

                        <el-table-column prop="email" label="邮箱 (Email)" min-width="200">
                            <template #default="scope">
                                {{ scope.row.email || 'N/A' }}
                            </template>
                        </el-table-column>

                        <el-table-column label="状态" width="100" align="center">
                            <template #default>
                                <el-tag type="success" size="small" effect="plain">Active</el-tag>
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
import axios from 'axios'
import { Refresh } from '@element-plus/icons-vue'
import GlassCard from '../../components/ui/GlassCard.vue'
import GlassButton from '../../components/ui/GlassButton.vue'
import { useToast } from '../../composables/useToast'

const users = ref([])
const loading = ref(false)
const { showToast } = useToast()

const fetchUsers = async () => {
    loading.value = true
    try {
        const res = await axios.get('http://127.0.0.1:8000/admin/users')
        users.value = res.data
        showToast("用户列表已刷新", "success", "bottom-right")
    } catch (e) {
        showToast(e.response?.data?.detail || "无法获取用户列表", "error", "bottom-right")
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    fetchUsers()
})
</script>
