import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useHealthStore } from './healthStore'

export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem('auth_token') || null)
    const user = ref(null)
    const isAuthenticated = computed(() => !!token.value)

    const healthStore = useHealthStore()

    // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
    // 中文注释：启动时若已有本地 token，立即恢复全局请求头，减少刷新后的鉴权抖动。
    if (token.value) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }

    async function login(username, password) {
        // 中文注释：登录流程先做请求鉴权，再补齐个人档案与健康上下文。
        // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
        logout()

        try {
            const params = new URLSearchParams()
            params.append('username', username)
            params.append('password', password)

            const res = await axios.post('/auth/token', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })

            // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
            token.value = res.data.access_token
            localStorage.setItem('auth_token', token.value)
            axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`

            // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
            await fetchProfile()

            // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
            // 中文注释：登录后拉取云端健康档案，确保首页进入即有完整上下文。
            await healthStore.fetchRemoteProfile()

            return true
        } catch (e) {
            console.error(e)
            throw new Error(e.response?.data?.detail || "Login failed")
        }
    }

    async function register(email, username, password) {
        try {
            // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
            await axios.post('/auth/register', {
                username, email, password
            })
            return true
        } catch (error) {
            // Extract specific error detail
            const errorMsg = error.response?.data?.detail || "注册服务连接失败"
            throw errorMsg // Throw string for view to display
        }
    }

    async function fetchProfile() {
        if (!token.value) return
        try {
            const res = await axios.get('/user/me')
            user.value = res.data

            // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
            if (res.data.profile) {
                // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
                // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
                // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
                healthStore.updateProfile(res.data.profile)
            }
        } catch (e) {
            logout()
        }
    }

    function logout() {
        // 中文注释：退出时清理本地缓存与默认请求头，避免后续请求携带旧凭证。
        token.value = null
        user.value = null
        localStorage.removeItem('auth_token')
        delete axios.defaults.headers.common['Authorization']
        // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
        // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
    }

    return {
        token,
        user,
        isAuthenticated,
        login,
        register,
        fetchProfile,
        logout
    }
})
