# Health AI Platform Data and Model Contract

## Ownership

- Owner: `architect`
- Status: `approved`
- Scope baseline: approved P0 core loop from [PRD.md](E:\health_ai_platform_2.0\docs\PRD.md)
- Review basis: full tracked-code scan completed on 2026-03-24

## Purpose

Define the canonical entities, persistence semantics, model-facing inputs/outputs, and AI/data boundaries used by the approved P0 product loop.

## 1. Canonical Entities

### 1.1 `User`

Source: [models.py](E:\health_ai_platform_2.0\backend\models.py)

Meaning:

- Authenticated platform account
- Owns one profile
- Owns many health records

Required fields:

- `id`
- `username`
- `email`
- `hashed_password`
- `is_superuser`

Ownership:

- Persistence and auth semantics: `be`
- Product meaning: `pm`

### 1.2 `UserProfile`

Source: [models.py](E:\health_ai_platform_2.0\backend\models.py)

Meaning:

- Canonical current-state health profile for a single user
- Primary working object for OCR merge, risk analysis, and chat context injection

P0-relevant field groups:

- Demographics: `Age`, `Gender`
- Body metrics: `Height`, `Weight`, `BMI`, `WaistCircum`
- Vitals: `SBP`, `DBP`
- Core metabolic biomarkers: `Glucose_Fasting`, `HbA1c`, `Cholesterol_Total`, `Triglycerides`, `Cholesterol_HDL`, `Cholesterol_LDL`, `eGFR`, `Creatinine`
- Additional biomarkers used by current code paths: `WBC`, `Platelet`, `GGT`, `ALP`, `ALT`
- Lifestyle: `Sleep_Hours`
- Flexible extension: `extra_data`

Protected fields:

- `id`
- `user_id`
- relationship objects

Sensitive fields:

- Genomic data is stored through `encrypted_genomic_data` and exposed via the `genomic_data` property
- `allow_research` controls anonymized research consent
- `risk_history` is a legacy field name; in this freeze its canonical meaning is "latest persisted normalized risk snapshot", not "append-only history array"

### 1.3 `HealthRecord`

Meaning:

- Time-series snapshot record of health data over time
- Used for historical listing and trend rendering

Required fields:

- `id`
- `user_id`
- `record_date`
- `source`
- `metrics`
- `risk_snapshot`

Contract semantics:

- `metrics` is persisted as JSON string
- `risk_snapshot` is persisted as serialized snapshot of current risk context when available
- `risk_snapshot` shares the same canonical envelope as `UserProfile.risk_history`, but is record-scoped and point-in-time

### 1.4 `MedicalDocument`

Meaning:

- One uploaded medical report file belonging to a user
- Connects file persistence with OCR extraction output

Required fields:

- `id`
- `user_id`
- `file_name`
- `file_path`
- `file_url`
- `upload_date`
- `ocr_summary`

Contract semantics:

- File payload is stored on disk under the upload directory
- OCR extraction output is stored as JSON-serialized summary in `ocr_summary`
- `ocr_summary` is the persisted report-summary field and now has a frozen canonical target envelope `ocr_summary.v1`, even though legacy rows remain shape-variable

## 2. Canonical P0 Data Shapes

### 2.1 Profile Payload Shape

The current profile contract is field-oriented, not nested by domain area.  
Clients may submit sparse updates containing only changed fields.

Rules:

- Unknown writable fields are ignored unless explicitly supported in backend logic
- JSON-like dict payloads such as `extra_data` must remain serializable
- Client-facing SNP input currently arrives as `user_snps` and is mapped into genomic storage

### 2.1.1 `UserProfile.field_state_snapshot` Canonical Shape

This slice freezes an additive backend-owned provenance record for clinical-field completeness without changing the existing canonical field names on `UserProfile`.

Canonical persisted or derived target shape:

```json
{
  "schema_version": "clinical_field_state_snapshot.v1",
  "fields": {
    "BMI": {
      "status": "derived",
      "source": "derived_formula",
      "derived_from": ["Height", "Weight"],
      "derivation_rule": "bmi.v1"
    },
    "Glucose_Fasting": {
      "status": "recognized",
      "source": "ocr_document"
    },
    "Weight": {
      "status": "user_entered",
      "source": "manual_entry"
    }
  }
}
```

Frozen field-state enum:

- `recognized`
- `derived`
- `missing`
- `user_confirmed`
- `user_entered`

Canonical semantics:

- `recognized` means the value came directly from OCR or another imported structured source.
- `derived` means the value came from a backend-approved deterministic formula.
- `missing` means the value is absent and must stay absent until the user or a recognized source supplies it.
- `user_confirmed` means the user explicitly confirmed a previously recognized or derived value.
- `user_entered` means the user manually typed the value.

Approved automatic derivation set:

- `BMI` may be derived from `Height` and `Weight` using `bmi.v1`.
- `eGFR` may be derived from `Creatinine`, `Age`, and `Gender` using the backend-approved CKD-EPI rule.

What must not be silently inferred:

- no default estimate, guessed placeholder, median-fill, or "roughly enter a value" numeric fallback is allowed
- no field outside the approved derivation set may be marked `derived`
- FE must not fabricate a state transition that the backend did not emit or store

Current runtime gap:

- [frontend/src/views/ClinicalView.vue](E:\health_ai_platform_2.0\frontend\src\views\ClinicalView.vue) currently has OCR-not-found styling and client-local eGFR derivation behavior, but there is no frozen backend-owned field-state snapshot yet

### 2.1.2 Provisional Analysis Metadata Shape

This slice freezes additive backend-owned metadata that explains whether a generated risk report is final, provisional, or blocked because of data completeness.

Canonical runtime shape:

```json
{
  "schema_version": "analysis_context.v1",
  "analysis_mode": "provisional",
  "provisional_reasons": [
    {
      "code": "derived_field_present",
      "fields": ["BMI", "eGFR"]
    }
  ],
  "blocking_fields": [],
  "field_state_summary": {
    "recognized": ["Age", "Gender"],
    "derived": ["BMI", "eGFR"],
    "missing": [],
    "user_confirmed": [],
    "user_entered": ["Weight"]
  }
}
```

Frozen semantics:

- `final` means the selected analysis path has the required field floor without prohibited estimates.
- `provisional` means a bounded report can still be produced, but at least one material field remains `derived` or some non-blocking fields remain `missing`.
- `blocked` means the required non-derivable field floor is not met.

Rules:

- `analysis_context.v1` is additive runtime metadata. It does not replace `risk_snapshot.v1` or the raw backend-owned `risk_report`.
- `provisional_reasons` and `blocking_fields` must use stable backend-authored field names only.
- `analysis_mode` must not be inferred from frontend heuristics once the backend emits it.

### 2.2 `MedicalDocument.ocr_summary` Canonical Shape

Canonical persisted target shape for new normalized writes:

```json
{
  "schema_version": "ocr_summary.v1",
  "document_type": null,
  "patient_context": {
    "Age": 45,
    "Gender": 1,
    "Height": 170,
    "Weight": 65
  },
  "metrics": {
    "Glucose_Fasting": {
      "value": 6.8,
      "unit": "mmol/L",
      "ref_range": "3.9-6.1",
      "hospital_flag": "H"
    }
  },
  "extra_findings": {},
  "narrative_summary": null
}
```

Required top-level fields:

- `schema_version`
- `metrics`

Allowed nullable or optional fields:

- `document_type`
- `patient_context`
- each `patient_context` child field
- `extra_findings`
- `narrative_summary`
- `unit`, `ref_range`, and `hospital_flag` within each metric object

Canonical metric-object rules:

- each metric entry is keyed by a canonical repository metric key
- each metric object may contain only:
  - `value`
  - `unit`
  - `ref_range`
  - `hospital_flag`
- `value` may be numeric, string, or `null`
- `extra_findings` reuses the same metric-object shape for non-core extracted findings

Legacy compatibility rules:

- legacy rows may still store flat extraction dicts where demographic fields live at top level
- legacy rows may still store metric values as scalars instead of metric objects
- legacy rows may still use approved OCR aliases such as `Glu`, `TC`, `TG`, `HDL`, `LDL`, and `PLT`
- legacy rows may still be JSON strings that decode into one of the above forms

Allowed read-time normalization:

- parse one serialized JSON layer when the stored field is a string
- move top-level `Age`, `Gender`, `Height`, and `Weight` into `patient_context`
- map approved legacy aliases into canonical metric keys:
  - `Glu` -> `Glucose_Fasting`
  - `TC` -> `Cholesterol_Total`
  - `TG` -> `Triglycerides`
  - `HDL` -> `Cholesterol_HDL`
  - `LDL` -> `Cholesterol_LDL`
  - `PLT` -> `Platelet`
- wrap scalar metric values into metric objects with only `value` populated
- normalize `extra_findings` entries into the same metric-object shape

What must not be silently inferred:

- `document_type` when not explicitly stored
- missing `unit`, `ref_range`, or `hospital_flag`
- a narrative summary string when the payload only contains structured metrics
- arbitrary unknown keys remapped into canonical metrics outside the approved alias set
- new metrics derived from OCR raw text that are not already present in the persisted payload

Current runtime gap:

- [backend/api/api_v1/endpoints/ocr.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\ocr.py) still writes raw extraction payloads rather than the frozen `ocr_summary.v1` envelope

### 2.2.1 `MedicalDocument.ocr_processing_status` Canonical Shape

This slice freezes an additive backend-owned processing-state record for uploaded documents. It does not replace `ocr_summary.v1`; it explains whether OCR reached a usable result after durable document save.

