<template>
    <div :class="avatarClasses">
        <img v-if="src && !imgError" :src="src" :alt="alt" class="aspect-square h-full w-full object-cover"
            @error="imgError = true" />
        <span v-else
            class="flex h-full w-full items-center justify-center rounded-full bg-linear-to-br from-blue-500 to-purple-600 text-white font-semibold">
            <slot name="fallback">{{ fallbackText }}</slot>
        </span>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
    src: String,
    alt: {
        type: String,
        default: ''
    },
    fallback: String,
    size: {
        type: String,
        default: 'default',
        validator: (v) => ['sm', 'default', 'lg'].includes(v)
    }
})

const imgError = ref(false)

const fallbackText = computed(() => {
    return props.fallback || props.alt?.charAt(0).toUpperCase() || '?'
})

const avatarClasses = computed(() => {
    const base = 'relative flex shrink-0 overflow-hidden rounded-full'
    const sizes = {
        sm: 'h-8 w-8 text-xs',
        default: 'h-10 w-10 text-sm',
        lg: 'h-14 w-14 text-lg'
    }
    return [base, sizes[props.size]].join(' ')
})
</script>
