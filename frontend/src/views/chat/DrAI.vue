<template>
    <div class="p-6 h-full">
        <div class="w-full max-w-6xl mx-auto h-full flex flex-col lg:flex-row gap-4">
            <GlassCard class="w-full lg:w-80 shrink-0 overflow-hidden" :glow="true">
                <div class="p-4 border-b border-gray-100 dark:border-white/10 flex items-center justify-between">
                    <div>
                        <h2 class="text-base font-semibold text-slate-800 dark:text-white">历史会话</h2>
                        <p class="text-xs text-slate-400 mt-1">切换上下文，继续之前的健康咨询。</p>
                    </div>
                    <el-button size="small" type="primary" plain data-testid="new-conversation-button" @click="startNewConversation" :disabled="loading">
                        新会话
                    </el-button>
                </div>

                <el-scrollbar class="h-[220px] lg:h-[calc(100%-73px)]">
                    <div class="p-3 space-y-2">
                        <el-input
                            v-model="conversationSearch"
                            size="small"
                            clearable
                            placeholder="搜索历史会话"
                        />

                        <div class="grid grid-cols-2 gap-2">
                                <el-button
                                    size="small"
                                    data-testid="active-conversations-tab"
                                    :type="showArchived ? 'default' : 'primary'"
                                    plain
                                    @click="showArchived = false"
                                >
                                活跃会话
                            </el-button>
                            <el-button
                                size="small"
                                data-testid="archived-conversations-tab"
                                :type="showArchived ? 'primary' : 'default'"
                                plain
                                @click="showArchived = true"
                            >
                                已归档
                            </el-button>
                        </div>
                        <div
                            v-if="showArchived"
                            class="rounded-xl border border-sky-200 bg-sky-50/80 px-3 py-3 text-xs text-slate-600 dark:border-sky-400/20 dark:bg-sky-500/10 dark:text-slate-200"
                        >
                            <div class="flex items-center justify-between gap-3">
                                <div class="flex min-w-0 items-center gap-3">
                                    <el-checkbox
                                        data-testid="select-all-archived-conversations"
                                        v-model="selectVisibleArchivedConversations"
                                        :disabled="visibleArchivedConversationIds.length === 0 || batchRestoreLoading"
                                        @click.stop
                                    >
                                        全选当前归档列表
                                    </el-checkbox>
                                    <span class="truncate">已选 {{ selectedArchivedConversationIds.length }} 个已归档会话</span>
                                </div>
                                <el-button
                                    size="small"
                                    type="primary"
                                    plain
                                    data-testid="batch-restore-button"
                                    :loading="batchRestoreLoading"
                                    :disabled="selectedArchivedConversationIds.length === 0 || loading"
                                    @click="restoreSelectedConversations"
                                >
                                    批量恢复
                                </el-button>
                            </div>
                            <div v-if="batchRestorePreview" class="mt-2 leading-5 text-[11px] text-slate-500 dark:text-slate-300">
                                <span>准备结果：</span>
                                <span>可恢复 {{ batchRestorePreview.restorable_count }}</span>
                                <span v-if="batchRestorePreview.already_active_conversation_ids?.length">
                                    ，已激活 {{ batchRestorePreview.already_active_conversation_ids.length }}
                                </span>
                                <span v-if="batchRestorePreview.missing_conversation_ids?.length">
                                    ，缺失 {{ batchRestorePreview.missing_conversation_ids.length }}
                                </span>
                                <span v-if="batchRestorePreview.duplicate_conversation_ids?.length">
                                    ，重复 {{ batchRestorePreview.duplicate_conversation_ids.length }}
                                </span>
                            </div>
                        </div>

                        <div
                            v-if="!showArchived"
                            class="rounded-xl border border-amber-200 bg-amber-50/80 px-3 py-3 text-xs text-slate-600 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-slate-200"
                        >
                            <div class="flex items-center justify-between gap-3">
                                <div class="flex min-w-0 items-center gap-3">
                                    <el-checkbox
                                        data-testid="select-all-active-conversations"
                                        v-model="selectVisibleActiveConversations"
                                        :disabled="visibleActiveConversationIds.length === 0 || batchArchiveLoading"
                                        @click.stop
                                    >
                                        全选当前列表
                                    </el-checkbox>
                                    <span class="truncate">已选 {{ selectedConversationIds.length }} 个活动会话</span>
                                </div>
                                <el-button
                                    size="small"
                                    type="warning"
                                    plain
                                    data-testid="batch-archive-button"
                                    :loading="batchArchiveLoading"
                                    :disabled="selectedConversationIds.length === 0 || loading"
                                    @click="archiveSelectedConversations"
                                >
                                    批量归档
                                </el-button>
                            </div>
                            <div v-if="batchArchivePreview" class="mt-2 leading-5 text-[11px] text-slate-500 dark:text-slate-300">
                                <span>准备结果：</span>
                                <span>可归档 {{ batchArchivePreview.archiveable_count }}</span>
                                <span v-if="batchArchivePreview.already_archived_conversation_ids?.length">
                                    ，已归档 {{ batchArchivePreview.already_archived_conversation_ids.length }}
                                </span>
                                <span v-if="batchArchivePreview.missing_conversation_ids?.length">
                                    ，缺失 {{ batchArchivePreview.missing_conversation_ids.length }}
                                </span>
                                <span v-if="batchArchivePreview.duplicate_conversation_ids?.length">
                                    ，重复 {{ batchArchivePreview.duplicate_conversation_ids.length }}
                                </span>
                            </div>
                        </div>

                        <div
                            class="w-full text-left rounded-xl border px-3 py-3 transition"
                            :class="
                                !conversationId
                                    ? 'border-blue-200 bg-blue-50/80 dark:border-blue-400/30 dark:bg-blue-500/10'
                                    : 'border-gray-200 bg-white/60 hover:border-blue-200 hover:bg-blue-50/40 dark:border-white/10 dark:bg-white/5 dark:hover:border-blue-400/20'
                            "
                            @click="startNewConversation"
                            :disabled="loading"
                        >
                            <div class="text-sm font-medium text-slate-800 dark:text-slate-100">新的健康咨询</div>
                            <div class="text-xs text-slate-400 mt-1 line-clamp-2">
                                开始新的上下文，不继承历史问答。
                            </div>
                        </div>

                        <template v-if="groupedConversationSections.length > 0">
                            <div v-for="section in groupedConversationSections" :key="section.key" class="space-y-2">
                                <div class="px-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                                    {{ section.label }}
                                </div>

                                <div
                                    v-for="item in section.items"
                                    :key="item.conversation_id"
                                    class="rounded-xl border px-3 py-3 transition"
                                    :data-testid="`conversation-card-${item.conversation_id}`"
                                    :class="getConversationCardClass(item, showArchived ? selectedArchivedConversationIds : selectedConversationIds)"
                                >
                                    <div class="flex items-start justify-between gap-3">
                                        <div class="flex min-w-0 flex-1 items-start gap-2">
                                            <el-checkbox
                                                v-if="!showArchived && !item.archived"
                                                v-model="selectedConversationIds"
                                                :value="item.conversation_id"
                                                :disabled="batchArchiveLoading || loading"
                                                class="mt-1 shrink-0"
                                                @click.stop
                                            />
                                            <el-checkbox
                                                v-else-if="showArchived && item.archived"
                                                v-model="selectedArchivedConversationIds"
                                                :value="item.conversation_id"
                                                :disabled="batchRestoreLoading || loading"
                                                class="mt-1 shrink-0"
                                                @click.stop
                                            />
                                            <div class="min-w-0 flex-1" @click="selectConversation(item)">
                                            <div
                                                v-if="activeRenameConversationId === item.conversation_id"
                                                class="space-y-2"
                                                :data-testid="`conversation-rename-editor-${item.conversation_id}`"
                                                @click.stop
                                            >
                                                <el-input
                                                    v-model="renameDraft"
                                                    size="small"
                                                    data-testid="conversation-rename-input"
                                                    placeholder="请输入会话标题"
                                                    @keydown.enter.prevent="renameConversation(item)"
                                                    @keydown.esc.prevent="cancelRenameConversation"
                                                />
                                                <div class="flex flex-wrap items-center gap-2">
                                                    <el-button
                                                        size="small"
                                                        type="primary"
                                                        data-testid="conversation-rename-save"
                                                        :disabled="loading || !renameDraft.trim()"
                                                        @click.stop="renameConversation(item)"
                                                    >
                                                        保存
                                                    </el-button>
                                                    <el-button size="small" text :disabled="loading" @click.stop="cancelRenameConversation">
                                                        取消
                                                    </el-button>
                                                </div>
                                            </div>
                                            <template v-else>
                                                <div class="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                                                    {{ item.title || '未命名会话' }}
                                                </div>
                                                <div class="text-xs text-slate-400 mt-1 line-clamp-2">
                                                    {{ item.preview || '暂无消息预览' }}
                                                </div>
                                                <div v-if="item.archived || item.pinned" class="mt-2 flex flex-wrap gap-2">
                                                    <el-tag v-if="item.pinned" size="small" type="warning" effect="plain">已置顶</el-tag>
                                                    <el-tag v-if="item.archived" size="small" type="info" effect="plain">已归档</el-tag>
                                                </div>
                                            </template>
                                            </div>
                                        </div>
                                        <div class="flex flex-col items-end gap-2 shrink-0">
                                            <span class="text-[10px] text-slate-400">
                                                {{ formatConversationTime(item.updated_at) }}
                                            </span>
                                            <el-button
                                                size="small"
                                                text
                                                :data-testid="`conversation-pin-trigger-${item.conversation_id}`"
                                                :disabled="loading"
                                                @click.stop="toggleConversationPin(item)"
                                            >
                                                {{ item.pinned ? '取消置顶' : '置顶' }}
                                            </el-button>
                                            <el-button
                                                size="small"
                                                text
                                                :disabled="loading"
                                                @click.stop="toggleConversationArchive(item)"
                                            >
                                                {{ item.archived ? '恢复' : '归档' }}
                                            </el-button>
                                            <el-button
                                                size="small"
                                                text
                                                :data-testid="`conversation-rename-trigger-${item.conversation_id}`"
                                                :disabled="loading || activeRenameConversationId === item.conversation_id"
                                                @click.stop="startRenameConversation(item)"
                                            >
                                                重命名
                                            </el-button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </template>

                        <div
                            v-if="conversations.length === 0"
                            class="rounded-xl border border-dashed border-gray-200 dark:border-white/10 px-3 py-6 text-center text-xs text-slate-400"
                        >
                            {{ showArchived ? '暂无已归档会话。' : '暂无历史会话，发送第一条消息后会自动生成会话记录。' }}
                        </div>
                    </div>
                </el-scrollbar>
            </GlassCard>

            <div class="flex-1 min-w-0 flex flex-col">
                <div class="flex items-center justify-between mb-4">
                    <h1 class="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        Dr. AI 智能健康顾问
                        <span class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">Beta</span>
                    </h1>
                    <div class="flex items-center gap-2">
                        <el-tag v-if="conversationId" type="success" effect="plain" round data-testid="current-conversation-badge">
                            会话 #{{ conversationId }}
                        </el-tag>
                        <el-tag type="info" effect="plain" round>Controlled Agent + SSE</el-tag>
                    </div>
                </div>

                <GlassCard class="flex-1 flex flex-col overflow-hidden" :glow="true">
                    <el-scrollbar ref="scrollbarRef" class="flex-1 p-6" wrap-class="flex flex-col gap-6">
                        <div class="space-y-6">
                            <div
                                v-for="(msg, index) in messages"
                                :key="`${msg.role}-${index}-${msg.sequence || 'live'}`"
                                class="flex w-full"
                                :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
                                :data-testid="msg.role === 'assistant' ? 'assistant-message' : 'user-message'"
                            >
                                <div
                                    v-if="msg.role === 'assistant'"
                                    class="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs mr-3 shadow-lg shrink-0"
                                >
                                    AI
                                </div>

                                <div class="max-w-[85%] flex flex-col">
                                    <div
                                        class="px-5 py-3 rounded-2xl shadow-sm text-sm leading-relaxed"
                                        :class="
                                            msg.role === 'user'
                                                ? 'bg-blue-600 text-white rounded-tr-none'
                                                : 'bg-white dark:bg-white/10 text-slate-800 dark:text-gray-100 rounded-tl-none border border-gray-100 dark:border-white/5'
                                        "
                                    >
                                        <div v-if="msg.role === 'assistant'" v-html="renderMarkdown(msg.content)" class="markdown-body"></div>
                                        <div v-else>{{ msg.content }}</div>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && msg.processStages && msg.processStages.length > 0"
                                        class="mt-2 text-xs text-slate-500 pl-2"
                                    >
                                        <div class="flex flex-wrap gap-2 items-center">
                                            <span>处理过程</span>
                                            <span
                                                v-for="(stage, idx) in msg.processStages"
                                                :key="`stage-${idx}`"
                                                class="bg-slate-100 text-slate-700 dark:bg-slate-500/10 dark:text-slate-200 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-400/20"
                                            >
                                                {{ stage.message }}
                                            </span>
                                        </div>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && msg.evidenceTags && msg.evidenceTags.length > 0"
                                        class="mt-2 text-xs text-slate-500 pl-2"
                                    >
                                        <div class="flex flex-wrap gap-2 items-center">
                                            <span>已参考</span>
                                            <span
                                                v-for="(tag, idx) in msg.evidenceTags"
                                                :key="`tag-${idx}`"
                                                class="bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-200 px-2 py-0.5 rounded border border-blue-100 dark:border-blue-400/20"
                                            >
                                                {{ formatEvidenceTag(tag) }}
                                            </span>
                                        </div>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && hasAnswerExplanation(msg)"
                                        class="mt-3 rounded-2xl border border-indigo-100 bg-indigo-50/70 px-4 py-4 text-sm text-slate-700 shadow-sm dark:border-indigo-400/20 dark:bg-indigo-500/10 dark:text-slate-100"
                                        data-testid="answer-explanation-card"
                                    >
                                        <div class="flex items-start justify-between gap-3">
                                            <div>
                                                <div class="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-700 dark:text-indigo-200">
                                                    为什么这样回答
                                                </div>
                                                <div class="mt-2 flex flex-wrap gap-2 text-[11px]">
                                                    <span class="rounded-full border border-indigo-200 bg-white/80 px-2.5 py-1 text-indigo-800 dark:border-indigo-400/30 dark:bg-white/5 dark:text-indigo-100" data-testid="answer-explanation-lane">
                                                        路由：{{ msg.decisionSummary?.lane || '未提供' }}
                                                    </span>
                                                    <span class="rounded-full border border-indigo-200 bg-white/80 px-2.5 py-1 text-indigo-800 dark:border-indigo-400/30 dark:bg-white/5 dark:text-indigo-100" data-testid="answer-explanation-verdict">
                                                        结果：{{ msg.decisionSummary?.verdict || '未提供' }}
                                                    </span>
                                                </div>
                                            </div>
                                            <el-tag size="small" type="info" effect="plain" data-testid="answer-explanation-policy-version">
                                                {{ msg.decisionSummary?.policy?.policy_version || msg.responseVerdict?.schema_version || '未提供' }}
                                            </el-tag>
                                        </div>

                                        <div class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                                            <div class="rounded-xl border border-white/60 bg-white/80 px-3 py-3 dark:border-white/10 dark:bg-white/5">
                                                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-300">
                                                    回答模式
                                                </div>
                                                <div class="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100" data-testid="answer-explanation-response-mode">
                                                    {{ formatResponseMode(msg) }}
                                                </div>
                                            </div>
                                            <div class="rounded-xl border border-white/60 bg-white/80 px-3 py-3 dark:border-white/10 dark:bg-white/5">
                                                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-300">
                                                    风险级别
                                                </div>
                                                <div class="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100" data-testid="answer-explanation-risk-level">
                                                    {{ formatMedicalRiskLevel(msg) }}
                                                </div>
                                            </div>
                                            <div class="rounded-xl border border-white/60 bg-white/80 px-3 py-3 dark:border-white/10 dark:bg-white/5">
                                                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-300">
                                                    证据充分性
                                                </div>
                                                <div class="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100" data-testid="answer-explanation-evidence-sufficiency">
                                                    {{ formatEvidenceSufficiency(msg) }}
                                                </div>
                                            </div>
                                            <div class="rounded-xl border border-white/60 bg-white/80 px-3 py-3 dark:border-white/10 dark:bg-white/5">
                                                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-300">
                                                    是否触发降级
                                                </div>
                                                <div class="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100" data-testid="answer-explanation-degrade-state">
                                                    {{ formatDegradeState(msg) }}
                                                </div>
                                            </div>
                                            <div class="rounded-xl border border-white/60 bg-white/80 px-3 py-3 dark:border-white/10 dark:bg-white/5">
                                                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-300">
                                                    是否建议人工/线下就医
                                                </div>
                                                <div class="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100" data-testid="answer-explanation-human-escalation">
                                                    {{ formatHumanEscalation(msg) }}
                                                </div>
                                            </div>
                                            <div class="rounded-xl border border-white/60 bg-white/80 px-3 py-3 dark:border-white/10 dark:bg-white/5">
                                                <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-300">
                                                    免责声明模式
                                                </div>
                                                <div class="mt-1 text-sm font-medium text-slate-800 dark:text-slate-100" data-testid="answer-explanation-disclaimer-mode">
                                                    {{ formatDisclaimerMode(msg) }}
                                                </div>
                                            </div>
                                        </div>

                                        <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-300">
                                            <span class="rounded-full border border-slate-200 bg-white/80 px-2.5 py-1 dark:border-white/10 dark:bg-white/5" data-testid="answer-explanation-selected-rule">
                                                选择规则：{{ msg.decisionSummary?.policy?.selected_rule || '未提供' }}
                                            </span>
                                            <span class="rounded-full border border-slate-200 bg-white/80 px-2.5 py-1 dark:border-white/10 dark:bg-white/5">
                                                工具可用性：{{ msg.decisionSummary?.policy?.tool_availability || '未提供' }}
                                            </span>
                                        </div>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && hasTakeover(msg)"
                                        class="mt-3 rounded-2xl border px-4 py-4 text-sm shadow-sm"
                                        :class="
                                            isTakeoverRequired(msg)
                                                ? 'border-rose-200 bg-rose-50/80 text-rose-900 dark:border-rose-400/20 dark:bg-rose-500/10 dark:text-rose-50'
                                                : 'border-slate-200 bg-slate-50/80 text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-100'
                                        "
                                        data-testid="takeover-card"
                                    >
                                        <div class="flex items-start justify-between gap-3">
                                            <div>
                                                <div
                                                    class="text-xs font-semibold uppercase tracking-[0.2em]"
                                                    :class="isTakeoverRequired(msg) ? 'text-rose-700 dark:text-rose-200' : 'text-slate-500 dark:text-slate-300'"
                                                >
                                                    人工接管
                                                </div>
                                                <div class="mt-2 flex flex-wrap gap-2 text-[11px]">
                                                    <span
                                                        class="rounded-full border px-2.5 py-1"
                                                        :class="
                                                            isTakeoverRequired(msg)
                                                                ? 'border-rose-200 bg-white/80 text-rose-800 dark:border-rose-400/30 dark:bg-white/5 dark:text-rose-100'
                                                                : 'border-slate-200 bg-white/80 text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200'
                                                        "
                                                        data-testid="takeover-status"
                                                    >
                                                        状态：{{ formatTakeoverStatus(msg) }}
                                                    </span>
                                                    <span
                                                        class="rounded-full border px-2.5 py-1"
                                                        :class="
                                                            isTakeoverRequired(msg)
                                                                ? 'border-rose-200 bg-white/80 text-rose-800 dark:border-rose-400/30 dark:bg-white/5 dark:text-rose-100'
                                                                : 'border-slate-200 bg-white/80 text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200'
                                                        "
                                                        data-testid="takeover-trigger-reason"
                                                    >
                                                        触发原因：{{ formatTakeoverTriggerReason(msg) }}
                                                    </span>
                                                </div>
                                            </div>
                                            <el-tag
                                                size="small"
                                                :type="isTakeoverRequired(msg) ? 'danger' : 'info'"
                                                effect="plain"
                                                data-testid="takeover-status-tag"
                                            >
                                                {{ isTakeoverRequired(msg) ? '需要接管' : '已评估' }}
                                            </el-tag>
                                        </div>

                                        <div
                                            class="mt-4 rounded-xl border px-3 py-3 text-sm leading-6"
                                            :class="
                                                isTakeoverRequired(msg)
                                                    ? 'border-rose-100 bg-white/85 dark:border-rose-400/20 dark:bg-white/5'
                                                    : 'border-slate-200 bg-white/85 dark:border-white/10 dark:bg-white/5'
                                            "
                                        >
                                            <div
                                                class="text-[10px] font-semibold uppercase tracking-[0.18em]"
                                                :class="isTakeoverRequired(msg) ? 'text-rose-600 dark:text-rose-200' : 'text-slate-400 dark:text-slate-300'"
                                            >
                                                后端接管说明
                                            </div>
                                            <div class="mt-1 whitespace-pre-line" data-testid="takeover-summary">
                                                {{ msg.takeover.summary || '未提供' }}
                                            </div>
                                        </div>

                                        <div
                                            v-if="isTakeoverRequired(msg)"
                                            class="mt-3 text-xs leading-5 text-rose-700 dark:text-rose-200"
                                            data-testid="takeover-next-step"
                                        >
                                            系统已停止继续生成医学建议，请等待人工接入，或按上方说明补充/落实下一步处理。
                                        </div>
                                        <div
                                            v-else
                                            class="mt-3 text-xs leading-5 text-slate-600 dark:text-slate-300"
                                            data-testid="takeover-suppressed-note"
                                        >
                                            当前 turn 已评估接管边界，但未触发人工接管。页面仅展示后端给出的接管评估结果。
                                        </div>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && msg.evidencePanel"
                                        class="mt-3 pl-2"
                                    >
                                        <div
                                            v-if="msg.evidencePanel.chips && msg.evidencePanel.chips.length > 0"
                                            class="flex flex-wrap gap-2"
                                        >
                                            <button
                                                v-for="(chip, chipIndex) in msg.evidencePanel.chips"
                                                :key="`evidence-chip-${chip.key || chip.label}-${chipIndex}`"
                                                type="button"
                                                class="rounded-full border px-3 py-1 text-[11px] font-medium transition"
                                                :class="
                                                    isEvidencePanelChipActive(msg, chip, chipIndex)
                                                        ? 'border-cyan-300 bg-cyan-50 text-cyan-800 dark:border-cyan-300/40 dark:bg-cyan-500/10 dark:text-cyan-100'
                                                        : 'border-slate-200 bg-slate-50 text-slate-600 hover:border-cyan-200 hover:text-cyan-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-cyan-300/30'
                                                "
                                                :data-testid="`evidence-chip-${chip.key || chip.label}`"
                                                @click="toggleEvidencePanelSection(msg, chip, chipIndex)"
                                            >
                                                {{ chip.label }}
                                            </button>
                                        </div>

                                        <template
                                            v-for="section in msg.evidencePanel.sections"
                                            :key="`evidence-section-${section.label}`"
                                        >
                                            <div
                                                v-if="msg.activeEvidencePanelKey === section.label"
                                                class="mt-3 rounded-2xl border border-cyan-100 bg-cyan-50/70 px-4 py-4 text-sm text-slate-700 shadow-sm dark:border-cyan-400/20 dark:bg-cyan-500/10 dark:text-slate-100"
                                                data-testid="evidence-panel-detail"
                                            >
                                                <div class="flex items-start justify-between gap-3">
                                                    <div>
                                                        <div class="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700 dark:text-cyan-200">
                                                            {{ section.label }}
                                                        </div>
                                                        <div class="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-100">
                                                            {{ section.summary }}
                                                        </div>
                                                    </div>
                                                    <el-button
                                                        size="small"
                                                        text
                                                        data-testid="evidence-panel-close"
                                                        @click="msg.activeEvidencePanelKey = null"
                                                    >
                                                        Close
                                                    </el-button>
                                                </div>

                                                <div
                                                    v-if="section.key_facts && section.key_facts.length > 0"
                                                    class="mt-4"
                                                >
                                                    <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">
                                                        Key Facts
                                                    </div>
                                                    <ul class="mt-2 space-y-1 text-xs leading-5 text-slate-600 dark:text-slate-200 list-disc pl-4">
                                                        <li v-for="(fact, factIndex) in section.key_facts" :key="`fact-${factIndex}`">
                                                            {{ fact }}
                                                        </li>
                                                    </ul>
                                                </div>

                                                <div class="mt-4">
                                                    <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">
                                                        Decision Basis
                                                    </div>
                                                    <div class="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-200">
                                                        {{ section.decision_basis }}
                                                    </div>
                                                </div>

                                                <div
                                                    v-if="section.source_refs && section.source_refs.length > 0"
                                                    class="mt-4"
                                                >
                                                    <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">
                                                        Source Refs
                                                    </div>
                                                    <div class="mt-2 flex flex-wrap gap-2">
                                                        <span
                                                            v-for="(sourceRef, sourceRefIndex) in section.source_refs"
                                                            :key="`source-ref-${sourceRefIndex}`"
                                                            class="rounded-full border border-slate-200 bg-white/80 px-2.5 py-1 text-[11px] text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
                                                        >
                                                            {{ sourceRef }}
                                                        </span>
                                                    </div>
                                                </div>

                                                <div
                                                    v-if="section.source_items && section.source_items.length > 0"
                                                    class="mt-4"
                                                    data-testid="evidence-panel-source-items"
                                                >
                                                    <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-300">
                                                        Source Items
                                                    </div>
                                                    <div class="mt-2 space-y-2">
                                                        <div
                                                            v-for="(sourceItem, sourceItemIndex) in section.source_items"
                                                            :key="`source-item-${sourceItemIndex}`"
                                                            data-testid="evidence-panel-source-item"
                                                            class="rounded-xl border border-slate-200 bg-white/80 px-3 py-3 shadow-sm dark:border-white/10 dark:bg-white/5"
                                                        >
                                                            <div class="flex items-start justify-between gap-3">
                                                                <div class="min-w-0 flex-1">
                                                                    <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-700 dark:text-cyan-200">
                                                                        {{ formatSourceType(sourceItem.source_type) }}
                                                                    </div>
                                                                    <div class="mt-1 truncate text-xs font-semibold text-slate-700 dark:text-slate-100">
                                                                        {{ sourceItem.title || 'Untitled source' }}
                                                                    </div>
                                                                </div>
                                                                <span
                                                                    v-if="sourceItem.timestamp"
                                                                    class="shrink-0 text-[10px] text-slate-400 dark:text-slate-400"
                                                                >
                                                                    {{ formatSourceTimestamp(sourceItem.timestamp) }}
                                                                </span>
                                                            </div>
                                                            <div
                                                                v-if="sourceItem.snippet"
                                                                class="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-200"
                                                            >
                                                                {{ sourceItem.snippet }}
                                                            </div>
                                                            <div
                                                                v-if="sourceItem.confidence !== null || sourceItem.relevance !== null"
                                                                class="mt-2 flex flex-wrap gap-2"
                                                            >
                                                                <span
                                                                    v-if="sourceItem.confidence !== null"
                                                                    class="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[10px] text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
                                                                >
                                                                    Confidence: {{ sourceItem.confidence }}
                                                                </span>
                                                                <span
                                                                    v-if="sourceItem.relevance !== null"
                                                                    class="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[10px] text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
                                                                >
                                                                    Relevance: {{ sourceItem.relevance }}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </template>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && msg.suggestionCard"
                                        class="mt-3 rounded-2xl border border-cyan-100 bg-cyan-50/80 dark:border-cyan-400/20 dark:bg-cyan-500/10 px-4 py-3"
                                    >
                                        <div class="flex items-start justify-between gap-3">
                                            <div>
                                                <div class="text-sm font-semibold text-cyan-900 dark:text-cyan-100">
                                                    {{ msg.suggestionCard.headline }}
                                                </div>
                                                <div class="mt-1 text-[11px] text-cyan-700 dark:text-cyan-200">
                                                    风险等级：{{ msg.suggestionCard.risk_level }}
                                                </div>
                                            </div>
                                            <el-tag size="small" type="success" effect="plain">建议卡片</el-tag>
                                        </div>
                                        <ul
                                            v-if="msg.suggestionCard.key_actions && msg.suggestionCard.key_actions.length > 0"
                                            class="mt-3 space-y-1 text-xs text-slate-700 dark:text-slate-200 list-disc pl-4"
                                        >
                                            <li v-for="(action, idx) in msg.suggestionCard.key_actions" :key="`action-${idx}`">
                                                {{ action }}
                                            </li>
                                        </ul>
                                        <div v-if="msg.suggestionCard.follow_up_hint" class="mt-3 text-xs text-slate-600 dark:text-slate-300">
                                            后续建议：{{ msg.suggestionCard.follow_up_hint }}
                                        </div>
                                        <div v-if="msg.suggestionCard.when_to_seek_care" class="mt-2 text-xs text-rose-600 dark:text-rose-300">
                                            就医提醒：{{ msg.suggestionCard.when_to_seek_care }}
                                        </div>
                                    </div>

                                    <div
                                        v-if="msg.role === 'assistant' && msg.sources && msg.sources.length > 0"
                                        class="mt-2 text-xs text-slate-400 pl-2"
                                    >
                                        <div class="flex flex-wrap gap-2 items-center">
                                            <span>参考来源</span>
                                            <span
                                                v-for="(source, idx) in msg.sources"
                                                :key="`source-${idx}`"
                                                class="bg-gray-100 dark:bg-white/5 px-2 py-0.5 rounded border border-gray-200 dark:border-white/10 truncate max-w-[220px]"
                                            >
                                                {{ cleanSourceName(source) }}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    v-if="msg.role === 'user'"
                                    class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs ml-3 shadow shrink-0"
                                >
                                    我
                                </div>
                            </div>

                            <div v-if="loading" class="flex w-full justify-start">
                                <div
                                    class="w-8 h-8 rounded-full bg-linear-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs mr-3 shadow-lg shrink-0"
                                >
                                    AI
                                </div>
                                <div class="max-w-[85%]">
                                    <div
                                        class="px-5 py-3 rounded-2xl bg-white dark:bg-white/10 rounded-tl-none border border-gray-100 dark:border-white/5 flex items-center gap-1"
                                    >
                                        <span class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"></span>
                                        <span class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce delay-75"></span>
                                        <span class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce delay-150"></span>
                                    </div>
                                    <div class="mt-2 ml-3 text-xs text-slate-400">
                                        {{ loadingHint }}
                                    </div>
                                    <div v-if="streamStages.length > 0" class="mt-2 ml-3 flex flex-wrap gap-2">
                                        <span
                                            v-for="(stage, idx) in streamStages"
                                            :key="`live-stage-${idx}`"
                                            class="bg-white/70 dark:bg-white/5 text-slate-500 dark:text-slate-300 px-2 py-0.5 rounded border border-gray-200 dark:border-white/10 text-[11px]"
                                        >
                                            {{ stage.message }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </el-scrollbar>

                    <div class="p-4 border-t border-gray-100 dark:border-white/10 bg-white/50 dark:bg-black/20 backdrop-blur-sm">
                        <div class="relative flex gap-2">
                            <el-input
                                v-model="inputMessage"
                                type="textarea"
                                :rows="1"
                                autosize
                                placeholder="输入您的健康问题..."
                                class="flex-1 custom-chat-input"
                                data-testid="chat-input"
                                @keydown.enter.prevent="sendMessage"
                                :disabled="loading"
                            />
                            <div class="flex flex-col justify-end">
                                <el-button
                                    type="primary"
                                    circle
                                    data-testid="send-message-button"
                                    :loading="loading"
                                    @click="sendMessage"
                                    :disabled="!inputMessage.trim()"
                                    aria-label="发送健康消息"
                                    title="发送健康消息"
                                >
                                    <template #icon>
                                        <el-icon>
                                            <Position />
                                        </el-icon>
                                    </template>
                                </el-button>
                            </div>
                        </div>
                        <div class="flex items-center justify-between mt-2 gap-3">
                            <el-checkbox v-model="forceRefresh" size="small" class="text-xs">
                                忽略缓存，重新回答
                            </el-checkbox>
                            <span class="text-[10px] text-slate-400 text-right">
                                Dr. AI 建议仅供参考，不能替代医生诊断。出现急症请及时就医。
                            </span>
                        </div>
                    </div>
                </GlassCard>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Position } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import MarkdownIt from 'markdown-it'

