# Source Split Phase 3

Generated on: 2026-04-24

## Phase

Phase 3: conservative oversized source split pilot.

## Scope

This phase split a bounded helper slice out of `backend/services/chat_service.py`. The selected slice contains chat tool presentation helpers only: SSE tool status text, tool completion text, and bounded prompt-summary formatting for tool outputs.

## Files Changed

- `backend/services/chat_service.py`
- `backend/services/chat_tool_presentation.py`
- `tests/test_chat_tool_presentation.py`
- `docs/maintenance/source-split-phase3.md`
- `docs/maintenance/maintenance-health-summary.md`
- `docs/blackboard/state.yaml`

## Split Summary

- Added `backend/services/chat_tool_presentation.py` for pure presentation/helper logic.
- Moved readable Chinese tool status and done messages out of the main `ChatService` class.
- Moved bounded tool-output prompt summaries out of the main `ChatService` class.
- Kept the public `ChatService` interface and all FastAPI route contracts unchanged.
- Added concise Chinese comments explaining that the extracted helpers affect only progress display and prompt summarization, not tool execution or API contracts.

## Size Impact

- `backend/services/chat_service.py`: from about 2361 lines to 2280 lines.
- `backend/services/chat_tool_presentation.py`: 84 lines.

This is intentionally a small pilot split. It proves the workflow and testing approach before attempting larger frontend or backend file decomposition.

## Explicit Non-Changes

- No public route path changed.
- No request or response envelope changed.
- No database schema, persistence behavior, OCR/RAG/Agent tool contract, or frontend API contract changed.
- No model, data, PDF, database, generated artifact, or large binary was deleted or moved.
- No blind global replacement was run.

## TDD Evidence

- Red step: `python -m pytest tests\test_chat_tool_presentation.py -q` failed first with `ModuleNotFoundError` because `backend.services.chat_tool_presentation` did not exist.
- Green step: after extracting the helper module, `python -m pytest tests\test_chat_tool_presentation.py -q` returned `3 passed`.

## Verification Evidence

- `python -m py_compile backend\services\chat_service.py backend\services\chat_tool_presentation.py` exited 0.
- `python -m pytest tests\test_chat_tool_presentation.py tests\test_chat_agent_service.py tests\test_agent_tools.py -q` returned `62 passed`.
- Precise encoding check for `backend/services/chat_tool_presentation.py`, `backend/services/chat_service.py`, and `tests/test_chat_tool_presentation.py` found no private-use characters, no replacement characters, and no known Phase 2 mojibake snippets.
- `python -m pytest tests -q` returned `240 passed`.
- `npm.cmd run build` in `frontend` completed successfully.

## Deferred Items

- Larger splits such as `frontend/src/views/chat/DrAI.vue`, `backend/services/agent_tools.py`, and further `chat_service.py` decomposition should be separate scoped phases with their own tests.
- Large data/model/PDF/generated artifact cleanup remains out of scope until ownership and retention policy are explicitly approved.
- Any future split that touches public route behavior, persisted payload shape, or frontend/backend contract boundaries must be escalated through the architecture change process.

