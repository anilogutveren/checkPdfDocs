// spec: specs/upload-and-analyse.plan.md
// seed: tests/seed.spec.ts
import { expect, test } from '@playwright/test'

import { mockAnalyze, samplePdfPath, ui } from '../support/app'

test.describe('Happy Path', () => {
  test('Keyboard access to the drop zone', async ({ page }) => {
    const app = ui(page)
    await mockAnalyze(page)
    await page.goto('/')

    // 1. Focus the drop zone with Tab.
    await page.keyboard.press('Tab')
    await expect(app.dropZone).toBeFocused()

    // 2. Press Enter (repeat with Space) while awaiting `page.waitForEvent('filechooser')`.
    const [enterChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.keyboard.press('Enter'),
    ])
    expect(enterChooser).toBeTruthy()

    await app.dropZone.focus()
    const [spaceChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.keyboard.press(' '),
    ])

    // 3. Set `sample_order_transporter.pdf` on the chooser and analyse.
    await spaceChooser.setFiles(samplePdfPath('sample_order_transporter.pdf'))
    await expect(page.getByText('sample_order_transporter.pdf')).toBeVisible()
    await app.analyseButton.click()

    await expect(app.resultRows).toHaveCount(4)
  })
})
