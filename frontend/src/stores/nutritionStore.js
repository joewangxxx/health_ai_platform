import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { showToast } from '../composables/useToast'

export const useNutritionStore = defineStore('nutrition', () => {
    const currentPlan = ref(null)
    const loading = ref(false)

    // Task 112: Added forceRefresh parameter for cache bypass
    async function generatePlan(conditions = [], forceRefresh = false) {
        loading.value = true
        currentPlan.value = null // Reset previous
        try {
            const payload = {
                health_conditions: conditions,
                force_refresh: forceRefresh,  // Task 111/112
            }

            const res = await axios.post('http://127.0.0.1:8000/nutrition/generate', payload)

            if (res.data.status === 'success') {
                currentPlan.value = res.data
                showToast(forceRefresh ? '已重新生成食谱' : '智能食谱生成成功', 'success')
                return true
            } else {
                showToast(res.data.detail || '生成失败', 'error')
                return false
            }
        } catch (e) {
            console.error(e)
            showToast(e.response?.data?.detail || "服务请求失败", 'error')
            return false
        } finally {
            loading.value = false
        }
    }

    return {
        currentPlan,
        loading,
        generatePlan
    }
})
