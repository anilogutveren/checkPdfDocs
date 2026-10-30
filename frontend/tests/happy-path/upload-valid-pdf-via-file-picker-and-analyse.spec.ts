// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { rowParts, samplePdfPath, skipUnlessBackendUp, ui } from '../support/app'

test.describe('Happy Path', () => {
  test('Upload a valid PDF via file picker and analyse', async ({ page, request }) => {
    await skipUnlessBackendUp(request)
    const app = ui(page)
    // Delay the real request slightly so the loading state is observable.
    await page.route('**/analyze', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500))
      await route.continue()
    })

    // 1. Navigate to `/`.
    await page.goto('/')
    await expect(app.heading).toBeVisible()

    // 2. Verify "Scan & Analyse" is disabled and the results placeholder is shown.
    await expect(app.analyseButton).toBeDisabled()
    await expect(app.placeholder).toBeVisible()

    // 3. Set `sample_order_pickup.pdf` on `input[type=file]`.
    await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))

    // 4. Verify the file chip shows `sample_order_pickup.pdf` and a non-zero size.
    await expect(page.getByText('sample_order_pickup.pdf')).toBeVisible()
    await expect(page.getByText(/^(?!0 B)[\d.]+ (B|KB|MB|GB)$/)).toBeVisible()

    // 5. Verify "Scan & Analyse" is enabled.
    await expect(app.analyseButton).toBeEnabled()

    // 6. Click "Scan & Analyse".
    const responsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/analyze') && response.request().method() === 'POST',
    )
    await app.analyseButton.click()

    // 7. Verify the button shows "Analysing…" and is disabled.
    await expect(app.analysingButton).toBeDisabled()

    // 8. Wait for the `POST /analyze` response (200).
    const response = await responsePromise
    expect(response.status()).toBe(200)

    await expect(app.wordsAnalysed).toBeVisible()
    const wordCount = Number((await app.wordsAnalysed.innerText()).replace(/\D/g, ''))
    expect(wordCount).toBeGreaterThan(0)

    await expect(app.resultRows).toHaveCount(4)
    const expectedNames = ['section', 'section', 'section', 'length']
    for (const [index, name] of expectedNames.entries()) {
      const row = rowParts(app.resultRows.nth(index))
      await expect(row.name).toHaveText(name)
      await expect(row.badge).toHaveText(/^(PASS|FAIL)$/)
      await expect(row.message).not.toBeEmpty()
    }
    await expect(rowParts(app.resultRows.nth(3)).message).toHaveText(
      /Contract length: \d+ words \(minimum 50\)\./,
    )

    await expect(app.analyseButton).toBeEnabled()
    await expect(app.errorAlert).toHaveCount(0)
  })
})