Canonical persisted or derived target shape:

```json
{
  "schema_version": "ocr_processing_status.v1",
  "status": "stored_unprocessed",
  "reason": "ocr_service_unavailable",
  "structured_data_present": false,
  "raw_text_present": false,
  "saved_at": "2026-04-03T12:00:00Z",
  "processed_at": null
}
```

Frozen status enum:

- `success`
- `partial_success`
- `stored_unprocessed`
- `error`

Canonical semantics:

- `success` means the file and document row were saved and canonical structured OCR output is available.
- `partial_success` means the file and document row were saved and some bounded OCR output is usable, but the structured result is incomplete.
- `stored_unprocessed` means the file and document row were saved, but OCR did not reach a usable parse because an OCR prerequisite was unavailable or processing was intentionally deferred.
- `error` means the backend could not establish a durable outcome and therefore could not safely report one of the three successful storage outcomes above.

Rules:

- `stored_unprocessed` is the canonical state for missing Baidu OCR credentials, unready OCR clients, or equivalent approved OCR-unavailable runtime conditions after the document is already durable.
- `structured_data_present` and `raw_text_present` are explicit booleans and must not be inferred by FE from `ocr_summary` alone.
- The processing-state record is additive and must not widen `ocr_summary.v1` with operational status fields.

Current runtime gap:

- [backend/api/api_v1/endpoints/ocr.py](E:\health_ai_platform_2.0\backend\api\api_v1\endpoints\ocr.py) currently stores the document first but raises a generic 500 for OCR-unavailable paths instead of persisting or projecting the frozen `stored_unprocessed` state

### 2.3 `HealthRecord.risk_snapshot` And `UserProfile.risk_history` Canonical Shape

Canonical persisted target shape for both fields:

```json
{
  "schema_version": "risk_snapshot.v1",
  "generated_at": "2026-03-24T12:00:00Z",
  "source": "analyze_comprehensive",
  "findings": [
    {
      "key": "T2D",
      "label": "2型糖尿病",
      "probability": 0.42,
      "risk_level": "medium"
    }
  ],
  "ckm": {
    "stage": 1,
    "stage_name": "Stage 1"
  }
}
```

Required top-level fields:

- `schema_version`
- `findings`

Allowed nullable or optional fields:

- `generated_at`
- `source`
- `ckm`
- `label`, `probability`, and `risk_level` within each finding
- `ckm.stage`
- `ckm.stage_name`

Canonical semantics:

- `UserProfile.risk_history` stores one latest normalized risk snapshot despite the legacy field name
- `HealthRecord.risk_snapshot` stores a point-in-time copy of the same normalized risk-snapshot envelope
- `findings` is an array of disease or condition findings, not a dynamic raw engine blob
- `probability` is normalized to `0..1` when known
- `risk_level` is normalized to one of `low`, `medium`, `high`, `very_high` when known

Legacy compatibility rules:

- legacy rows may still store raw engine payloads as JSON strings or decoded dicts keyed by disease names
- legacy rows may still express magnitude in `probability`, `final_risk`, or `risk`
- legacy rows may still express severity in `risk_level` or `level`
- legacy rows may still carry CKM under `ckm`, `ckm_stage`, `CKM`, or `CKM_stage`

Allowed read-time normalization:

- parse one serialized JSON layer when the stored field is a string
- extract disease findings from raw keyed dict payloads only when the child value is an object
- normalize magnitude from `probability`, `final_risk`, or `risk`
- coerce percentage-style numbers greater than `1` into `0..1` scale
- normalize severity from known `risk_level` or `level` strings into `low`, `medium`, `high`, or `very_high`
- extract CKM from the approved legacy key set when the stored value is an object
- populate tool-facing `captured_at` from the owning `HealthRecord.record_date` when the normalized envelope itself lacks `generated_at`

What must not be silently inferred:

- additional disease findings not explicitly present in stored payload
- CKM stage when no explicit CKM object exists
- diagnosis, recommendation, or treatment plan from raw risk payloads
- an ordered history array from `UserProfile.risk_history`
- timestamps for profile-level snapshots when no stored timestamp or owning record timestamp exists

Current runtime gaps:

- [backend/main.py](E:\health_ai_platform_2.0\backend\main.py) still writes `risk_history` from raw `risk_report` payloads and copies that raw payload directly into `risk_snapshot`
- current services already do tolerant parsing, but there is still no shared canonical normalizer or canonical write path for `risk_snapshot.v1`

### 2.4 Risk Report Shape

The comprehensive analysis endpoint returns `risk_report` as engine-owned nested JSON.  
This contract does **not** normalize disease keys or every metric today, but it freezes these expectations:

- response is JSON object
- keys represent assessed risks or related analysis outputs
- values may contain probability-style fields, final-risk style fields, labels, and explanatory details

Frontend and downstream code must treat engine output as backend-owned and avoid inventing alternative semantics.

Additional analysis-quality rule:

- later BE work may attach additive `analysis_context.v1` metadata to explain whether the report is `final`, `provisional`, or `blocked`, but it must not silently redefine the engine-owned `risk_report` shape

### 2.5 Normalization Boundary Across Layers

This slice freezes three distinct layers for the shape-variable persisted fields and the tool views derived from them:

- Persisted raw or legacy payloads:
  - the actual stored database value, which may still be a legacy JSON string or legacy decoded object until BE repair work lands
- Normalized backend-internal shape:
  - one of the architect-frozen envelopes above:
    - `ocr_summary.v1`
    - `risk_snapshot.v1`
- Tool-facing bounded outputs:
  - deterministic read models derived from the normalized envelopes rather than raw pass-through payloads

Field-to-output mapping:

- `MedicalDocument.ocr_summary`
  - normalized backend shape: `ocr_summary.v1`
  - primary bounded output: `medication_summary_lookup`
  - secondary bounded output: `report_comparison_lookup`
- `HealthRecord.metrics`
  - normalized backend shape: latest metric payloads
  - primary bounded output: `recent_metric_anomaly_lookup`
- `UserProfile` metric fields
  - normalized backend shape: latest metric payloads
  - fallback bounded output: `recent_metric_anomaly_lookup`
- `UserProfile.extra_data`
  - backend-owned fallback input for medication facts when a stable medication subsection exists

The existing `risk_snapshot.v1` normalization remains governed by earlier contract slices and is not redefined by this tool freeze.

Compatibility route rule:

- `GET /user/profile` and `GET /api/v1/user/documents` still expose compatibility payloads directly today; FE must treat those fields as opaque until BE ships the normalized read layer

### 2.6 Assistant Evidence Panel Shape

Assistant evidence metadata now has two layers in the frozen contract:

- existing compact metadata: `sources`, `evidence_tags`, `decision_summary`
- richer optional metadata: `evidence_panel`

`evidence_panel` shape:

```json
{
  "chips": [
    {
      "key": "profile_summary",
      "label": "Health Profile"
    }
  ],
  "sections": [
    {
      "label": "Health Profile",
      "summary": "Recent profile context influenced the answer.",
      "key_facts": [
        "Recent fasting-glucose context was considered"
      ],
      "decision_basis": "The reply prioritized guidance that matches current profile state.",
      "source_refs": ["profile_summary"],
      "source_items": [
        {
          "source_type": "profile",
          "title": "Recent profile snapshot",
          "snippet": "Recent fasting-glucose context was considered.",
          "timestamp": "2026-03-24T12:00:00Z",
          "confidence": 0.86
        }
      ]
    }
  ]
}
```

Contract semantics:

- `chips` is the compact-summary layer for inline assistant chips
- each chip has stable backend-owned `key` semantics plus a user-facing `label`
- `sections` is the single expanded-detail layer for the approved hybrid UI
- each section must use the frozen fields `label`, `summary`, `key_facts`, `decision_basis`, `source_refs`, and `source_items`
- `source_refs` is a concise list of backend-authored reference labels, usually reusing top-level `sources` values when an external source exists
- `source_items` is the renderable drill-down layer for section-level source detail
- each source item must use `source_type`, `title`, `snippet`, and a `timestamp` field; `timestamp` may be `null` when no reliable capture time is available, and the item may optionally include `confidence` or `relevance`
- initial `source_type` values are limited to `profile`, `trend`, `report`, and `guideline`
- source items are safe backend-authored summaries only; they must not expose raw large JSON payloads or unbounded tool output
- `evidence_panel` is optional during rollout, but when present it must be replay-safe and match the live assistant payload shape
- the current chat UI may ignore `evidence_panel` until FE implementation lands; backward compatibility depends on keeping `sources`, `evidence_tags`, and `decision_summary`

### 2.6.1 Dr. AI Answer-Explanation Persistence Boundary

This slice does not add a new persisted explanation entity or a new FE-owned semantic layer. The frontend "why did Dr. AI answer this way" view is a read-only projection over the existing assistant-message metadata fields.

Persisted assistant message fields that FE may read:

- `sources`
- `evidence_tags`
- `decision_summary`
- `response_verdict`
- `evidence_panel`
- `suggestion_card`
- `takeover`

Persistence rules:

- no new database column is required for this slice
- no new persisted explanation status, explanation verdict, or explanation reason field is required for this slice
- `evidence_panel` remains backend-authored assistant-message metadata, while the explanation UI only renders the backend-owned meaning already present in the stored row
- replay must keep using the same stored assistant-message metadata; it may not recompute or translate an alternate explanation schema for historical rows
- if a stored row predates one of the frozen assistant-message metadata fields, that field may remain `null` or omitted on replay instead of being fabricated

