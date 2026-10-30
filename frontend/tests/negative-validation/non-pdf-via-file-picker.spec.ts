// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Non-PDF via file picker', async ({ page }) => {
    const app = ui(page)
    await page.goto('/')

    // 1. Set a `.txt` buffer (`mimeType: 'text/plain'`) on the file input.
    await app.fileInput.setInputFiles({
      name: 'notes.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('not a pdf'),
    })

    await expect(app.errorAlert).toContainText('Error')
    await expect(app.errorAlert).toContainText('Only PDF files are supported.')
    await expect(app.removeButton).toHaveCount(0)
    await expect(app.analyseButton).toBeDisabled()
  })
})
