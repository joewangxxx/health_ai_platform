<template>
    <div class="p-6 h-full overflow-auto">
        <div class="max-w-2xl mx-auto">
            <h1 class="text-2xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                ⚙️ 设置 (Settings)
            </h1>

            <GlassCard :glowProximity="100" class="mb-6">
                <template #header>
                    <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                        <el-icon>
                            <Lock />
                        </el-icon>
                        <span>修改密码</span>
                    </div>
                </template>

                <form @submit.prevent="handleChangePassword" class="grid gap-4">
                    <div class="grid gap-2">
                        <Label>当前密码</Label>
                        <div class="relative">
                            <ShadcnInput v-model="passwordForm.current" :type="showCurrentPwd ? 'text' : 'password'"
                                placeholder="请输入当前密码" />
                            <button type="button"
                                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                                @click="showCurrentPwd = !showCurrentPwd">
                                <Eye v-if="!showCurrentPwd" class="w-4 h-4" />
                                <EyeOff v-else class="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div class="grid gap-2">
                        <Label>新密码</Label>
                        <div class="relative">
                            <ShadcnInput v-model="passwordForm.newPassword" :type="showNewPwd ? 'text' : 'password'"
                                placeholder="请输入新密码" />
                            <button type="button"
                                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                                @click="showNewPwd = !showNewPwd">
                                <Eye v-if="!showNewPwd" class="w-4 h-4" />
                                <EyeOff v-else class="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div class="grid gap-2">
                        <Label>确认新密码</Label>
                        <div class="relative">
                            <ShadcnInput v-model="passwordForm.confirm" :type="showConfirmPwd ? 'text' : 'password'"
                                placeholder="请再次输入新密码" />
                            <button type="button"
                                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                                @click="showConfirmPwd = !showConfirmPwd">
                                <Eye v-if="!showConfirmPwd" class="w-4 h-4" />
                                <EyeOff v-else class="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div class="flex justify-end pt-2">
                        <GlassButton type="submit" :disabled="changingPassword">
                            {{ changingPassword ? '保存中...' : '💾 保存密码' }}
                        </GlassButton>
                    </div>
                </form>
            </GlassCard>

            <GlassCard :glowProximity="100" class="mb-6">
                <template #header>
                    <div class="flex items-center gap-2 text-sm text-slate-500">
                        <el-icon>
                            <View />
                        </el-icon>
                        <span>外观设置</span>
                    </div>
                </template>

                <div class="space-y-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-slate-700">减少动画效果</p>
                            <p class="text-xs text-slate-500">关闭页面过渡和微动画以提高性能</p>
                        </div>
                        <Switch v-model="settings.reduceMotion" />
                    </div>

                    <Separator />

                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-slate-700">紧凑模式</p>
                            <p class="text-xs text-slate-500">减少UI元素间距以显示更多内容</p>
                        </div>
                        <Switch v-model="settings.compactMode" />
                    </div>
                </div>
            </GlassCard>

            <GlassCard :glowProximity="100">
                <template #header>
                    <div class="flex items-center gap-2 text-sm text-slate-500">
                        <el-icon>
                            <Hide />
                        </el-icon>
                        <span>隐私设置</span>
                    </div>
                </template>

                <div class="space-y-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-slate-700 dark:text-slate-200">允许匿名数据用于科研</p>
                            <p class="text-xs text-slate-500 dark:text-slate-400">您的数据将被脱敏处理并用于医学研究</p>
                        </div>
                        <Switch v-model="settings.allowResearchData" />
                    </div>

                    <Separator />

                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-slate-700 dark:text-slate-200">接收健康建议通知</p>
                            <p class="text-xs text-slate-500 dark:text-slate-400">根据您的健康数据推送个性化建议</p>
                        </div>
                        <Switch v-model="settings.healthNotifications" />
                    </div>
                </div>
            </GlassCard>

            <div class="mt-6 flex justify-end">
                <GlassButton @click="saveSettings">
                    ✅ 保存所有设置
                </GlassButton>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Lock, View, Hide } from '@element-plus/icons-vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import GlassCard from '../components/ui/GlassCard.vue'
import GlassButton from '../components/ui/GlassButton.vue'
import ShadcnInput from '../components/ui/ShadcnInput.vue'
import Label from '../components/ui/Label.vue'
import Switch from '../components/ui/Switch.vue'
import Separator from '../components/ui/Separator.vue'
import { useToast } from '../composables/useToast'

const { showToast } = useToast()

const changingPassword = ref(false)

// Password visibility toggles
const showCurrentPwd = ref(false)
const showNewPwd = ref(false)
const showConfirmPwd = ref(false)

const passwordForm = reactive({
    current: '',
    newPassword: '',
    confirm: ''
})

const settings = reactive({
    reduceMotion: false,
    compactMode: false,
    allowResearchData: true,
    healthNotifications: true
})

// Load settings from localStorage on mount
onMounted(() => {
    const saved = localStorage.getItem('healthai_settings')
    if (saved) {
        const parsed = JSON.parse(saved)
        Object.assign(settings, parsed)
    }
})

const handleChangePassword = async () => {
    // Prevent double submit
    if (changingPassword.value) return

    if (!passwordForm.current || !passwordForm.newPassword) {
        return showToast('请填写完整密码信息', 'warning')
    }
    if (passwordForm.current === passwordForm.newPassword) {
        return showToast('新密码不能与当前密码相同', 'warning')
    }
    if (passwordForm.newPassword !== passwordForm.confirm) {
        return showToast('两次输入的新密码不一致', 'error')
    }
    if (passwordForm.newPassword.length < 6) {
        return showToast('新密码长度至少 6 位', 'warning')
    }

    changingPassword.value = true
    try {
        // TODO: Implement actual password change API call
        await new Promise(resolve => setTimeout(resolve, 1000))
        showToast('密码修改成功', 'success')
        passwordForm.current = ''
        passwordForm.newPassword = ''
        passwordForm.confirm = ''
    } catch (e) {
        showToast('密码修改失败', 'error')
    } finally {
        changingPassword.value = false
    }
}

const saveSettings = () => {
    localStorage.setItem('healthai_settings', JSON.stringify(settings))
    showToast('设置已保存', 'success')

    // Apply settings
    if (settings.reduceMotion) {
        document.documentElement.classList.add('reduce-motion')
    } else {
        document.documentElement.classList.remove('reduce-motion')
    }

    if (settings.compactMode) {
        document.documentElement.classList.add('compact-mode')
    } else {
        document.documentElement.classList.remove('compact-mode')
    }
}
</script>
