<template>
  <div 
    ref="rootRef"
    :class="cn('glowing-effect-wrapper relative', props.class)"
    @mouseenter="handleEnter"
    @mouseleave="handleLeave"
    @mousemove="handleMove"
  >
    <!-- 发光层 -->
    <div
      ref="containerRef"
      :style="containerStyle"
      :class="cn(
        'pointer-events-none absolute inset-0 rounded-[inherit] transition-opacity duration-300',
        glow && 'opacity-100',
        !glow && 'opacity-0',
        disabled && 'hidden'
      )"
    >
      <div
        :class="cn(
          'glow-layer',
          'absolute inset-0 rounded-[inherit]',
          'after:content-[\'\'] after:absolute after:inset-[-2px] after:rounded-[inherit]',
          'after:opacity-[var(--active)] after:transition-opacity after:duration-300',
          'after:[border:var(--border-width)_solid_transparent]',
          'after:[background:var(--gradient)]',
          'after:[mask-image:conic-gradient(from_calc((var(--start)-var(--spread))*1deg)_at_50%_50%,transparent_0deg,#fff_calc(var(--spread)*2deg),transparent_calc(var(--spread)*2deg))]',
          'after:[mask-composite:intersect]',
          blur > 0 && `after:blur-[${blur}px]`
        )"
      />
    </div>
    
    <!-- 内容插槽 -->
    <div class="relative z-10 h-full w-full rounded-[inherit]">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { animate } from "motion"
import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

const props = defineProps({
  blur: { type: Number, default: 0 },
  inactiveZone: { type: Number, default: 0.7 },
  proximity: { type: Number, default: 0 },
  spread: { type: Number, default: 20 },
  variant: { type: String, default: 'default' },
  glow: { type: Boolean, default: false },
  class: { type: String, default: '' },
  movementDuration: { type: Number, default: 0.5 },
  borderWidth: { type: Number, default: 2 },
  disabled: { type: Boolean, default: false }
})

const rootRef = ref(null)
const containerRef = ref(null)
const isHovering = ref(false)
let animationFrameId = null
let currentAngle = 0

function cn(...inputs) {
  return twMerge(clsx(inputs))
}

const containerStyle = computed(() => {
  const gradient = props.variant === 'white'
    ? `repeating-conic-gradient(from 236.84deg at 50% 50%, #000, #000 calc(25% / 5))`
    : `repeating-conic-gradient(from 236.84deg at 50% 50%, 
       #dd7bbb 0deg, 
       #d79f1e calc(25% / 5), 
       #5a922c calc(50% / 5), 
       #4c7894 calc(75% / 5), 
       #dd7bbb calc(100% / 5))`

  return {
    '--spread': props.spread,
    '--start': currentAngle,
    '--active': isHovering.value ? '1' : '0',
    '--border-width': `${props.borderWidth}px`,
    '--gradient': gradient
  }
})

const handleEnter = () => {
  if (props.disabled) return
  isHovering.value = true
  if (containerRef.value) {
    containerRef.value.style.setProperty('--active', '1')
  }
}

const handleLeave = () => {
  if (props.disabled) return
  isHovering.value = false
  if (containerRef.value) {
    containerRef.value.style.setProperty('--active', '0')
  }
}

const handleMove = (e) => {
  if (!containerRef.value || props.disabled || !isHovering.value) return

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }

  animationFrameId = requestAnimationFrame(() => {
    const element = containerRef.value
    if (!element || !rootRef.value) return

    const rect = rootRef.value.getBoundingClientRect()
    const mouseX = e.clientX
    const mouseY = e.clientY

    const centerX = rect.left + rect.width * 0.5
    const centerY = rect.top + rect.height * 0.5

    // 计算鼠标相对于卡片中心的角度
    const dx = mouseX - centerX
    const dy = mouseY - centerY
    const angle = (Math.atan2(dy, dx) * 180) / Math.PI + 90

    // 计算距离中心的距离
    const distanceFromCenter = Math.hypot(dx, dy)
    const inactiveRadius = 0.5 * Math.min(rect.width, rect.height) * props.inactiveZone

    if (distanceFromCenter < inactiveRadius) {
      element.style.setProperty('--active', '0')
      return
    }

    // 确保角度在 0-360 范围内
    let normalizedAngle = ((angle % 360) + 360) % 360

    // 平滑动画到目标角度
    const angleDiff = ((normalizedAngle - currentAngle + 180) % 360) - 180
    const targetAngle = currentAngle + angleDiff

    animate(currentAngle, targetAngle, {
      duration: props.movementDuration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (value) => {
        currentAngle = value
        if (element) {
          element.style.setProperty('--start', String(value))
        }
      }
    })
  })
}

onMounted(() => {
  if (props.disabled) return
  // 初始化角度
  if (containerRef.value) {
    containerRef.value.style.setProperty('--start', '0')
    containerRef.value.style.setProperty('--active', '0')
  }
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<style scoped>
.glowing-effect-wrapper {
  overflow: visible !important;
}

.glow-layer {
  z-index: 0;
  pointer-events: none;
}

.glow-layer::after {
  z-index: 0;
  pointer-events: none;
}

/* 确保发光效果不被裁剪 */
:deep(.glowing-effect-wrapper) {
  overflow: visible !important;
}
</style>