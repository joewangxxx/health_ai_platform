<template>
    <div class="relative inline-block" ref="popoverRef">
        <!-- Trigger -->
        <div @click="toggle" class="cursor-pointer">
            <slot name="trigger" />
        </div>

        <!-- Content -->
        <Teleport to="body">
            <Transition enter-active-class="transition ease-out duration-200" enter-from-class="opacity-0 scale-95"
                enter-to-class="opacity-100 scale-100" leave-active-class="transition ease-in duration-150"
                leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-95">
                <div v-if="isOpen" ref="contentRef" :class="contentClasses" :style="positionStyle">
                    <slot />
                </div>
            </Transition>
        </Teleport>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'

const props = defineProps({
    align: {
        type: String,
        default: 'center',
        validator: (v) => ['start', 'center', 'end'].includes(v)
    },
    side: {
        type: String,
        default: 'bottom',
        validator: (v) => ['top', 'bottom', 'left', 'right'].includes(v)
    },
    sideOffset: {
        type: Number,
        default: 8
    }
})

const isOpen = ref(false)
const popoverRef = ref(null)
const contentRef = ref(null)
const positionStyle = ref({})

const toggle = () => {
    isOpen.value = !isOpen.value
}

const close = () => {
    isOpen.value = false
}

const updatePosition = async () => {
    await nextTick()
    if (!popoverRef.value || !contentRef.value) return

    const triggerRect = popoverRef.value.getBoundingClientRect()
    const contentRect = contentRef.value.getBoundingClientRect()

    let top = 0
    let left = 0

    // Side positioning
    if (props.side === 'bottom') {
        top = triggerRect.bottom + props.sideOffset
    } else if (props.side === 'top') {
        top = triggerRect.top - contentRect.height - props.sideOffset
    }

    // Align positioning
    if (props.align === 'start') {
        left = triggerRect.left
    } else if (props.align === 'center') {
        left = triggerRect.left + (triggerRect.width / 2) - (contentRect.width / 2)
    } else if (props.align === 'end') {
        left = triggerRect.right - contentRect.width
    }

    // Keep within viewport
    if (left < 8) left = 8
    if (left + contentRect.width > window.innerWidth - 8) {
        left = window.innerWidth - contentRect.width - 8
    }

    positionStyle.value = {
        position: 'fixed',
        top: `${top}px`,
        left: `${left}px`,
        zIndex: 9999
    }
}

watch(isOpen, async (newVal) => {
    if (newVal) {
        await nextTick()
        updatePosition()
    }
})

const handleClickOutside = (e) => {
    if (popoverRef.value && !popoverRef.value.contains(e.target) &&
        contentRef.value && !contentRef.value.contains(e.target)) {
        close()
    }
}

const handleEscape = (e) => {
    if (e.key === 'Escape') close()
}

onMounted(() => {
    document.addEventListener('click', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    window.addEventListener('resize', updatePosition)
})

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
    document.removeEventListener('keydown', handleEscape)
    window.removeEventListener('resize', updatePosition)
})

const contentClasses = computed(() => {
    return 'w-72 rounded-xl border border-slate-200 bg-white p-4 shadow-lg outline-none dark:border-slate-800 dark:bg-slate-950'
})

defineExpose({ close })
</script>
