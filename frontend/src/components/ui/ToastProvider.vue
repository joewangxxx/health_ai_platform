<template>
    <div class="toast-provider">
        <div class="sr-only" :role="liveRole" :aria-live="livePoliteness" aria-atomic="true">
            {{ liveMessage }}
        </div>
        <!-- We render a container for each of the 5 positions -->
        <div v-for="pos in positions" :key="pos"
            aria-hidden="true"
            :class="['fixed z-9999 w-full max-w-sm px-4 sm:px-0 space-y-2 pointer-events-none', getPositionClasses(pos)]">
            <TransitionGroup name="toast-slide" tag="div" class="flex flex-col gap-2 pointer-events-auto">
                <div v-for="toast in getToastsByPosition(pos)" :key="toast.id"
                    class="transform transition-all duration-300 ease-in-out">
                    <!-- Toast Component Inline -->
                    <div
                        :class="['border rounded-lg shadow-lg p-4 flex items-center justify-between backdrop-blur-sm', getTypeClasses(toast.type)]">
                        <div class="flex items-center space-x-3">
                            <component :is="getIcon(toast.type)" class="w-5 h-5 opacity-90" />
                            <p class="font-medium text-sm">{{ toast.message }}</p>
                        </div>
                    </div>
                </div>
            </TransitionGroup>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { useToast } from '../../composables/useToast'
import {
    CircleCheck,
    Warning,
    CircleClose,
    InfoFilled
} from '@element-plus/icons-vue'

const { toasts } = useToast()

const positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'top-center']
const latestToast = computed(() => toasts.value[toasts.value.length - 1] || null)
const liveMessage = computed(() => latestToast.value?.message || '')
const liveRole = computed(() => latestToast.value?.type === 'error' ? 'alert' : 'status')
const livePoliteness = computed(() => latestToast.value?.type === 'error' ? 'assertive' : 'polite')

const getToastsByPosition = (position) => {
    // Mobile Adjustment: On small screens, force everything to bottom-center or top-center
    // But for now keeping exact logic requested
    return toasts.value.filter(t => t.position === position)
}

const getPositionClasses = (position) => {
    switch (position) {
        case 'top-left': return 'top-4 left-4 items-start'
        case 'top-right': return 'top-4 right-4 items-end'
        case 'bottom-left': return 'bottom-4 left-4 items-start'
        case 'bottom-right': return 'bottom-4 right-4 items-end'
        case 'top-center': return 'top-4 left-1/2 -translate-x-1/2 items-center'
        case 'center': return 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 items-center'
        default: return 'top-4 left-1/2 -translate-x-1/2 items-center'
    }
}

const getTypeClasses = (type) => {
    switch (type) {
        case 'success':
            return 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-300'
        case 'error':
            return 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-300'
        case 'warning':
            return 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/30 dark:border-yellow-800 dark:text-yellow-300'
        case 'info':
        default:
            return 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300'
    }
}

const getIcon = (type) => {
    switch (type) {
        case 'success': return CircleCheck
        case 'error': return CircleClose
        case 'warning': return Warning
        case 'info': return InfoFilled
        default: return InfoFilled
    }
}
</script>

<style scoped>
/* Slide & Fade Animation mimicking Framer Motion */
.toast-slide-enter-active,
.toast-slide-leave-active {
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-slide-enter-from,
.toast-slide-leave-to {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
}

/* Adjust initial direction based on position could be done with more complex CSS 
   but simplistic Y-shift is usually sufficient specifically for toasts. */
</style>
