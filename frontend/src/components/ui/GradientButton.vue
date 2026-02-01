<template>
  <button
    :class="cn(
      'gradient-button inline-flex items-center justify-center rounded-[11px] min-w-[132px] px-9 py-4 text-base leading-[19px] text-white font-sans font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 transition-all duration-300 shadow-[0_0_20px_rgba(0,0,0,0.3)] hover:scale-105 active:scale-95',
      props.class
    )"
  >
    <slot />
  </button>
</template>

<script setup>
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const props = defineProps({
  class: {
    type: String,
    default: "",
  },
});

function cn(...inputs) {
  return twMerge(clsx(inputs));
}
</script>