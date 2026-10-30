# Frontend end-to-end tests (Playwright)

These tests open the Smart PDF Analyser in a real browser (Chromium) and check the upload-and-analyse flow.
They follow the test plan in [specs/upload-and-analyse.plan.md](../specs/upload-and-analyse.plan.md).

## Quick start

All commands run from the `frontend/` folder.

```sh
cd frontend
npm install                      # first time only
npx playwright install chromium  # first time only: downloads the test browser
npm run test:e2e
```

Playwright starts the Vite dev server (`npm run dev`, port 5173) for you.
If the dev server is already running, it is reused.

> Do **not** run `npx playwright test` from the repository root.
> It loads a second copy of Playwright and fails with
> `Playwright Test did not expect test.describe() to be called here`.

## Two kinds of tests

| Kind | Needs the Python backend? | What it does |
|---|---|---|
| **Mocked** | No | Replaces `POST /analyze` with a fake response (`page.route`). Fast and always repeatable. |
| **Real backend** | Yes, on `http://localhost:8000` | Sends the PDF to the real FastAPI backend. |

Real-backend tests call `GET /health` first. If the backend does not answer, the test is **skipped**, not failed.

To run the real-backend tests, start the backend in a second terminal from the repository root:

```sh
source .venv/bin/activate
uvicorn contract_checker.api:app --port 8000
```

Use another backend address with the `BACKEND_URL` environment variable:

```sh
BACKEND_URL=http://localhost:9000 npm run test:e2e
```

## Useful commands

Add Playwright options after `--`.

| Goal | Command |
|---|---|
| Run everything | `npm run test:e2e` |
| One file | `npm run test:e2e -- tests/happy-path/upload-via-drag-and-drop.spec.ts` |
| One folder | `npm run test:e2e -- tests/negative-validation` |
| Filter by test name | `npm run test:e2e -- -g "drag and drop"` |
| Watch the browser | `npm run test:e2e -- --headed` |
| Interactive UI mode | `npm run test:e2e -- --ui` |
| Debug step by step | `npm run test:e2e -- --debug` |
| Check for flaky tests | `npm run test:e2e -- --repeat-each=3` |
| Open the last HTML report | `npx playwright show-report` |

