// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { MOCK_BASE_RESULTS, mockAnalyze, rowParts, samplePdfPath, ui } from '../support/app'

test.describe('Happy Path', () => {
  test('Analyse with LLM enabled (mocked)', async ({ page }) => {
    const app = ui(page)

    // 1. Mock `**/analyze` to return 5 results, last being the `llm` check.
    await mockAnalyze(page, [
      ...MOCK_BASE_RESULTS,
      { name: 'llm', passed: true, message: 'Nimble contract-plausibility score 0.90 (threshold 0.50).' },
    ])
    await page.goto('/')

    // 2. Tick "Use LLM (requires local Ollama)".
    await app.llmCheckbox.check()
    await expect(app.llmCheckbox).toBeChecked()

    // 3. Upload a PDF and click "Scan & Analyse".
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
    const requestPromise = page.waitForRequest((req) => req.url().endsWith('/analyze'))
    await app.analyseButton.click()

    const analyzeRequest = await requestPromise
    expect(analyzeRequest.postDataBuffer()?.toString('latin1')).toMatch(/name="use_llm"\r\n\r\ntrue/)

    await expect(app.resultRows).toHaveCount(5)
    const llmRow = rowParts(app.resultRows.nth(4))
    await expect(llmRow.name).toHaveText('llm')
    await expect(llmRow.badge).toHaveText('PASS')
  })
})
