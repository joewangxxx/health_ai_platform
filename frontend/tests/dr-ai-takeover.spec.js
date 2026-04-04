import { expect, test } from '@playwright/test'

const authToken = 'playwright-takeover-token'

const mockAuthenticatedShell = async (page) => {
  await page.addInitScript((token) => {
    localStorage.setItem('auth_token', token)
  }, authToken)

  await page.route('**/user/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 42,
        username: 'takeover-user',
        email: 'takeover@example.com',
      }),
    })
  })

  await page.route('**/chat/conversations**', async (route) => {
    const url = new URL(route.request().url())

    if (url.pathname !== '/chat/conversations') {
      await route.fallback()
      return
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          conversation_id: 101,
          title: 'Takeover regression case',
          archived: false,
        },
      ]),
    })
  })
}

const openTakeoverConversation = async (page, takeover) => {
  await page.route('**/chat/conversations/101/messages', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 101,
        messages: [
          {
            role: 'assistant',
            content: 'Takeover regression fixture response.',
            sequence: 2,
            created_at: '2026-04-02T08:00:00Z',
            takeover,
          },
        ],
      }),
    })
  })

  await page.goto('/chat')
  await expect(page.getByTestId('conversation-card-101')).toBeVisible()
  await page.getByTestId('conversation-card-101').getByText('Takeover regression case').click()
}

test.describe('Dr. AI takeover regression', () => {
  test('shows takeover card when required', async ({ page }) => {
    await mockAuthenticatedShell(page)
    await openTakeoverConversation(page, {
      schema_version: 'takeover.v1',
      status: 'required',
      trigger_reason: 'high_risk',
      summary: 'Stop AI advice and hand off to a clinician.',
    })

    await expect(page.getByTestId('takeover-card')).toBeVisible()
    await expect(page.getByTestId('takeover-status')).toBeVisible()
    await expect(page.getByTestId('takeover-trigger-reason')).toBeVisible()
    await expect(page.getByTestId('takeover-status-tag')).toBeVisible()
    await expect(page.getByTestId('takeover-summary')).toContainText('Stop AI advice')
    await expect(page.getByTestId('takeover-next-step')).toBeVisible()
    await expect(page.getByTestId('takeover-suppressed-note')).toHaveCount(0)
  })

  test('shows suppression note when takeover is suppressed', async ({ page }) => {
    await mockAuthenticatedShell(page)
    await openTakeoverConversation(page, {
      schema_version: 'takeover.v1',
      status: 'suppressed',
      trigger_reason: 'boundary_false_positive',
      summary: 'Assessment completed, no human handoff required.',
    })

    await expect(page.getByTestId('takeover-card')).toBeVisible()
    await expect(page.getByTestId('takeover-status')).toBeVisible()
    await expect(page.getByTestId('takeover-trigger-reason')).toBeVisible()
    await expect(page.getByTestId('takeover-status-tag')).toBeVisible()
    await expect(page.getByTestId('takeover-summary')).toContainText('Assessment completed')
    await expect(page.getByTestId('takeover-suppressed-note')).toBeVisible()
    await expect(page.getByTestId('takeover-next-step')).toHaveCount(0)
  })

  test('does not render a takeover card when takeover is absent', async ({ page }) => {
    await mockAuthenticatedShell(page)
    await openTakeoverConversation(page, null)

    await expect(page.getByTestId('takeover-card')).toHaveCount(0)
  })
})
