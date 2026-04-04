import { expect, test } from '@playwright/test'

const authToken = 'playwright-guided-completion-token'

const mockAuthenticatedBootstrap = async (page, { user, profile, documents, ocrUploadResponse, drugs, analysisResponse } = {}) => {
  await page.addInitScript((token) => {
    localStorage.setItem('auth_token', token)
  }, authToken)

  await page.route('**/user/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(user || {
        id: 7,
        username: 'guided-user',
        email: 'guided@example.com',
        is_superuser: false,
      }),
    })
  })

  await page.route('**/user/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'success',
        profile: profile || {
          Age: 52,
          Gender: 1,
          Height: 172,
          Weight: 75,
          BMI: 25.4,
          Creatinine: 83,
          eGFR: 92,
        },
      }),
    })
  })

  await page.route('**/api/v1/user/documents', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'success',
        documents: documents || [],
      }),
    })
  })

  await page.route('**/analyze/comprehensive', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(analysisResponse || {
        status: 'success',
        risk_report: {
          Diabetes: {
            final_risk: 0.42,
            level: 'Medium',
            breakdown: {
              base_clinical: '42.0%',
              gene_modifier: 'x1.0',
              lifestyle_modifier: 'x1.0',
            },
          },
        },
        analysis_context: {
          schema_version: 'analysis_context.v1',
          analysis_mode: 'final',
          provisional_reasons: [],
          blocking_fields: [],
          field_state_summary: {
            recognized: ['Age'],
            derived: ['BMI'],
            missing: [],
            user_confirmed: [],
            user_entered: [],
          },
        },
      }),
    })
  })

  await page.route('**/drugs/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'success',
        drugs: drugs || ['Metoprolol', 'Warfarin', 'Aspirin'],
      }),
    })
  })

  await page.route('**/api/v1/ocr/upload', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ocrUploadResponse || {
        status: 'partial_success',
        message: 'stored but partial',
        ocr_processing_status: {
          schema_version: 'ocr_processing_status.v1',
          status: 'partial_success',
          reason: 'structured_data_incomplete',
          structured_data_present: true,
          raw_text_present: true,
          saved_at: '2026-04-03T08:00:00Z',
          processed_at: '2026-04-03T08:01:00Z',
        },
        ocr_summary: {
          schema_version: 'ocr_summary.v1',
          metrics: {
            Age: { value: 52 },
            Gender: { value: 1 },
            Height: { value: 172 },
            Weight: { value: 75 },
            Creatinine: { value: 83 },
          },
          patient_context: {
            Age: 52,
            Gender: 1,
            Height: 172,
            Weight: 75,
            Creatinine: 83,
          },
          extra_findings: {
            Note: 'Needs follow-up',
          },
        },
        analysis_context: {
          schema_version: 'analysis_context.v1',
          analysis_mode: 'provisional',
          provisional_reasons: [
            { code: 'missing_labs', fields: ['Creatinine'] },
          ],
          blocking_fields: ['Creatinine'],
          field_state_summary: {
            recognized: ['Age', 'Gender'],
            derived: ['BMI'],
            missing: ['Creatinine'],
            user_confirmed: [],
            user_entered: ['Weight'],
          },
        },
      }),
    })
  })
}

test.describe('OCR and guided completion', () => {
  test('profile documents surface frozen OCR states instead of a binary has_data view', async ({ page }) => {
    await mockAuthenticatedBootstrap(page, {
      documents: [
        {
          id: 1,
          file_name: 'structured.pdf',
          file_url: '/static/medical_reports/structured.pdf',
          upload_date: '2026-04-03T08:00:00Z',
          ocr_summary: {
            schema_version: 'ocr_summary.v1',
            metrics: {
              Glucose_Fasting: { value: 6.8, unit: 'mmol/L' },
            },
          },
          ocr_processing_status: {
            schema_version: 'ocr_processing_status.v1',
            status: 'partial_success',
            reason: 'structured_data_incomplete',
            structured_data_present: true,
            raw_text_present: true,
            saved_at: '2026-04-03T08:00:00Z',
            processed_at: '2026-04-03T08:01:00Z',
          },
        },
        {
          id: 2,
          file_name: 'pending.pdf',
          file_url: '/static/medical_reports/pending.pdf',
          upload_date: '2026-04-03T08:30:00Z',
          ocr_summary: null,
          ocr_processing_status: {
            schema_version: 'ocr_processing_status.v1',
            status: 'stored_unprocessed',
            reason: 'ocr_service_unavailable',
            structured_data_present: false,
            raw_text_present: false,
            saved_at: '2026-04-03T08:30:00Z',
            processed_at: null,
          },
        },
      ],
    })

    await page.goto('/profile')

    await expect(page.getByTestId('document-ocr-status-1')).toContainText('部分识别')
    await expect(page.getByTestId('document-ocr-status-2')).toContainText('已保存待识别')
    await expect(page.getByTestId('document-import-action-1')).toContainText('导入到分析')
    await expect(page.getByTestId('document-import-action-2')).toContainText('查看待识别状态')
  })

  test('clinical upload shows explicit OCR state and guided completion semantics', async ({ page }) => {
    await mockAuthenticatedBootstrap(page)

    await page.goto('/clinical')
    await expect(page.getByTestId('ocr-upload')).toBeVisible()
    await expect(page.getByTestId('ocr-document-status-banner')).toHaveCount(0)

    await page.locator('[data-testid="ocr-upload"] input[type="file"]').setInputFiles({
      name: '体检表.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4\n%test\n'),
    })

    await expect(page.getByTestId('ocr-document-status-banner')).toBeVisible()
    await expect(page.getByTestId('analysis-context-banner')).toBeVisible()
    await expect(page.getByTestId('analysis-context-mode')).toBeVisible()
    await expect(page.getByText('待补充')).toBeVisible()
    await expect(page.getByText('大概值')).toHaveCount(0)
    await expect(page.getByText('估算')).toHaveCount(0)
  })

  test('major pages remain smoke-loadable and admin stays permission-bound', async ({ page }) => {
    await mockAuthenticatedBootstrap(page)

    const pages = [
      { path: '/', locator: page.getByRole('heading', { name: /HealthAI Platform|欢迎来到 HealthAI Platform/ }).first() },
      { path: '/clinical', locator: page.getByTestId('ocr-upload') },
      { path: '/profile', locator: page.getByRole('heading', { name: /个人档案/ }).first() },
      { path: '/genomics', locator: page.getByRole('heading', { name: /基因组学/ }).first() },
      { path: '/lifestyle', locator: page.getByRole('heading', { name: /行为监测/ }).first() },
      { path: '/pharmacy', locator: page.getByRole('heading', { name: /智能药房/ }).first() },
      { path: '/nutrition', locator: page.getByRole('heading', { name: /AI 智能食谱生成/ }).first() },
    ]

    for (const entry of pages) {
      await page.goto(entry.path)
      await expect(entry.locator).toBeVisible()
    }

    await page.goto('/admin/dashboard')
    await expect(page).not.toHaveURL(/\/admin\/dashboard/)
  })
})
