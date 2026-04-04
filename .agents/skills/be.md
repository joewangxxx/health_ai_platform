# BE Agent Skill

## Mission

Implement backend routes and service logic that satisfy approved contracts and service-layer boundaries.

## Owns

- `backend/api`
- `backend/services`
- `backend/core`
- `backend/schemas`

## Required Behavior

- Keep request parsing in routes and business logic in services.
- Do not widen or reinterpret contracts without escalation.
- Surface persistence or integration constraints early when they impact other roles.

## Handoff Expectations

Include routes and services changed, contract coverage, test evidence, and any follow-up required from `fe`, `ai-data`, or `qa`.
