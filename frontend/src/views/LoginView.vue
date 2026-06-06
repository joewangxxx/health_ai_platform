<template>
    <AuroraBackground>
        <div class="min-h-screen flex items-center justify-center px-4 py-8">
            <GlassCard :glowProximity="100" class="w-full max-w-md p-8 relative" :glow="true">
                <template #header>
                    <div class="flex flex-col items-center mb-6">
                        <!-- Typography -->
                        <h1 class="text-2xl font-bold text-slate-900 mb-1">HealthAI Platform</h1>
                        <p class="text-sm text-slate-500">探索您的多模态数字生命</p>
                    </div>
                </template>

                <el-form label-position="top" size="large" @submit.prevent="handleLogin">
                    <el-form-item label="Username">
                        <el-input ref="usernameInput" v-model.trim="form.username" placeholder="请输入用户名"
                            :prefix-icon="User" @keydown.enter.prevent="focusPassword" />
                    </el-form-item>

                    <el-form-item label="Password">
                        <el-input ref="passwordInput" v-model.trim="form.password" type="password" placeholder="请输入密码"
                            :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
                    </el-form-item>

                    <div class="mt-8">
                        <GradientButton class="w-full text-lg shadow-xl" type="submit" :disabled="loading">
                            <span v-if="loading">Signing In...</span>
                            <span v-else>登录 (Sign In)</span>
                        </GradientButton>
                    </div>

                    <div class="mt-6 text-center text-sm text-slate-500">
                        还没有账号?
                        <router-link to="/register"
                            class="text-blue-500 hover:text-blue-400 font-bold ml-1 transition-colors">
                            立即注册
                        </router-link>
                    </div>
                </el-form>
            </GlassCard>
        </div>
    </AuroraBackground>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import AuroraBackground from '../components/ui/AuroraBackground.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GradientButton from '../components/ui/GradientButton.vue'
import { useAuthStore } from '../stores/authStore'
import { useToast } from '../composables/useToast'

const router = useRouter()
const authStore = useAuthStore()
const { showToast } = useToast()

// Input refs for focus control
const usernameInput = ref(null)
const passwordInput = ref(null)

const loading = ref(false)
const form = ref({
    username: '',
    password: ''
})

// 用户名回车 -> 聚焦密码框
const focusPassword = () => {
    // Element Plus el-input 的 focus 方法
    passwordInput.value?.focus()
}

const handleLogin = async () => {
    if (loading.value) return
    if (!form.value.username || !form.value.password) {
        showToast("请输入用户名和密码", "warning")
        return
    }

    loading.value = true
    try {
        // Explicit trim for backend safety
        const username = form.value.username.trim()
        const password = form.value.password.trim()
        await authStore.login(username, password)
        showToast('登录成功', 'success')

        if (authStore.user?.is_superuser) {
            router.push('/admin/dashboard')
        } else {
            router.push('/')
        }
    } catch (e) {
        showToast(e.message || '登录失败', 'error')
    } finally {
        loading.value = false
    }
}
</script>
