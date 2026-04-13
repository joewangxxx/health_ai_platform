# Findings

## Governance Context
- Repository blackboard marks the project as implementation/QA mature with architecture, API, and data-model contracts approved.
- Current platform framing already emphasizes guided completion, controlled tools, evidence panels, and decision summaries rather than autonomous actuation.

## Doc-Level Findings
- PRD language describes the platform value chain as multimodal fusion, risk prediction, report interpretation, RAG health Q&A, and personalized intervention recommendations.
- PRD acceptance criteria for Dr. AI explicitly emphasize evidence-backed health Q&A and state that the current version does not treat multi-turn diagnosis agents or autonomous closed-loop decision-making as acceptance prerequisites.
- Architecture/API/data-model contracts repeatedly freeze the system as backend-owned bounded guidance with six chat lanes, evidence sufficiency levels, refusal/escalation modes, and optional human takeover.
- The contract set treats chat tools as read-only self-only lookups behind the existing chat runtime, not as external-action tools or autonomous medical workflow executors.

## Code-Level Findings
- `backend/services/agent_safety.py` classifies user questions into bounded lanes such as `urgent_symptom`, `diagnosis_sensitive`, `medication_related`, and `general_health`, showing explicit safety routing rather than autonomous decision authority.
- `backend/services/agent_tools.py` freezes chat tools as `read_only=True` and `scope="self_only"` with lane-specific whitelists, so the chat runtime can look up evidence but cannot execute medical actions.
- `backend/services/chat_service.py` builds `response_verdict` and `takeover` metadata, including human-escalation requirements and insufficient-evidence handoff, which is characteristic of guarded decision support.
- `backend/main.py` exposes `/analyze/comprehensive` as an analysis endpoint that returns `risk_report` plus `analysis_context`; it does not autonomously apply interventions or update care plans.
- `frontend/src/views/ClinicalView.vue` renders OCR status and `analysis_context` banners for guided completion, especially around missing/derived fields, reinforcing that the system asks users to complete evidence rather than silently deciding for them.
- `frontend/src/views/chat/DrAI.vue` shows source references, evidence panels, suggestion cards, and disclaimers that the advice is for reference and does not replace a clinician.
- Some modules do output recommendations or plans, such as CKM-stage recommendations, diet-plan generation, intervention simulation, and pharmacogenomic dosage suggestions, but these are exposed as advisory results from user-triggered endpoints rather than autonomous decision execution.
