<template>
    <AuroraBackground>
        <div class="common-layout w-full min-h-screen">
            <el-container class="min-h-screen">

                <!-- 顶部栏 -->
                <el-header
                    class="backdrop-blur-md bg-white/30 border-b border-gray-200/20 flex items-center justify-between px-6 z-50">
                    <div class="flex items-center gap-3">
                        <h2 class="m-0 font-extrabold tracking-wide text-slate-800 text-xl">HealthAI
                            Platform</h2>
                        <el-tag type="info" effect="dark" round size="small">Bayesian Fusion</el-tag>
                    </div>

                    <div class="flex items-center gap-6">
                        <!-- 设备状态 -->
                        <div class="flex items-center gap-2">
                            <el-tag :type="store.deviceStatus === '设备在线' ? 'success' : 'danger'" effect="dark" round>
                                {{ store.deviceStatus }}
                            </el-tag>
                        </div>

                        <!-- 用户弹出菜单 -->
                        <Popover
                            align="end"
                            ref="userPopover"
                            trigger-label="Open user menu"
                            trigger-class="h-10 w-10 rounded-full border border-white/20 bg-white/20 backdrop-blur-md hover:bg-white/30"
                        >
                            <template #trigger>
                                <Avatar :fallback="authStore.user?.username?.charAt(0).toUpperCase()" size="sm" />
                            </template>

                            <!-- 弹出层内容 -->
                            <div class="grid gap-4">
                                <!-- 用户信息头部 -->
                                <div class="flex items-center gap-3">
                                    <Avatar :fallback="authStore.user?.username?.charAt(0).toUpperCase()"
                                        size="default" />
                                    <div class="grid gap-0.5">
                                        <p class="text-sm font-semibold text-slate-900">
                                            {{ authStore.user?.username || '加载中...' }}
                                        </p>
                                        <p class="text-xs text-slate-500">
                                            {{ authStore.user?.email || 'user@example.com' }}
                                        </p>
                                    </div>
                                </div>

                                <Separator />

                                <!-- 菜单项 -->
                                <div class="grid gap-1">
                                    <ShadcnButton variant="ghost" class="w-full justify-start gap-2 h-9"
                                        @click="navigateTo('/profile')">
                                        <el-icon>
                                            <UserFilled />
                                        </el-icon>
                                        个人档案
                                    </ShadcnButton>
                                    <ShadcnButton variant="ghost" class="w-full justify-start gap-2 h-9"
                                        @click="navigateTo('/settings')">
                                        <el-icon>
                                            <Setting />
                                        </el-icon>
                                        设置
                                    </ShadcnButton>
                                </div>

                                <Separator />

                                <!-- 退出登录 -->
                                <ShadcnButton variant="ghost"
                                    class="w-full justify-start gap-2 h-9 text-red-500 hover:text-red-600 hover:bg-red-50"
                                    @click="handleLogout">
                                    <el-icon>
                                        <SwitchButton />
                                    </el-icon>
                                    退出登录
                                </ShadcnButton>
                            </div>
                        </Popover>
                    </div>
                </el-header>

                <el-container style="height: calc(100vh - 60px);">

                    <!-- 侧边导航栏 -->
                    <el-aside width="220px" class="app-sidebar backdrop-blur-sm bg-white/40 border-r border-gray-200/20">
                        <el-scrollbar>
                            <el-menu :default-active="$route.path" router class="bg-transparent border-none"
                                background-color="transparent">

                                <template v-if="authStore.user?.is_superuser">
                                    <div class="px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                                        Administration</div>
                                    <el-menu-item index="/admin/dashboard">
                                        <el-icon>
                                            <Odometer />
                                        </el-icon>
                                        <span>系统概览 Dashboard</span>
                                    </el-menu-item>
                                    <el-menu-item index="/admin/users">
                                        <el-icon>
                                            <User />
                                        </el-icon>
                                        <span>用户管理 Users</span>
                                    </el-menu-item>
                                    <el-menu-item index="/admin/data-center">
                                        <el-icon>
                                            <DataLine />
                                        </el-icon>
                                        <span>数据中心 Data Center</span>
                                    </el-menu-item>
                                </template>

                                <template v-else>
                                    <div class="px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                                        User
                                        Panel</div>
                                    <el-menu-item index="/">
                                        <el-icon>
                                            <Odometer />
                                        </el-icon>
                                        <span>仪表盘 Dashboard</span>
                                    </el-menu-item>
                                    <el-menu-item index="/clinical">
                                        <el-icon>
                                            <Memo />
                                        </el-icon>
                                        <span>临床体检 Clinical</span>
                                    </el-menu-item>
                                    <el-menu-item index="/genomics">
                                        <el-icon>
                                            <Microphone />
                                        </el-icon>
                                        <span>基因组学 Genomics</span>
                                    </el-menu-item>
                                    <el-menu-item index="/lifestyle">
                                        <el-icon>
                                            <Camera />
                                        </el-icon>
                                        <span>行为视觉 Lifestyle</span>
                                    </el-menu-item>
                                    <el-menu-item index="/chat">
                                        <el-icon>
                                            <ChatDotRound />
                                        </el-icon>
                                        <span>Dr. AI 健康顾问</span>
                                    </el-menu-item>
                                    <el-menu-item index="/timeline">
                                        <el-icon>
                                            <TrendCharts />
                                        </el-icon>
                                        <span>全周期慢病管理</span>
                                    </el-menu-item>
                                    <el-menu-item index="/pharmacy">
                                        <el-icon>
                                            <FirstAidKit />
                                        </el-icon>
                                        <span>智能药房 Pharmacy</span>
                                    </el-menu-item>
                                    <el-menu-item index="/nutrition">
                                        <el-icon>
                                            <Bowl />
                                        </el-icon>
                                        <span>AI 营养师 Nutrition</span>
                                    </el-menu-item>
                                </template>

                            </el-menu>
                        </el-scrollbar>
                    </el-aside>

                    <!-- 主内容区 -->
                    <el-main class="app-main p-0 relative overflow-auto flex flex-col min-h-0">
                        <router-view v-slot="{ Component }">
                            <transition name="fade">
                                <component :is="Component" :key="$route.fullPath" />
                            </transition>
                        </router-view>
                    </el-main>

                </el-container>
            </el-container>
        </div>
    </AuroraBackground>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
    Odometer, Memo, Microphone, Camera, FirstAidKit, DataLine,
    UserFilled, SwitchButton, User, Setting, Bowl, ChatDotRound, TrendCharts
} from '@element-plus/icons-vue'
import AuroraBackground from '../components/ui/AuroraBackground.vue'
import Popover from '../components/ui/Popover.vue'
import Avatar from '../components/ui/Avatar.vue'
import Separator from '../components/ui/Separator.vue'
import ShadcnButton from '../components/ui/ShadcnButton.vue'
import { useHealthStore } from '../stores/healthStore'
import { useAuthStore } from '../stores/authStore'
import { useToast } from '../composables/useToast'

