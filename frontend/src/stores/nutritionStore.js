import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { showToast } from '../composables/useToast'

export const useNutritionStore = defineStore('nutrition', () => {
    const currentPlan = ref(null)
    const loading = ref(false)
    // 中文注释：营养计划生成是串行动作，请求开始时先清空旧结果避免用户误读。

    // 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
    async function generatePlan(conditions = [], forceRefresh = false) {
        // 中文注释：force_refresh 交给后端决定是否跳过缓存，前端不自行实现缓存策略。
        loading.value = true
        currentPlan.value = null // Reset previous
        try {
            const payload = {
                health_conditions: conditions,
                force_refresh: forceRefresh,  // Task 111/112
            }

            const res = await axios.post('/nutrition/generate', payload)

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
