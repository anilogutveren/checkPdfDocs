// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { dropFile, mockAnalyze, pdfFile, ui } from '../support/app'

test.describe('Happy Path', () => {
  test('Upload via drag and drop', async ({ page }) => {
    const app = ui(page)
    await mockAnalyze(page)

    // 1. Navigate to `/`.
    await page.goto('/')

    // 2. Create a `DataTransfer` containing `sample_order_minibus.pdf`; dispatch `dragover` then `drop` on the drop zone.
    await dropFile(page, pdfFile('sample_order_minibus.pdf'))
    await expect(page.getByText('sample_order_minibus.pdf')).toBeVisible()

    // 3. Click "Scan & Analyse".
    await app.analyseButton.click()

    await expect(app.resultRows).toHaveCount(4)
  })
})