import GlassCard from '../../components/ui/GlassCard.vue'
import { useAuthStore } from '../../stores/authStore'
import { apiUrl } from '../../utils/api'

const CHAT_SEND_URL = apiUrl('/chat/send')
const CHAT_STREAM_URL = apiUrl('/chat/stream')
const CHAT_CONVERSATIONS_URL = apiUrl('/chat/conversations')

const authStore = useAuthStore()
const md = new MarkdownIt({ html: false, breaks: true, linkify: true })
const scrollbarRef = ref(null)

const conversations = ref([])
const conversationSearch = ref('')
const selectedConversationIds = ref([])
const selectedArchivedConversationIds = ref([])
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const batchArchiveLoading = ref(false)
const batchArchivePreview = ref(null)
const batchRestoreLoading = ref(false)
const batchRestorePreview = ref(null)
const forceRefresh = ref(false)
const conversationId = ref(null)
const showArchived = ref(false)
const loadingHint = ref('正在建立会话上下文...')
const streamStages = ref([])
const activeRenameConversationId = ref(null)
const renameDraft = ref('')

const groupedConversationSections = computed(() => {
    const sections = []
    let currentSection = null

    conversations.value.forEach((item) => {
        const groupKey = item.group_key || 'older'
        const groupLabel = item.group_label || 'Older'

        if (!currentSection || currentSection.key !== groupKey) {
            currentSection = {
                key: groupKey,
                label: groupLabel,
                items: [],
            }
            sections.push(currentSection)
        }

        currentSection.items.push(item)
    })

    return sections
})

