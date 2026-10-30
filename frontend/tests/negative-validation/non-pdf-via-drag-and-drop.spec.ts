// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { dropFile, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Non-PDF via drag and drop', async ({ page }) => {
    const app = ui(page)
    await page.goto('/')

    // 1. Drop a `.png` file on the drop zone.
    await dropFile(page, {
      name: 'image.png',
      mimeType: 'image/png',
      buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    })

    await expect(app.errorAlert).toContainText('Only PDF files are supported.')
    await expect(app.removeButton).toHaveCount(0)
    await expect(app.analyseButton).toBeDisabled()
  })
})
