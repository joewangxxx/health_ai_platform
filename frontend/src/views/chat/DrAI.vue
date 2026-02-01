<template>
    <div class="p-6 h-full flex flex-col">
        <div class="w-full max-w-5xl mx-auto h-full flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between mb-4">
                <h1 class="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    🤖 Dr. AI 智能健康顾问 <span
                        class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">Beta</span>
                </h1>
                <el-tag type="info" effect="plain" round>Context-Aware RAG</el-tag>
            </div>

            <!-- Chat Container -->
            <GlassCard class="flex-1 flex flex-col overflow-hidden" :glow="true">

                <!-- Messages Area -->
                <el-scrollbar ref="scrollbarRef" class="flex-1 p-6" wrap-class="flex flex-col gap-6">
                    <div class="space-y-6">
                        <div v-for="(msg, index) in messages" :key="index" class="flex w-full"
                            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">

                            <!-- Avatar (AI) -->
                            <div v-if="msg.role === 'assistant'"
                                class="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs mr-3 shadow-lg shrink-0">
                                🤖
                            </div>

                            <!-- Message Bubble -->
                            <div class="max-w-[80%] flex flex-col">
                                <div class="px-5 py-3 rounded-2xl shadow-sm text-sm leading-relaxed"
                                    :class="msg.role === 'user'
                                        ? 'bg-blue-600 text-white rounded-tr-none'
                                        : 'bg-white dark:bg-white/10 text-slate-800 dark:text-gray-100 rounded-tl-none border border-gray-100 dark:border-white/5'">

                                    <!-- Markdown Content -->
                                    <div v-if="msg.role === 'assistant'" v-html="renderMarkdown(msg.content)"
                                        class="markdown-body"></div>
                                    <div v-else>{{ msg.content }}</div>
                                </div>

                                <!-- Source Citations (AI only) -->
                                <div v-if="msg.role === 'assistant' && msg.sources && msg.sources.length > 0"
                                    class="mt-2 text-xs text-slate-400 pl-2">
                                    <div class="flex flex-wrap gap-2 items-center">
                                        <span>📚 参考来源:</span>
                                        <span v-for="(source, idx) in msg.sources" :key="idx"
                                            class="bg-gray-100 dark:bg-white/5 px-2 py-0.5 rounded border border-gray-200 dark:border-white/10 truncate max-w-[200px]">
                                            {{ cleanSourceName(source) }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <!-- Avatar (User) -->
                            <div v-if="msg.role === 'user'"
                                class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs ml-3 shadow shrink-0">
                                👤
                            </div>
                        </div>

                        <!-- Typing Indicator -->
                        <div v-if="loading" class="flex w-full justify-start">
                            <div
                                class="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs mr-3 shadow-lg shrink-0">
                                🤖
                            </div>
                            <div
                                class="px-5 py-3 rounded-2xl bg-white dark:bg-white/10 rounded-tl-none border border-gray-100 dark:border-white/5 flex items-center gap-1">
                                <span class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"></span>
                                <span class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce delay-75"></span>
                                <span class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce delay-150"></span>
                            </div>
                        </div>
                    </div>
                </el-scrollbar>

                <!-- Input Area -->
                <div
                    class="p-4 border-t border-gray-100 dark:border-white/10 bg-white/50 dark:bg-black/20 backdrop-blur-sm">
                    <div class="relative flex gap-2">
                        <el-input v-model="inputMessage" type="textarea" :rows="1" autosize placeholder="输入您的健康问题..."
                            class="flex-1 custom-chat-input" @keydown.enter.prevent="sendMessage" :disabled="loading" />
                        <div class="flex flex-col justify-end">
                            <el-button type="primary" circle :loading="loading" @click="sendMessage"
                                :disabled="!inputMessage.trim()">
                                <template #icon>
                                    <el-icon>
                                        <Position />
                                    </el-icon>
                                </template>
                            </el-button>
                        </div>
                    </div>
                    <!-- Task 112: Force Refresh Checkbox -->
                    <div class="flex items-center justify-between mt-2">
                        <el-checkbox v-model="forceRefresh" size="small" class="text-xs">
                            🔄 忽略缓存，重新回答
                        </el-checkbox>
                        <span class="text-[10px] text-slate-400">Dr. AI 建议仅供参考，不作为最终诊断依据。急重症请立即就医。</span>
                    </div>
                </div>
            </GlassCard>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { Position } from '@element-plus/icons-vue'
import GlassCard from '../../components/ui/GlassCard.vue'
import axios from 'axios'
import { useAuthStore } from '../../stores/authStore'
import MarkdownIt from 'markdown-it'

const authStore = useAuthStore()
const md = new MarkdownIt({ html: false, breaks: true, linkify: true })
const scrollbarRef = ref(null)

const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const forceRefresh = ref(false)  // Task 112: Force refresh checkbox state

// Markdown Renderer
const renderMarkdown = (text) => {
    return md.render(text)
}

// Helper: Clean filename
const cleanSourceName = (sourceString) => {
    // Example: "Ref 1 - Guidelines.pdf] content..." -> "Guidelines.pdf"
    if (sourceString.includes(' - ')) {
        return sourceString.split(' - ')[1].split(']')[0]
    }
    return sourceString
}

// Scroll to bottom
const scrollToBottom = async () => {
    await nextTick()
    if (scrollbarRef.value) {
        const wrap = scrollbarRef.value.wrapRef
        wrap.scrollTop = wrap.scrollHeight
    }
}

// Send Message
const sendMessage = async (e) => {
    // Prevent shift+enter from sending
    if (e && e.shiftKey) return

    const content = inputMessage.value.trim()
    if (!content || loading.value) return

    // 1. Add User Message
    messages.value.push({
        role: 'user',
        content: content
    })
    inputMessage.value = ''
    scrollToBottom()

    // 2. Call API
    loading.value = true
    try {
        const res = await axios.post('http://127.0.0.1:8000/chat/send', {
            message: content,
            force_refresh: forceRefresh.value  // Task 112
        }, {
            headers: { Authorization: `Bearer ${authStore.token}` }
        })

        // 3. Add AI Response
        if (res.data) {
            messages.value.push({
                role: 'assistant',
                content: res.data.reply,
                sources: res.data.sources || []
            })
        }
    } catch (error) {
        messages.value.push({
            role: 'assistant',
            content: "抱歉，网络连接异常，请稍后再试。",
            sources: []
        })
    } finally {
        loading.value = false
        scrollToBottom()
    }
}

// Initial Greeting
onMounted(() => {
    messages.value.push({
        role: 'assistant',
        content: "您好，我是 Dr. AI。基于您的健康档案，我已经学习了最新的高血压、糖尿病及痛风指南。有什么可以帮您？",
        sources: []
    })
})
</script>

<style scoped>
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 5px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
    padding-left: 20px;
    list-style-type: disc;
    margin-bottom: 8px;
}

.markdown-body :deep(p) {
    margin-bottom: 8px;
}

.markdown-body :deep(strong) {
    color: #2563eb;
    /* blue-600 */
    font-weight: 700;
}

.dark .markdown-body :deep(strong) {
    color: #60a5fa;
    /* blue-400 */
}

/* Custom Input Style to match Glass Theme */
.custom-chat-input :deep(.el-textarea__inner) {
    background-color: transparent;
    box-shadow: none;
    resize: none;
    padding: 8px 0;
    font-size: 14px;
}
</style>