const visibleActiveConversationIds = computed(() =>
    conversations.value
        .filter((item) => item && !item.archived && item.conversation_id)
        .map((item) => item.conversation_id),
)

const visibleArchivedConversationIds = computed(() =>
    conversations.value
        .filter((item) => item && item.archived && item.conversation_id)
        .map((item) => item.conversation_id),
)

const selectVisibleActiveConversations = computed({
    get: () =>
        visibleActiveConversationIds.value.length > 0 &&
        visibleActiveConversationIds.value.every((conversationIdValue) =>
            selectedConversationIds.value.includes(conversationIdValue),
        ),
    set: (checked) => {
        if (checked) {
            const mergedIds = new Set([...selectedConversationIds.value, ...visibleActiveConversationIds.value])
            selectedConversationIds.value = Array.from(mergedIds)
            return
        }

        const visibleIds = new Set(visibleActiveConversationIds.value)
        selectedConversationIds.value = selectedConversationIds.value.filter((conversationIdValue) => !visibleIds.has(conversationIdValue))
    },
})

const selectVisibleArchivedConversations = computed({
    get: () =>
        visibleArchivedConversationIds.value.length > 0 &&
        visibleArchivedConversationIds.value.every((conversationIdValue) =>
            selectedArchivedConversationIds.value.includes(conversationIdValue),
        ),
    set: (checked) => {
        if (checked) {
            const mergedIds = new Set([
                ...selectedArchivedConversationIds.value,
                ...visibleArchivedConversationIds.value,
            ])
            selectedArchivedConversationIds.value = Array.from(mergedIds)
            return
        }

        const visibleIds = new Set(visibleArchivedConversationIds.value)
        selectedArchivedConversationIds.value = selectedArchivedConversationIds.value.filter(
            (conversationIdValue) => !visibleIds.has(conversationIdValue),
        )
    },
})