See [Debugging tests](#debugging-tests) for step-by-step debugging.

## Debugging tests

All commands run from `frontend/`. Debug **one test at a time**; it is much easier to follow.

### 1. Playwright Inspector (step through a test)

```sh
npm run test:e2e -- tests/happy-path/upload-via-drag-and-drop.spec.ts --debug
```

What happens:

- A real Chromium window opens, plus the **Playwright Inspector** window.
- The test stops before the first action. Click **Step over** to run one action at a time, or **Resume** to run until the end or the next pause.
- The Inspector highlights the element each locator matches, so you can see what the test is clicking.
- `--debug` turns off the test timeout and runs with one worker, so you can take your time.

To start at a specific test, add its line number (the line with `test(`):

```sh
npm run test:e2e -- tests/happy-path/upload-via-drag-and-drop.spec.ts:8 --debug
```

### 2. Pause at a specific line

Add `await page.pause()` where you want to stop, then run the test with `--headed`:

```ts
await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
await page.pause() // the Inspector opens here
await app.analyseButton.click()
```

```sh
npm run test:e2e -- tests/happy-path/upload-via-drag-and-drop.spec.ts --headed
```

Remove `page.pause()` before you commit.

### 3. UI mode (watch, re-run, time travel)

```sh
npm run test:e2e -- --ui
```

- Pick a test in the left panel and press the play button.
- After a run, click any step to see a snapshot of the page at that moment ("time travel").
- The **Network** and **Console** tabs show the `/analyze` request and browser errors.
- Turn on **watch mode** (eye icon) to re-run a test each time you save the file.

### 4. Trace of a failed run

Use this when a test fails but you did not watch it run, for example a flaky test:

```sh
npm run test:e2e -- tests/happy-path/upload-valid-pdf-via-file-picker-and-analyse.spec.ts --trace on
npx playwright show-report
```

Open the failed test in the report and click the trace. It shows every action, a page snapshot per step, network calls and console output.

### 5. VS Code breakpoints

1. Install the **Playwright Test for VSCode** extension (`ms-playwright.playwright`).
2. Open the **Testing** view (beaker icon). The tests from `frontend/playwright.config.ts` appear there.
3. Set a breakpoint in a `.spec.ts` file or in `tests/support/app.ts`.
4. Right-click the test and choose **Debug Test**.

The test stops at your breakpoint and you can inspect variables in the VS Code debugger. Tick **Show browser** in the Testing view to see the browser while debugging.

If the extension does not find the tests, open the `frontend` folder as the workspace, or select `frontend/playwright.config.ts` in the extension's settings panel.

### 6. Extra log output

Print every Playwright action to the terminal:

```sh
DEBUG=pw:api npm run test:e2e -- tests/happy-path/upload-via-drag-and-drop.spec.ts
```

### Debugging tips for this project

- **Real-backend tests are skipped** when the backend is not running. Start it first (see [Two kinds of tests](#two-kinds-of-tests)), otherwise there is nothing to debug.
- **Mocked tests never reach the backend.** If the UI shows unexpected data, check the `mockAnalyze(...)` call in the test, not the Python code.
- **Locator problems:** in the Inspector or UI mode, use **Pick locator** and hover over the page. It shows the locator Playwright would use. Compare it with `ui(page)` in `tests/support/app.ts`.
- The dev server log (`[WebServer] …` lines) shows browser console errors from the app.

## Folder layout

```
frontend/
├── playwright.config.ts        # test dir, base URL, browser, dev server
├── specs/
│   └── upload-and-analyse.plan.md   # the test plan
└── tests/
    ├── seed.spec.ts            # opens the app; used by the Playwright agents as a starting point
    ├── support/app.ts          # shared helpers (locators, mocks, file helpers)
    ├── happy-path/             # plan section 1
    ├── state-transitions/      # plan section 2
    ├── negative-validation/    # plan section 3
    └── loading-ux/             # plan section 4
```

Each `.spec.ts` file holds **one** plan scenario. The `test.describe` name matches the plan section and the test name matches the scenario title.

## Test list

| Plan | File | Kind |
|---|---|---|
| 1.1 | `happy-path/upload-valid-pdf-via-file-picker-and-analyse.spec.ts` | Real backend |
| 1.2 | `happy-path/upload-via-drag-and-drop.spec.ts` | Mocked |
| 1.3 | `happy-path/keyboard-access-to-the-drop-zone.spec.ts` | Mocked |
| 1.4 | `happy-path/analyse-each-sample-pdf-data-driven.spec.ts` (3 tests, one per sample PDF) | Real backend |
| 1.5 | `happy-path/analyse-with-llm-enabled-mocked.spec.ts` | Mocked |
| 1.6 | `happy-path/llm-enabled-but-model-unavailable.spec.ts` | Mocked (see note below) |
| 2.1 | `state-transitions/remove-selected-file.spec.ts` | Mocked |
| 2.2 | `state-transitions/replacing-the-file-clears-previous-results.spec.ts` | Mocked |
| 2.3 | `state-transitions/re-analyse-the-same-file.spec.ts` | Mocked |
| 3.1 | `negative-validation/non-pdf-via-file-picker.spec.ts` | Mocked |
| 3.2 | `negative-validation/non-pdf-via-drag-and-drop.spec.ts` | Mocked |
| 3.3 | `negative-validation/error-clears-after-a-valid-upload.spec.ts` | Mocked |
| 3.4 | `negative-validation/fake-pdf-pdf-mime-invalid-content.spec.ts` | Real backend |
| 3.5 | `negative-validation/empty-pdf.spec.ts` | Real backend |
| 3.6 | `negative-validation/pdf-with-too-little-text.spec.ts` | Real backend |
| 3.7 | `negative-validation/backend-unreachable.spec.ts` | Mocked (request aborted) |
| 3.8 | `negative-validation/server-error-without-json-body.spec.ts` | Mocked |
| 4.1 | `loading-ux/no-double-submit-while-loading.spec.ts` | Mocked |

**Note on 1.6:** the plan asks for a real backend without an LLM model. A machine with the model installed cannot produce that state, so the test mocks the exact fallback message that `llm_contract_check` returns (`LLM check unavailable (…)`). It checks how the UI shows that result.

## Test data

- Sample PDFs: `documents/samples/sample_order_*.pdf` (repository root).
- Expected check results: `tests/fixtures/sample_orders_ground_truth.json` (field `expected_checks`). Test 1.4 compares the backend answer with it.
- Small files are built in memory inside the tests: a `.txt` and `.png` for wrong file types, an empty `empty.pdf`, a `fake.pdf` with the text `hello`, and a tiny valid PDF with fewer than 50 words (`buildTinyPdf`).

## Shared helpers (`support/app.ts`)

| Helper | Purpose |
|---|---|
| `ui(page)` | All page locators: drop zone, file input, LLM checkbox, analyse button, result rows, error alert, … |
| `rowParts(row)` | Name, PASS/FAIL badge and message inside one result row |
| `mockAnalyze(page, results?, delayMs?)` | Fake a successful `/analyze` response, with an optional delay |
| `mockAnalyzePlainTextError(page, status)` | Fake an error response with a plain-text body |
| `skipUnlessBackendUp(request)` | Skip the test when the backend `/health` does not answer |
| `samplePdfPath(name)` / `pdfFile(name)` | Path to, or contents of, a sample PDF |
| `dropFile(page, file)` | Simulate drag and drop of a file on the drop zone |
| `expectedChecksFor(name)` | Expected PASS/FAIL list from the ground-truth fixture |
| `buildTinyPdf(text)` | Build a minimal one-page PDF in memory |

Mocked responses include the header `access-control-allow-origin: *`. Without it the browser blocks the cross-origin response and the app only sees "Failed to fetch".

## Adding a new test

1. Add the scenario to [specs/upload-and-analyse.plan.md](../specs/upload-and-analyse.plan.md).
2. Create one file in the matching folder, named after the scenario (kebab-case).
3. Start from this template:

   ```ts
   // spec: specs/upload-and-analyse.plan.md
   // seed: tests/seed.spec.ts
   import { expect, test } from '@playwright/test'

   import { mockAnalyze, samplePdfPath, ui } from '../support/app'

   test.describe('Happy Path', () => {
     test('My new scenario', async ({ page }) => {
       const app = ui(page)
       await mockAnalyze(page)
       await page.goto('/')

       // 1. Upload a PDF and analyse.
       await app.fileInput.setInputFiles(samplePdfPath('sample_order_pickup.pdf'))
       await app.analyseButton.click()

       await expect(app.resultRows).toHaveCount(4)
     })
   })
   ```

4. For a real-backend test, add the `request` fixture and call `await skipUnlessBackendUp(request)` first.
5. Run it a few times: `npm run test:e2e -- <file> --repeat-each=3`.

## Known issues

- **Result rows have no test id.** Tests find them with the CSS selector `.space-y-3 > div`. If the layout classes in `src/App.tsx` change, update `resultRows` in `support/app.ts`. Adding a `data-testid` to each row would make this more robust.
- **Word count is not reset (plan 2.2).** After you pick a new file, "N words analysed" from the previous run stays visible. The test records this as an annotation and does not fail on it.
- **React duplicate-key warning.** The dev server log shows `Encountered two children with the same key`. Result rows in `src/App.tsx` use `name + message` as the key, and two `section` rows can be identical. It does not affect the tests.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Playwright Test did not expect test.describe() to be called here` | You ran from the repository root. Run from `frontend/`. |
| `Executable doesn't exist … chromium` | Browser not installed. Run `npx playwright install chromium`. |
| Real-backend tests show as **skipped** | Backend not running on port 8000. Start `uvicorn` (see above). |
| Port 5173 already in use by another app | Stop that app, or start this project's dev server yourself with `npm run dev`; Playwright reuses it. |
| A test fails only sometimes | Re-run it with a trace: `npm run test:e2e -- <file> --trace on`, then `npx playwright show-report` and open the failed test. |
