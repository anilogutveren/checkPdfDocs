// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { samplePdfPath, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Error clears after a valid upload', async ({ page }) => {
    const app = ui(page)
    await page.goto('/')

    // 1. Trigger 3.1.
    await app.fileInput.setInputFiles({
      name: 'notes.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('not a pdf'),
    })
    await expect(app.errorAlert).toContainText('Only PDF files are supported.')

    // 2. Upload a valid PDF.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))

    await expect(app.errorAlert).toHaveCount(0)
    await expect(page.getByText('sample_order_pickup.pdf')).toBeVisible()
  })
})