const createWelcomeMessage = () => ({
    role: 'assistant',
    content: '你好，我是 Dr. AI。我会结合你的健康档案、历史趋势和医学资料，给出尽量谨慎的健康建议。',
    sources: [],
    evidenceTags: [],
    decisionSummary: {},
    responseVerdict: null,
    takeover: null,
    evidencePanel: null,
    activeEvidencePanelKey: null,
    suggestionCard: null,
    processStages: [],
})

const authHeaders = () => ({
    Authorization: `Bearer ${authStore.token}`,
})

const renderMarkdown = (text) => md.render(text || '')

const normalizeEvidencePanel = (panel) => {
    if (!panel || typeof panel !== 'object') return null

    const normalizeSourceItem = (sourceItem) => {
        if (!sourceItem || typeof sourceItem !== 'object') return null

        return {
            source_type: sourceItem.source_type || '',
            title: sourceItem.title || '',
            snippet: sourceItem.snippet || '',
            timestamp: sourceItem.timestamp || '',
            confidence: sourceItem.confidence ?? null,
            relevance: sourceItem.relevance ?? null,
        }
    }

    const chips = Array.isArray(panel.chips)
        ? panel.chips
              .filter((chip) => chip && typeof chip === 'object' && chip.label)
              .map((chip) => ({
                  key: chip.key || chip.label,
                  label: chip.label,
              }))
        : []

    const sections = Array.isArray(panel.sections)
        ? panel.sections
              .filter((section) => section && typeof section === 'object' && section.label)
              .map((section) => ({
                  label: section.label,
                  summary: section.summary || '',
                  key_facts: Array.isArray(section.key_facts) ? section.key_facts : [],
                  decision_basis: section.decision_basis || '',
                  source_refs: Array.isArray(section.source_refs) ? section.source_refs : [],
                  source_items: Array.isArray(section.source_items)
                      ? section.source_items.map(normalizeSourceItem).filter(Boolean)
                      : [],
              }))
        : []

    if (chips.length === 0 && sections.length === 0) {
        return null
    }

    return {
        chips,
        sections,
    }
}

