# Phase 6 Generated Answer Quality Evaluation

## Scope

- Evaluated 100 health-consultation answers across the same 5 classes used by the Agent behavior benchmark.
- Scored key-point coverage, evidence grounding, safety compliance, actionability, and clarity.
- Candidate source: `offline_reference_template`.
- This benchmark is designed so exported production/LLM answers can replace offline candidates in future reruns.

## Overall Metrics

| Metric | Value |
|---|---:|
| Pass rate | 1.000 |
| Mean total score | 0.940 |
| Mean key-point coverage | 0.950 |
| Mean evidence grounding | 1.000 |
| Mean safety compliance | 1.000 |
| Mean actionability | 0.700 |
| Mean clarity | 1.000 |

## Category Metrics

| Category | Count | Pass rate | Total | Key points | Evidence | Safety | Action | Clarity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| general_health_education | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| personal_trend_review | 20 | 1.000 | 0.925 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 |
| report_evidence_consult | 20 | 1.000 | 0.900 | 1.000 | 1.000 | 1.000 | 0.333 | 1.000 |
| unsafe_or_overreach | 20 | 1.000 | 0.925 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| urgent_triage | 20 | 1.000 | 0.950 | 1.000 | 1.000 | 1.000 | 0.667 | 1.000 |

## Runtime Boundary

- `OPENAI_API_KEY` present: `false`.
- Default phase result should be described as offline rubric evidence, not live provider quality.

## Known Limits

- Default candidates are offline reference-template answers, not live LLM outputs.
- Automatic lexical scoring checks rubric compliance but does not replace clinician review.
- External production answers can be supplied with --candidate-file for the same 100-question rubric.
