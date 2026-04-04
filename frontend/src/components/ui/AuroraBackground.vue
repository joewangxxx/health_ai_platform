<template>
  <div
    :class="cn(
      'relative flex flex-col min-h-screen w-full items-center justify-center text-slate-950 transition-colors duration-500 overflow-x-hidden bg-zinc-50',
      props.class
    )"
  >
    <!-- Aurora Layer - Light Mode Only -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div
        :class="cn(
          `
          /* 极光层 - 亮色模式 */
          [--white-gradient:repeating-linear-gradient(100deg,var(--color-white)_0%,var(--color-white)_7%,transparent_10%,transparent_12%,var(--color-white)_16%)]
          [--aurora:repeating-linear-gradient(100deg,var(--color-blue-500)_10%,var(--color-indigo-300)_15%,var(--color-blue-300)_20%,var(--color-violet-200)_25%,var(--color-blue-400)_30%)]
          
          [background-image:var(--white-gradient),var(--aurora)]
          
          bg-size-[300%,200%]
          bg-position-[50%_50%,50%_50%]
          filter blur-[10px] invert
          
          after:content-[''] after:absolute after:inset-0 
          after:[background-image:var(--white-gradient),var(--aurora)] 
          after:bg-size-[200%,100%] 
          animate-aurora-custom after:bg-fixed after:mix-blend-difference
          
          pointer-events-none
          absolute -inset-[10px] opacity-50 will-change-transform`,
          showRadialGradient &&
            `mask-[radial-gradient(ellipse_at_100%_0%,black_10%,transparent_70%)]`
        )"
      ></div>
    </div>
    
    <!-- Content Layer -->
    <div class="relative z-10 w-full min-h-screen">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const props = defineProps({
  class: { type: String, default: "" },
  showRadialGradient: { type: Boolean, default: true },
});

function cn(...inputs) {
  return twMerge(clsx(inputs));
}
</script>
