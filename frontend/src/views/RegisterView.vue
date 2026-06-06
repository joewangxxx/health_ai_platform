<template>
    <AuroraBackground>
        <div class="min-h-screen flex items-start justify-center px-4 pt-12 pb-8 sm:pt-14">
            <GlassCard :glowProximity="100" class="w-full max-w-md p-8" :glow="true">
                <template #header>
                    <div class="flex flex-col items-center mb-6">
                        <!-- Typography -->
                        <h1 class="text-2xl font-bold text-slate-900 mb-1">HealthAI Platform</h1>
                        <p class="text-sm text-slate-500">创建一个新账户</p>
                    </div>
                </template>

                <el-form label-position="top" size="large" @submit.prevent="handleRegister">
                    <el-form-item label="Email">
                        <el-input v-model.trim="form.email" placeholder="example@email.com" :prefix-icon="Message" />
                    </el-form-item>

                    <el-form-item label="Username">
                        <el-input v-model.trim="form.username" placeholder="设置用户名" :prefix-icon="User" />
                    </el-form-item>

                    <el-form-item label="Password">
                        <el-input v-model.trim="form.password" type="password" placeholder="设置密码" :prefix-icon="Lock"
                            show-password />
                    </el-form-item>

                    <el-form-item label="Confirm Password">
                        <el-input
                            v-model.trim="form.confirmPassword"
                            type="password"
                            placeholder="再次输入密码"
                            :prefix-icon="Lock"
                            show-password
                        />
                    </el-form-item>

                    <div class="mt-8">
                        <GradientButton class="w-full text-lg shadow-xl" type="submit" :disabled="loading">
                            <span v-if="loading">Creating Account...</span>
                            <span v-else>注册 (Sign Up)</span>
                        </GradientButton>
                    </div>

                    <div class="mt-6 text-center text-sm text-slate-500">
                        已有账号?
                        <router-link to="/login"
                            class="text-blue-500 hover:text-blue-400 font-bold ml-1 transition-colors">
                            去登录
                        </router-link>
                    </div>
                </el-form>
            </GlassCard>
        </div>
    </AuroraBackground>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message } from '@element-plus/icons-vue'
import AuroraBackground from '../components/ui/AuroraBackground.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import GradientButton from '../components/ui/GradientButton.vue'
import ShadcnInput from '../components/ui/ShadcnInput.vue'
import { useAuthStore } from '../stores/authStore'
import { useToast } from '../composables/useToast'

const router = useRouter()
const authStore = useAuthStore()
const { showToast } = useToast()

const loading = ref(false)
const form = reactive({
    email: '',
    username: '',
    password: '',
    confirmPassword: ''
})

const handleRegister = async () => {
    // 0. Prevent Double Submit
    if (loading.value) return

    // 1. Basic Empty Check
    if (!form.username || !form.password || !form.email || !form.confirmPassword) {
        showToast("请填写完整信息", "warning")
        return
    }

    // 2. Email Regex Check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(form.email)) {
        showToast("请输入有效的邮箱地址", "warning")
        return
    }

    // 3. Length Checks
    if (form.username.length < 3) {
        showToast("用户名长度至少需要 3 位", "warning")
        return
    }
    if (form.password.length < 6) {
        showToast("密码长度至少需要 6 位", "warning")
        return
    }

    // 4. Password Confirmation
    if (form.password !== form.confirmPassword) {
        showToast("两次密码输入不一致", "error")
        return
    }

    loading.value = true
    try {
        await authStore.register(form.email, form.username, form.password)
        showToast('注册成功！请登录', 'success')
        router.push('/login')
    } catch (errorHtmlOrString) {
        showToast(errorHtmlOrString, 'error')
    } finally {
        loading.value = false
    }
}
</script>
