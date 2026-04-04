# Post-QA Remaining Issues Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the remaining issues found in second-round QA by fixing OCR service readiness and degraded UX, eliminating non-blocking runtime warnings that threaten release confidence, and closing the highest-risk browser coverage gaps.

**Architecture:** Treat this as three linked workstreams. First, fix the OCR contract so "document saved but extraction unavailable" is represented explicitly rather than as a generic 500. Second, make optional runtime dependencies and persisted payload shapes deterministic so the platform starts cleanly in both full and degraded modes. Third, add regression coverage for the OCR/document flow and the highest-risk unverified screens before the next release decision.

**Tech Stack:** FastAPI, SQLModel, Pydantic Settings, Vue 3, Pinia, Axios, Playwright, Pytest

---

## Scope and Root Causes

### Confirmed root causes from QA

1. OCR extraction is environment-sensitive and currently fails closed.
   - `backend/services/ocr_service.py` marks Baidu OCR unavailable and returns `"status": "error"` when OCR text is empty.
   - `backend/api/api_v1/endpoints/ocr.py` persists the document first, then turns that extraction error into HTTP 500.
   - Result: upload succeeds operationally, but the UI sees a hard failure even though the document is already stored and user-visible.

2. OCR incomplete-data handling is product-unsafe today.
   - The current fallback pattern is effectively "ask user to estimate missing values".
   - This is too loose for health data. Missing values need explicit status, confidence, and guided follow-up instead of approximate manual guessing.

3. Runtime startup remains noisy and environment parity is weak.
   - `backend/main.py` now degrades correctly when fusion engine dependencies are missing, but `xgboost` absence still needs explicit environment policy and test coverage.
   - `backend/services/risk_engine.py` and related model loaders emit sklearn version mismatch warnings.
   - Redis absence is handled, but there is no clear release rule for "cache optional vs required".
   - `extra_data` can still cross layers as a string, causing serialization warnings.

4. Browser coverage is still incomplete outside the main flow.
   - Core paths were validated.
   - `admin`, `genomics`, `lifestyle`, `pharmacy`, and `nutrition` still need browser smoke coverage to support a true release-ready claim.

## File Map

### Architecture and contracts
- Modify: `docs/architecture.md`
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model-contract.md`
- Modify: `docs/qa-report.md`

### Backend OCR and data normalization
- Modify: `backend/api/api_v1/endpoints/ocr.py`
- Modify: `backend/services/ocr_service.py`
- Modify: `backend/services/payload_normalization.py`
- Modify: `backend/models.py`
- Modify: `backend/main.py`
- Modify: `backend/core/config.py`
- Modify: `backend/services/risk_engine.py`
- Modify: `backend/services/lifestyle_service.py`
- Modify: `backend/services/inference_service.py`

### Frontend OCR UX and guided completion
- Modify: `frontend/src/views/ClinicalView.vue`
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/stores/healthStore.js`
- Modify: `frontend/src/utils/api.js` only if contract or error-mapping needs a shared helper

### Tests
- Modify: `tests/test_main.py`
- Add: `tests/test_ocr_service.py`
- Add: `tests/test_payload_normalization.py` if missing focused coverage
- Add: `frontend/tests/ocr-upload.spec.js`
- Add: `frontend/tests/profile-documents.spec.js`
- Add: `frontend/tests/app-smoke.spec.js`

## Chunk 1: OCR Contract and Service Behavior

### Task 1: Define the OCR degraded contract before implementation