What FE must not infer:

- new clinical certainty labels that are not explicitly stored
- a second explanation verdict hierarchy separate from `decision_summary.verdict` and `response_verdict`
- evidence provenance beyond the stored assistant-message metadata and backend-authored `evidence_panel` content

### 2.6.2 Human Takeover Persistence Boundary

This slice adds a backend-owned assistant-message field for human-handoff semantics. It is not a workflow engine, ticketing system, or disclaimer replacement.

Frozen persisted takeover shape for assistant messages:

```json
{
  "schema_version": "takeover.v1",
  "status": "required",
  "trigger_reason": "high_risk",
  "summary": "Backend-owned handoff summary explaining why human review is required."
}
```

Required top-level fields:

- `schema_version`
- `status`
- `trigger_reason`
- `summary`

Canonical semantics:

- `ChatMessage.takeover` stores the optional backend-owned human-handoff state for the assistant turn.
- `status` is the backend decision about whether the turn should surface a human-handoff UI. Frozen values are `required` and `suppressed`.
- `trigger_reason` is the backend-owned boundary classification. Frozen values are `high_risk`, `insufficient_evidence`, `boundary_false_positive`, and `boundary_not_triggered`.
- `summary` is a short backend-authored explanation of the boundary decision. It must remain neutral, bounded, and non-diagnostic.
- `status="required"` means the backend has crossed the human-handoff boundary and the object should be replayed and displayed as such. `response_verdict.human_escalation_required=true` is broader than takeover and does not by itself require the takeover object.
- `status="suppressed"` means the backend explicitly evaluated takeover and chose not to surface it. FE must not synthesize a hidden handoff state from other metadata.
- `trigger_reason="high_risk"` means the turn crossed the high-risk boundary, typically because the backend classified the situation as urgent or clinically unsafe to leave as a normal answer.
- `trigger_reason="insufficient_evidence"` means the turn crossed the evidence boundary, typically because the backend could not answer safely with the available evidence.
- `trigger_reason="boundary_false_positive"` means the backend detected a near-hit but vetoed it as a false positive.
- `trigger_reason="boundary_not_triggered"` means the backend evaluated the turn and concluded that no takeover boundary was crossed.

Replay and persistence rules:

- `POST /chat/send`, `POST /chat/stream` final payloads, and `GET /chat/conversations/{conversation_id}/messages` assistant rows must use the same takeover shape when it is present.
- For one assistant turn, replay must surface the same stored `takeover` object rather than recomputing it from newer runtime heuristics.
- Legacy stored assistant rows may lack `takeover`; historical replay must remain valid in that case.
- User turns in history replay should also return `takeover=null`.
- `takeover.status="suppressed"` must not be used by FE to infer a hidden clinical state.
- `evidence_panel` may support the takeover decision with evidence provenance, but it does not own takeover semantics.
- `suggestion_card` remains an ordinary guidance card. It must not be repurposed into a takeover workflow, ticket, or disclaimer substitute.

### 2.7 Read-Only Tool Slice Shapes

The next safe read-only tool slice is frozen as normalized backend-internal data shapes over existing persistence objects. These shapes are not new database tables.

Each tool result may also carry a transient `evidence_metadata` envelope for freshness, coverage, confidence, and comparison counts. That envelope is backend-owned runtime metadata only and is not a new persisted entity or column.

#### `medication_summary_lookup`

Persistence source:

- Primary: medication-related facts normalized out of `MedicalDocument.ocr_summary`
- Fallback: stable medication facts stored in `UserProfile.extra_data`
- Selection key: explicit `MedicalDocument.id` when provided, otherwise the latest user-owned document or profile medication facts with a persisted medication summary

Canonical tool result shape:

```json
{
  "has_medication_summary": true,
  "document_id": 123,
  "file_name": "report.pdf",
  "summary_source": "medical_document_ocr_summary",
  "medication_summary": {
    "schema_version": "medication_summary.v1",
    "status": "info",
    "count": 2,
    "message": "2 medication facts found",
    "medication_items": [
      {
        "name": "Metformin",
        "dose": "500",
        "unit": "mg",
        "frequency": "BID",
        "route": "oral",
        "instruction": "after meals",
        "source_ref": "report:123",
        "source_type": "report"
      }
    ],
    "medication_items_truncated": false,
    "source_refs": ["report:123"]
  }
}
```

Contract semantics:

- `medication_summary` is a bounded normalized projection over persisted medication facts, not a raw payload pass-through or prescribing engine.
- `medication_items` contains normalized medication rows only and must not leak arbitrary legacy payload subkeys.
- `medication_items_truncated` indicates whether the tool omitted additional normalized medication items to stay bounded.
- `source_ref` and `source_refs` are backend-stable labels and may not invent new evidence buckets.
- `evidence_metadata` for this tool uses the `summary_min` bundle: `freshness`, `coverage`, `confidence`, and `missing_fields` when coverage is not full.

#### `recent_metric_anomaly_lookup`

Persistence source:

- Primary: latest user-owned `HealthRecord.metrics`
- Fallback: current `UserProfile` metric fields projected into the anomaly-detection input shape

Canonical tool result shape:

```json
{
  "has_metric_anomalies": true,
  "evaluated_at": "2026-03-24T12:00:00",
  "evaluated_source": "health_record",
  "summary": {
    "status": "warning",
    "count": 2,
    "message": "2 abnormal metrics found"
  },
  "items": [
    {
      "metric_key": "Glucose_Fasting",
      "display_name": "Glucose_Fasting",
      "value": 6.8,
      "unit": "",
      "status": "High",
      "tag": "Diabetes_Risk",
      "message": "Glucose_Fasting high",
      "detection_source": "standard_range",
      "source_ref": "health_record_metrics"
    }
  ]
}
```

Contract semantics:

- `items` is a normalized projection of the anomaly-detection result rather than a raw persistence payload.
- `summary` is a bounded derivative of the same anomaly pass and is intended for chat evidence use, not for replacing the public anomaly endpoint.
- `evaluated_source` is `health_record` or `user_profile` only in this slice.
- The backend may map the resulting evidence into `trend`- or `profile`-type source items, but it may not invent a new source taxonomy for this slice.
- `evidence_metadata` for this tool uses the `summary_min` bundle: `freshness`, `coverage`, `confidence`, and `missing_fields` when coverage is not full.

#### `report_comparison_lookup`

Persistence source:

- Primary: two user-owned `MedicalDocument.ocr_summary` payloads
- Fallback: the latest two user-owned documents with persisted OCR summaries, compared in chronological order when explicit document ids are omitted

Canonical tool result shape:

```json
{
  "has_report_comparison": true,
  "baseline_document_id": 123,
  "comparison_document_id": 456,
  "baseline_file_name": "report-a.pdf",
  "comparison_file_name": "report-b.pdf",
  "comparison_basis": "medical_document_ocr_summary",
  "summary": {
    "status": "different",
    "count": 3,
    "message": "3 bounded differences found"
  },
  "delta_items": [
    {
      "field": "Glucose_Fasting",
      "baseline_value": 5.6,
      "comparison_value": 6.8,
      "change": "up",
      "source_refs": ["baseline_report", "comparison_report"]
    }
  ],
  "shared_metric_count": 4,
  "new_findings_count": 1,
  "removed_findings_count": 0,
  "source_refs": ["baseline_report", "comparison_report"]
}
```

Contract semantics:

- `delta_items` is a bounded normalized projection over two stored OCR summaries, not a raw file diff or arbitrary history browser.
- `comparison_basis` must stay on the normalized OCR-summary layer; the tool must not compare raw PDF text or export blobs.
- `source_refs` are backend-stable labels for the two compared reports and may not expand into a new source taxonomy.
- The tool may surface only the two selected reports and may not widen into broader multi-document discovery behavior.
- `evidence_metadata` for this tool uses the `comparison_min` bundle: `freshness`, `coverage`, `confidence`, `missing_fields`, and `comparable_fields_count`.

### 2.8 RAG Chunk Metadata Shape

RAG chunk metadata is an internal build-time data model attached to vector-store documents or a transient rebuild manifest. It is not a public database entity and it does not change the chat API contract.

Canonical internal chunk metadata shape:

```json
{
  "source": "medical-guideline.pdf",
  "page": 12,
  "chunk_index": 3,
  "section_title": "HbA1c interpretation",
  "page_range": [12, 12]
}
```

Required fields:

- `source`
- `page`
- `chunk_index`

Optional fields:

- `section_title`
- `page_range`

Rules:

- `source` is the stable document provenance label, usually the original PDF file name or an equivalent backend-stable source key.
- `page` is the 1-based source page for the chunk's primary origin.
- `chunk_index` is the backend-owned sequence number for the chunk within the source document.
- `section_title` may be derived from nearby headings or OCR layout hints when available, but it is optional and must not be invented when absent.
- `page_range`, when present, must remain a bounded pair of page numbers and is only a convenience for cross-page chunks; it does not replace `page`.
- The chunk metadata floor is for internal retrieval, citation assembly, and rebuild verification only.
- Do not promote chunk metadata to a frontend-visible schema or new public API field without a separate architect-owned contract update.
- This shape does not authorize semantic chunking or LLM-assisted chunking; it only freezes the metadata floor for the existing recursive splitter path.

### 2.8.1 Query-Time RAG Quality Summary

`rag_quality_summary` is a backend-owned runtime summary that may be copied into internal audit and replay records. It is not part of `ChatMessage` and must not appear on any public `/chat/*` response.