const normalizeTakeover = (takeover) => {
    if (!takeover || typeof takeover !== 'object') return null

    const normalized = {
        schema_version: takeover.schema_version || takeover.schemaVersion || '',
        status: takeover.status || '',
        trigger_reason: takeover.trigger_reason || takeover.triggerReason || '',
        summary: takeover.summary || '',
    }

    return normalized.schema_version || normalized.status || normalized.trigger_reason || normalized.summary
        ? normalized
        : null
}

const closeEvidencePanels = (currentMessage) => {
    messages.value.forEach((message) => {
        if (message !== currentMessage && message?.activeEvidencePanelKey) {
            message.activeEvidencePanelKey = null
        }
    })
}

const getEvidencePanelSection = (msg, chip, chipIndex) => {
    if (!msg?.evidencePanel?.sections || msg.evidencePanel.sections.length === 0) {
        return null
    }

    return (
        msg.evidencePanel.sections.find((section) => section.label === chip?.label) ||
        msg.evidencePanel.sections[chipIndex] ||
        null
    )
}

const isEvidencePanelChipActive = (msg, chip, chipIndex) => {
    const section = getEvidencePanelSection(msg, chip, chipIndex)
    return !!section && msg.activeEvidencePanelKey === section.label
}

const toggleEvidencePanelSection = (msg, chip, chipIndex) => {
    const section = getEvidencePanelSection(msg, chip, chipIndex)
    if (!section) return

    if (msg.activeEvidencePanelKey === section.label) {
        msg.activeEvidencePanelKey = null
        return
    }

    closeEvidencePanels(msg)
    msg.activeEvidencePanelKey = section.label
}

