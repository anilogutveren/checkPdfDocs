// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { samplePdfPath, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Backend unreachable', async ({ page }) => {
    const app = ui(page)

    // 1. `page.route('**/analyze', route => route.abort())`.
    await page.route('**/analyze', (route) => route.abort())
    await page.goto('/')

    // 2. Upload a PDF and analyse.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await app.analyseButton.click()

    await expect(app.errorAlert).toContainText(/Failed to fetch|NetworkError|Load failed/)
    await expect(app.analyseButton).toBeEnabled()
  })
})