Canonical internal shape:

```json
{
  "retrieval_status": "ok",
  "hit_count": 3,
  "unique_source_count": 2,
  "source_kind": "mixed",
  "density_status": "low_density",
  "ocr_fallback_state": "available",
  "provenance_state": "partial",
  "chunk_quality": "mixed"
}
```

Required fields:

- `retrieval_status`
- `hit_count`
- `source_kind`
- `density_status`
- `ocr_fallback_state`
- `provenance_state`
- `chunk_quality`

Optional fields:

- `unique_source_count`

Rules:

- `retrieval_status="ok"` means the retriever returned at least one attributable chunk.
- `retrieval_status="empty"` means no attributable chunks were found.
- `retrieval_status="unavailable"` means retrieval could not be trusted because a vector-store, loader, or OCR dependency was unavailable.
- `source_kind` may be `pdf_text`, `ocr_text`, `mixed`, or `unknown` and must be derived from existing chunk metadata and `ocr_touched`, not from a new corpus taxonomy.
- `density_status` may be `normal`, `low_density`, or `unknown`. It may be informed by build-time diagnostics, but the stored summary only carries the bounded status, not the full benchmark trace.
- `ocr_fallback_state` may be `available`, `degraded`, `unavailable`, or `unknown`.
- `provenance_state` may be `full`, `partial`, or `missing`. `full` requires the chunk metadata floor (`source`, `page`, `chunk_index`); optional `section_title` / `page_range` hints may improve the state but are not themselves public data.
- `chunk_quality` may be `strong`, `mixed`, `weak`, or `empty`. It is the aggregate summary that chat runtime uses when deciding whether RAG evidence is sufficient, limited, or unusable.
- `rag_quality_summary` may be `null` for urgent short-circuit paths or any path that bypasses retrieval.
- When persisted in `AgentAuditEvent` or `AgentAnswerReplay`, the summary must remain bounded and must not include per-hit similarity scores, raw passages, OCR text, benchmark reason strings, or loader exception payloads.
- This summary is for answer-boundary accountability and conservative degradation only.

## 3. Model And AI Asset Boundaries

### 3.1 Runtime Model Dependencies

- Disease risk models
- Gene risk engine
- Fusion risk engine
- OCR parsing pipeline
- RAG vector retrieval stack

These are runtime dependencies behind backend-owned APIs, not direct frontend contracts.

### 3.2 AI/Data Ownership Boundary

`ai-data` owns:

- Training scripts in `ai_core`
- ETL scripts in `backend/etl`
- Dataset assumptions in `data_warehouse`
- Model asset preparation and refresh procedures

`be` owns:

- The HTTP surface that consumes these assets
- Request validation and response semantics

`fe` consumes only the backend contract and must not infer direct model-file semantics.

## 4. Inference Inputs And Outputs

### 4.1 Comprehensive Risk Analysis Input

Input sources:

- Request body `clinical`
- Request body `user_snps`
- Stored `UserProfile`
- Default device state from backend config

Merge rule:

- Stored profile data may be used as base context
- Request-supplied clinical fields override missing or stale values

### 4.2 Chat Input

Input sources:

- Authenticated user identity
- Current profile context
- RAG search results
- User message text
- Cache bypass flag

Output:

- `reply`
- `sources`

Implemented runtime note as of 2026-03-24:

- chat output now also includes `conversation_id`, `evidence_tags`, and `decision_summary`
- chat output is now also frozen to carry an additive top-level `response_verdict` for assistant replies
- chat output is now contractually extended with an optional `evidence_panel`
- chat output may also include an optional backend-owned `suggestion_card` for structured health guidance
- prompt reconstruction now depends on a recent sliding window of persisted conversation turns
- current runtime conflict: repository code already carries `evidence_panel`, but it does not yet emit the frozen `lane` / `verdict` routing metadata through `decision_summary` across live and replay flows
- provider-native tool calling may now expose the frozen tool names `medication_summary_lookup`, `recent_metric_anomaly_lookup`, and `report_comparison_lookup` through the internal tool registry

### 4.2.1 Frozen Lane And Verdict Metadata

The medical risk routing matrix is carried through assistant `decision_summary` metadata inside the existing chat payloads and replayed historical messages.

Canonical routing metadata shape:

```json
{
  "intent": "guideline_lookup",
  "lane": "general_health",
  "verdict": "general_guidance",
  "tool_needed": true,
  "tool_used": ["get_user_profile_summary", "search_medical_guidelines"],
  "safety_level": "normal"
}
```

Contract semantics:

- `decision_summary.intent` remains a backward-compatible backend trace field. It is not the frozen FE routing contract.
- `decision_summary.lane` is the backend-owned routing lane that FE may consume after this freeze.
- `decision_summary.verdict` is the backend-owned result code that FE may consume after this freeze.
- `lane` is restricted to exactly:
  - `general_health`
  - `report_interpretation`
  - `trend_review`
  - `medication_related`
  - `urgent_symptom`
  - `diagnosis_sensitive`
- `verdict` is restricted to exactly:
  - `general_guidance`
  - `report_context_only`
  - `trend_context_only`
  - `medication_context_only`
  - `seek_urgent_care`
  - `needs_clinical_diagnosis`
  - `insufficient_evidence`
- If a specialized non-urgent lane lacks enough evidence, the backend must keep the selected `lane` and degrade by setting `verdict="insufficient_evidence"` rather than switching to a different lane.
- `urgent_symptom` must emit `verdict="seek_urgent_care"` and `diagnosis_sensitive` must emit either `needs_clinical_diagnosis` or `insufficient_evidence`.
- FE may render colors, badges, labels, or layout based on backend-emitted `lane` / `verdict`, but FE must not infer or redefine those semantics from `intent`, tool names, reply text, or evidence tags.

### 4.2.2 Frozen Six-Lane Matrix

| Lane | Trigger conditions | Allowed tools | Allowed output depth | Degrade / fallback strategy | Mandatory offline / in-person reminder |
|------|--------------------|---------------|----------------------|-----------------------------|----------------------------------------|
| `general_health` | Default non-acute health question that does not fit a narrower frozen lane | `get_user_profile_summary`, `get_latest_risk_report`, `recent_metric_anomaly_lookup`, `search_medical_guidelines` | `standard_bounded` | Fall back to conservative general guidance with `insufficient_evidence` when profile or guideline evidence is weak | `No` |
| `report_interpretation` | User asks to explain one report or compare persisted reports | `report_summary_lookup`, `report_comparison_lookup`, `get_uploaded_documents_summary`, `search_medical_guidelines` | `structured_bounded` | Do not invent report values; fall back to upload / exact-value guidance with `insufficient_evidence` when persisted report context is missing | `No` |
| `trend_review` | User asks about changes over time, historical movement, or whether a metric is rising / falling | `get_history_trends`, `recent_metric_anomaly_lookup`, `latest_analysis_snapshot_lookup`, `search_medical_guidelines` | `structured_bounded` | If fewer than two usable records exist, say trend evidence is insufficient and emit `insufficient_evidence` | `No` |
| `medication_related` | User asks about current medications or medication facts already present in persisted records | `medication_summary_lookup`, `report_summary_lookup`, `search_medical_guidelines` | `brief_bounded` | If no persisted medication facts exist, do not guess; ask for the medication name or report and emit `insufficient_evidence` | `No` |
| `urgent_symptom` | Acute symptom / emergency-risk / serious reaction language | No read-only tools before the first response | `safety_only` | Immediate short-circuit safety response; missing data must not delay the answer | `Yes` |
| `diagnosis_sensitive` | User asks for diagnosis, disease confirmation, exclusion, or diagnostic certainty | `get_user_profile_summary`, `report_summary_lookup`, `latest_analysis_snapshot_lookup`, `search_medical_guidelines` | `guardrail_brief` | Explain that chat cannot determine a diagnosis from current evidence and use `insufficient_evidence` when context is incomplete | `Yes` |

Execution rules bound to the matrix:

- `urgent_symptom` preempts all other lanes.
- `diagnosis_sensitive` preempts all non-urgent explanatory lanes when the user is seeking diagnostic judgment rather than descriptive explanation.
- No seventh lane, per-client lane alias, or frontend-derived lane is allowed in this freeze.
- Non-mandatory-reminder lanes may still include a care reminder when evidence warrants it, but only `urgent_symptom` and `diagnosis_sensitive` require one on every response in this slice.

### 4.2.3 Explicit Policy Envelope

`ChatMessage.decision_summary` may also persist the backend-owned explicit policy envelope for assistant turns:

```json
{
  "policy_version": "explicit_policy.v1",
  "evaluation_order": [
    "urgent_symptom",
    "diagnosis_sensitive",
    "medication_related",
    "trend_review",
    "report_interpretation",
    "general_health"
  ],
  "selected_rule": "general_health",
  "risk_level": "low",
  "evidence_state": "limited",
  "tool_availability": "partial",
  "answer_mode": "bounded_answer",
  "disclaimer_mode": "conservative",
  "degrade_reason": "evidence_insufficient"
}
```

Contract semantics:

