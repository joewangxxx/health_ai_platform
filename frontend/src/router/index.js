import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import MainLayout from '../layout/MainLayout.vue'
import { showToast } from '../composables/useToast'

// Views
import DashboardView from '../views/DashboardView.vue'
import ClinicalView from '../views/ClinicalView.vue'
import GenomicsView from '../views/GenomicsView.vue'
import LifestyleView from '../views/LifestyleView.vue'
import PharmacyView from '../views/PharmacyView.vue'
import NutritionPlanView from '../views/nutrition/NutritionPlan.vue'
import ProfileView from '../views/ProfileView.vue'
import SettingsView from '../views/SettingsView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DataCenterView from '../views/admin/DataCenterView.vue'
import AdminDashboardView from '../views/admin/AdminDashboardView.vue'
import UserManagementView from '../views/admin/UserManagementView.vue'
import KnowledgeBaseView from '../views/admin/KnowledgeBase.vue'

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: LoginView
    },
    {
        path: '/register',
        name: 'Register',
        component: RegisterView
    },
    {
        path: '/',
        component: MainLayout,
        meta: { requiresAuth: true },
        children: [
            { path: '', name: 'Dashboard', component: DashboardView }, // User Dashboard
            { path: 'clinical', name: 'Clinical', component: ClinicalView },
            { path: 'genomics', name: 'Genomics', component: GenomicsView },
            { path: 'lifestyle', name: 'Lifestyle', component: LifestyleView },
            { path: 'pharmacy', name: 'Pharmacy', component: PharmacyView },
            { path: 'nutrition', name: 'Nutrition', component: NutritionPlanView },
            { path: 'profile', name: 'Profile', component: ProfileView },
            { path: 'settings', name: 'Settings', component: SettingsView },
            { path: 'chat', name: 'DrAI', component: () => import('../views/chat/DrAI.vue') }, // Lazy load
            { path: 'timeline', name: 'HealthTimeline', component: () => import('../views/clinical/HealthTimeline.vue') }, // Task 29
        ]
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
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Global Guard
router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()

    // 1. Auth Guard
    if (to.matched.some(record => record.meta.requiresAuth)) {
        // Explicit token check
        if (!authStore.token) {
            next({ name: 'Login' })
            return
        }

        // Ensure profile is loaded for role check
        if (!authStore.user) {
            try {
                await authStore.fetchProfile()
                // Double-check user loaded
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

        // 2. Admin Guard
        if (to.matched.some(record => record.meta.requiresAdmin)) {
            if (!authStore.user?.is_superuser) {
                showToast("Access Denied: Admin only", "error")
                next({ name: 'Dashboard' }) // Kick back to user dashboard
                return
            }
        }

        next()
    } else {
        // Redirect to appropriate dashboard if logged in
        if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
            if (authStore.user?.is_superuser) {
                next({ name: 'AdminDashboard' })
            } else {
                next({ name: 'Dashboard' })
            }
        } else {
            next()
        }
    }
})

export default router