const cleanSourceName = (sourceString) => {
    if (!sourceString) return ''
    if (sourceString.includes(' - ')) {
        return sourceString.split(' - ')[1].split(']')[0]
    }
    return sourceString
}

const formatSourceType = (sourceType) => {
    const typeMap = {
        profile: 'Profile',
        trend: 'Trend',
        report: 'Report',
        guideline: 'Guideline',
    }

    return typeMap[sourceType] || sourceType || 'Source'
}

const formatSourceTimestamp = (value) => {
    if (!value) return ''

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
        return String(value)
    }

    return `${date.toISOString().slice(0, 16).replace('T', ' ')} UTC`
}

const formatConversationTime = (value) => {
    if (!value) return ''
    try {
        const date = new Date(value)
        return `${date.getMonth() + 1}/${date.getDate()}`
    } catch {
        return ''
    }
}

const isConversationSelected = (conversationIdValue, selectedIds = selectedConversationIds.value) =>
    selectedIds.includes(conversationIdValue)

const getConversationCardClass = (item, selectedIds = selectedConversationIds.value) => {
    const isSelected = isConversationSelected(item.conversation_id, selectedIds)
    const isCurrent = conversationId.value === item.conversation_id

    if (isSelected && isCurrent) {
        return 'border-amber-300 bg-amber-50/90 ring-1 ring-amber-200 dark:border-amber-300/40 dark:bg-amber-500/10 dark:ring-amber-300/20'
    }

    if (isSelected) {
        return 'border-amber-200 bg-amber-50/80 dark:border-amber-400/30 dark:bg-amber-500/10'
    }

    return isCurrent
        ? 'border-blue-200 bg-blue-50/80 dark:border-blue-400/30 dark:bg-blue-500/10'
        : 'border-gray-200 bg-white/60 hover:border-blue-200 hover:bg-blue-50/40 dark:border-white/10 dark:bg-white/5 dark:hover:border-blue-400/20'
}

const formatEvidenceTag = (tag) => {
    const tagMap = {
        profile_summary: '健康档案',
        latest_risk_report: '风险报告',
        history_trends: '历史趋势',
        uploaded_documents: '上传报告',
        guideline_search: '医学指南',
        urgent_route: '安全分流',
    }
    return tagMap[tag] || tag
}

const getDecisionPolicy = (msg) => msg?.decisionSummary?.policy || {}

const getResponseVerdict = (msg) => msg?.responseVerdict || null

const getTakeover = (msg) => msg?.takeover || null

const hasTakeover = (msg) => {
    const takeover = getTakeover(msg)
    return (
        msg?.role === 'assistant' &&
        Boolean(takeover?.schema_version || takeover?.status || takeover?.trigger_reason || takeover?.summary)
    )
}

const isTakeoverRequired = (msg) => getTakeover(msg)?.status === 'required'

const formatTakeoverStatus = (msg) =>
    formatEnumValue(getTakeover(msg)?.status, {
        required: '需要人工接管',
        suppressed: '已评估，未触发',
    })

const formatTakeoverTriggerReason = (msg) =>
    formatEnumValue(getTakeover(msg)?.trigger_reason, {
        high_risk: '高风险',
        insufficient_evidence: '证据不足',
        boundary_false_positive: '误触发已抑制',
        boundary_not_triggered: '未触发边界',
    })

const hasAnswerExplanation = (msg) => {
    if (msg?.role !== 'assistant') return false

    const policy = getDecisionPolicy(msg)
    return Boolean(
        msg?.decisionSummary?.lane ||
            msg?.decisionSummary?.verdict ||
            policy.policy_version ||
            policy.selected_rule ||
            policy.evidence_state ||
            policy.tool_availability ||
            policy.answer_mode ||
            policy.disclaimer_mode ||
            getResponseVerdict(msg),
    )
}

const formatEnumValue = (value, map) => map[value] || value || '未提供'

const formatResponseMode = (msg) => {
    const verdict = getResponseVerdict(msg)
    const policy = getDecisionPolicy(msg)
    return formatEnumValue(verdict?.response_mode || policy.answer_mode, {
        direct_answer: 'direct_answer',
        bounded_answer: 'bounded_answer',
        clarify_missing_context: 'clarify_missing_context',
        refusal_with_disclaimer: 'refusal_with_disclaimer',
        urgent_care_disclaimer: 'urgent_care_disclaimer',
    })
}

const formatMedicalRiskLevel = (msg) => {
    const verdict = getResponseVerdict(msg)
    const policy = getDecisionPolicy(msg)
    return formatEnumValue(verdict?.medical_risk_level || policy.risk_level, {
        low: 'low',
        medium: 'medium',
        high: 'high',
    })
}

