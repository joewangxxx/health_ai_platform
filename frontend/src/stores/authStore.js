import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useHealthStore } from './healthStore'

export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem('auth_token') || null)
    const user = ref(null)
    const isAuthenticated = computed(() => !!token.value)

    const healthStore = useHealthStore()

    // Config Axios defaults when token changes
    if (token.value) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }

    async function login(username, password) {
        // 0. Clean state before new attempt
        logout()

        try {
            const params = new URLSearchParams()
            params.append('username', username)
            params.append('password', password)

            const res = await axios.post('/auth/token', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })

            // Save Token
            token.value = res.data.access_token
            localStorage.setItem('auth_token', token.value)
            axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`

            // Sync Profile (user info from /user/me)
            await fetchProfile()

            // 🔥 V7: Sync remote profile data (clinical + genomic)
            await healthStore.fetchRemoteProfile()

            return true
        } catch (e) {
            console.error(e)
            throw new Error(e.response?.data?.detail || "Login failed")
        }
    }

    async function register(email, username, password) {
        try {
            // Fix: ensure correct endpoint /auth/register
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

            // Sync clinical data to HealthStore
            if (res.data.profile) {
                // Filter out nulls to avoid overwriting defaults with null if desired, 
                // or just overwriting is fine as we handled nulls in backend.
                // Here we pass everything, healthStore can handle.
                healthStore.updateProfile(res.data.profile)
            }
        } catch (e) {
            logout()
        }
    }

    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('auth_token')
        delete axios.defaults.headers.common['Authorization']
        // Optional: clear health store?
        // healthStore.$reset()
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