**Files:**
- Modify: `docs/api-contract.md`
- Modify: `docs/data-model-contract.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Document the new OCR outcome matrix**

Define these backend outcomes precisely:
- `success`: document saved, OCR extracted structured fields
- `partial_success`: document saved, OCR ran but only partial or low-confidence extraction is available
- `stored_unprocessed`: document saved, OCR provider unavailable or credentials invalid, no extracted fields yet
- `error`: file invalid, corrupt, or server-side persistence failed

- [ ] **Step 2: Freeze the response contract**

Specify the OCR upload response shape:

```json
{
  "status": "partial_success",
  "document_id": 123,
  "file_url": "/static/medical_reports/20260403_123000_abcd1234.pdf",
  "ocr": {
    "provider_status": "unavailable",
    "extraction_status": "not_started",
    "message": "OCR provider unavailable; document saved for later processing.",
    "confidence": null,
    "missing_fields": ["Height", "Weight", "SBP"]
  },
  "data": null
}
```

- [ ] **Step 3: Define the canonical per-field schema**

Add a canonical OCR metric entry shape:

```json
{
  "value": 6.8,
  "unit": "mmol/L",
  "confidence": 0.93,
  "source_excerpt": "空腹血糖 6.8 mmol/L",
  "field_status": "recognized"
}
```

Allowed `field_status` values:
- `recognized`
- `derived`
- `missing`
- `user_confirmed`
- `user_entered`

- [ ] **Step 4: Escalate if contract changes require architect approval**

Do not let FE and BE silently reinterpret HTTP 500 as a business-state success. This is an API contract change and must be routed through architecture.

- [ ] **Step 5: Commit**

```bash
git add docs/architecture.md docs/api-contract.md docs/data-model-contract.md
git commit -m "docs: define degraded OCR contract and field status model"
```

### Task 2: Make OCR upload fail soft instead of fail closed

**Files:**
- Modify: `backend/api/api_v1/endpoints/ocr.py`
- Modify: `backend/services/ocr_service.py`
- Test: `tests/test_main.py`
- Test: `tests/test_ocr_service.py`

- [ ] **Step 1: Write failing backend tests for degraded OCR**

Add tests for:
- document is persisted even when provider is unavailable
- API returns `200` with `stored_unprocessed` or `partial_success`, not `500`
- response includes `document_id`, `file_url`, and explicit OCR provider/extraction status

Example test shape:

```python
def test_ocr_upload_returns_stored_unprocessed_when_provider_unavailable(client, session, monkeypatch):
    monkeypatch.setattr(
        "backend.api.api_v1.endpoints.ocr.medical_ocr_service.parse_medical_report",
        lambda file_bytes: {
            "status": "stored_unprocessed",
            "message": "OCR provider unavailable; document saved for later processing.",
            "data": None,
            "ocr": {
                "provider_status": "unavailable",
                "extraction_status": "not_started",
                "confidence": None,
                "missing_fields": []
            },
        },
    )
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
python -m pytest tests/test_main.py -k ocr -q
```

Expected: current endpoint still returns 500 on `"status": "error"` style OCR failures.

- [ ] **Step 3: Refactor `MedicalOCRService.parse_medical_report`**

Implement these rules:
- If provider is unavailable, return `stored_unprocessed`
- If OCR text is empty but provider was reachable, return `partial_success`
- If text exists but no structured fields extracted, still return `partial_success`
- Only return `error` for unrecoverable request-level failures

- [ ] **Step 4: Refactor the upload endpoint**

In `backend/api/api_v1/endpoints/ocr.py`:
- Keep persistence first
- Persist a canonical `ocr_summary.v1` only when structured data exists
- Return the new business-state response instead of raising 500 for degraded OCR
- Invalidate cache only after document mutation succeeds

- [ ] **Step 5: Re-run the targeted backend tests**

Run:

```bash
python -m pytest tests/test_main.py -k ocr -q
python -m pytest tests/test_ocr_service.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/api/api_v1/endpoints/ocr.py backend/services/ocr_service.py tests/test_main.py tests/test_ocr_service.py
git commit -m "fix: return explicit degraded OCR states instead of upload 500s"
```

## Chunk 2: Safe Incomplete-Data UX

### Task 3: Replace "approximate value" guidance with guided completion

**Files:**
- Modify: `frontend/src/views/ClinicalView.vue`
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/stores/healthStore.js`
- Modify: `docs/architecture.md`
- Test: `frontend/tests/ocr-upload.spec.js`
- Test: `frontend/tests/profile-documents.spec.js`

