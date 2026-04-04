# Shared Agent Policy

Apply these rules before following any role-specific instructions:

1. Read `AGENTS.md`, `.codex/config.toml`, your `.codex/agents/<role>.toml`, and `docs/blackboard/state.yaml`.
2. Treat `docs/blackboard/state.yaml` as read-only unless you are the parent-thread `orchestrator`.
3. Respect ownership boundaries. Do not edit another role's source-of-truth doc unless the `orchestrator` explicitly reassigns ownership.
4. Do not bypass workflow gates. If your `entry_gate` is closed, stop and report the blocker instead of working ahead.
5. Record assumptions, decisions, blockers, and evidence in the doc you own or in your handoff message.
6. If work reveals a cross-role conflict, stop and escalate with evidence instead of making a silent change.
7. `fe`, `be`, and `ai-data` must never change `docs/api-contract.md` or `docs/data-model-contract.md` directly. They escalate contract changes to the `orchestrator`.
