import hashlib
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from sqlmodel import Session

from backend.core.cache import CacheManager
from backend.core.config import settings
from backend.models import AgentAuditEvent, User
from backend.services.agent_answer_replay import (
    build_answer_replay_record,
    persist_answer_replay_record,
)
from backend.services.agent_audit import build_audit_record, persist_audit_record
from backend.services.agent_safety import (
    classify_policy_pressure,
    classify_query_safety,
    describe_evidence_gap,
    evaluate_chat_policy,
    evaluate_post_tool_sufficiency,
)
from backend.services.agent_tools import (
    execute_registered_tool,
    execute_tool_call,
    get_allowed_tool_names_for_lane,
    get_tool_definitions,
)
from backend.services.chat_tool_presentation import (
    build_tool_done_message,
    build_tool_status_message,
    summarize_tool_output_for_prompt,
)
from backend.services.payload_normalization import summarize_risk_snapshot_for_context
from backend.services.context_builder import (
    DEFAULT_CONTEXT_BUDGETS,
    build_context_payload,
    trim_history_to_token_budget,
)
from backend.services.conversation_service import build_message_window, conversation_service
from backend.services.rag_service import rag_service

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL or "https://api.moonshot.cn/v1"
        self.model = settings.OPENAI_MODEL or "moonshot-v1-8k"

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None
            logger.info("ChatService: OPENAI_API_KEY missing. Chat response will be degraded.")

    async def chat(
        self,
        user: User,
        query: str,
        session: Session,
        conversation_id: Optional[int] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        final_response: Optional[Dict[str, Any]] = None
        async for event in self._chat_events(
            user=user,
            query=query,
            session=session,
            conversation_id=conversation_id,
            force_refresh=force_refresh,
        ):
            if event["event"] == "final":
                final_response = event["data"]

        if final_response is None:
            raise RuntimeError("ChatService finished without final response")
        return final_response

    async def stream_chat(
        self,
        user: User,
        query: str,
        session: Session,
        conversation_id: Optional[int] = None,
        force_refresh: bool = False,
    ) -> AsyncIterator[Dict[str, Any]]:
        async for event in self._chat_events(
            user=user,
            query=query,
            session=session,
            conversation_id=conversation_id,
            force_refresh=force_refresh,
        ):
            yield event

    async def _chat_events(
        self,
        *,
        user: User,
        query: str,
        session: Session,
        conversation_id: Optional[int],
        force_refresh: bool,
    ) -> AsyncIterator[Dict[str, Any]]:
        query_text = query.strip()
        turn_started_at = time.perf_counter()
        conversation = self._get_conversation(session=session, user=user, conversation_id=conversation_id)
        conversation_service.append_message(
            session=session,
            conversation=conversation,
            role="user",
            content=query_text,
        )
        yield self._status_event(
            stage="conversation_ready",
            message="会话已建立，正在分析当前问题。",
            conversation_id=conversation.id,
        )

        safety_result = classify_query_safety(query_text)
        lane = safety_result.get("lane", "general_health")
        planned_tool_names = self._plan_tools(query_text, lane=lane)
        if safety_result["route"] == "medical_escalation":
            yield self._status_event(
                stage="urgent_route",
                message="检测到潜在急症风险，正在优先给出安全分流建议。",
                conversation_id=conversation.id,
            )
            urgent_response = self._build_urgent_response(
                user=user,
                conversation_id=conversation.id,
                session=session,
                safety_result=safety_result,
                response_latency_ms=self._elapsed_ms(turn_started_at),
                tool_outputs=[],
            )
            yield {"event": "final", "data": urgent_response}
            return

        yield self._status_event(
            stage="reading_profile",
            message="正在读取健康档案与个体化背景。",
            conversation_id=conversation.id,
        )
        profile_summary = self._get_user_context(user, session)
        profile_evidence = self._build_profile_evidence(user)

        yield self._status_event(
            stage="searching_knowledge",
            message="正在检索医学知识与参考资料。",
            conversation_id=conversation.id,
        )
        rag_result = self._search_rag_context_with_quality(query_text, k=3)
        rag_context = rag_result["context"]
        rag_quality_summary = rag_result["rag_quality_summary"]
        sources = self._extract_sources(rag_context)

        system_prompt = self._build_system_prompt()
        planning_context = build_context_payload(
            profile_summary=profile_summary,
            rag_context=rag_context,
            tool_evidence_text="暂无额外工具证据。",
            query=query_text,
        )
        planning_prompt = self._build_user_prompt(
            profile_summary=planning_context["profile_summary"],
            rag_context=planning_context["rag_context"],
            tool_evidence_text=planning_context["tool_evidence_text"],
            query=planning_context["query"],
        )

        history = conversation_service.get_recent_history(
            session=session,
            conversation=conversation,
            max_rounds=5,
        )
        bounded_history = trim_history_to_token_budget(
            history[:-1],
            token_budget=DEFAULT_CONTEXT_BUDGETS["history"],
        )
        planning_messages = build_message_window(
            system_prompt=system_prompt,
            history=bounded_history + [{"role": "user", "content": planning_prompt}],
            max_rounds=5,
        )

        yield self._status_event(
            stage="planning_tools",
            message="正在规划需要调用的只读工具。",
            conversation_id=conversation.id,
        )
        direct_reply, tool_outputs, fallback_used, tool_latency_ms = await self._select_tools_with_fallback(
            user=user,
            session=session,
            query_text=query_text,
            lane=lane,
            planned_tool_names=planned_tool_names,
            planning_messages=planning_messages,
            conversation_id=conversation.id,
        )

        for tool_output in tool_outputs:
            tool_name = tool_output.get("tool", "unknown_tool")
            tool_start_message = build_tool_status_message(tool_name)
            yield {
                "event": "tool_start",
                "data": {
                    "tool_name": tool_name,
                    "message": tool_start_message,
                    "conversation_id": conversation.id,
                },
            }
            yield self._status_event(
                stage="running_tool",
                message=tool_start_message,
                conversation_id=conversation.id,
                tool_name=tool_name,
            )
            yield {
                "event": "tool_done",
                "data": {
                    "tool_name": tool_name,
                    "message": build_tool_done_message(tool_name),
                    "conversation_id": conversation.id,
                },
            }

        evidence_tags = self._collect_evidence_tags(tool_outputs)
        decision_summary = self._build_decision_summary(
            query=query_text,
            safety_result=safety_result,
            planned_tool_names=planned_tool_names,
            tool_outputs=tool_outputs,
            profile_evidence=profile_evidence,
            retrieval_evidence=rag_context,
            rag_quality_summary=rag_quality_summary,
        )
        response_verdict = self._build_response_verdict(decision_summary=decision_summary)
        takeover = self._build_takeover(
            decision_summary=decision_summary,
            response_verdict=response_verdict,
        )
        post_check = evaluate_post_tool_sufficiency(
            lane=decision_summary.get("lane", "general_health"),
            allowed_tool_names=list(dict.fromkeys(planned_tool_names)),
            tool_outputs=tool_outputs,
            profile_evidence=profile_evidence,
            retrieval_evidence=rag_context,
            rag_quality_summary=rag_quality_summary,
        )
        lane_direct_reply = self._build_lane_direct_reply(
            query=query_text,
            decision_summary=decision_summary,
            tool_outputs=tool_outputs,
            planned_tool_names=planned_tool_names,
            profile_evidence=profile_evidence,
            retrieval_evidence=rag_context,
            post_check=post_check,
        )
        if lane_direct_reply is not None:
            direct_reply = lane_direct_reply
        suggestion_card = self._build_suggestion_card(
            query=query_text,
            decision_summary=decision_summary,
            evidence_tags=evidence_tags,
        )
        evidence_panel = self._build_evidence_panel(
            sources=sources,
            evidence_tags=evidence_tags,
            decision_summary=decision_summary,
            tool_outputs=tool_outputs,
        )
        tool_evidence_text = self._build_tool_evidence_text(tool_outputs)

        final_context = build_context_payload(
            profile_summary=profile_summary,
            rag_context=rag_context,
            tool_evidence_text=tool_evidence_text,
            query=query_text,
        )
        response_latency_ms = self._elapsed_ms(turn_started_at)
        final_prompt = self._build_user_prompt(
            profile_summary=final_context["profile_summary"],
            rag_context=final_context["rag_context"],
            tool_evidence_text=final_context["tool_evidence_text"],
            query=final_context["query"],
        )
        final_messages = build_message_window(
            system_prompt=system_prompt,
            history=bounded_history + [{"role": "user", "content": final_prompt}],
            max_rounds=5,
        )
        cache_key = self._build_cache_key(
            user_id=user.id,
            conversation_id=conversation.id,
            messages=final_messages,
        )

        if not force_refresh:
            cached_data = await CacheManager.get(cache_key)
            if cached_data:
                yield self._status_event(
                    stage="cache_hit",
                    message="已命中上下文缓存，正在返回整理后的结果。",
                    conversation_id=conversation.id,
                )
                reply = cached_data.get("reply", "")
                cached_decision_summary = self._merge_decision_summary(
                    cached_decision_summary=cached_data.get("decision_summary"),
                    fallback_decision_summary=decision_summary,
                )
                cached_response_verdict = self._merge_response_verdict(
                    cached_response_verdict=cached_data.get("response_verdict"),
                    fallback_response_verdict=response_verdict,
                    decision_summary=cached_decision_summary,
                )
                cached_takeover = self._merge_takeover(
                    cached_takeover=cached_data.get("takeover"),
                    fallback_takeover=takeover,
                )
                audit_record = self._build_responsibility_audit_record(
                    user_id=conversation.user_id,
                    conversation_id=conversation.id,
                    decision_summary=cached_decision_summary,
                    response_verdict=cached_response_verdict,
                    evidence_tags=cached_data.get("evidence_tags", evidence_tags),
                    context_budget_summary=final_context["budget_summary"],
                    tool_latency_ms=0,
                    tool_count=len(cached_decision_summary.get("tool_used", [])),
                    response_latency_ms=response_latency_ms,
                    fallback_used=False,
                    model_name=None,
                    tool_plan_source="cache_replay",
                    cache_hit=True,
                )
                audit_event = self._record_audit_event(session=session, audit_record=audit_record)
                message = conversation_service.append_message(
                    session=session,
                    conversation=conversation,
                    role="assistant",
                    content=reply,
                    sources=cached_data.get("sources", []),
                    evidence_tags=cached_data.get("evidence_tags", evidence_tags),
                    decision_summary=cached_decision_summary,
                    response_verdict=cached_response_verdict,
                    takeover=cached_takeover,
                    evidence_panel=cached_data.get("evidence_panel") or evidence_panel,
                    suggestion_card=cached_data.get("suggestion_card"),
                )
                self._persist_answer_replay(
                    session=session,
                    conversation=conversation,
                    conversation_id=conversation.id,
                    message_id=message.id,
                    audit_event=audit_event,
                    decision_summary=cached_decision_summary,
                    response_verdict=cached_response_verdict,
                    sources=cached_data.get("sources", []),
                    tool_outputs=tool_outputs,
                    context_budget_summary=final_context["budget_summary"],
                    tool_latency_ms=0,
                    response_latency_ms=response_latency_ms,
                    tool_count=len(cached_decision_summary.get("tool_used", [])),
                    fallback_used=False,
                    model_name=None,
                    tool_plan_source="cache_replay",
                    cache_hit=True,
                )
                yield {
                    "event": "final",
                    "data": {
                        "conversation_id": conversation.id,
                        "reply": reply,
                        "sources": cached_data.get("sources", []),
                        "evidence_tags": cached_data.get("evidence_tags", evidence_tags),
                        "decision_summary": cached_decision_summary,
                        "response_verdict": cached_response_verdict,
                        "takeover": cached_takeover,
                        "evidence_panel": cached_data.get("evidence_panel") or evidence_panel,
                        "suggestion_card": cached_data.get("suggestion_card"),
                    },
                }
                return

        yield self._status_event(
            stage="generating_answer",
            message="正在整合证据并生成最终回答。",
            conversation_id=conversation.id,
        )

        tool_plan_source = self._determine_audit_tool_plan_source(
            planned_tool_names=planned_tool_names,
            fallback_used=fallback_used,
        )

        if direct_reply:
            result = await self._finalize_response(
                session=session,
                conversation_id=conversation.id,
                conversation=conversation,
                reply=direct_reply,
                sources=sources,
                evidence_tags=evidence_tags,
                decision_summary=decision_summary,
                response_verdict=response_verdict,
                takeover=takeover,
                evidence_panel=evidence_panel,
                suggestion_card=suggestion_card,
                context_budget_summary=final_context["budget_summary"],
                tool_outputs=tool_outputs,
                tool_latency_ms=tool_latency_ms,
                response_latency_ms=response_latency_ms,
                tool_count=len(tool_outputs),
                fallback_used=fallback_used,
                model_name=self._determine_audit_model_name(
                    tool_plan_source=tool_plan_source,
                    used_final_model=False,
                ),
                tool_plan_source=tool_plan_source,
                cache_hit=False,
                cache_key=cache_key,
            )
            yield {"event": "final", "data": result}
            return

        if not self.client:
            result = await self._finalize_response(
                session=session,
                conversation_id=conversation.id,
                conversation=conversation,
                reply="抱歉，当前大模型连接不可用，请检查配置后重试。",
                sources=sources,
                evidence_tags=evidence_tags,
                decision_summary=decision_summary,
                response_verdict=response_verdict,
                takeover=takeover,
                evidence_panel=evidence_panel,
                suggestion_card=suggestion_card,
                context_budget_summary=final_context["budget_summary"],
                tool_outputs=tool_outputs,
                tool_latency_ms=tool_latency_ms,
                response_latency_ms=response_latency_ms,
                tool_count=len(tool_outputs),
                fallback_used=fallback_used,
                model_name=None,
                tool_plan_source=tool_plan_source,
                cache_hit=False,
                cache_key=None,
            )
            yield {"event": "final", "data": result}
            return

        used_final_model = False
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=final_messages,
            )
            reply_text = response.choices[0].message.content or ""
            reply_text = re.sub(r"<think>.*?</think>", "", reply_text, flags=re.DOTALL).strip()
            used_final_model = True
        except Exception as exc:
            logger.error("Chat LLM error: %s", exc)
            reply_text = "抱歉，我暂时无法完成分析，请稍后再试。"
            cache_key = None

        result = await self._finalize_response(
            session=session,
            conversation_id=conversation.id,
            conversation=conversation,
            reply=reply_text,
            sources=sources,
            evidence_tags=evidence_tags,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            takeover=takeover,
            evidence_panel=evidence_panel,
            suggestion_card=suggestion_card,
            context_budget_summary=final_context["budget_summary"],
            tool_outputs=tool_outputs,
            tool_latency_ms=tool_latency_ms,
            response_latency_ms=response_latency_ms,
            tool_count=len(tool_outputs),
            fallback_used=fallback_used,
            model_name=self._determine_audit_model_name(
                tool_plan_source=tool_plan_source,
                used_final_model=used_final_model,
            ),
            tool_plan_source=tool_plan_source,
            cache_hit=False,
            cache_key=cache_key,
        )
        yield {"event": "final", "data": result}

    async def _select_tools_with_fallback(
        self,
        *,
        user: User,
        session: Session,
        query_text: str,
        lane: str,
        planned_tool_names: List[str],
        planning_messages: List[Dict[str, str]],
        conversation_id: int,
    ) -> Tuple[Optional[str], List[Dict[str, Any]], bool, int]:
        tool_started_at = time.perf_counter()
        if not planned_tool_names:
            return None, [], False, self._elapsed_ms(tool_started_at)

        direct_reply, tool_outputs = await self._try_native_tool_calling(
            user=user,
            session=session,
            lane=lane,
            query_text=query_text,
            allowed_tool_names=planned_tool_names,
            planning_messages=planning_messages,
            conversation_id=conversation_id,
        )
        if direct_reply is not None or tool_outputs:
            return direct_reply, tool_outputs, False, self._elapsed_ms(tool_started_at)

        allowed_tool_names = planned_tool_names
        fallback_outputs: List[Dict[str, Any]] = []
        for tool_name in planned_tool_names:
            extra_kwargs = {"query": query_text} if tool_name == "search_medical_guidelines" else {}
            fallback_outputs.append(
                execute_registered_tool(
                    tool_name,
                    user=user,
                    session=session,
                    allowed_tool_names=allowed_tool_names,
                    lane=lane,
                    query_text=query_text,
                    **extra_kwargs,
                )
            )
        return None, fallback_outputs, True, self._elapsed_ms(tool_started_at)

    async def _try_native_tool_calling(
        self,
        *,
        user: User,
        session: Session,
        lane: str,
        query_text: str,
        allowed_tool_names: List[str],
        planning_messages: List[Dict[str, str]],
        conversation_id: int,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        if not self.client:
            return None, []

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=planning_messages,
                tools=get_tool_definitions(tool_names=allowed_tool_names),
                tool_choice="auto",
            )
        except Exception as exc:
            logger.warning("Native tool calling unavailable for conversation %s: %s", conversation_id, exc)
            return None, []

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            tool_outputs = []
            for tool_call in tool_calls[:3]:
                tool_outputs.append(
                    execute_tool_call(
                        tool_call,
                        user=user,
                        session=session,
                        allowed_tool_names=allowed_tool_names,
                        lane=lane,
                        query_text=query_text,
                    )
                )
            return None, tool_outputs

        # Native tool-planning is advisory only. If the provider returns plain text
        # without tool calls, we fall back to deterministic local planning instead
        # of trusting that intermediate response as the final answer.
        return None, []

    def _status_event(
        self,
        *,
        stage: str,
        message: str,
        conversation_id: int,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "stage": stage,
            "message": message,
            "conversation_id": conversation_id,
        }
        if tool_name:
            payload["tool_name"] = tool_name
        return {"event": "status", "data": payload}

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int(round((time.perf_counter() - started_at) * 1000)))

    def _record_audit_event(self, *, session: Session, audit_record: Dict[str, Any]) -> Optional[AgentAuditEvent]:
        logger.info("Agent audit: %s", audit_record)
        if "user_id" not in audit_record or "conversation_id" not in audit_record:
            return None
        return persist_audit_record(session=session, audit_record=audit_record)

    def _persist_answer_replay(
        self,
        *,
        session: Session,
        conversation,
        conversation_id: int,
        message_id: int,
        audit_event: Optional[AgentAuditEvent],
        decision_summary: Dict[str, Any],
        response_verdict: Optional[Dict[str, Any]],
        sources: List[str],
        tool_outputs: List[Dict[str, Any]],
        context_budget_summary: Optional[Dict[str, Any]],
        tool_latency_ms: int,
        response_latency_ms: int,
        tool_count: int,
        fallback_used: bool,
        model_name: Optional[str],
        tool_plan_source: str,
        cache_hit: bool,
    ) -> None:
        if audit_event is None:
            return

        replay_record = build_answer_replay_record(
            user_id=conversation.user_id,
            conversation_id=conversation_id,
            chat_message_id=message_id,
            audit_event_id=audit_event.id if audit_event.id is not None else 0,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            context_budget_summary=context_budget_summary,
            tool_outputs=tool_outputs,
            rag_source_refs=sources,
            tool_latency_ms=tool_latency_ms,
            response_latency_ms=response_latency_ms,
            tool_count=tool_count,
            fallback_used=fallback_used,
            model_name=model_name,
            tool_plan_source=tool_plan_source,
            cache_hit=cache_hit,
        )
        try:
            persist_answer_replay_record(session=session, replay_record=replay_record)
        except Exception as exc:
            session.rollback()
            logger.warning(
                "ChatService: failed to persist answer replay for conversation %s: %s",
                conversation_id,
                exc,
            )

    def _build_responsibility_audit_record(
        self,
        *,
        user_id: int,
        conversation_id: int,
        decision_summary: Dict[str, Any],
        response_verdict: Optional[Dict[str, Any]],
        evidence_tags: List[str],
        context_budget_summary: Optional[Dict[str, Any]],
        tool_latency_ms: int,
        tool_count: int,
        response_latency_ms: int,
        fallback_used: bool,
        model_name: Optional[str],
        tool_plan_source: str,
        cache_hit: bool,
    ) -> Dict[str, Any]:
        policy = decision_summary.get("policy") or {}
        verdict_payload = response_verdict or self._build_response_verdict(decision_summary=decision_summary) or {}

        return build_audit_record(
            user_id=user_id,
            conversation_id=conversation_id,
            intent=decision_summary.get("intent"),
            lane=decision_summary.get("lane"),
            verdict=decision_summary.get("verdict"),
            selected_rule=policy.get("selected_rule"),
            policy_version=policy.get("policy_version"),
            response_mode=verdict_payload.get("response_mode") or policy.get("answer_mode"),
            evidence_sufficiency=verdict_payload.get("evidence_sufficiency")
            or self._public_evidence_sufficiency(policy.get("evidence_state")),
            degraded_reason=verdict_payload.get("degraded_reason"),
            human_escalation_required=bool(verdict_payload.get("human_escalation_required")),
            governance_version="agent_runtime_governance.v1",
            model_name=model_name,
            tool_plan_source=tool_plan_source,
            tool_used=decision_summary.get("tool_used", []),
            cache_hit=cache_hit,
            safety_level=decision_summary.get("safety_level"),
            evidence_tags=evidence_tags,
            context_budget_summary=context_budget_summary,
            tool_latency_ms=tool_latency_ms,
            tool_count=tool_count,
            response_latency_ms=response_latency_ms,
            fallback_used=fallback_used,
        )

    def _determine_audit_tool_plan_source(
        self,
        *,
        planned_tool_names: List[str],
        fallback_used: bool,
    ) -> str:
        if not planned_tool_names:
            return "no_tool_path"
        if fallback_used:
            return "local_fallback_planner"
        return "native_function_calling"

    def _determine_audit_model_name(
        self,
        *,
        tool_plan_source: str,
        used_final_model: bool,
    ) -> Optional[str]:
        if used_final_model or tool_plan_source == "native_function_calling":
            return self.model
        return None

    def _merge_decision_summary(
        self,
        *,
        cached_decision_summary: Any,
        fallback_decision_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = dict(fallback_decision_summary)
        if not isinstance(cached_decision_summary, dict):
            return merged

        merged_policy = dict(fallback_decision_summary.get("policy") or {})
        cached_policy = cached_decision_summary.get("policy")
        if isinstance(cached_policy, dict):
            merged_policy.update(cached_policy)

        for key, value in cached_decision_summary.items():
            if key == "policy":
                continue
            merged[key] = value

        if merged_policy:
            merged["policy"] = merged_policy
        return merged

    def _merge_response_verdict(
        self,
        *,
        cached_response_verdict: Any,
        fallback_response_verdict: Optional[Dict[str, Any]],
        decision_summary: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        merged = dict(fallback_response_verdict or self._build_response_verdict(decision_summary=decision_summary) or {})
        if not isinstance(cached_response_verdict, dict):
            return merged or None
        merged.update(cached_response_verdict)
        return merged

    def _merge_takeover(
        self,
        *,
        cached_takeover: Any,
        fallback_takeover: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if isinstance(cached_takeover, dict):
            return cached_takeover
        return fallback_takeover

    def _get_conversation(self, *, session: Session, user: User, conversation_id: Optional[int]):
        try:
            return conversation_service.get_or_create_conversation(
                session=session,
                user=user,
                conversation_id=conversation_id,
            )
        except ValueError:
            logger.warning(
                "ChatService: invalid conversation_id=%s for user_id=%s, starting new conversation",
                conversation_id,
                user.id,
            )
            return conversation_service.get_or_create_conversation(
                session=session,
                user=user,
                conversation_id=None,
            )

    def _build_cache_key(
        self,
        user_id: int,
        conversation_id: int,
        messages: List[Dict[str, str]],
    ) -> str:
        payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"chat_response:{user_id}:{conversation_id}:{fingerprint}"

    def _plan_tools(self, query: str, *, lane: str) -> List[str]:
        query_lower = query.lower()
        lane_defaults = {
            "general_health": ["get_user_profile_summary"],
            "report_interpretation": ["report_summary_lookup"],
            "trend_review": ["get_history_trends"],
            "medication_related": ["medication_summary_lookup"],
            "urgent_symptom": [],
            "diagnosis_sensitive": ["get_user_profile_summary", "latest_analysis_snapshot_lookup"],
        }
        planned = list(lane_defaults.get(lane, ["get_user_profile_summary"]))
        lane_keyword_map = {
            "general_health": [
                ("get_latest_risk_report", ["risk", "risk report", "result"]),
                ("recent_metric_anomaly_lookup", ["abnormal", "metric", "glucose", "blood sugar", "high", "low"]),
                ("search_medical_guidelines", ["what should", "pay attention", "advice", "guideline", "diet", "exercise"]),
            ],
            "report_interpretation": [
                ("report_comparison_lookup", ["compare", "comparison", "difference", "versus"]),
                ("get_uploaded_documents_summary", ["upload", "uploaded", "document", "ocr"]),
                ("search_medical_guidelines", ["guideline", "meaning"]),
            ],
            "trend_review": [
                ("recent_metric_anomaly_lookup", ["abnormal", "anomaly"]),
                ("latest_analysis_snapshot_lookup", ["analysis", "snapshot", "risk"]),
                ("search_medical_guidelines", ["guideline", "what should"]),
            ],
            "medication_related": [
                ("report_summary_lookup", ["report", "lab", "result"]),
                ("search_medical_guidelines", ["guideline", "caution", "interaction"]),
            ],
            "diagnosis_sensitive": [
                ("report_summary_lookup", ["report", "lab", "result"]),
                ("search_medical_guidelines", ["guideline", "criteria"]),
            ],
        }
        for tool_name, tokens in lane_keyword_map.get(lane, []):
            if any(token in query_lower for token in tokens):
                planned.append(tool_name)

        allowed = set(get_allowed_tool_names_for_lane(lane))
        filtered = [tool_name for tool_name in planned if tool_name in allowed]
        return list(dict.fromkeys(filtered))[:4]
        planned = ["get_user_profile_summary"]
        if any(token in query_lower for token in ["medication", "medications", "药物", "用药"]):
            planned.append("medication_summary_lookup")
        if any(token in query_lower for token in ["metric anomaly", "metric anomalies", "abnormal metrics", "异常指标", "异常"]):
            planned.append("recent_metric_anomaly_lookup")
        if any(token in query_lower for token in ["report comparison", "compare reports", "report diff", "对比报告", "报告对比"]):
            planned.append("report_comparison_lookup")
        keyword_map = [
            ("get_latest_risk_report", ["风险", "风险评估", "报告", "结果", "risk"]),
            ("get_history_trends", ["趋势", "历史", "最近", "变化", "波动", "trend"]),
            ("get_uploaded_documents_summary", ["体检", "报告单", "检查单", "上传", "ocr", "document"]),
            ("medication_summary_lookup", ["medication", "medications", "med summary", "药物", "用药", "用药总结"]),
            ("recent_metric_anomaly_lookup", ["metric anomaly", "metric anomalies", "abnormal metrics", "异常指标", "异常"]),
            ("report_comparison_lookup", ["report comparison", "compare reports", "report diff", "对比报告", "报告对比"]),
            ("report_summary_lookup", ["uploaded report", "latest report", "report summary", "ocr summary"]),
            ("recent_abnormal_metrics_lookup", ["abnormal metrics", "abnormal metric", "abnormal", "异常指标"]),
            ("latest_analysis_snapshot_lookup", ["analysis snapshot", "latest analysis", "snapshot", "分析快照"]),
            ("search_medical_guidelines", ["怎么办", "注意", "建议", "指南", "饮食", "运动", "guideline"]),
        ]
        for tool_name, tokens in keyword_map:
            if any(token.lower() in query_lower for token in tokens):
                planned.append(tool_name)
        return list(dict.fromkeys(planned))[:4]

    def _collect_evidence_tags(self, tool_outputs: List[Dict[str, Any]]) -> List[str]:
        new_tag_map = {
            "medication_summary_lookup": "medication_summary",
            "recent_metric_anomaly_lookup": "metric_anomalies",
            "report_comparison_lookup": "report_comparison",
        }
        tag_map = {
            "get_user_profile_summary": "profile_summary",
            "get_latest_risk_report": "latest_risk_report",
            "get_history_trends": "history_trends",
            "get_uploaded_documents_summary": "uploaded_documents",
            "report_summary_lookup": "report_summary",
            "recent_abnormal_metrics_lookup": "abnormal_metrics",
            "latest_analysis_snapshot_lookup": "analysis_snapshot",
            "search_medical_guidelines": "guideline_search",
        }
        tags = []
        for item in tool_outputs:
            if item.get("status") == "ok":
                tool_name = item.get("tool")
                if tool_name in new_tag_map:
                    tags.append(new_tag_map[tool_name])
                elif tool_name in tag_map:
                    tags.append(tag_map[tool_name])
        return list(dict.fromkeys(tags))

    def _format_evidence_metadata_brief(self, metadata: Optional[Dict[str, Any]]) -> str:
        if not isinstance(metadata, dict):
            return "quality=unknown"

        parts = [
            f"freshness={metadata.get('freshness', 'unknown')}",
            f"coverage={metadata.get('coverage', 'unknown')}",
            f"confidence={metadata.get('confidence', 'unknown')}",
        ]
        missing_fields = metadata.get("missing_fields") or []
        if missing_fields:
            parts.append(f"missing_fields={', '.join(str(field) for field in missing_fields[:3])}")
        if metadata.get("comparable_fields_count") is not None:
            parts.append(f"comparable_fields_count={metadata.get('comparable_fields_count')}")
        return ", ".join(parts)

    def _tool_quality_note(self, tool_outputs: List[Dict[str, Any]]) -> Optional[str]:
        notes = []
        for item in tool_outputs:
            if item.get("status") != "ok":
                continue
            result = item.get("result") or {}
            metadata = result.get("evidence_metadata") if isinstance(result, dict) else None
            if not isinstance(metadata, dict):
                continue
            flags = []
            coverage = metadata.get("coverage")
            freshness = metadata.get("freshness")
            confidence = metadata.get("confidence")
            if coverage in {"partial", "empty"}:
                flags.append(str(coverage))
            if freshness == "stale":
                flags.append("stale")
            if confidence == "low":
                flags.append("low confidence")
            if flags:
                notes.append(f"{item.get('tool', 'unknown_tool')}: {', '.join(flags)}")
        if not notes:
            return None
        return "; ".join(notes[:2])

    def _format_evidence_gap_classes(self, classes: List[str]) -> str:
        labels = {
            "retrieved guidance": "医学知识或参考资料",
            "profile data": "个人健康档案数据",
            "report values": "报告指标数据",
            "trend data": "历史趋势数据",
            "medication data": "用药数据",
            "symptom history": "症状历史",
            "conflicting evidence": "相互冲突的证据",
            "required context": "必要上下文",
            "personal data vs retrieved guidance": "个人数据与医学参考资料",
        }
        translated = [labels.get(str(item), str(item)) for item in classes if item]
        return "、".join(translated) if translated else "必要上下文"

    def _build_tool_evidence_text(self, tool_outputs: List[Dict[str, Any]]) -> str:
        blocks = []
        for item in tool_outputs:
            if item.get("status") != "ok":
                continue
            tool_name = item.get("tool", "unknown_tool")
            result = item.get("result", {}) or {}
            metadata_brief = self._format_evidence_metadata_brief(result.get("evidence_metadata"))
            summary = summarize_tool_output_for_prompt(tool_name, result)
            blocks.append(f"[{tool_name}] {metadata_brief}; {summary}")
        return "\n\n".join(blocks) if blocks else "暂无额外工具证据。"

    def _build_decision_summary(
        self,
        *,
        query: str,
        safety_result: Dict[str, str],
        planned_tool_names: List[str],
        tool_outputs: List[Dict[str, Any]],
        profile_evidence: Optional[Dict[str, Any]] = None,
        retrieval_evidence: Optional[str] = None,
        rag_quality_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lane = safety_result.get("lane", "general_health")
        tool_used = [item["tool"] for item in tool_outputs if item.get("status") == "ok"]
        policy = self._evaluate_response_policy(
            query=query,
            safety_result=safety_result,
            planned_tool_names=planned_tool_names,
            tool_outputs=tool_outputs,
            profile_evidence=profile_evidence,
            retrieval_evidence=retrieval_evidence,
            rag_quality_summary=rag_quality_summary,
        )
        return {
            "intent": self._infer_intent(query),
            "lane": lane,
            "verdict": self._determine_verdict(lane=lane, policy=policy),
            "tool_needed": bool(tool_used),
            "tool_used": tool_used,
            "safety_level": safety_result["safety_level"],
            "policy": policy,
        }

    def _build_response_verdict(
        self,
        *,
        decision_summary: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        policy = decision_summary.get("policy") or {}
        if not policy:
            return None

        response_mode = policy.get("answer_mode") or "direct_answer"
        medical_risk_level = policy.get("risk_level") or "low"
        if medical_risk_level not in {"low", "medium", "high"}:
            medical_risk_level = "high" if decision_summary.get("lane") == "urgent_symptom" else "low"

        evidence_state = policy.get("evidence_state")
        evidence_sufficiency = self._public_evidence_sufficiency(evidence_state)

        return {
            "schema_version": "response_verdict.v1",
            "response_mode": response_mode,
            "medical_risk_level": medical_risk_level,
            "evidence_sufficiency": evidence_sufficiency,
            "human_escalation_required": self._requires_human_escalation(
                lane=decision_summary.get("lane"),
                response_mode=response_mode,
                evidence_sufficiency=evidence_sufficiency,
            ),
            "degraded_reason": self._public_degraded_reason(
                lane=decision_summary.get("lane"),
                response_mode=response_mode,
                evidence_sufficiency=evidence_sufficiency,
                internal_degrade_reason=policy.get("degrade_reason"),
            ),
        }

    def _build_takeover(
        self,
        *,
        decision_summary: Dict[str, Any],
        response_verdict: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        policy = decision_summary.get("policy") or {}
        verdict = response_verdict or self._build_response_verdict(decision_summary=decision_summary) or {}

        lane = decision_summary.get("lane")
        response_mode = verdict.get("response_mode") or policy.get("answer_mode") or "direct_answer"
        evidence_sufficiency = verdict.get("evidence_sufficiency") or self._public_evidence_sufficiency(
            policy.get("evidence_state")
        )

        if lane == "urgent_symptom" or response_mode == "urgent_care_disclaimer":
            return {
                "schema_version": "takeover.v1",
                "status": "required",
                "trigger_reason": "high_risk",
                "summary": "Potential urgent symptoms require immediate human review and urgent care guidance.",
            }

        if response_mode == "refusal_with_disclaimer" and lane in {"medication_related", "diagnosis_sensitive"}:
            return {
                "schema_version": "takeover.v1",
                "status": "suppressed",
                "trigger_reason": "boundary_false_positive",
                "summary": "The backend evaluated human handoff but kept the turn within disclaimer-only guardrails.",
            }

        if evidence_sufficiency == "insufficient":
            return {
                "schema_version": "takeover.v1",
                "status": "required",
                "trigger_reason": "insufficient_evidence",
                "summary": "Available evidence is not sufficient for a safe answer, so human review is recommended.",
            }

        return None

    def _public_evidence_sufficiency(self, evidence_state: Optional[str]) -> str:
        if evidence_state in {"sufficient", "limited", "insufficient"}:
            return str(evidence_state)
        return "insufficient"

    def _requires_human_escalation(
        self,
        *,
        lane: Optional[str],
        response_mode: str,
        evidence_sufficiency: str,
    ) -> bool:
        if lane in {"urgent_symptom", "diagnosis_sensitive"}:
            return True
        if evidence_sufficiency == "insufficient":
            return True
        return response_mode == "refusal_with_disclaimer"

    def _public_degraded_reason(
        self,
        *,
        lane: Optional[str],
        response_mode: str,
        evidence_sufficiency: str,
        internal_degrade_reason: Optional[str],
    ) -> Optional[str]:
        if lane == "urgent_symptom" or response_mode == "urgent_care_disclaimer":
            return "urgent_risk_detected"
        if response_mode == "refusal_with_disclaimer":
            return "policy_guardrail"
        if internal_degrade_reason == "conflicting_evidence":
            return "conflicting_evidence"
        if internal_degrade_reason == "tool_unavailable":
            return "tool_unavailable"
        if internal_degrade_reason == "missing_required_context":
            return "missing_required_context"
        if response_mode == "clarify_missing_context":
            return "missing_required_context"
        if evidence_sufficiency != "sufficient":
            return "insufficient_evidence"
        return None

    def _build_suggestion_card(
        self,
        *,
        query: str,
        decision_summary: Dict[str, Any],
        evidence_tags: List[str],
    ) -> Optional[Dict[str, Any]]:
        if decision_summary.get("lane") != "general_health":
            return None
        policy = decision_summary.get("policy", {})
        if policy.get("answer_mode") not in {"direct_answer", "bounded_answer"}:
            return None
        intent = decision_summary.get("intent")
        if intent not in {
            "general_consultation",
            "guideline_lookup",
            "trend_review",
            "risk_explanation",
        }:
            return None

        headline_map = {
            "general_consultation": "建议先做稳妥的健康管理",
            "guideline_lookup": "建议按循证指引做后续管理",
            "trend_review": "建议结合趋势持续跟踪",
            "risk_explanation": "建议围绕风险结果做针对性管理",
        }
        actions_map = {
            "general_consultation": ["先从饮食和运动管理开始", "持续观察近期症状和指标变化"],
            "guideline_lookup": ["结合医学指南持续监测关键指标", "优先落实饮食和运动管理"],
            "trend_review": ["继续记录近期指标变化", "按趋势结果安排下一次复查"],
            "risk_explanation": ["结合风险结果复查异常指标", "如有加重症状尽快线下就医"],
        }
        key_actions = list(actions_map.get(intent, ["持续观察当前健康状态"]))
        if "profile_summary" in evidence_tags:
            key_actions.append("关注个人档案中的异常项")

        return {
            "headline": headline_map.get(intent, "建议继续观察并按需复查"),
            "risk_level": self._suggest_risk_level(query=query, decision_summary=decision_summary),
            "key_actions": key_actions[:3],
            "follow_up_hint": "建议在近期复盘关键指标变化，必要时联系医生进一步评估。",
            "when_to_seek_care": "如果出现胸痛、呼吸困难、持续加重或明显不适，请尽快线下就医。",
        }

    def _determine_verdict(self, *, lane: str, policy: Dict[str, Any]) -> str:
        if lane == "urgent_symptom":
            return "seek_urgent_care"
        if policy.get("evidence_state") != "sufficient":
            return "insufficient_evidence"
        if lane == "diagnosis_sensitive":
            return "needs_clinical_diagnosis"
        if lane == "report_interpretation":
            return "report_context_only"
        if lane == "trend_review":
            return "trend_context_only"
        if lane == "medication_related":
            return "medication_context_only"
        return "general_guidance"

    def _evaluate_response_policy(
        self,
        *,
        query: str,
        safety_result: Dict[str, str],
        planned_tool_names: List[str],
        tool_outputs: List[Dict[str, Any]],
        profile_evidence: Optional[Dict[str, Any]] = None,
        retrieval_evidence: Optional[str] = None,
        rag_quality_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        planned = list(dict.fromkeys(planned_tool_names))
        policy = evaluate_chat_policy(
            query=query,
            safety_result=safety_result,
            allowed_tool_names=planned,
            tool_outputs=tool_outputs,
            profile_evidence=profile_evidence,
            retrieval_evidence=retrieval_evidence,
            rag_quality_summary=rag_quality_summary,
        )
        policy["must_refuse"] = policy["answer_mode"] == "refusal_with_disclaimer"
        return policy

    def _determine_disclaimer_mode(
        self,
        *,
        lane: str,
        answer_mode: str,
        evidence_state: str,
        tool_availability: str,
    ) -> str:
        if answer_mode == "urgent_care_disclaimer" or lane == "urgent_symptom":
            return "urgent_care"
        if (
            answer_mode in {"refusal_with_disclaimer", "clarify_missing_context"}
            or lane in {"medication_related", "diagnosis_sensitive"}
            or evidence_state != "sufficient"
            or tool_availability != "full"
        ):
            return "conservative"
        return "none"

    def _build_lane_direct_reply(
        self,
        *,
        query: str,
        decision_summary: Dict[str, Any],
        tool_outputs: List[Dict[str, Any]],
        planned_tool_names: List[str],
        profile_evidence: Optional[Dict[str, Any]] = None,
        retrieval_evidence: Optional[str] = None,
        post_check: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        # 该函数只负责“保守直答模板”选择，不做工具执行与证据检索。
        # 进入条件通常是：风险 lane 明确、或证据门控要求降级输出。
        lane = decision_summary.get("lane")
        verdict = decision_summary.get("verdict")
        policy = decision_summary.get("policy", {})
        # 若 post_check 表示证据不足/冲突，这里用其结果覆盖旧策略，
        # 确保最终回复与最新门控判定保持一致。
        if post_check and not post_check.get("should_continue", True):
            policy = dict(policy)
            if post_check.get("evidence_state"):
                policy["evidence_state"] = post_check["evidence_state"]
            if post_check.get("tool_availability"):
                policy["tool_availability"] = post_check["tool_availability"]
            if post_check.get("degrade_reason"):
                policy["degrade_reason"] = post_check["degrade_reason"]
        gap = describe_evidence_gap(
            lane=lane or "general_health",
            allowed_tool_names=list(dict.fromkeys(planned_tool_names)),
            tool_outputs=tool_outputs,
            profile_evidence=profile_evidence,
            retrieval_evidence=retrieval_evidence,
        )
        quality_note = self._tool_quality_note(tool_outputs)

        if lane == "medication_related" and policy.get("answer_mode") == "refusal_with_disclaimer":
            medication = self._tool_result_for_name("medication_summary_lookup", tool_outputs).get("medication_summary") or {}
            items = medication.get("medication_items") or []
            if items:
                name = items[0].get("name") or "your current medication"
                return (
                    "我不能在这里建议你自行停药、启用药物、换药或调整剂量。"
                    f"目前系统只能确认你的用药记录中提到 {name}。"
                    "任何用药变化都需要先和线下医生确认。"
                )
            return (
                "我不能在这里建议你自行停药、启用药物、换药或调整剂量。"
                "在做任何用药调整前，请先咨询线下医生或开药医生。"
            )

        if lane == "diagnosis_sensitive":
            quality_suffix = f" 证据质量：{quality_note}。" if quality_note else ""
            return (
                "我不能仅凭当前聊天内容做出诊断或排除诊断。"
                f"目前还不确定，因为可用的{self._format_evidence_gap_classes(gap['classes'])}不足。"
                f"建议下一步：{gap['next_steps'][0]}{quality_suffix}"
            )

        if policy.get("evidence_state") != "sufficient":
            if gap["degrade_reason"] == "conflicting_evidence":
                reason_text = f"当前{self._format_evidence_gap_classes(gap['classes'])}之间存在不一致"
            else:
                reason_text = f"仍缺少可靠的{self._format_evidence_gap_classes(gap['classes'])}"
            if quality_note:
                reason_text = f"{reason_text}。证据质量：{quality_note}"
            lane_openers = {
                "general_health": "我现在只能给出保守的一般健康建议。",
                "report_interpretation": "我现在还不能安全地解释这份报告。",
                "trend_review": "我现在还不能安全地判断趋势变化。",
                "medication_related": "我现在还不能安全地总结你的用药细节。",
            }
            opener = lane_openers.get(lane or "", "我现在还不能安全地回答这个问题。")
            return f"{opener}原因是{reason_text}。建议下一步：{gap['next_steps'][0]}"
        if lane == "diagnosis_sensitive":
            if verdict == "insufficient_evidence":
                return "目前证据不足，无法根据现有聊天信息判断或排除具体诊断。请尽快线下就医，由临床医生结合检查结果做正式评估。"
            return "我不能根据当前聊天内容为你做出诊断或给出诊断确定性结论。请尽快线下就医，由临床医生结合检查结果完成正式诊断。"
        if lane == "report_interpretation" and verdict == "insufficient_evidence":
            return "我目前缺少可用的报告内容，无法安全解释你的最新报告。请上传报告或提供具体指标数值，我再按现有信息帮你做保守说明。"
        if lane == "medication_related":
            medication = self._tool_result_for_name("medication_summary_lookup", tool_outputs).get("medication_summary") or {}
            items = medication.get("medication_items") or []
            if policy.get("answer_mode") == "refusal_with_disclaimer":
                if items:
                    name = items[0].get("name") or "当前药物"
                    return f"我不能根据当前聊天为你做停药、换药或剂量调整决定。系统里能确认的药物事实包括 {name}，但是否需要停用、加量或改方案必须由线下医生结合病情确认。"
                return "我不能根据当前聊天为你做停药、换药或剂量调整决定。请尽快联系线下医生或开药医生确认下一步方案。"
            if not items:
                return "我目前没有足够的既往用药事实，无法安全总结你的当前用药。请提供药名或上传相关报告，并在线下医生指导下确认是否需要调整。"
            item = items[0]
            name = item.get("name") or "当前用药"
            dose = item.get("dose")
            unit = item.get("unit") or ""
            frequency = item.get("frequency")
            parts = [f"我目前能确认的用药信息包括：{name}"]
            if dose is not None:
                parts.append(f"{dose}{unit}".strip())
            if frequency:
                parts.append(str(frequency))
            parts.append("这里只能做事实性总结，不能替代线下医生做启停、换药或剂量调整决定。")
            return "，".join(parts)
        if lane == "trend_review" and verdict == "insufficient_evidence":
            return "当前可用的历史记录不足，暂时不能安全回答趋势变化问题。请补充至少两次可比较的记录，或在线下复查后再一起看趋势。"
        if lane == "general_health" and verdict == "insufficient_evidence":
            return "目前可用证据有限，我只能给出保守的一般健康建议。若症状持续、加重或你担心存在明确疾病，请尽快线下就医。"
        return None

    def _build_evidence_panel(
        self,
        *,
        sources: List[str],
        evidence_tags: List[str],
        decision_summary: Dict[str, Any],
        tool_outputs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        ordered_tags = list(dict.fromkeys(evidence_tags))
        if not ordered_tags:
            if sources:
                ordered_tags = ["guideline_search"]
            else:
                return None

        return {
            "chips": [
                {"key": tag, "label": self._evidence_label(tag)}
                for tag in ordered_tags
            ],
            "sections": [
                self._build_evidence_section(
                    tag=tag,
                    sources=sources,
                    decision_summary=decision_summary,
                    tool_outputs=tool_outputs,
                )
                for tag in ordered_tags
            ],
        }

    def _build_evidence_section(
        self,
        *,
        tag: str,
        sources: List[str],
        decision_summary: Dict[str, Any],
        tool_outputs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        label = self._evidence_label(tag)
        return {
            "label": label,
            "summary": self._evidence_summary(tag, label),
            "key_facts": self._build_evidence_key_facts(tag=tag, sources=sources, tool_outputs=tool_outputs),
            "decision_basis": self._evidence_decision_basis(tag=tag, label=label, decision_summary=decision_summary),
            "source_refs": self._evidence_source_refs(tag=tag, sources=sources),
            "source_items": self._build_evidence_source_items(tag=tag, sources=sources, tool_outputs=tool_outputs),
        }

    def _evidence_label(self, tag: str) -> str:
        if tag == "medication_summary":
            return "Medication Summary"
        if tag == "metric_anomalies":
            return "Metric Anomalies"
        if tag == "report_comparison":
            return "Report Comparison"
        return {
            "profile_summary": "Health Profile",
            "latest_risk_report": "Risk Report",
            "history_trends": "Trend Review",
            "uploaded_documents": "Document Evidence",
            "report_summary": "Report Summary",
            "abnormal_metrics": "Abnormal Metrics",
            "analysis_snapshot": "Analysis Snapshot",
            "guideline_search": "Guideline Evidence",
            "urgent_route": "Urgent Safety",
        }.get(tag, "Evidence Context")

    def _evidence_summary(self, tag: str, label: str) -> str:
        if tag == "medication_summary":
            return "A bounded medication summary influenced the answer."
        if tag == "metric_anomalies":
            return "Recent metric anomalies influenced the answer."
        if tag == "report_comparison":
            return "A bounded report comparison influenced the answer."
        return {
            "profile_summary": "Stored profile context influenced the answer.",
            "latest_risk_report": "The latest saved risk context influenced the answer.",
            "history_trends": "Recent history trends influenced the answer.",
            "uploaded_documents": "Uploaded document findings informed the answer.",
            "report_summary": "A persisted uploaded-report summary influenced the answer.",
            "abnormal_metrics": "Recent abnormal metrics influenced the answer.",
            "analysis_snapshot": "The latest saved analysis snapshot influenced the answer.",
            "guideline_search": "Retrieved guidance supported the recommendation.",
            "urgent_route": "The request triggered urgent safety escalation guidance.",
        }.get(tag, f"{label} influenced the answer.")

    def _build_evidence_key_facts(
        self,
        *,
        tag: str,
        sources: List[str],
        tool_outputs: List[Dict[str, Any]],
    ) -> List[str]:
        if tag == "urgent_route":
            return ["Urgent safety symptoms triggered immediate escalation guidance."]

        tool_name = self._tool_name_for_tag(tag)
        tool_result: Dict[str, Any] = {}
        if tool_name:
            for item in tool_outputs:
                if item.get("status") == "ok" and item.get("tool") == tool_name:
                    tool_result = item.get("result", {}) or {}
                    break

        if tag == "medication_summary":
            summary = tool_result.get("medication_summary") or {}
            items = summary.get("medication_items") or []
            if items:
                rendered = []
                for medication in items[:2]:
                    name = medication.get("name") or "Medication"
                    dose = medication.get("dose")
                    unit = medication.get("unit") or ""
                    rendered.append(f"{name} {dose or ''}{unit}".strip())
                return rendered[:3]
            return ["Bounded medication summary was reviewed."]
        if tag == "metric_anomalies":
            items = tool_result.get("items") or []
            facts = []
            for metric in items[:2]:
                metric_key = metric.get("metric_key") or metric.get("display_name")
                status = metric.get("status")
                if metric_key and status:
                    facts.append(f"{metric_key}: {status}")
            if facts:
                return facts[:3]
            return ["Recent metric anomalies were reviewed."]
        if tag == "report_comparison":
            summary = tool_result.get("summary") or {}
            delta_items = tool_result.get("delta_items") or []
            facts = []
            if tool_result.get("baseline_file_name") or tool_result.get("comparison_file_name"):
                facts.append(
                    f"Compared {tool_result.get('baseline_file_name') or 'baseline report'} to {tool_result.get('comparison_file_name') or 'comparison report'}"
                )
            if summary.get("count") is not None:
                facts.append(f"Bounded differences: {summary['count']}")
            for item in delta_items[:2]:
                field = item.get("field")
                change = item.get("change")
                if field and change:
                    facts.append(f"{field}: {change}")
            if facts:
                return facts[:3]
            return ["Two persisted reports were compared."]

        facts: List[str] = []
        if tag == "profile_summary":
            if tool_result.get("glucose_fasting") is not None:
                facts.append(f"Fasting glucose context: {tool_result['glucose_fasting']}")
            for abnormal_flag in (tool_result.get("abnormal_flags") or [])[:2]:
                facts.append(str(abnormal_flag))
            if tool_result.get("age") is not None:
                facts.append(f"Age context: {tool_result['age']}")
        elif tag == "latest_risk_report":
            risk_report = tool_result.get("risk_report")
            if isinstance(risk_report, dict) and risk_report:
                facts.append(f"Latest risk areas: {', '.join(list(risk_report.keys())[:3])}")
            elif tool_result.get("has_risk_report"):
                facts.append("A saved risk report was reviewed.")
        elif tag == "history_trends":
            count = tool_result.get("count")
            if count:
                facts.append(f"Recent trend records reviewed: {count}")
        elif tag == "uploaded_documents":
            count = tool_result.get("count")
            if count:
                facts.append(f"Uploaded reports reviewed: {count}")
            for item in (tool_result.get("items") or [])[:1]:
                if item.get("file_name"):
                    facts.append(f"Recent report: {item['file_name']}")
        elif tag == "report_summary":
            if tool_result.get("file_name"):
                facts.append(f"Report reviewed: {tool_result['file_name']}")
            report_summary = tool_result.get("report_summary")
            if isinstance(report_summary, dict):
                summary_text = report_summary.get("narrative_summary")
                if summary_text:
                    facts.append(str(summary_text))
                metrics = report_summary.get("metrics") or []
                for metric in metrics[:2]:
                    metric_key = metric.get("metric_key")
                    value = metric.get("value")
                    if metric_key is not None and value is not None:
                        facts.append(f"{metric_key}: {value}")
        elif tag == "abnormal_metrics":
            summary = tool_result.get("summary") or {}
            if summary.get("count") is not None:
                facts.append(f"Abnormal metrics found: {summary['count']}")
            for item in (tool_result.get("items") or [])[:2]:
                if item.get("metric_key") and item.get("status"):
                    facts.append(f"{item['metric_key']}: {item['status']}")
        elif tag == "analysis_snapshot":
            findings = tool_result.get("top_findings") or []
            if findings:
                top = findings[0]
                facts.append(f"Top finding: {top.get('label') or top.get('key')}")
            ckm = tool_result.get("ckm") or {}
            if ckm.get("stage_name"):
                facts.append(f"CKM stage: {ckm['stage_name']}")
        elif tag == "guideline_search":
            if sources:
                facts.append(f"Retrieved references: {', '.join(sources[:2])}")
            if tool_result.get("matches_found"):
                facts.append("Knowledge-base guidance was retrieved for this question.")

        if not facts:
            facts.append(
                {
                    "profile_summary": "Stored health profile context was considered.",
                    "latest_risk_report": "Saved risk context was considered.",
                    "history_trends": "Recent trend context was considered.",
                    "uploaded_documents": "Uploaded medical report context was considered.",
                    "report_summary": "Stored uploaded-report summary was considered.",
                    "abnormal_metrics": "Recent abnormal metrics were considered.",
                    "analysis_snapshot": "The latest analysis snapshot was considered.",
                    "guideline_search": "Retrieved medical guidance informed the answer.",
                }.get(tag, "Relevant evidence context was considered.")
            )
        return facts[:3]

    def _evidence_decision_basis(
        self,
        *,
        tag: str,
        label: str,
        decision_summary: Dict[str, Any],
    ) -> str:
        intent = decision_summary.get("intent", "general_consultation")
        if tag == "urgent_route":
            return "Potentially urgent symptoms shifted the reply to immediate safety guidance."
        return f"The reply prioritized {label.lower()} while answering a {intent.replace('_', ' ')} request."

    def _evidence_source_refs(self, *, tag: str, sources: List[str]) -> List[str]:
        if tag == "guideline_search":
            return sources[:3] or ["guideline_search"]
        if tag == "urgent_route":
            return ["urgent_route"]
        return [tag]

    def _build_evidence_source_items(
        self,
        *,
        tag: str,
        sources: List[str],
        tool_outputs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        tool_name = self._tool_name_for_tag(tag)
        tool_result = self._tool_result_for_name(tool_name, tool_outputs)

        if tag == "urgent_route":
            return [
                self._source_item(
                    source_type="profile",
                    title="Urgent safety review",
                    snippet="Potential urgent symptoms triggered immediate escalation guidance.",
                    timestamp=None,
                )
            ]

        if tag == "medication_summary":
            summary = tool_result.get("medication_summary") or {}
            items = summary.get("medication_items") or []
            snippet_bits = []
            for medication in items[:2]:
                name = medication.get("name") or "Medication"
                dose = medication.get("dose")
                unit = medication.get("unit") or ""
                frequency = medication.get("frequency")
                part = f"{name}"
                if dose is not None:
                    part += f" {dose}{unit}"
                if frequency:
                    part += f" {frequency}"
                snippet_bits.append(part)
            snippet = "; ".join(snippet_bits) if snippet_bits else "Bounded medication summary was reviewed."
            source_type = "report" if tool_result.get("summary_source") == "medical_document_ocr_summary" else "profile"
            return [
                self._source_item(
                    source_type=source_type,
                    title=tool_result.get("file_name") or "Medication summary",
                    snippet=snippet,
                    timestamp=None,
                )
            ]

        if tag == "metric_anomalies":
            items = []
            for metric in (tool_result.get("items") or [])[:2]:
                items.append(
                    self._source_item(
                        source_type="trend",
                        title=metric.get("display_name") or metric.get("metric_key") or "Abnormal metric",
                        snippet=self._abnormal_metric_snippet(metric),
                        timestamp=tool_result.get("evaluated_at"),
                        relevance=self._source_item_relevance(metric),
                    )
                )
            if items:
                return items
            summary = tool_result.get("summary") or {}
            return [
                self._source_item(
                    source_type="trend",
                    title="Metric anomaly summary",
                    snippet=summary.get("message") or "Recent metric anomalies were reviewed.",
                    timestamp=tool_result.get("evaluated_at"),
                )
            ]

        if tag == "report_comparison":
            delta_items = tool_result.get("delta_items") or []
            if delta_items:
                first_delta = delta_items[0]
                snippet = f"{first_delta.get('field')}: {first_delta.get('baseline_value')} -> {first_delta.get('comparison_value')}"
            else:
                snippet = "Two persisted reports were compared."
            title = f"{tool_result.get('baseline_file_name') or 'Baseline report'} vs {tool_result.get('comparison_file_name') or 'Comparison report'}"
            return [
                self._source_item(
                    source_type="report",
                    title=title,
                    snippet=snippet,
                    timestamp=None,
                )
            ]

        if tag == "profile_summary":
            snippet_bits: List[str] = []
            if tool_result.get("age") is not None:
                snippet_bits.append(f"Age {tool_result['age']}")
            if tool_result.get("gender"):
                snippet_bits.append(f"Gender {tool_result['gender']}")
            if tool_result.get("bmi") is not None:
                snippet_bits.append(f"BMI {tool_result['bmi']}")
            if tool_result.get("glucose_fasting") is not None:
                snippet_bits.append(f"Fasting glucose {tool_result['glucose_fasting']}")
            for abnormal_flag in (tool_result.get("abnormal_flags") or [])[:2]:
                snippet_bits.append(str(abnormal_flag))
            snippet = "; ".join(snippet_bits) if snippet_bits else "Stored profile context was reviewed."
            return [
                self._source_item(
                    source_type="profile",
                    title="Stored profile snapshot",
                    snippet=snippet,
                    timestamp=None,
                )
            ]

        if tag == "latest_risk_report":
            risk_report = tool_result.get("risk_report")
            return [
                self._source_item(
                    source_type="report",
                    title="Latest risk report",
                    snippet=self._snapshot_projection_snippet(risk_report),
                    timestamp=None,
                )
            ]

        if tag == "history_trends":
            items = tool_result.get("items") or []
            latest_item = items[0] if items else {}
            snippet_bits = []
            if tool_result.get("count") is not None:
                snippet_bits.append(f"{tool_result['count']} trend records reviewed")
            if latest_item.get("record_date"):
                snippet_bits.append(f"Latest record {latest_item['record_date']}")
            if latest_item.get("source"):
                snippet_bits.append(f"Source {latest_item['source']}")
            return [
                self._source_item(
                    source_type="trend",
                    title="Recent trend review",
                    snippet="; ".join(snippet_bits) if snippet_bits else "Recent trend context was reviewed.",
                    timestamp=latest_item.get("record_date"),
                )
            ]

        if tag == "uploaded_documents":
            items = []
            for document in (tool_result.get("items") or [])[:2]:
                items.append(
                    self._source_item(
                        source_type="report",
                        title=document.get("file_name") or "Uploaded report",
                        snippet=self._document_source_snippet(document),
                        timestamp=document.get("upload_date"),
                    )
                )
            return items or [
                self._source_item(
                    source_type="report",
                    title="Uploaded report",
                    snippet="Uploaded document evidence was reviewed.",
                    timestamp=None,
                )
            ]

        if tag == "report_summary":
            report_summary = tool_result.get("report_summary") or {}
            snippet_bits = []
            if report_summary.get("narrative_summary"):
                snippet_bits.append(str(report_summary["narrative_summary"]))
            for metric in (report_summary.get("metrics") or [])[:2]:
                metric_key = metric.get("metric_key")
                value = metric.get("value")
                unit = metric.get("unit") or ""
                if metric_key is not None and value is not None:
                    snippet_bits.append(f"{metric_key}: {value}{unit}")
            return [
                self._source_item(
                    source_type="report",
                    title=tool_result.get("file_name") or "Report summary",
                    snippet=self._ocr_projection_snippet(report_summary, fallback="Persisted report summary was reviewed."),
                    timestamp=tool_result.get("upload_date"),
                )
            ]

        if tag == "abnormal_metrics":
            items = []
            for metric in (tool_result.get("items") or [])[:2]:
                items.append(
                    self._source_item(
                        source_type="trend",
                        title=metric.get("display_name") or metric.get("metric_key") or "Abnormal metric",
                        snippet=self._abnormal_metric_snippet(metric),
                        timestamp=tool_result.get("evaluated_at"),
                        relevance=self._source_item_relevance(metric),
                    )
                )
            if items:
                return items
            summary = tool_result.get("summary") or {}
            return [
                self._source_item(
                    source_type="trend",
                    title="Abnormal metrics summary",
                    snippet=summary.get("message") or "Recent abnormal metrics were reviewed.",
                    timestamp=tool_result.get("evaluated_at"),
                )
            ]

        if tag == "analysis_snapshot":
            return [
                self._source_item(
                    source_type="report",
                    title="Latest analysis snapshot",
                    snippet=self._snapshot_projection_snippet(tool_result),
                    timestamp=tool_result.get("captured_at"),
                )
            ]

        if tag == "guideline_search":
            snippet = "Retrieved guidance supported the recommendation."
            if tool_result.get("context"):
                first_line = str(tool_result["context"]).splitlines()[0].strip()
                if first_line:
                    snippet = first_line
            title = sources[0] if sources else "Guideline evidence"
            return [
                self._source_item(
                    source_type="guideline",
                    title=title,
                    snippet=snippet,
                    timestamp=None,
                )
            ]

        return [
            self._source_item(
                source_type="report" if tag in {"latest_risk_report", "report_summary", "analysis_snapshot"} else "profile",
                title=self._evidence_label(tag),
                snippet=self._evidence_summary(tag, self._evidence_label(tag)),
                timestamp=None,
            )
        ]

    def _tool_result_for_name(self, tool_name: Optional[str], tool_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not tool_name:
            return {}
        for item in tool_outputs:
            if item.get("status") == "ok" and item.get("tool") == tool_name:
                result = item.get("result", {}) or {}
                if isinstance(result, dict):
                    return result
        return {}

    def _source_item(
        self,
        *,
        source_type: str,
        title: str,
        snippet: str,
        timestamp: Optional[str],
        confidence: Optional[float] = None,
        relevance: Optional[float] = None,
    ) -> Dict[str, Any]:
        item = {
            "source_type": source_type,
            "title": title,
            "snippet": self._clip_text(snippet),
            "timestamp": timestamp,
        }
        if confidence is not None:
            item["confidence"] = confidence
        if relevance is not None:
            item["relevance"] = relevance
        return item

    def _snapshot_projection_snippet(self, projection: Any) -> str:
        if not isinstance(projection, dict):
            return "Recent risk context was reviewed."

        parts: List[str] = []
        findings = projection.get("top_findings") or projection.get("findings") or []
        for finding in findings[:2]:
            if not isinstance(finding, dict):
                continue
            label = finding.get("label") or finding.get("key")
            risk_level = finding.get("risk_level")
            probability = finding.get("probability")
            if label and risk_level and probability is not None:
                parts.append(f"{label} {risk_level} ({probability})")
            elif label and risk_level:
                parts.append(f"{label} {risk_level}")
            elif label and probability is not None:
                parts.append(f"{label} {probability}")
            elif label:
                parts.append(str(label))

        ckm = projection.get("ckm") or {}
        if isinstance(ckm, dict) and (ckm.get("stage") is not None or ckm.get("stage_name")):
            stage_bits = []
            if ckm.get("stage") is not None:
                stage_bits.append(f"stage {ckm['stage']}")
            if ckm.get("stage_name"):
                stage_bits.append(str(ckm["stage_name"]))
            parts.append("CKM " + ", ".join(stage_bits))

        if projection.get("captured_at"):
            parts.append(f"captured_at {projection['captured_at']}")

        if parts:
            return "; ".join(parts)
        if projection.get("has_analysis_snapshot"):
            return "Recent risk context was reviewed."
        return "Recent risk context was reviewed."

    def _ocr_projection_snippet(self, projection: Any, *, fallback: str) -> str:
        if not isinstance(projection, dict):
            return fallback

        parts: List[str] = []
        patient_context = projection.get("patient_context") or {}
        if isinstance(patient_context, dict):
            for key in ("Age", "Gender", "Height", "Weight"):
                if patient_context.get(key) is not None:
                    parts.append(f"{key} {patient_context[key]}")

        metrics = projection.get("metrics") or []
        for metric in metrics[:2]:
            if not isinstance(metric, dict):
                continue
            metric_key = metric.get("metric_key")
            value = metric.get("value")
            unit = metric.get("unit") or ""
            if metric_key is not None and value is not None:
                parts.append(f"{metric_key} {value}{unit}")

        narrative = projection.get("narrative_summary")
        if narrative:
            parts.append(str(narrative))

        extra_findings_count = projection.get("extra_findings_count")
        if extra_findings_count:
            parts.append(f"{extra_findings_count} extra findings")

        return "; ".join(parts) if parts else fallback

    def _clip_text(self, text: Any, limit: int = 180) -> str:
        normalized = " ".join(str(text or "").split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    def _document_source_snippet(self, document: Dict[str, Any]) -> str:
        ocr_summary = document.get("ocr_summary")
        summary_text = self._ocr_projection_snippet(
            ocr_summary,
            fallback="Uploaded document evidence was reviewed.",
        )
        if summary_text:
            return summary_text
        if document.get("file_name"):
            return f"Uploaded report {document['file_name']} was reviewed."
        return "Uploaded report evidence was reviewed."

    def _abnormal_metric_snippet(self, metric: Dict[str, Any]) -> str:
        metric_key = metric.get("metric_key") or "metric"
        status = metric.get("status")
        value = metric.get("value")
        unit = metric.get("unit") or ""
        parts = []
        if status:
            parts.append(f"{metric_key} {status}")
        if value is not None:
            parts.append(f"value {value}{unit}")
        if metric.get("message"):
            parts.append(str(metric["message"]))
        return "; ".join(parts) if parts else f"{metric_key} was reviewed."

    def _source_item_relevance(self, metric: Dict[str, Any]) -> Optional[float]:
        relevance = metric.get("relevance")
        if isinstance(relevance, (int, float)):
            return float(relevance)
        return None

    def _tool_name_for_tag(self, tag: str) -> Optional[str]:
        if tag == "medication_summary":
            return "medication_summary_lookup"
        if tag == "metric_anomalies":
            return "recent_metric_anomaly_lookup"
        if tag == "report_comparison":
            return "report_comparison_lookup"
        return {
            "profile_summary": "get_user_profile_summary",
            "latest_risk_report": "get_latest_risk_report",
            "history_trends": "get_history_trends",
            "uploaded_documents": "get_uploaded_documents_summary",
            "report_summary": "report_summary_lookup",
            "abnormal_metrics": "recent_abnormal_metrics_lookup",
            "analysis_snapshot": "latest_analysis_snapshot_lookup",
            "guideline_search": "search_medical_guidelines",
        }.get(tag)

    def _suggest_risk_level(self, *, query: str, decision_summary: Dict[str, Any]) -> str:
        if decision_summary.get("safety_level") == "urgent":
            return "high"

        query_lower = query.lower()
        if any(token in query_lower for token in ["risk", "高", "异常", "偏高", "升高"]):
            return "medium"
        return "low"

    def _infer_intent(self, query: str) -> str:
        if any(token in query for token in ["风险", "评估", "报告", "risk"]):
            return "risk_explanation"
        if any(token in query for token in ["趋势", "历史", "变化", "最近", "trend"]):
            return "trend_review"
        if any(token in query for token in ["指南", "建议", "怎么办", "注意", "guideline"]):
            return "guideline_lookup"
        return "general_consultation"

    def _build_urgent_response(
        self,
        *,
        user: User,
        conversation_id: int,
        session: Session,
        safety_result: Dict[str, str],
        response_latency_ms: int,
        tool_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        reply = (
            "你提到的情况可能存在急性风险。请立即就医，或尽快联系急诊/线下医生。"
            "如果症状正在加重，请马上寻求现场医疗帮助。"
        )
        urgent_safety_result = {"lane": "urgent_symptom", "risk_level": "high", **safety_result}
        decision_summary = {
            "intent": "urgent_triage",
            "lane": "urgent_symptom",
            "verdict": "seek_urgent_care",
            "tool_needed": False,
            "tool_used": [],
            "safety_level": safety_result["safety_level"],
            "policy": self._evaluate_response_policy(
                query="",
                safety_result=urgent_safety_result,
                planned_tool_names=[],
                tool_outputs=[],
            ),
        }
        evidence_panel = self._build_evidence_panel(
            sources=[],
            evidence_tags=["urgent_route"],
            decision_summary=decision_summary,
            tool_outputs=[],
        )
        response_verdict = self._build_response_verdict(decision_summary=decision_summary)
        takeover = self._build_takeover(
            decision_summary=decision_summary,
            response_verdict=response_verdict,
        )
        audit_record = self._build_responsibility_audit_record(
            user_id=user.id,
            conversation_id=conversation_id,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            evidence_tags=["urgent_route"],
            context_budget_summary=None,
            tool_latency_ms=0,
            tool_count=0,
            response_latency_ms=response_latency_ms,
            fallback_used=False,
            model_name=None,
            tool_plan_source="urgent_short_circuit",
            cache_hit=False,
        )
        audit_event = self._record_audit_event(session=session, audit_record=audit_record)
        conversation = conversation_service.get_or_create_conversation(
            session=session,
            user=user,
            conversation_id=conversation_id,
        )
        message = conversation_service.append_message(
            session=session,
            conversation=conversation,
            role="assistant",
            content=reply,
            sources=[],
            evidence_tags=["urgent_route"],
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            takeover=takeover,
            evidence_panel=evidence_panel,
            suggestion_card=None,
        )
        self._persist_answer_replay(
            session=session,
            conversation=conversation,
            conversation_id=conversation_id,
            message_id=message.id,
            audit_event=audit_event,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            sources=[],
            tool_outputs=tool_outputs or [],
            context_budget_summary=None,
            tool_latency_ms=0,
            response_latency_ms=response_latency_ms,
            tool_count=0,
            fallback_used=False,
            model_name=None,
            tool_plan_source="urgent_short_circuit",
            cache_hit=False,
        )
        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "sources": [],
            "evidence_tags": ["urgent_route"],
            "decision_summary": decision_summary,
            "response_verdict": response_verdict,
            "takeover": takeover,
            "evidence_panel": evidence_panel,
            "suggestion_card": None,
        }

    async def _finalize_response(
        self,
        *,
        session: Session,
        conversation_id: int,
        conversation,
        reply: str,
        sources: List[str],
        evidence_tags: List[str],
        decision_summary: Dict[str, Any],
        response_verdict: Optional[Dict[str, Any]],
        takeover: Optional[Dict[str, Any]],
        evidence_panel: Optional[Dict[str, Any]],
        suggestion_card: Optional[Dict[str, Any]],
        context_budget_summary: Optional[Dict[str, Any]],
        tool_outputs: List[Dict[str, Any]],
        tool_latency_ms: int,
        response_latency_ms: int,
        tool_count: int,
        fallback_used: bool,
        model_name: Optional[str],
        tool_plan_source: str,
        cache_hit: bool,
        cache_key: Optional[str],
    ) -> Dict[str, Any]:
        result = {
            "conversation_id": conversation_id,
            "reply": reply,
            "sources": sources,
            "evidence_tags": evidence_tags,
            "decision_summary": decision_summary,
            "response_verdict": response_verdict,
            "takeover": takeover,
            "evidence_panel": evidence_panel,
            "suggestion_card": suggestion_card,
        }
        audit_record = self._build_responsibility_audit_record(
            user_id=conversation.user_id,
            conversation_id=conversation_id,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            evidence_tags=evidence_tags,
            context_budget_summary=context_budget_summary,
            tool_latency_ms=tool_latency_ms,
            tool_count=tool_count,
            response_latency_ms=response_latency_ms,
            fallback_used=fallback_used,
            model_name=model_name,
            tool_plan_source=tool_plan_source,
            cache_hit=cache_hit,
        )
        audit_event = self._record_audit_event(session=session, audit_record=audit_record)
        message = conversation_service.append_message(
            session=session,
            conversation=conversation,
            role="assistant",
            content=reply,
            sources=sources,
            evidence_tags=evidence_tags,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            takeover=takeover,
            evidence_panel=evidence_panel,
            suggestion_card=suggestion_card,
        )
        self._persist_answer_replay(
            session=session,
            conversation=conversation,
            conversation_id=conversation_id,
            message_id=message.id,
            audit_event=audit_event,
            decision_summary=decision_summary,
            response_verdict=response_verdict,
            sources=sources,
            tool_outputs=tool_outputs,
            context_budget_summary=context_budget_summary,
            tool_latency_ms=tool_latency_ms,
            response_latency_ms=response_latency_ms,
            tool_count=tool_count,
            fallback_used=fallback_used,
            model_name=model_name,
            tool_plan_source=tool_plan_source,
            cache_hit=cache_hit,
        )
        if cache_key:
            await CacheManager.set(cache_key, result, ttl=3600)
            logger.info("Cached chat response [%s...] for 1h", cache_key[:24])
        return result

    def _extract_sources(self, rag_context: Optional[str]) -> List[str]:
        if not rag_context:
            return []
        matches = re.findall(r"Ref \d+ - (.*?)]", rag_context)
        return list(dict.fromkeys(matches))

    def _search_rag_context_with_quality(self, query_text: str, *, k: int = 3) -> Dict[str, Any]:
        search_with_quality = getattr(rag_service, "search_context_with_quality", None)
        if callable(search_with_quality):
            try:
                result = search_with_quality(query_text, k=k)
            except TypeError:
                result = search_with_quality(query_text)
            if isinstance(result, dict):
                context = result.get("context")
                quality_summary = result.get("rag_quality_summary")
                if isinstance(context, str) and isinstance(quality_summary, dict):
                    return {"context": context, "rag_quality_summary": quality_summary}

        context = ""
        search_context = getattr(rag_service, "search_context", None)
        if callable(search_context):
            try:
                context = search_context(query_text, k=k)
            except TypeError:
                context = search_context(query_text)
        if not isinstance(context, str):
            context = ""
        return {
            "context": context,
            "rag_quality_summary": None,
        }

    def _build_system_prompt(self) -> str:
        return (
            "你是 Dr. AI，一位基于循证医学的专业健康顾问。\n"
            "你必须综合用户画像、工具证据和参考资料回答问题。\n\n"
            "核心原则：\n"
            "1. 优先依据系统给出的证据，不要凭空发挥。\n"
            "2. 回答要清晰、友好、保守，不得替代医生诊断。\n"
            "3. 如果证据不足，要明确说明不确定性。\n"
            "4. 遇到急重症风险时，优先建议立即就医。"
        )

    def _build_user_prompt(
        self,
        *,
        profile_summary: str,
        rag_context: Optional[str],
        tool_evidence_text: str,
        query: str,
    ) -> str:
        rag_block = rag_context if rag_context else "暂无直接相关指南资料。"
        return (
            f"【用户画像】\n{profile_summary}\n\n"
            f"【工具证据】\n{tool_evidence_text}\n\n"
            f"【参考资料】\n{rag_block}\n\n"
            f"【用户问题】\n{query}"
        )

    def _build_profile_evidence(self, user: User) -> Dict[str, Any]:
        profile = user.profile
        if not profile:
            return {}

        evidence: Dict[str, Any] = {}
        for metric_key, attribute in (
            ("glucose_fasting", "Glucose_Fasting"),
            ("sbp", "SBP"),
            ("dbp", "DBP"),
            ("bmi", "BMI"),
        ):
            value = getattr(profile, attribute, None)
            if value is not None:
                evidence[metric_key] = value

        abnormal_flags = []
        if profile.BMI and profile.BMI > 24:
            abnormal_flags.append("high bmi")
        if profile.SBP and profile.SBP > 140:
            abnormal_flags.append("high blood pressure")
        if profile.Glucose_Fasting and profile.Glucose_Fasting > 6.1:
            abnormal_flags.append("high fasting glucose")
        if abnormal_flags:
            evidence["abnormal_flags"] = abnormal_flags
        return evidence

    def _get_user_context(self, user: User, session: Session) -> str:
        if not user.profile:
            return f"用户ID: {user.username}，暂时无详细体检档案。"

        profile = user.profile
        abnormal_flags = []
        if profile.BMI and profile.BMI > 24:
            abnormal_flags.append(f"BMI 偏高({profile.BMI})")
        if profile.SBP and profile.SBP > 140:
            abnormal_flags.append(f"收缩压偏高({profile.SBP})")
        if profile.Glucose_Fasting and profile.Glucose_Fasting > 6.1:
            abnormal_flags.append(f"空腹血糖偏高({profile.Glucose_Fasting})")

        age = profile.Age if profile.Age else "未知"
        gender = "男" if profile.Gender == 1 else "女" if profile.Gender == 2 else "未知"
        risk_history = summarize_risk_snapshot_for_context(profile.risk_history) if profile.risk_history else "暂无"

        return (
            f"- 基本信息: {age}岁，{gender}\n"
            f"- 关键风险/异常: {', '.join(abnormal_flags) if abnormal_flags else '无明显异常记录'}\n"
            f"- 风险历史: {risk_history}"
        )


chat_service = ChatService()
