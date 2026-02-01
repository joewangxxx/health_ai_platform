<template>
    <button type="button" role="switch" :aria-checked="modelValue" @click="$emit('update:modelValue', !modelValue)"
        :class="switchClasses" :disabled="disabled">
        <span :class="thumbClasses" />
    </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    modelValue: Boolean,
    disabled: Boolean
})

defineEmits(['update:modelValue'])

const switchClasses = computed(() => {
    const base = 'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:opacity-50 dark:focus-visible:ring-slate-300 dark:focus-visible:ring-offset-slate-950'
    const state = props.modelValue
        ? 'bg-slate-900 dark:bg-slate-50'
        : 'bg-slate-200 dark:bg-slate-800'
    return [base, state].join(' ')
})

const thumbClasses = computed(() => {
    const base = 'pointer-events-none block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform dark:bg-slate-950'
    const position = props.modelValue ? 'translate-x-4' : 'translate-x-0'
    return [base, position].join(' ')
})
</script>