const store = useHealthStore()
const authStore = useAuthStore()
const router = useRouter()
const { showToast } = useToast()

let pollInterval = null

// 1. 实现全局设备轮询
onMounted(async () => {
    // 首次拉取
    store.fetchIoTData()

    // 每 2 秒轮询一次
    pollInterval = setInterval(() => {
        store.fetchIoTData()
    }, 2000)

    // 强化逻辑：若存在登录凭证但缺少用户信息，则补拉一次用户信息
    if (!authStore.user && authStore.token) {
        try {
            await authStore.fetchProfile()
        } catch (e) {
            // 登录凭证无效时执行登出并重定向
            authStore.logout()
            router.push('/login')
        }
    }
})
onUnmounted(() => {
    if (pollInterval) {
        clearInterval(pollInterval)
    }
})

// 2. 退出登录逻辑
const userPopover = ref(null)

const handleLogout = () => {
    userPopover.value?.close()
    authStore.logout()
    showToast('已退出登录', 'success')
    router.push('/login')
}

const navigateTo = (path) => {
    userPopover.value?.close()
    router.push(path)
}
</script>

<style scoped>
:deep(.el-menu-item) {
    font-weight: 500;
    color: #334155;
    /* slate-700 色值 */
}

:deep(.el-menu-item.is-active) {
    color: #2563eb;
    /* blue-600 色值 */
}

:deep(.el-menu-item:hover) {
    background-color: rgba(255, 255, 255, 0.2) !important;
    color: #2563eb;
}

@media (max-width: 768px) {
    .app-sidebar {
        display: none;
    }

    .app-main {
        width: 100%;
    }
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