const formatEvidenceSufficiency = (msg) => {
    const verdict = getResponseVerdict(msg)
    const policy = getDecisionPolicy(msg)
    return formatEnumValue(verdict?.evidence_sufficiency || policy.evidence_state, {
        sufficient: 'sufficient',
        limited: 'limited',
        insufficient: 'insufficient',
    })
}

const formatDegradeState = (msg) => {
    const verdict = getResponseVerdict(msg)
    const policy = getDecisionPolicy(msg)
    const reason = verdict?.degraded_reason ?? policy.degrade_reason
    return reason ? `已触发：${reason}` : '未触发'
}

const formatHumanEscalation = (msg) => {
    const verdict = getResponseVerdict(msg)
    if (verdict?.human_escalation_required === true) return '需要'
    if (verdict?.human_escalation_required === false) return '不需要'
    return '未提供'
}

const formatDisclaimerMode = (msg) => {
    const policy = getDecisionPolicy(msg)
    return formatEnumValue(policy.disclaimer_mode, {
        none: 'none',
        conservative: 'conservative',
        diagnosis_guardrail: 'diagnosis_guardrail',
        urgent_care: 'urgent_care',
    })
}

const rememberStreamStage = (payload) => {
    if (!payload?.message) return

    const stageKey = payload.stage || payload.event || 'status'

    const lastStage = streamStages.value[streamStages.value.length - 1]
    if (lastStage && lastStage.stage === stageKey && lastStage.message === payload.message) {
        return
    }

    streamStages.value.push({
        stage: stageKey,
        message: payload.message,
    })
    loadingHint.value = payload.message
}

const scrollToBottom = async () => {
    await nextTick()
    if (scrollbarRef.value?.wrapRef) {
        const wrap = scrollbarRef.value.wrapRef
        wrap.scrollTop = wrap.scrollHeight
    }
}

const parseSseBuffer = (buffer, onEvent) => {
    let normalized = buffer.replace(/\r\n/g, '\n')
    let separatorIndex = normalized.indexOf('\n\n')

    while (separatorIndex !== -1) {
        const rawEvent = normalized.slice(0, separatorIndex).trim()
        normalized = normalized.slice(separatorIndex + 2)

        if (rawEvent) {
            let eventName = 'message'
            const dataLines = []

            rawEvent.split('\n').forEach((line) => {
                if (line.startsWith('event:')) {
                    eventName = line.slice(6).trim()
                } else if (line.startsWith('data:')) {
                    dataLines.push(line.slice(5).trimStart())
                }
            })

            if (dataLines.length > 0) {
                try {
                    onEvent({
                        event: eventName,
                        data: JSON.parse(dataLines.join('\n')),
                    })
                } catch (error) {
                    console.error('Failed to parse SSE event', error)
                }
            }
        }

        separatorIndex = normalized.indexOf('\n\n')
    }

    return normalized
}

const normalizeStoredMessage = (message) => ({
    role: message.role,
    content: message.content,
    sequence: message.sequence,
    createdAt: message.created_at,
    sources: message.sources || [],
    evidenceTags: message.evidence_tags || [],
    decisionSummary: message.decision_summary || {},
    responseVerdict: message.response_verdict || null,
    takeover: normalizeTakeover(message.takeover),
    evidencePanel: normalizeEvidencePanel(message.evidence_panel),
    activeEvidencePanelKey: null,
    suggestionCard: message.suggestion_card || null,
    processStages: [],
})

const fetchConversationList = async () => {
    if (!authStore.token) return
    try {
        const res = await axios.get(CHAT_CONVERSATIONS_URL, {
            headers: authHeaders(),
            params: {
                query: conversationSearch.value || undefined,
                archived: showArchived.value,
            },
        })
        conversations.value = res.data || []
    } catch (error) {
        console.error('Failed to load conversations', error)
    }
}

const loadConversation = async (targetConversationId) => {
    if (!targetConversationId || loading.value) return

    try {
        const res = await axios.get(`${CHAT_CONVERSATIONS_URL}/${targetConversationId}/messages`, {
            headers: authHeaders(),
        })
        conversationId.value = res.data.conversation_id
        messages.value = (res.data.messages || []).map(normalizeStoredMessage)
        if (messages.value.length === 0) {
            messages.value = [createWelcomeMessage()]
        }
        await fetchConversationList()
        streamStages.value = []
        loadingHint.value = '正在建立会话上下文...'
        await scrollToBottom()
    } catch (error) {
        console.error('Failed to load conversation detail', error)
    }
}

const startNewConversation = async () => {
    if (loading.value) return
    conversationId.value = null
    activeRenameConversationId.value = null
    renameDraft.value = ''
    streamStages.value = []
    loadingHint.value = '正在建立会话上下文...'
    messages.value = [createWelcomeMessage()]
    await scrollToBottom()
}

const startRenameConversation = (item) => {
    if (!item?.conversation_id || loading.value) return

    activeRenameConversationId.value = item.conversation_id
    renameDraft.value = item.title || ''
}

const cancelRenameConversation = () => {
    activeRenameConversationId.value = null
    renameDraft.value = ''
}

const renameConversation = async (item) => {
    if (!item?.conversation_id || loading.value) return

    const title = renameDraft.value.trim()
    if (!title) return

    try {
        await axios.patch(
            `${CHAT_CONVERSATIONS_URL}/${item.conversation_id}`,
            { title },
            { headers: authHeaders() },
        )
        await fetchConversationList()
        cancelRenameConversation()
    } catch (error) {
        console.error('Failed to rename conversation', error)
    }
}

const selectConversation = async (item) => {
    if (!item?.conversation_id) return
    cancelRenameConversation()
    await loadConversation(item.conversation_id)
}

const toggleConversationArchive = async (item) => {
    if (!item?.conversation_id || loading.value) return

    const endpoint = item.archived ? 'restore' : 'archive'
    try {
        await axios.post(
            `${CHAT_CONVERSATIONS_URL}/${item.conversation_id}/${endpoint}`,
            {},
            { headers: authHeaders() },
        )

        if (!item.archived && conversationId.value === item.conversation_id && !showArchived.value) {
            await startNewConversation()
        }

        selectedConversationIds.value = selectedConversationIds.value.filter((id) => id !== item.conversation_id)
        selectedArchivedConversationIds.value = selectedArchivedConversationIds.value.filter(
            (id) => id !== item.conversation_id,
        )
        batchArchivePreview.value = null
        batchRestorePreview.value = null
        await fetchConversationList()
    } catch (error) {
        console.error('Failed to toggle conversation archive state', error)
    }
}

const toggleConversationPin = async (item) => {
    if (!item?.conversation_id || loading.value) return

    const endpoint = item.pinned ? 'unpin' : 'pin'
    try {
        await axios.post(
            `${CHAT_CONVERSATIONS_URL}/${item.conversation_id}/${endpoint}`,
            {},
            { headers: authHeaders() },
        )
        await fetchConversationList()
    } catch (error) {
        console.error('Failed to toggle conversation pin state', error)
    }
}

const clearBatchArchiveSelection = () => {
    selectedConversationIds.value = []
    batchArchivePreview.value = null
}

const clearBatchRestoreSelection = () => {
    selectedArchivedConversationIds.value = []
    batchRestorePreview.value = null
}

