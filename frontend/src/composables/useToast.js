import { ref } from 'vue'

const toasts = ref([])

/**
 * Remove a toast by id
 */
export const removeToast = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
        toasts.value.splice(index, 1)
    }
}

/**
 * Show a toast notification (Global Function)
 * @param {string} message - Content of the message
 * @param {string} type - 'success' | 'error' | 'warning' | 'info'
 * @param {string} position - 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center'
 */
export const showToast = (message, type = 'info', position = 'top-center') => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9)
    toasts.value.push({
        id,
        message,
        type,
        position
    })

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        removeToast(id)
    }, 5000)
}

/**
 * Global composable to manage toast notifications.
 * State is shared across the application.
 */
export function useToast() {
    return {
        toasts,
        showToast,
        removeToast
    }
}

export const toast = {
    show: showToast,
    success: (msg, pos) => showToast(msg, 'success', pos),
    error: (msg, pos) => showToast(msg, 'error', pos),
    warning: (msg, pos) => showToast(msg, 'warning', pos),
    info: (msg, pos) => showToast(msg, 'info', pos),
}
