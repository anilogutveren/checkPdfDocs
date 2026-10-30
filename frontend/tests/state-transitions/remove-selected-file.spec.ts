// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { samplePdfPath, ui } from '../support/app'

test.describe('State Transitions', () => {
  test('Remove selected file', async ({ page }) => {
    const app = ui(page)
    await page.goto('/')

    // 1. Upload a PDF.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await expect(page.getByText('sample_order_pickup.pdf')).toBeVisible()

    // 2. Click "Remove".
    await app.removeButton.click()

    await expect(page.getByText('sample_order_pickup.pdf')).toHaveCount(0)
    await expect(app.removeButton).toHaveCount(0)
    await expect(app.analyseButton).toBeDisabled()
  })
})
