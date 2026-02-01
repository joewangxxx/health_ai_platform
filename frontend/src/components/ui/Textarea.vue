<template>
    <textarea :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" :placeholder="placeholder"
        :disabled="disabled" :rows="rows" :class="textareaClasses" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    modelValue: String,
    placeholder: String,
    disabled: Boolean,
    rows: {
        type: Number,
        default: 3
    }
})

defineEmits(['update:modelValue'])

const textareaClasses = computed(() => {
    return 'flex min-h-[60px] w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-base shadow-sm placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:border-slate-800 dark:placeholder:text-slate-400 dark:focus-visible:ring-slate-300'
})
</script>