- `ChatMessage.decision_summary.policy` is additive backend-owned runtime metadata nested under the existing decision-summary JSON shape.
- `policy_version` is compatibility-gated by major version. Same-major additive changes are compatible if they preserve the frozen lane/verdict meanings and keep the answer-mode set stable.
- Rule evaluation is first-match-wins and follows the frozen priority order listed above.
- `selected_rule` is the question-type/routing rule id for this slice, so no separate `question_type` field is required.
- `risk_level` is the backend risk assessment for the selected rule. It is typically `low`, `medium`, or `high`.
- `evidence_state` uses the exact enum `sufficient`, `limited`, or `insufficient`.
- `missing` is deprecated and reserved only as a legacy replay synonym for `insufficient`; BE must not persist or emit `missing` on new assistant turns.
- `tool_availability` is the backend summary of whether the selected rule has full, partial, or no usable tools available.
- `degrade_reason` is `null` or one of `evidence_insufficient`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `unsafe_medication_request`, `diagnosis_sensitive_request`, or `urgent_symptom`.
- The allowed answer-mode categories are `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, and `urgent_care_disclaimer`.
- The allowed disclaimer-mode categories are `none`, `conservative`, `diagnosis_guardrail`, and `urgent_care`.
- Degrade order when evidence or tool availability is insufficient is `direct_answer` -> `bounded_answer` -> `clarify_missing_context` -> `refusal_with_disclaimer`, while `urgent_care_disclaimer` short-circuits for urgent routing.
- `disclaimer_mode="conservative"` is used when the request is safe to answer but evidence is limited or tool availability is partial; the reply must stay bounded, surface uncertainty, and avoid implied certainty.
- Refusal and disclaimer triggers remain backend-owned. Typical triggers are urgent symptoms, diagnosis requests, medication start/stop/titration/substitution requests, evidence conflicts, missing evidence with a safety-sensitive request, and other unsafe asks that exceed the frozen lane guardrails.
- The model contract keeps `lane` and `verdict` as the FE-consumable routing contract. FE may ignore `policy`; it must not derive routing semantics from `policy`, `intent`, or `reply`.
- Historical rows may omit `decision_summary.policy`; lane/verdict remain the backward-compatible contract for replay.

### 4.2.3.1 Frozen Evidence Sufficiency Gate

The evidence sufficiency gate is part of the persisted assistant-turn contract even though the gate itself is evaluated at runtime before a new assistant message is stored.

Runtime inputs that may affect the persisted policy fields:

- profile evidence from persisted profile, latest risk snapshot, or anomaly-derived context
- report evidence from persisted report summaries, report comparisons, or uploaded-document projections
- trend/history evidence from persisted historical records and bounded trend projections
- knowledge-base / RAG evidence from attributable retrieval results
- tool evidence from successful read-only tool outputs, plus blocked or empty tool outcomes

Source rules:

- profile evidence is usable only when at least one query-relevant user-owned fact is available
- report evidence is usable only when persisted report-summary or report-comparison facts are available; file existence alone is not sufficient
- trend evidence is sufficient only when at least two comparable historical points exist for the requested trend claim; one point may support only `limited`
- knowledge-base / RAG evidence may contextualize a reply but cannot by itself make `report_interpretation`, `trend_review`, `medication_related`, or `diagnosis_sensitive` sufficient
- tool evidence is usable only when a tool returns `status="ok"` and bounded factual content; blocked, empty, or non-owned results count as unavailable

Decision priority:

1. `urgent_symptom` short-circuits first and does not wait on profile, RAG, or tool evidence.
2. Any unresolved contradiction across relevant evidence forces `ChatMessage.decision_summary.policy.evidence_state="insufficient"` and `degrade_reason="conflicting_evidence"`.
3. If the lane-specific minimum evidence floor is not met, `evidence_state="insufficient"`.
4. If some lane-relevant evidence exists but the minimum floor is only partially met, `evidence_state="limited"`.
5. Only when the lane-specific floor is met and no material contradiction remains unresolved may `evidence_state="sufficient"`.

Lane-specific minimum evidence floors:

- `general_health`: at least one usable personalized source or attributable guideline support for bounded general guidance; guideline-only support for a personalized question is at most `limited`
- `report_interpretation`: usable report-summary or report-comparison evidence
- `trend_review`: at least two comparable historical records
- `medication_related`: at least one persisted medication fact from report or profile-backed medication evidence
- `diagnosis_sensitive`: enough bounded context to summarize available facts while still refusing diagnosis-like certainty; this never authorizes a diagnosis claim
- `urgent_symptom`: fixed to the safety short-circuit path and therefore exposed as `insufficient` on the answer-level verdict path

Persistence and reply-boundary effects:

- when `evidence_state="insufficient"`, persisted `answer_mode` must not be `direct_answer`
- a conflict-driven turn must stay in its selected lane; BE must not silently switch to an easier lane before persisting the assistant metadata
- non-urgent lanes may persist only their lane-specific success verdict or `insufficient_evidence`; `urgent_symptom` always keeps `seek_urgent_care`
- the stored assistant reply must refuse over-inference, explicitly state uncertainty, identify the missing or conflicting evidence class, and provide concrete next-step guidance
- `urgent_symptom` and `diagnosis_sensitive` still require their mandatory offline care reminder on every stored assistant response; other lanes may include clinician-review guidance when evidence is conflicting or too weak
- pre-execution applicability checks and post-execution sufficiency checks are backend-owned hard checks; they do not add a new persistence column or a new public metadata shape
- the transient read-only tool `evidence_metadata` envelope is runtime-only; it must not be persisted onto `ChatMessage`, `AgentAuditEvent`, or a new table as part of this freeze
- tool calls that are blocked, empty, weak, or mismatched to the selected lane must be reflected through the existing policy fields rather than through a synthetic success record
- the persisted dominant degrade reason must follow the frozen priority `urgent_risk_detected` -> `policy_guardrail` -> `conflicting_evidence` -> `tool_unavailable` -> `missing_required_context` -> `insufficient_evidence`

### 4.2.4 Response Verdict Metadata

`ChatMessage` assistant turns now also freeze one additive top-level answer-level verdict object:

```json
{
  "schema_version": "response_verdict.v1",
  "response_mode": "bounded_answer",
  "medical_risk_level": "medium",
  "evidence_sufficiency": "limited",
  "human_escalation_required": false,
  "degraded_reason": "insufficient_evidence"
}
```

Contract semantics:

- The container name is exactly `response_verdict`.
- Naming is intentional: `response_verdict` avoids collision with `ChatMessage.decision_summary.verdict`, which remains the already-frozen routing-matrix verdict code.
- `response_verdict` is top-level assistant metadata, not a nested `decision_summary` child and not a replacement for `decision_summary.policy`.
- the pre/post tool checks that happen before this object is stored are backend-owned hard checks and do not require extra persisted fields
- Required fields for every new assistant turn are:
  - `schema_version`: `response_verdict.v1`
  - `response_mode`: `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, or `urgent_care_disclaimer`
  - `medical_risk_level`: `low`, `medium`, or `high`
  - `evidence_sufficiency`: `sufficient`, `limited`, or `insufficient`
  - `human_escalation_required`: boolean
  - `degraded_reason`: `null` or one of `insufficient_evidence`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `policy_guardrail`, or `urgent_risk_detected`
- Coexistence rules:
  - `decision_summary.verdict` remains the lane/result code for the six-lane routing matrix.
  - `decision_summary.policy` remains the explicit policy-evaluation trace.
  - `response_verdict` is the answer-level summary of the emitted assistant reply and must not silently redefine either existing field.
- Replay and persistence rules:
  - new assistant turns should persist `response_verdict` on the `ChatMessage` row and replay the same stored object later
  - replay must not recompute `response_verdict` for a stored turn from newer heuristics once the row already has one
  - user turns should store or return `response_verdict=null`
  - legacy assistant rows may lack `response_verdict`; replay must remain valid and should return `null` rather than guessing a synthetic verdict object
- Alignment rules:
  - when `decision_summary.policy` exists, `response_verdict.response_mode` should stay aligned with `decision_summary.policy.answer_mode`
  - `medical_risk_level` should stay aligned with backend policy risk
  - `evidence_sufficiency` is the public bounded summary of answer evidence and should map from policy evidence state without leaking extra backend-only categories
  - the mapping is exact: `decision_summary.policy.evidence_state=sufficient|limited|insufficient` maps to the same `response_verdict.evidence_sufficiency` value; new turns must never emit `missing`
- `human_escalation_required=true` means the assistant answer requires offline human follow-up as part of the safe answer boundary. It is mandatory for urgent-care routing and diagnosis-sensitive answers, and may also be true for medication guardrail refusals.
- `degraded_reason` is the public dominant degradation reason. If multiple causes apply, the backend should persist one dominant reason using this priority: `urgent_risk_detected` -> `policy_guardrail` -> `conflicting_evidence` -> `tool_unavailable` -> `missing_required_context` -> `insufficient_evidence`.
- This slice does not require backfill. Legacy rows remain valid persistence facts even if they lack `response_verdict`.

### 4.2.5 QA Coverage Expectations For The Routing Freeze

- Normal consultation coverage must prove `general_health` emits only allowed tools, stays non-diagnostic, and degrades to `insufficient_evidence` instead of fabricating health facts.
- Urgent symptom coverage must prove `urgent_symptom` short-circuits before tool or RAG execution, emits `seek_urgent_care`, and always includes the mandatory in-person care reminder.
- Medication coverage must prove `medication_related` stays factual, uses only medication/report/guideline tools, and never emits prescribing, titration, or stop/start advice.
- Diagnosis-sensitive coverage must prove diagnosis-seeking prompts land in `diagnosis_sensitive`, avoid diagnosis claims, and always include the mandatory clinician / in-person reminder.
- Insufficient-evidence coverage must prove `general_health`, `report_interpretation`, `trend_review`, `medication_related`, and `diagnosis_sensitive` can all emit `insufficient_evidence` without silently switching lane semantics.
- Conflict-evidence coverage must prove contradictory personal evidence or weak-retrieval disagreement persists `conflicting_evidence`, keeps the selected lane stable, and stores clarification / clinician-follow-up guidance instead of guessed reconciliation.