const prepareBatchArchiveSelection = async (conversationIds) => {
    const normalizedIds = Array.from(new Set(conversationIds)).filter(Boolean)
    if (normalizedIds.length === 0) {
        return null
    }

    const response = await axios.post(
        `${CHAT_CONVERSATIONS_URL}/batch/archive/prepare`,
        { conversation_ids: normalizedIds },
        { headers: authHeaders() },
    )

    batchArchivePreview.value = response.data || null
    return batchArchivePreview.value
}

const prepareBatchRestoreSelection = async (conversationIds) => {
    const normalizedIds = Array.from(new Set(conversationIds)).filter(Boolean)
    if (normalizedIds.length === 0) {
        return null
    }

    const response = await axios.post(
        `${CHAT_CONVERSATIONS_URL}/batch/restore/prepare`,
        { conversation_ids: normalizedIds },
        { headers: authHeaders() },
    )

    batchRestorePreview.value = response.data || null
    return batchRestorePreview.value
}

const archiveSelectedConversations = async () => {
    if (loading.value || batchArchiveLoading.value || showArchived.value) return

    const selectedIds = Array.from(new Set(selectedConversationIds.value)).filter(Boolean)
    if (selectedIds.length === 0) {
        ElMessage.warning('请先选择要归档的活动会话')
        return
    }

    batchArchiveLoading.value = true
    try {
        const preview = await prepareBatchArchiveSelection(selectedIds)
        if (!preview || preview.archiveable_count === 0) {
            ElMessage.info('所选会话没有可归档项')
            return
        }

        await axios.post(
            `${CHAT_CONVERSATIONS_URL}/batch/archive`,
            { conversation_ids: selectedIds },
            { headers: authHeaders() },
        )

        if (conversationId.value && selectedIds.includes(conversationId.value) && !showArchived.value) {
            await startNewConversation()
        }

        clearBatchArchiveSelection()
        await fetchConversationList()
        ElMessage.success(`已归档 ${preview.archiveable_count} 个会话`)
    } catch (error) {
        console.error('Failed to archive selected conversations', error)
        ElMessage.error('批量归档失败，请稍后再试')
    } finally {
        batchArchiveLoading.value = false
    }
}

const restoreSelectedConversations = async () => {
    if (loading.value || batchRestoreLoading.value || !showArchived.value) return

    const selectedIds = Array.from(new Set(selectedArchivedConversationIds.value)).filter(Boolean)
    if (selectedIds.length === 0) {
        ElMessage.warning('请先选择要恢复的已归档会话')
        return
    }

    batchRestoreLoading.value = true
    try {
        const preview = await prepareBatchRestoreSelection(selectedIds)
        if (!preview || preview.restorable_count === 0) {
            ElMessage.info('所选会话没有可恢复项目')
            return
        }

        await axios.post(
            `${CHAT_CONVERSATIONS_URL}/batch/restore`,
            { conversation_ids: selectedIds },
            { headers: authHeaders() },
        )

        clearBatchRestoreSelection()
        await fetchConversationList()
        ElMessage.success(`已恢复 ${preview.restorable_count} 个会话`)
    } catch (error) {
        console.error('Failed to restore selected conversations', error)
        ElMessage.error('批量恢复失败，请稍后再试')
    } finally {
        batchRestoreLoading.value = false
    }
}

const pushAssistantMessage = async (payload) => {
    conversationId.value = payload.conversation_id
    messages.value.push({
        role: 'assistant',
        content: payload.reply,
        sources: payload.sources || [],
        evidenceTags: payload.evidence_tags || [],
        decisionSummary: payload.decision_summary || {},
        responseVerdict: payload.response_verdict || null,
        takeover: normalizeTakeover(payload.takeover),
        evidencePanel: normalizeEvidencePanel(payload.evidence_panel),
        activeEvidencePanelKey: null,
        suggestionCard: payload.suggestion_card || null,
        processStages: [...streamStages.value],
    })
    await fetchConversationList()
}

const sendMessageViaFallback = async (content) => {
    const res = await axios.post(
        CHAT_SEND_URL,
        {
            message: content,
            conversation_id: conversationId.value,
            force_refresh: forceRefresh.value,
        },
        {
            headers: authHeaders(),
        },
    )

    if (res.data) {
        await pushAssistantMessage(res.data)
    }
}

const sendMessage = async (e) => {
    if (e && e.shiftKey) return

    const content = inputMessage.value.trim()
    if (!content || loading.value) return

    messages.value.push({
        role: 'user',
        content,
    })
    inputMessage.value = ''
    streamStages.value = []
    loading.value = true
    loadingHint.value = '正在建立会话上下文...'
    await scrollToBottom()

    try {
        const response = await fetch(CHAT_STREAM_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders(),
            },
            body: JSON.stringify({
                message: content,
                conversation_id: conversationId.value,
                force_refresh: forceRefresh.value,
            }),
        })

        if (!response.ok || !response.body) {
            throw new Error(`Stream request failed with status ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        let finalPayload = null

        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            buffer = parseSseBuffer(buffer, ({ event, data }) => {
                if (event === 'status') {
                    rememberStreamStage(data)
                    if (data?.conversation_id) {
                        conversationId.value = data.conversation_id
                    }
                } else if (event === 'tool_start' || event === 'tool_done') {
                    rememberStreamStage({
                        ...data,
                        event,
                    })
                    if (data?.conversation_id) {
                        conversationId.value = data.conversation_id
                    }
                } else if (event === 'final') {
                    finalPayload = data
                } else if (event === 'error') {
                    throw new Error(data?.message || 'Unknown stream error')
                }
            })

            await scrollToBottom()
        }

        buffer += decoder.decode()
        parseSseBuffer(buffer, ({ event, data }) => {
            if (event === 'status') {
                rememberStreamStage(data)
            } else if (event === 'tool_start' || event === 'tool_done') {
                rememberStreamStage({
                    ...data,
                    event,
                })
            } else if (event === 'final') {
                finalPayload = data
            }
        })

        if (!finalPayload) {
            throw new Error('Missing final SSE payload')
        }

        await pushAssistantMessage(finalPayload)
    } catch (error) {
        console.error('SSE chat failed, falling back to standard request.', error)
        try {
            if (streamStages.value.length === 0) {
                loadingHint.value = '流式连接异常，正在切换为标准请求...'
            }
            await sendMessageViaFallback(content)
        } catch (fallbackError) {
            console.error('Fallback chat failed.', fallbackError)
            messages.value.push({
                role: 'assistant',
                content: '抱歉，网络连接异常，请稍后再试。',
                sources: [],
                evidenceTags: [],
                decisionSummary: {},
                responseVerdict: null,
                takeover: null,
                evidencePanel: null,
                activeEvidencePanelKey: null,
                suggestionCard: null,
                processStages: [...streamStages.value],
            })
        }
    } finally {
        loading.value = false
        streamStages.value = []
        await scrollToBottom()
    }
}

onMounted(async () => {
    await startNewConversation()
    await fetchConversationList()
})

watch(conversationSearch, async () => {
    await fetchConversationList()
})

watch(showArchived, async (isArchivedView) => {
    if (isArchivedView) {
        clearBatchArchiveSelection()
    } else {
        clearBatchRestoreSelection()
    }

    await fetchConversationList()
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
    font-weight: 700;
}

.dark .markdown-body :deep(strong) {
    color: #60a5fa;
}

.custom-chat-input :deep(.el-textarea__inner) {
    background-color: transparent;
    box-shadow: none;
    resize: none;
    padding: 8px 0;
    font-size: 14px;
}
</style>