- [ ] **Step 1: Write failing browser tests for partial OCR**

Cover:
- upload returns degraded state and UI shows "document saved, extraction unavailable"
- recognized fields are applied
- missing fields are highlighted but not auto-guessed
- user can continue with a provisional analysis
- profile documents page shows status badges correctly

- [ ] **Step 2: Run the Playwright specs to verify they fail**

Run:

```bash
cd frontend
npx playwright test tests/ocr-upload.spec.js tests/profile-documents.spec.js
```

Expected: current UI only shows a generic failure toast and does not expose a guided completion path.

- [ ] **Step 3: Add a field-state model in the clinical form**

Implement:
- recognized fields: auto-filled and visually tagged
- derived fields: auto-computed and visually tagged
- missing high-impact fields: highlighted with exact prompts
- low-impact missing fields: left optional

Do not auto-fill with guessed values.

- [ ] **Step 4: Add a provisional analysis mode**

In `healthStore` and `ClinicalView`:
- compute whether minimum analysis prerequisites are met
- if not fully complete but still analyzable, label the result as provisional
- surface a concise note: which missing fields most reduce confidence

- [ ] **Step 5: Improve the documents page status model**

In `ProfileView.vue`, document badges should distinguish:
- `已提取结构化数据`
- `仅已保存，待识别`
- `识别部分完成`

- [ ] **Step 6: Re-run browser tests**

Run:

```bash
cd frontend
npx playwright test tests/ocr-upload.spec.js tests/profile-documents.spec.js
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/ClinicalView.vue frontend/src/views/ProfileView.vue frontend/src/stores/healthStore.js frontend/tests/ocr-upload.spec.js frontend/tests/profile-documents.spec.js docs/architecture.md
git commit -m "feat: add guided completion flow for incomplete OCR data"
```

## Chunk 3: Runtime Warning Cleanup and Environment Policy

### Task 4: Make optional dependencies explicit and testable

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/core/config.py`
- Modify: `docs/deployment.md`
- Modify: `docs/release.md`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write failing tests or assertions for startup modes**

Cover:
- backend starts without Redis
- backend starts without xgboost and uses degraded fusion fallback
- backend logs one concise warning per missing optional dependency

- [ ] **Step 2: Define release policy for optional services**

Document in `docs/deployment.md` and `docs/release.md`:
- Redis optional in local/dev
- xgboost optional only if degraded fusion fallback is accepted for target environment
- OCR credentials required for claiming OCR extraction readiness

- [ ] **Step 3: Normalize startup logging**

Ensure warnings are:
- concise
- emitted once
- actionable
- not mixed with tracebacks during normal degraded startup

- [ ] **Step 4: Run the targeted startup tests**

Run:

```bash
python -m pytest tests/test_main.py -k "warning or fusion or startup" -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/core/config.py docs/deployment.md docs/release.md tests/test_main.py
git commit -m "chore: define optional dependency startup policy"
```

### Task 5: Eliminate sklearn and payload-shape warnings

**Files:**
- Modify: `backend/services/risk_engine.py`
- Modify: `backend/services/lifestyle_service.py`
- Modify: `backend/services/inference_service.py`
- Modify: `backend/services/payload_normalization.py`
- Modify: `backend/models.py`
- Test: `tests/test_payload_normalization.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write failing tests for payload shape normalization**

Cover:
- `extra_data` string payloads are normalized to dict before model serialization
- profile save/read paths no longer emit Pydantic serialization warnings

- [ ] **Step 2: Investigate model bundle version mismatch**

Determine whether the correct fix is:
- retrain/re-export model bundles with current sklearn version, or
- pin runtime sklearn to the bundle version

Do not do both. Pick one environment strategy and document it.

- [ ] **Step 3: Implement the chosen model compatibility fix**

Options:
- preferred: regenerate `joblib` bundles using the production sklearn version and store reproducibility metadata
- fallback: pin sklearn in environment files and startup docs

