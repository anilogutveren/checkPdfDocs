// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { skipUnlessBackendUp, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('Fake PDF (PDF MIME, invalid content)', async ({ page, request }) => {
    await skipUnlessBackendUp(request)
    const app = ui(page)
    await page.goto('/')

    // 1. Upload buffer `fake.pdf`, `mimeType: 'application/pdf'`, content `hello`.
    await app.fileInput.setInputFiles({
      name: 'fake.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('hello'),
    })

    // 2. Analyse.
    const responsePromise = page.waitForResponse((response) => response.url().endsWith('/analyze'))
    await app.analyseButton.click()

    expect((await responsePromise).status()).toBe(422)
    await expect(app.errorAlert).toContainText('The uploaded file is not a valid PDF.')
  })
})
