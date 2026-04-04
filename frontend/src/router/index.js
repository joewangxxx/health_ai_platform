import { createRouter, createWebHistory } from 'vue-router'

import { showToast } from '../composables/useToast'
import { useAuthStore } from '../stores/authStore'

const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const MainLayout = () => import('../layout/MainLayout.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const ClinicalView = () => import('../views/ClinicalView.vue')
const GenomicsView = () => import('../views/GenomicsView.vue')
const LifestyleView = () => import('../views/LifestyleView.vue')
const PharmacyView = () => import('../views/PharmacyView.vue')
const NutritionPlanView = () => import('../views/nutrition/NutritionPlan.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const SettingsView = () => import('../views/SettingsView.vue')
const DrAIView = () => import('../views/chat/DrAI.vue')
const HealthTimelineView = () => import('../views/clinical/HealthTimeline.vue')
const DataCenterView = () => import('../views/admin/DataCenterView.vue')
const AdminDashboardView = () => import('../views/admin/AdminDashboardView.vue')
const UserManagementView = () => import('../views/admin/UserManagementView.vue')
const KnowledgeBaseView = () => import('../views/admin/KnowledgeBase.vue')

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: LoginView,
    },
    {
        path: '/register',
        name: 'Register',
        component: RegisterView,
    },
    {
        path: '/',
        component: MainLayout,
        meta: { requiresAuth: true },
        children: [
            { path: '', name: 'Dashboard', component: DashboardView },
            { path: 'clinical', name: 'Clinical', component: ClinicalView },
            { path: 'genomics', name: 'Genomics', component: GenomicsView },
            { path: 'lifestyle', name: 'Lifestyle', component: LifestyleView },
            { path: 'pharmacy', name: 'Pharmacy', component: PharmacyView },
            { path: 'nutrition', name: 'Nutrition', component: NutritionPlanView },
            { path: 'profile', name: 'Profile', component: ProfileView },
            { path: 'settings', name: 'Settings', component: SettingsView },
            { path: 'chat', name: 'DrAI', component: DrAIView },
            { path: 'timeline', name: 'HealthTimeline', component: HealthTimelineView },
        ],
    },
    {
        path: '/admin',
        component: MainLayout,
        meta: { requiresAuth: true, requiresAdmin: true },
        children: [
            { path: 'dashboard', name: 'AdminDashboard', component: AdminDashboardView },
            { path: 'data-center', name: 'DataCenter', component: DataCenterView },
            { path: 'users', name: 'UserManagement', component: UserManagementView },
            { path: 'knowledge', name: 'KnowledgeBase', component: KnowledgeBaseView },
        ],
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()

    if (to.matched.some((record) => record.meta.requiresAuth)) {
        if (!authStore.token) {
            next({ name: 'Login' })
            return
        }

        if (!authStore.user) {
            try {
                await authStore.fetchProfile()
                if (!authStore.user) {
                    authStore.logout()
                    next({ name: 'Login' })
                    return
                }
            } catch (e) {
                authStore.logout()
                next({ name: 'Login' })
                return
            }
        }

        if (to.matched.some((record) => record.meta.requiresAdmin)) {
            if (!authStore.user?.is_superuser) {
                showToast('Access Denied: Admin only', 'error')
                next({ name: 'Dashboard' })
                return
            }
        }

        next()
    } else if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
        if (authStore.user?.is_superuser) {
            next({ name: 'AdminDashboard' })
        } else {
            next({ name: 'Dashboard' })
        }
    } else {
        next()
    }
})

export default router
