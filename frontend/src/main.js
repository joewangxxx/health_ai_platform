import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './assets/main.css' // Ensure this exists or Remove if not needed, but safe to keep usually

import axios from 'axios'
import { useAuthStore } from './stores/authStore'
import { showToast } from './composables/useToast'
import { API_BASE_URL } from './utils/api'

const app = createApp(App)

axios.defaults.baseURL = API_BASE_URL || undefined

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// Global Axios Interceptor for 401 Session Handling
axios.interceptors.response.use(
    response => response,
    error => {
        if (error.response && error.response.status === 401) {
            // Ignore 401 from Login page (User typed wrong password)
            if (error.config?.url?.includes('/auth/token')) {
                return Promise.reject(error)
            }

            // Handle Session Expiry (Token invalid/expired)
            const authStore = useAuthStore()
            authStore.logout()
            showToast('会话已过期，请重新登录', 'warning')
            router.push('/login')
        }
        return Promise.reject(error)
    }
)

app.mount('#app')
