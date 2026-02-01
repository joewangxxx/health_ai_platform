<template>
    <div :class="cn('relative group rounded-3xl overflow-visible', props.class)">
        <GlowingEffect class="rounded-3xl h-full" :blur="10" :spread="glowSpread" :glow="true" :disabled="false"
            :proximity="glowProximity" :inactiveZone="0.01" :borderWidth="2">
            <div
                class="glass-content relative z-10 h-full w-full rounded-3xl bg-white/60 dark:bg-zinc-900/60 p-5 shadow-lg backdrop-blur-md border border-white/40 dark:border-white/10 transition-all duration-300 flex flex-col">
                <!-- Header Slot -->
                <div v-if="$slots.header" class="mb-4">
                    <slot name="header" />
                </div>

                <!-- Default Content Slot -->
                <slot />
            </div>
        </GlowingEffect>
    </div>
</template>

<script setup>
import GlowingEffect from './GlowingEffect.vue'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

const props = defineProps({
    class: { type: String, default: '' },
    glowSpread: { type: Number, default: 30 },
    glowProximity: { type: Number, default: 80 }
})

function cn(...inputs) {
    return twMerge(clsx(inputs))
}
</script>

<style scoped>
/* Ensure content flex column works for extending height */
.glass-content {
    flex: 1;
}
</style>
