<template>
    <div :class="separatorClasses" role="separator" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    orientation: {
        type: String,
        default: 'horizontal',
        validator: (v) => ['horizontal', 'vertical'].includes(v)
    }
})

const separatorClasses = computed(() => {
    const base = 'shrink-0 bg-slate-200 dark:bg-slate-800'
    const orientation = props.orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]'
    return [base, orientation].join(' ')
})
</script>
