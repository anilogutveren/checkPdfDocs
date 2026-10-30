// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { mockAnalyze, samplePdfPath, ui } from '../support/app'

test.describe('State Transitions', () => {
  test('Re-analyse the same file', async ({ page }) => {
    const app = ui(page)
    await mockAnalyze(page, undefined, 500)
    await page.goto('/')

    // 1. Upload a PDF and analyse.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await app.analyseButton.click()
    await expect(app.resultRows).toHaveCount(4)

    // 2. Click "Scan & Analyse" again.
    await app.analyseButton.click()

    await expect(app.analysingButton).toBeVisible()
    await expect(app.resultRows).toHaveCount(0)
    await expect(app.resultRows).toHaveCount(4)
    await expect(app.analyseButton).toBeEnabled()
  })
})
