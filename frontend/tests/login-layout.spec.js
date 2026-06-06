import { expect, test } from '@playwright/test'

test('login panel is visually centered in the first viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.goto('/login')
  await page.waitForLoadState('networkidle')

  const heading = page.getByRole('heading', { name: 'HealthAI Platform' })
  const panel = heading.locator('xpath=ancestor::div[contains(@class, "group")][1]')
  const box = await panel.boundingBox()

  expect(box).not.toBeNull()

  const panelCenter = box.y + box.height / 2
  const viewportCenter = 720 / 2

  expect(Math.abs(panelCenter - viewportCenter)).toBeLessThanOrEqual(45)
})

test('register panel keeps comfortable top breathing room in the first viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.goto('/register')
  await page.waitForLoadState('networkidle')

  const heading = page.getByRole('heading', { name: 'HealthAI Platform' })
  const panel = heading.locator('xpath=ancestor::div[contains(@class, "group")][1]')
  const box = await panel.boundingBox()

  expect(box).not.toBeNull()

  expect(box.y).toBeGreaterThanOrEqual(48)
})
