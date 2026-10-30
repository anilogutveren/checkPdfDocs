// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { mockAnalyze, samplePdfPath, ui } from '../support/app'

test.describe('Loading / UX', () => {
  test('No double submit while loading', async ({ page }) => {
    const app = ui(page)
    let analyzeRequests = 0
    page.on('request', (req) => {
      if (req.url().endsWith('/analyze') && req.method() === 'POST') analyzeRequests += 1
    })

    // 1. Mock `**/analyze` with a 2 s delay.
    await mockAnalyze(page, undefined, 2_000)
    await page.goto('/')

    // 2. Upload a PDF and click "Scan & Analyse".
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await app.analyseButton.click()

    // 3. Click the button again.
    await expect(app.analysingButton).toBeDisabled()
    await app.analysingButton.click({ force: true })

    await expect(app.resultRows).toHaveCount(4)
    expect(analyzeRequests).toBe(1)
  })
})
