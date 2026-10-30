// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { MOCK_BASE_RESULTS, mockAnalyze, rowParts, samplePdfPath, ui } from '../support/app'

test.describe('Happy Path', () => {
  test('LLM enabled but model unavailable', async ({ page }) => {
    const app = ui(page)
    // Mirrors the fallback result `llm_contract_check` returns when the model cannot be reached.
    await mockAnalyze(page, [
      ...MOCK_BASE_RESULTS,
      { name: 'llm', passed: false, message: 'LLM check unavailable (ConnectError: [Errno 61] Connection refused)' },
    ])
    await page.goto('/')

    // 1. Tick the LLM checkbox, upload a PDF, analyse.
    await app.llmCheckbox.check()
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    await app.analyseButton.click()

    await expect(app.resultRows).toHaveCount(5)
    const llmRow = rowParts(app.resultRows.nth(4))
    await expect(llmRow.name).toHaveText('llm')
    await expect(llmRow.badge).toHaveText('FAIL')
    await expect(llmRow.message).toHaveText(/^LLM check unavailable \(/)
    for (const index of [0, 1, 2, 3]) {
      await expect(rowParts(app.resultRows.nth(index)).badge).toHaveText(/^(PASS|FAIL)$/)
    }
  })
})
