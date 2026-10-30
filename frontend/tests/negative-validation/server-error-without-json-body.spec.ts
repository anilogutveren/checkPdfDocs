// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { mockAnalyzePlainTextError, samplePdfPath, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Server error without JSON body', async ({ page }) => {
    const app = ui(page)

    // 1. Mock `**/analyze` → status 500, plain-text body.
    await mockAnalyzePlainTextError(page, 500)
    await page.goto('/')

    // 2. Upload a PDF and analyse.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await app.analyseButton.click()

    await expect(app.errorAlert).toContainText('Unknown error')
  })
})