### 4.3 Chat Conversation Persistence

Primary entities:

- `ChatConversation`
- `ChatMessage`

Meaning:

- `ChatConversation` is the server-owned container for one Dr. AI session
- `ChatMessage` is the ordered persisted turn record for that conversation

Rules:

- one conversation belongs to exactly one authenticated user
- `ChatConversation.title` is backend-owned and may be summarized from the first user turn, or set by an explicit manual rename
- `ChatConversation.last_accessed_at` is backend-owned recency metadata used for recent-session ordering
- `ChatConversation.pinned_at` is backend-owned pin metadata used to keep selected sessions at the top of the sidebar
- `ChatConversation.archived_at` represents whether the session is currently archived from the default sidebar view
- `ChatConversation.archived_at` is the only persisted archive flag used by single-item archive/restore plus batch archive/restore flows
- batch archive/restore does not introduce a separate bulk marker, folder flag, restore queue, or selection column
- batch archive/restore preparation state lives only in the frontend or in a transient request body; it is not persisted on the conversation row
- batch restore clears `archived_at` only and does not rewrite `pinned_at`, `last_accessed_at`, `title`, or derived grouping metadata
- the backend must preserve a user-set non-empty title and must not overwrite it with auto-generated summaries on later turns
- user and assistant turns are both persisted
- `ChatMessage` may also persist assistant evidence metadata through `sources`, `evidence_tags`, `decision_summary`, `response_verdict`, `evidence_panel`, and `suggestion_card`
- prompt reconstruction uses a recent sliding window rather than full transcript replay
- conversation state supports continuity, cache correctness, later auditability, and historical replay of assistant evidence context
- conversation list grouping metadata (`group_key`, `group_label`) is derived at read time from the backend recency and pin state; it is not a persisted column in this freeze
- `response_verdict` is assistant-message metadata only; user turns must not invent a non-null answer-level verdict object
- `evidence_panel` is assistant-message metadata only; user turns must not invent sectioned evidence payloads
- `ChatMessage` must not absorb internal-only replay fields such as `context_budget_summary`, `tool_result_summary`, `rag_source_refs`, `tool_plan_source`, `fallback_used`, or `model_name`
- replay packages must reference the existing assistant `ChatMessage` row instead of duplicating `ChatMessage.content`

### 4.3.1 Agent Answer Replay

Meaning:

- Internal-only bounded replay package for one finalized assistant answer turn
- Separate from `ChatMessage` because replay needs postmortem/accountability metadata that must not become part of the frontend-visible conversation-history contract
- Separate from `AgentAuditEvent` because replay needs one assistant-message keyed reconstruction bundle rather than only the append-only responsibility row

Required persisted fields for new rows:

- `schema_version`
- `user_id`
- `conversation_id`
- `chat_message_id`
- `audit_event_id`
- `policy_snapshot`
- `execution_snapshot`
- `context_budget_summary`
- `tool_result_summary`
- `rag_source_refs`
- `created_at`

Canonical persisted payload shape:

```json
{
  "schema_version": "agent_answer_replay.v1",
  "user_id": 1,
  "conversation_id": 12,
  "chat_message_id": 88,
  "audit_event_id": 144,
  "policy_snapshot": {
    "lane": "general_health",
    "verdict": "general_guidance",
    "selected_rule": "general_health",
    "policy_version": "explicit_policy.v1",
    "response_mode": "bounded_answer",
    "evidence_sufficiency": "limited",
    "medical_risk_level": "medium",
    "human_escalation_required": false,
    "degraded_reason": "insufficient_evidence"
  },
  "execution_snapshot": {
    "governance_version": "agent_runtime_governance.v1",
    "model_name": "moonshot-v1-8k",
    "tool_plan_source": "native_function_calling",
    "cache_hit": false,
    "fallback_used": false,
    "tool_count": 1,
    "tool_latency_ms": 17,
    "response_latency_ms": 93
  },
  "context_budget_summary": {
    "profile": {"budget": 500, "used": 120},
    "rag": {"budget": 1500, "used": 420},
    "tools": {"budget": 800, "used": 90},
    "query": {"budget": 300, "used": 18},
    "history": {"budget": 320}
  },
  "rag_quality_summary": {
    "retrieval_status": "ok",
    "hit_count": 3,
    "unique_source_count": 2,
    "source_kind": "mixed",
    "density_status": "low_density",
    "ocr_fallback_state": "available",
    "provenance_state": "partial",
    "chunk_quality": "mixed"
  },
  "tool_result_summary": [
    {
      "tool_name": "search_medical_guidelines",
      "status": "ok",
      "summary_label": "Guideline evidence retrieved",
      "count": 1,
      "freshness": "recent",
      "coverage": "partial",
      "confidence": "medium",
      "blocked_reason": null,
      "source_refs": ["guideline.pdf"]
    }
  ],
  "rag_source_refs": [
    {
      "source": "guideline.pdf",
      "page": 12,
      "chunk_index": 3,
      "page_range": [12, 12]
    }
  ],
  "created_at": "2026-04-01T12:00:00Z"
}
```

Contract semantics:

- `schema_version` must be `agent_answer_replay.v1` for new rows.
- One row corresponds to exactly one finalized assistant `ChatMessage` and exactly one `AgentAuditEvent`.
- `chat_message_id` must point only to an assistant turn. User turns, partial SSE status events, and tool events do not get replay rows.
- `policy_snapshot` is a bounded denormalized answer-boundary snapshot. It may contain only `lane`, `verdict`, `selected_rule`, `policy_version`, `response_mode`, `evidence_sufficiency`, `medical_risk_level`, `human_escalation_required`, and `degraded_reason`.
- `execution_snapshot` is a bounded denormalized runtime snapshot. It may contain only `governance_version`, sanitized `model_name`, `tool_plan_source`, `cache_hit`, `fallback_used`, `tool_count`, `tool_latency_ms`, and `response_latency_ms`.
- `context_budget_summary` reuses the same bounded lane structure as `AgentAuditEvent`; only `profile`, `rag`, `tools`, `query`, and `history` are allowed, and only `budget` plus optional `used` are allowed under each lane.
- `rag_quality_summary` is optional bounded runtime metadata. When present, it may contain only `retrieval_status`, `hit_count`, `unique_source_count`, `source_kind`, `density_status`, `ocr_fallback_state`, `provenance_state`, and `chunk_quality`.
- `tool_result_summary` is a bounded list. Each item may contain only `tool_name`, `status`, `summary_label`, `count`, `freshness`, `coverage`, `confidence`, `blocked_reason`, and stable `source_refs`.
- `rag_source_refs` is provenance-only. Each item may contain only `source` plus optional `page`, `chunk_index`, `page_range`, and `section_title`.
- Replay rows must not duplicate `ChatMessage.content`; the row references the assistant message instead.
- Replay rows must not persist raw query text, raw assistant reply text, prompt text, planning messages, large RAG text, passage snippets, raw tool results, raw tool arguments, raw OCR payloads, raw risk payloads, or unsanitized medical payloads.
- The runtime may use bounded backend-authored `summary_label` text in `tool_result_summary`, but it must not copy free-form provider output or raw evidence text into replay storage.

Current runtime gaps called out explicitly:

- [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) currently has no `AgentAnswerReplay` entity or equivalent one-to-one replay storage.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) already computes the bounded policy, verdict, context-budget, tool, and RAG-reference inputs, but it does not yet persist them as a separate replay row tied to the finalized assistant message or attach the bounded RAG quality summary.
- [backend/services/conversation_service.py](E:\health_ai_platform_2.0\backend\services\conversation_service.py) currently replays only `ChatMessage` fields, which must stay frontend-safe and must not silently grow the internal replay payload.

### 4.4 Agent Audit Event

Meaning:

- Durable backend-owned responsibility evidence for one completed assistant turn or one short-circuited safety response
- Append-only operational record that persists bounded runtime-governance metadata rather than raw transcript content
- Internal-only storage that supports later backend observability, retention, and answer-boundary accountability workflows

Required persisted fields for new rows:

- `schema_version`
- `governance_version`
- `timestamp`
- `user_id`
- `conversation_id`
- `intent`
- `lane`
- `verdict`
- `selected_rule`
- `policy_version`
- `response_mode`
- `evidence_sufficiency`
- `degraded_reason`
- `human_escalation_required`
- `model_name`
- `tool_plan_source`
- `tool_used`
- `cache_hit`
- `safety_level`
- `evidence_tags`
- `context_budget_summary`
- `tool_latency_ms`
- `tool_count`
- `response_latency_ms`
- `fallback_used`

Canonical persisted payload shape:

```json
{
  "schema_version": "agent_audit_responsibility.v2",
  "governance_version": "agent_runtime_governance.v1",
  "timestamp": "2026-04-01T12:00:00Z",
  "user_id": 1,
  "conversation_id": 12,
  "intent": "guideline_lookup",
  "lane": "general_health",
  "verdict": "general_guidance",
  "selected_rule": "general_health",
  "policy_version": "explicit_policy.v1",
  "response_mode": "bounded_answer",
  "evidence_sufficiency": "limited",
  "degraded_reason": "insufficient_evidence",
  "human_escalation_required": false,
  "model_name": "moonshot-v1-8k",
  "tool_plan_source": "native_function_calling",
  "tool_used": ["search_medical_guidelines"],
  "cache_hit": false,
  "safety_level": "normal",
  "evidence_tags": ["guideline_search"],
  "context_budget_summary": {
    "profile": {"budget": 500, "used": 120},
    "rag": {"budget": 1500, "used": 420},
    "tools": {"budget": 800, "used": 90},
    "query": {"budget": 300, "used": 18},
    "history": {"budget": 320}
  },
  "rag_quality_summary": {
    "retrieval_status": "ok",
    "hit_count": 3,
    "unique_source_count": 2,
    "source_kind": "mixed",
    "density_status": "low_density",
    "ocr_fallback_state": "available",
    "provenance_state": "partial",
    "chunk_quality": "mixed"
  },
  "tool_latency_ms": 17,
  "tool_count": 1,
  "response_latency_ms": 93,
  "fallback_used": false
}
```

Contract semantics:

- `schema_version` is the persisted audit schema identifier. New rows must use `agent_audit_responsibility.v2`. Historical `audit_event.v1` rows remain valid legacy facts but are not the target write shape.
- `governance_version` is the architect-owned runtime-governance baseline for the turn. The frozen value in this docs set is `agent_runtime_governance.v1`, and future changes must be approved in docs first and then recorded by `orchestrator` in `docs/blackboard/state.yaml`.
- `intent` remains a backward-compatible trace field, but the responsibility meaning of the row is carried by `lane`, `verdict`, `selected_rule`, `policy_version`, `response_mode`, `evidence_sufficiency`, `degraded_reason`, and `human_escalation_required`.
- `lane` must use the frozen six-lane enum from the chat-routing contract.
- `verdict` must use the frozen routing-verdict enum from the chat-routing contract.
- `selected_rule` must mirror `decision_summary.policy.selected_rule` and is expected to remain lane-aligned in the current runtime.
- `policy_version` must mirror `decision_summary.policy.policy_version` and is required for every new row.
- `response_mode` must be one of `direct_answer`, `bounded_answer`, `clarify_missing_context`, `refusal_with_disclaimer`, or `urgent_care_disclaimer`.
- `evidence_sufficiency` must be one of `sufficient`, `limited`, or `insufficient`.
- `degraded_reason` must be `null` or one of `insufficient_evidence`, `missing_required_context`, `tool_unavailable`, `conflicting_evidence`, `policy_guardrail`, `urgent_risk_detected`, `unsafe_medication_request`, `diagnosis_sensitive_request`, or `urgent_symptom`.
- `human_escalation_required` is the persisted offline-follow-up flag for the emitted assistant answer.
- `model_name` is an optional sanitized model identifier. It must be `null` when no new model call materially contributed to the emitted answer, such as urgent short-circuit and cache replay.
- `tool_plan_source` must be one of `native_function_calling`, `local_fallback_planner`, `no_tool_path`, `cache_replay`, or `urgent_short_circuit`.
- `cache_hit` is required and records whether the emitted assistant reply body came from cache on the current turn.
- `fallback_used` is required and records whether tool planning degraded from native tool calling to the local planner on the current turn.
- `tool_used` is a bounded list of backend-registered tool names only; it must not contain free-form notes or arguments.
- The payload is metadata-only and must not store raw query text, assistant reply text, prompt text, large RAG snippets, model tokens, provider response ids, or other unbounded content.
- The payload must not store raw tool results, raw OCR text, raw report payloads, raw risk snapshots, or unsanitized medical payloads.
- `context_budget_summary` may contain only bounded lane-level budget and usage facts for `profile`, `rag`, `tools`, `query`, and `history`. It must not contain source text or raw medical payloads.
- `rag_quality_summary` may contain only the bounded query-time quality fields frozen above. It must not contain similarity scores, raw passages, OCR text, benchmark traces, or loader exception payloads.
- The record is user-scoped and conversation-scoped but not user-visible.
- Storage is owned by `be`; read access is limited to backend services and internal maintenance/observability workflows.
- Backend runtime logging remains alongside persisted audit rows. The logger-based audit trail is operational trace data, not a replacement for durable persisted records.
- Retention is frozen to the internal observability window for the associated conversation. Responsibility rows must survive at least as long as the associated conversation history and may not silently become a broader transcript-retention surface.
- FE and public API callers must not read, mutate, or widen this record directly.
- Any future request to expose audit search, export, or filtering through chat routes is contract pressure and must return through `architect`.

Current runtime gaps called out explicitly:

- [backend/models.py](E:\health_ai_platform_2.0\backend\models.py) still persists `AgentAuditEvent` as `audit_event.v1` and does not yet declare the frozen responsibility fields.
- [backend/services/agent_audit.py](E:\health_ai_platform_2.0\backend\services\agent_audit.py) still builds and sanitizes only the older call-record shape.
- [backend/services/chat_service.py](E:\health_ai_platform_2.0\backend\services\chat_service.py) already computes `policy_version`, `response_mode`, `evidence_sufficiency`, `degraded_reason`, cache-hit state, and planner provenance, but it does not yet persist them as one normalized responsibility row across every finalize path.

### 4.5 Projection/Trend Inputs

Projection and timeline behaviors depend on `UserProfile`, `HealthRecord`, and current engine behavior.  
They are P1-supporting in product priority, but still part of the current data landscape because timeline views and health history are already surfaced in the app.

## 5. Persistence And Privacy Rules

- `UserProfile` is the current-state source of truth
- `HealthRecord` is append-only historical evidence from profile updates
- `MedicalDocument` is the uploaded artifact record
- `ChatConversation` is the session container for Dr. AI
- `ChatConversation.title` stores the latest authoritative backend-owned display title, whether auto-generated or manually renamed
- `ChatConversation.last_accessed_at` stores recent-session ordering state for the sidebar
- `ChatConversation.pinned_at` stores optional pinned-session ordering state for the sidebar
- `ChatConversation.archived_at` stores archive state for active-vs-archived session management
- `ChatMessage` is the append-only turn log for Dr. AI
- `ChatMessage.sources` stores persisted source labels for historical assistant replay when available
- `ChatMessage.evidence_tags` stores persisted backend-owned evidence tags for historical assistant replay when available
- `ChatMessage.decision_summary` stores persisted backend-owned decision metadata, including the optional nested `policy` envelope, for historical assistant replay when available
- `ChatMessage.response_verdict` stores the additive backend-owned answer-level verdict object for historical assistant replay when available
- `ChatMessage.evidence_panel` stores optional backend-owned compact-chip plus sectioned-detail evidence metadata for historical assistant replay when available
- `ChatMessage.suggestion_card` stores an optional backend-owned structured health-guidance card for historical assistant replay when available
- `ChatMessage.takeover` stores an optional backend-owned human-handoff projection for historical assistant replay when available
- `AgentAnswerReplay` stores the internal-only bounded replay package for one finalized assistant answer turn
- `AgentAuditEvent` stores durable backend-owned responsibility metadata for operational observability, retention, and answer-boundary accountability workflows
- Genomic payloads must remain encrypted at rest through the current property-backed mechanism
- Research export features remain outside the current contract freeze, but `allow_research` is already a persisted consent field
- Backfill is not required in this slice; legacy persisted payloads may remain until BE repair scripts are introduced under the frozen normalization rules

## 6. Lifecycle Rules

### 6.1 Profile Lifecycle

1. User is created
2. Empty profile may be created immediately
3. Profile is updated through manual entry and/or OCR-assisted merge
4. Update may create `HealthRecord` snapshot
5. Updated state may invalidate cache and affect downstream analysis/chat

### 6.2 Medical Document Lifecycle

1. File uploaded
2. File saved on disk
3. `MedicalDocument` row created
4. OCR parsing attempted when prerequisites are available
5. `ocr_processing_status` resolves to `success`, `partial_success`, `stored_unprocessed`, or `error`
6. `ocr_summary` is populated only when structured OCR output exists
7. Client may later fetch or delete the document

### 6.3 Clinical Field Lifecycle

1. User profile fields start as absent or previously persisted values
2. OCR/import, manual entry, or approved derivation may update one or more fields
3. Backend-owned field-state metadata records whether each value is `recognized`, `derived`, `missing`, `user_confirmed`, or `user_entered`
4. Analysis uses the field-state metadata to decide whether the result is `final`, `provisional`, or `blocked`
5. Missing required non-derivable fields remain missing until a real source or user action supplies them

## 7. ETL And Training Boundaries

Current ETL/training assets are repository-local and important, but not part of the P0 public contract freeze.

This document freezes only these expectations:

- ETL and training outputs may influence runtime model behavior
- Runtime APIs should not depend on frontend knowing training-pipeline internals
- Changes to model input/output semantics that alter API-visible meaning require escalation back through `architect`

## 8. Open Issues And Risks

