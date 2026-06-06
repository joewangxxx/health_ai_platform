<template>
    <div class="glass-button-wrap" :class="sizeClasses.wrap">
        <button type="button" class="glass-button group" :class="[sizeClasses.button, contentClass]" :disabled="disabled"
            @click="$emit('click', $event)">
            <span class="glass-button-text">
                <slot />
            </span>
        </button>
        <div class="glass-button-shadow" :class="sizeClasses.shadow"></div>
    </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    size: {
        type: String,
        default: 'default',
        validator: (v) => ['default', 'sm', 'lg', 'icon'].includes(v)
    },
    contentClass: {
        type: String,
        default: ''
    },
    disabled: {
        type: Boolean,
        default: false
    }
})

defineEmits(['click'])

// 中文注释：该步骤用于衔接当前状态流，需与接口返回结构保持一致。
const sizeClasses = computed(() => {
    const variants = {
        default: {
            wrap: '',
            button: 'h-11 px-6 text-sm',
            shadow: ''
        },
        sm: {
            wrap: '',
            button: 'h-9 px-4 text-xs',
            shadow: 'blur-sm'
        },
        lg: {
            wrap: '',
            button: 'h-14 px-10 text-base',
            shadow: 'blur-lg'
        },
        icon: {
            wrap: '',
            button: 'h-10 w-10 p-0',
            shadow: ''
        }
    }
    return variants[props.size] || variants.default
})
</script>

<style scoped>
/* 按钮外层容器 */
.glass-button-wrap {
    position: relative;
    display: inline-flex;
}

/* 主按钮样式 */
.glass-button {
    position: relative;
    z-index: 10;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    border-radius: 9999px;
    font-weight: 600;
    letter-spacing: 0.025em;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    /* 玻璃质感底层 */
    background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.25) 0%,
            rgba(255, 255, 255, 0.1) 100%);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);

    /* 边框高光 */
    border: 1px solid rgba(255, 255, 255, 0.4);
    box-shadow:
        inset 0 1px 1px rgba(255, 255, 255, 0.4),
        0 4px 16px -2px rgba(0, 0, 0, 0.1),
        0 2px 4px -1px rgba(0, 0, 0, 0.06);

    /* 文本颜色 */
    color: #1e293b;
}

/* 深色模式 */
:global(.dark) .glass-button {
    background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.12) 0%,
            rgba(255, 255, 255, 0.05) 100%);
    border-color: rgba(255, 255, 255, 0.2);
    color: #f8fafc;
    box-shadow:
        inset 0 1px 1px rgba(255, 255, 255, 0.15),
        0 4px 20px -2px rgba(0, 0, 0, 0.4),
        0 2px 8px -1px rgba(0, 0, 0, 0.3);
}

/* 悬浮状态 */
.glass-button:hover:not(:disabled) {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.6);
    box-shadow:
        inset 0 1px 2px rgba(255, 255, 255, 0.5),
        0 8px 24px -4px rgba(59, 130, 246, 0.3),
        0 4px 8px -2px rgba(0, 0, 0, 0.1),
        0 0 20px rgba(59, 130, 246, 0.2);
    background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.35) 0%,
            rgba(255, 255, 255, 0.15) 100%);
}

:global(.dark) .glass-button:hover:not(:disabled) {
    box-shadow:
        inset 0 1px 2px rgba(255, 255, 255, 0.2),
        0 8px 32px -4px rgba(99, 102, 241, 0.4),
        0 4px 12px -2px rgba(0, 0, 0, 0.4),
        0 0 30px rgba(99, 102, 241, 0.25);
    background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.2) 0%,
            rgba(255, 255, 255, 0.08) 100%);
}

/* 激活/按压状态 */
.glass-button:active:not(:disabled) {
    transform: translateY(0);
    box-shadow:
        inset 0 2px 4px rgba(0, 0, 0, 0.1),
        0 2px 8px -2px rgba(0, 0, 0, 0.1);
}

/* 禁用状态 */
.glass-button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
}

/* 文本层 */
.glass-button-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
    z-index: 10;
}

/* 阴影光晕层 */
.glass-button-shadow {
    position: absolute;
    inset: 0;
    border-radius: 9999px;
    background: linear-gradient(135deg,
            rgba(59, 130, 246, 0.4) 0%,
            rgba(139, 92, 246, 0.4) 100%);
    filter: blur(12px);
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: 0;
}

.glass-button-wrap:hover .glass-button-shadow {
    opacity: 0.6;
}

:global(.dark) .glass-button-shadow {
    background: linear-gradient(135deg,
            rgba(99, 102, 241, 0.5) 0%,
            rgba(168, 85, 247, 0.5) 100%);
}

:global(.dark) .glass-button-wrap:hover .glass-button-shadow {
    opacity: 0.7;
}
</style>