- [ ] **Step 4: Normalize `extra_data` at the boundary**

Ensure any stringified JSON is parsed before attaching it to response models.

- [ ] **Step 5: Re-run targeted tests**

Run:

```bash
python -m pytest tests/test_main.py -k profile -q
python -m pytest tests/test_payload_normalization.py -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/risk_engine.py backend/services/lifestyle_service.py backend/services/inference_service.py backend/services/payload_normalization.py backend/models.py tests/test_payload_normalization.py tests/test_main.py
git commit -m "fix: normalize payload shapes and align model runtime versions"
```

## Chunk 4: Coverage Closure

### Task 6: Add browser smoke coverage for remaining high-risk screens

**Files:**
- Add: `frontend/tests/app-smoke.spec.js`
- Modify: `frontend/playwright.config.js` only if fixture or timeout tuning is required
- Modify: `docs/qa-report.md`

- [ ] **Step 1: Write the smoke spec**

Include authenticated navigation and basic render assertions for:
- `/dashboard`
- `/clinical`
- `/profile`
- `/genomics`
- `/lifestyle`
- `/pharmacy`
- `/nutrition`
- `/admin` if test credentials support it

- [ ] **Step 2: Run the new smoke spec**

Run:

```bash
cd frontend
npx playwright test tests/app-smoke.spec.js
```

- [ ] **Step 3: Fix only true regressions**

Do not expand this into deep scenario tests during the smoke phase. Keep to:
- page loads
- no blocking console errors
- one key component visible per page

- [ ] **Step 4: Update QA evidence**

Add the second-round and post-fix evidence to `docs/qa-report.md`.

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/app-smoke.spec.js frontend/playwright.config.js docs/qa-report.md
git commit -m "test: add smoke coverage for remaining product areas"
```

## Final Verification

### Task 7: Run the full verification pass

**Files:**
- No code changes expected
- Evidence: `docs/qa-report.md`

- [ ] **Step 1: Run backend regression**

```bash
python -m pytest tests -q
```

Expected: PASS

- [ ] **Step 2: Run frontend build**

```bash
cd frontend
cmd /c npm run build
```

Expected: PASS

- [ ] **Step 3: Run Playwright regression**

```bash
cd frontend
cmd /c npx playwright test
```

Expected: PASS

- [ ] **Step 4: Run real local verification with the provided OCR PDF**

Use:
- `C:\Users\JoeWang\Desktop\新建文件夹\体检表.pdf`

Verify:
- upload returns non-500 degraded or success contract
- document appears in Profile
- extraction status badge is accurate
- recognized fields populate the clinical form
- missing fields are highlighted, not guessed
- provisional/final analysis labeling is correct

- [ ] **Step 5: Record remaining caveats**

If OCR credentials are intentionally absent in the target environment, release notes must state:
- OCR document storage works
- OCR extraction is disabled
- UI communicates this clearly

- [ ] **Step 6: Commit QA evidence**

```bash
git add docs/qa-report.md
git commit -m "test: record post-remediation verification evidence"
```

## Release Exit Criteria

- OCR upload no longer returns generic 500 for provider unavailability after document persistence.
- OCR response contract explicitly distinguishes saved, partial, and failed states.
- The UI never asks users to invent approximate health values by default.
- Missing fields are displayed explicitly with guided completion.
- Provisional analysis is labeled and tied to data completeness.
- Optional dependency startup warnings are concise, intentional, and documented.
- sklearn bundle compatibility is resolved by policy, not ignored.
- `extra_data` serialization warnings are eliminated.
- Browser smoke coverage exists for the remaining major screens.
- Full regression, build, Playwright, and real local verification all pass.

## Recommended Implementation Order

1. Architect contract update for OCR degraded states.
2. Backend OCR soft-failure implementation.
3. Frontend guided completion and status badges.
4. Runtime warning cleanup and environment policy.
5. Browser smoke coverage expansion.
6. Full regression and release decision.