- The repository uses SQLModel table models directly in several API-facing flows, so strict separation between DB schema and API schema is incomplete
- OCR extraction output shape is already variable in persistence and now has a frozen canonical target envelope that BE still needs to adopt
- OCR processing state is not yet frozen in runtime storage or route projection; BE still needs to separate saved-but-unprocessed uploads from true OCR errors
- There is still no backend-owned persisted or derived `clinical_field_state_snapshot.v1`, so FE currently relies on local heuristics for OCR-not-found and derived values
- Risk-report structure is engine-owned and only partially standardized; the existing `risk_snapshot.v1` envelope freezes a normalized persistence target without changing the raw engine contract itself
- SQLite is current runtime truth, while some repo docs mention PostgreSQL as future direction
- Current runtime note: `backend/models.py`, `backend/api/api_v1/endpoints/chat.py`, and the chat runtime now carry `evidence_panel`, so that metadata contract is live rather than pending
- Current runtime note: `backend/models.py`, `backend/api/api_v1/endpoints/chat.py`, and the chat runtime already carry `response_verdict`, but the evidence sufficiency semantics still drift between legacy `missing` wording and the newer `insufficient` wording; BE must align persisted and live policy metadata to the frozen gate without breaking replay
- Current runtime note: `AgentAuditEvent` is still implemented as `audit_event.v1` with call-oriented fields only, so BE must align `backend/models.py`, `backend/services/agent_audit.py`, and finalize-path writes to the frozen responsibility schema without exposing any audit surface publicly
- Current runtime note: the repository still has no dedicated `AgentAnswerReplay` structure, so BE must add the frozen bounded replay package without widening `ChatMessage` or exposing replay-only fields on history routes
- There is no dedicated persisted medication entity; `medication_summary_lookup` therefore depends on normalized medication facts embedded in `MedicalDocument.ocr_summary` and stable medication facts in `UserProfile.extra_data`
- `recent_metric_anomaly_lookup` depends on existing anomaly-detection semantics whose output fields are more detailed than current chat-evidence needs; BE must implement the frozen bounded projection rather than pass the full raw anomaly list through unchecked
- `report_comparison_lookup` depends on selecting two user-owned OCR summaries and comparing their normalized projections; BE must avoid raw file diffing or arbitrary history scans
- RAG chunk metadata is still build-time only in the current code path; BE must enrich internal chunk provenance with `source`, `page`, and `chunk_index` while keeping the chat API unchanged
- current prompt-building code still truncates raw `risk_history` strings and some OCR consumers still expect a `summary` field that legacy payloads do not guarantee; BE needs to move those reads onto the shared normalizer
- current product behavior still needs one backend-owned answer to incomplete-data semantics: provisional analysis is not yet surfaced as a frozen contract, and default-estimate behavior must remain prohibited
- current chat routing code still centers on open-ended `intent` strings plus urgent-vs-normal safety checks; BE must align persisted and live `decision_summary` metadata to the frozen `lane` / `verdict` enums without introducing a frontend-owned classifier
- current chat response code still has no frozen `takeover` field on `ChatMessage`, so BE must add the new object across send, stream final, and history replay if it implements the contract
- lane-level tool eligibility is not yet persisted or enforced as its own backend-owned matrix, so BE must keep the tool whitelist behind the runtime boundary rather than letting FE or prompt wording redefine it

## 9. Contract Escalation Rules

- `fe` may not redefine profile, OCR, or risk result semantics
- `be` may not silently rewrite data-model meaning or the `evidence_panel` section schema without updating this contract
- `fe` and `be` may not silently redefine the canonical envelopes for `MedicalDocument.ocr_summary`, `HealthRecord.risk_snapshot`, or `UserProfile.risk_history`
- `be` may not silently replace the normalized result shapes for `medication_summary_lookup`, `recent_metric_anomaly_lookup`, or `report_comparison_lookup` with raw persistence payloads or write-capable behavior
- `fe` may consume only backend-emitted `decision_summary.lane` and `decision_summary.verdict` as chat-routing semantics; it may not reinterpret `intent` or derive its own medical lane model
- `fe` may ignore `decision_summary.policy` fields, including `risk_level`, `evidence_state`, `tool_availability`, and `disclaimer_mode`; they remain backend-owned policy hints.
- `fe` may read `response_verdict`, but it may not redefine it, infer it from `decision_summary.verdict`, or introduce another answer-level verdict object
- `fe` may read `takeover`, but it may not derive new clinical meaning, infer a hidden handoff state from `summary`, or repurpose the object into a workflow, ticketing, or disclaimer system
- `be` may not silently change the `decision_summary.policy` shape, policy-version compatibility rule, or answer-mode set without an architect-owned contract update
- `be` may not silently rename `response_verdict`, move it under `decision_summary`, widen its enums, or synthesize it for legacy rows without an architect-owned contract update
- `be` may not silently rename `takeover`, move it under `decision_summary`, widen its status or trigger enums, or synthesize a different human-handoff object for legacy rows without an architect-owned contract update
- `be` may not silently widen `AgentAuditEvent` beyond the frozen responsibility fields, persist raw query/reply/prompt text, large RAG text, or unsanitized medical payloads into audit storage, or auto-bump `schema_version` / `governance_version` without an architect-owned contract update
- `be` may not silently widen `ChatMessage` with internal replay-only fields or collapse the replay package into `AgentAuditEvent`; bounded replay must stay in the separate `AgentAnswerReplay` structure
- `be` may not silently persist raw query/reply/prompt text, large RAG text, raw tool results, raw tool arguments, or unsanitized medical payloads into `AgentAnswerReplay`
- `be` may not silently emit new lane names, verdict codes, or lane / verdict combinations outside the frozen six-lane matrix
- `be` may not silently introduce a batch-delete, hard-delete, purge, or archived-folder mutation conversation model in this freeze; batch archive/restore stays row-wise and continues to use `ChatConversation.archived_at`
- `ai-data` may not change model-visible output semantics that affect API consumers without routing the change through `architect`

## 10. Decision Log

| Decision | Rationale |
|----------|-----------|
| Treat `UserProfile` as the canonical current-state health entity | Matches current repository behavior and frontend integration |
| Treat `HealthRecord` as historical evidence rather than secondary editable profile | Preserves timeline semantics |
| Keep OCR extraction as best-effort structured JSON rather than over-constraining every field | Matches the current fallback-heavy OCR pipeline |
| Freeze model semantics at the backend boundary, not the frontend boundary | Prevents API drift caused by direct model assumptions in UI code |
| Freeze `evidence_panel` as persisted assistant metadata rather than frontend-derived UI state | Keeps evidence semantics replayable and backend-owned across live and historical chat flows |
| Freeze section-level `source_items` as bounded drill-down metadata | Preserves replay parity while adding renderable source detail without raw payload exposure |
| Reuse existing persistence objects for the next tool slice instead of introducing new tables in the architecture-only pass | Keeps the slice additive and conservative for implementation handoff |
| Freeze `medication_summary_lookup` as a bounded medication-facts projection rather than prescribing advice | Keeps the tool retrieval-only and backend-internal |
| Freeze `recent_metric_anomaly_lookup` as a bounded anomaly summary over latest metric inputs | Reduces medical-domain overexposure of raw anomaly payloads |
| Freeze `report_comparison_lookup` as a pairwise normalized OCR-summary comparison | Gives BE a bounded diff surface without raw file export semantics |
| Freeze transient `evidence_metadata` as runtime-only tool quality metadata | Preserves the existing persisted assistant-message model without adding a new storage surface |
| Keep the next tool slice backend-internal through the provider-native function-calling path | Avoids public chat API churn while preserving the current route surface |
| Reuse existing `report`, `profile`, and `trend` source types for evidence mapping in this slice | Prevents inventing a new taxonomy just for the tool boundary |
| Freeze `ocr_summary.v1` and `risk_snapshot.v1` as canonical persistence targets while preserving legacy-read compatibility | Gives BE one safe target for shared normalization and later repair scripts without forcing immediate backfill |
| Freeze internal RAG chunk metadata as `source`, `page`, and `chunk_index` with optional section hints | Preserves page-aware provenance without turning KB build state into a public model |
| Freeze query-time RAG quality summary as bounded runtime metadata for internal audit/replay only | Keeps conservative degrade behavior observable without widening the public chat contract |
| Treat `UserProfile.risk_history` as a single latest-snapshot contract despite the legacy name | Prevents accidental drift into incompatible list/history semantics |
| Keep batch archive row-wise over `archived_at` and refuse a new bulk-delete persistence model | Preserves the current conversation schema and avoids destructive bulk semantics |
| Keep batch restore row-wise over `archived_at` and refuse a new archived-folder or bulk-restore persistence model | Preserves the current conversation schema and keeps restore semantics additive rather than structural |
| Freeze `decision_summary.lane` and `decision_summary.verdict` as the FE-consumable medical-routing metadata | Replaces ad hoc intent semantics with one bounded backend-owned routing contract |
| Freeze the chat runtime into six medical risk lanes with per-lane tool and depth boundaries | Prevents BE/FE drift on safety posture and evidence use without widening the route surface |
| Freeze `decision_summary.policy` as an additive backend-owned explicit policy envelope | Makes rule priority, answer mode, and degrade behavior explicit without creating a new persistence table |
| Freeze top-level `response_verdict` as additive assistant-turn metadata | Avoids semantic collision with `decision_summary.verdict` while preserving replay-safe answer-boundary metadata |
| Freeze `takeover` as a separate backend-owned human-handoff projection | Gives FE a bounded handoff signal without turning the assistant-message model into a workflow, ticketing, or disclaimer system |
| Freeze the evidence sufficiency gate to `sufficient`, `limited`, and `insufficient`, and add `conflicting_evidence` as an explicit degrade reason | Removes doc/runtime drift and prevents BE from inventing new insufficiency semantics later |
| Upgrade `AgentAuditEvent` to `agent_audit_responsibility.v2` with explicit governance fields | Captures why the runtime answered, degraded, or escalated without storing prompts, transcripts, large RAG text, or unsanitized medical payloads |
| Freeze `AgentAnswerReplay` as a separate bounded per-answer structure | Preserves postmortem reconstruction needs without widening `ChatMessage`, overloading `AgentAuditEvent`, or turning replay into raw-context archiving |
