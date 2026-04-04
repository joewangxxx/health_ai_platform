<template>
    <div class="p-6 h-full flex flex-col">
        <div class="w-full max-w-7xl mx-auto">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                🚀 系统概览 (System Overview)
            </h1>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <GlassCard class="p-6">
                    <div class="text-sm text-slate-500 mb-2">Total Users</div>
                    <div class="text-3xl font-bold text-blue-600">{{ stats.total_users }}</div>
                </GlassCard>
                <GlassCard class="p-6">
                    <div class="text-sm text-slate-500 mb-2">System Status</div>
                    <div class="text-3xl font-bold text-green-500">{{ stats.status }}</div>
                </GlassCard>
                <GlassCard class="p-6">
                    <div class="text-sm text-slate-500 mb-2">Active Tasks</div>
                    <div class="text-3xl font-bold text-purple-500">{{ stats.active_tasks }}</div>
                </GlassCard>
            </div>

            <div class="mt-8 text-center text-slate-400">
                <p>Welcome to the Admin Control Panel.</p>
                <p class="text-sm">More metrics coming soon...</p>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import GlassCard from '../../components/ui/GlassCard.vue'

const stats = ref({
    total_users: 0,
    status: 'Unknown',
    active_tasks: 0
})

onMounted(async () => {
    try {
        const res = await axios.get('/admin/stats')
        stats.value = res.data
    } catch (e) {
        console.error("Failed to load admin stats", e)
    }
})
</script>
