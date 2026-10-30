// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { expectedChecksFor, SAMPLE_PDFS, samplePdfPath, skipUnlessBackendUp, ui } from '../support/app'

test.describe('Happy Path', () => {
  for (const sample of SAMPLE_PDFS) {
    test(`Analyse each sample PDF (data-driven) - ${sample}`, async ({ page, request }) => {
      await skipUnlessBackendUp(request)
      const app = ui(page)
      await page.goto('/')

      // 1. For each sample PDF: upload, analyse.
      await app.fileInput.setInputFiles(samplePdfPath(sample))
      const responsePromise = page.waitForResponse((response) => response.url().endsWith('/analyze'))
      await app.analyseButton.click()
      const body = (await (await responsePromise).json()) as {
        word_count: number
        results: { passed: boolean }[]
      }

      expect(body.results).toHaveLength(4)
      expect(body.word_count).toBeGreaterThan(0)
      const expectedChecks = expectedChecksFor(sample)
      if (expectedChecks) {
        expect(body.results.map((result) => result.passed)).toEqual(expectedChecks)
      }
      await expect(app.resultRows).toHaveCount(4)
    })
  }
})
