// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { mockAnalyze, samplePdfPath, ui } from '../support/app'

test.describe('State Transitions', () => {
  test('Replacing the file clears previous results', async ({ page }) => {
    test.info().annotations.push({
      type: 'issue',
      description: 'Known gap: "N words analysed" persists after replacing the file (wordCount state is not reset).',
    })
    const app = ui(page)
    await mockAnalyze(page)
    await page.goto('/')

    // 1. Upload PDF A and analyse; verify results render.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await app.analyseButton.click()
    await expect(app.resultRows).toHaveCount(4)

    // 2. Upload PDF B.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_minibus.pdf'))

    await expect(app.placeholder).toBeVisible()
    await expect(app.resultRows).toHaveCount(0)
    await expect(page.getByText('sample_order_minibus.pdf')).toBeVisible()
    await expect(page.getByText('sample_order_pickup.pdf')).toHaveCount(0)
  })
})
