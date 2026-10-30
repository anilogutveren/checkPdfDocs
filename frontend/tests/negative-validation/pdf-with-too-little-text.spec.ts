// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { buildTinyPdf, rowParts, skipUnlessBackendUp, ui } from '../support/app'

test.describe('Negative / Validation', () => {
  test('PDF with too little text', async ({ page, request }) => {
    await skipUnlessBackendUp(request)
    const app = ui(page)
    await page.goto('/')

    // 1. Upload a valid PDF with fewer than 50 words.
    await app.fileInput.setInputFiles({
      name: 'short.pdf',
      mimeType: 'application/pdf',
      buffer: buildTinyPdf('Short memo about lunch plans'),
    })

    // 2. Analyse.
    await app.analyseButton.click()

    await expect(app.resultRows).toHaveCount(4)
    const lengthRow = rowParts(app.resultRows.nth(3))
    await expect(lengthRow.name).toHaveText('length')
    await expect(lengthRow.badge).toHaveText('FAIL')
    for (const index of [0, 1, 2]) {
      const sectionRow = rowParts(app.resultRows.nth(index))
      await expect(sectionRow.badge).toHaveText('FAIL')
      await expect(sectionRow.message).toHaveText(/^Missing expected section\(s\): /)
    }
  })
})
