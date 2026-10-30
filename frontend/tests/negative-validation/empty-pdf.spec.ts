// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { skipUnlessBackendUp, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Empty PDF', async ({ page, request }) => {
    await skipUnlessBackendUp(request)
    const app = ui(page)
    await page.goto('/')

    // 1. Upload 0-byte `empty.pdf` with `application/pdf`.
    await app.fileInput.setInputFiles({
      name: 'empty.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.alloc(0),
    })

    // 2. Analyse.
    const responsePromise = page.waitForResponse((response) => response.url().endsWith('/analyze'))
    await app.analyseButton.click()

    expect((await responsePromise).status()).toBe(400)
    await expect(app.errorAlert).toContainText('Uploaded file is empty.')
  })
})
