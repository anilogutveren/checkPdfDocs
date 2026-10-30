# Smart PDF Analyser – Upload & Analyse Test Plan

## Application Overview

Single-page React app (Vite, `http://localhost:5173`) that posts a PDF to the FastAPI backend (`POST http://localhost:8000/analyze`) and renders contract check results.

**Key UI elements**

| Element | Locator |
|---|---|
| Heading "Smart PDF Analyser" | `getByRole('heading', { name: 'Smart PDF Analyser' })` |
| Drop zone | `getByRole('button', { name: 'Drop a PDF file here or click to browse' })` |
| Hidden file input | `locator('input[type=file]')` (accept `application/pdf`) |
| File chip | file name + size + `getByRole('button', { name: 'Remove' })` |
| LLM checkbox | `getByRole('checkbox', { name: /Use LLM/ })` |
| Analyse button | `getByRole('button', { name: 'Scan & Analyse' })` (disabled without file; shows "Analysing…" while loading) |
| Results card | placeholder "Results will appear here after scanning." → "N words analysed" + one row per check with PASS/FAIL badge and message |
| Error alert | `getByRole('alert')` with title "Error" |

**Backend checks returned (in order):** `section` (parties), `section` (terms), `section` (signature/agreement), `length` (≥ 50 words), and `llm` only when the checkbox is ticked.

**Test data:** `documents/samples/sample_order_minibus.pdf`, `sample_order_pickup.pdf`, `sample_order_transporter.pdf`; ground truth in `tests/fixtures/sample_orders_ground_truth.json`.

**Seed:** `frontend/tests/seed.spec.ts`

**Preconditions:** fresh page load. Scenarios tagged *(real backend)* need `uvicorn contract_checker.api:app --port 8000`; all others mock `**/analyze` with `page.route`.

---

## 1. Happy Path

### 1.1 Upload a valid PDF via file picker and analyse *(real backend)*
**Steps**
1. Navigate to `/`.
2. Verify "Scan & Analyse" is disabled and the results placeholder is shown.
3. Set `sample_order_pickup.pdf` on `input[type=file]`.
4. Verify the file chip shows `sample_order_pickup.pdf` and a non-zero size.
5. Verify "Scan & Analyse" is enabled.
6. Click "Scan & Analyse".
7. Verify the button shows "Analysing…" and is disabled.
8. Wait for the `POST /analyze` response (200).

**Expected**
- "N words analysed" is shown with N > 0.
- 4 result rows: `section`, `section`, `section`, `length`, each with PASS or FAIL badge and a non-empty message.
- `length` message matches `/Contract length: \d+ words \(minimum 50\)\./`.
- Button returns to "Scan & Analyse"; no error alert.

### 1.2 Upload via drag and drop
**Steps**
1. Navigate to `/`.
2. Create a `DataTransfer` containing `sample_order_minibus.pdf`; dispatch `dragover` then `drop` on the drop zone.
3. Click "Scan & Analyse".

**Expected**
- File chip shows `sample_order_minibus.pdf`.
- 4 result rows render.

### 1.3 Keyboard access to the drop zone
**Steps**
1. Focus the drop zone with Tab.
2. Press Enter (repeat with Space) while awaiting `page.waitForEvent('filechooser')`.
3. Set `sample_order_transporter.pdf` on the chooser and analyse.

**Expected**
- File chooser opens for both keys.
- Results render.

### 1.4 Analyse each sample PDF (data-driven) *(real backend)*
**Steps**
1. For each sample PDF: upload, analyse.

**Expected**
- Response contains 4 results and `word_count > 0`.
- Optionally matches `tests/fixtures/sample_orders_ground_truth.json`.

### 1.5 Analyse with LLM enabled (mocked)
**Steps**
1. Mock `**/analyze` to return 5 results, last being `{ name: "llm", passed: true, message: "Nimble contract-plausibility score 0.90 (threshold 0.50)." }`.
2. Tick "Use LLM (requires local Ollama)".
3. Upload a PDF and click "Scan & Analyse".

**Expected**
- Request form data contains `use_llm=true`.
- 5 rows render; the `llm` row shows PASS.

### 1.6 LLM enabled but model unavailable *(real backend, no model)*
**Steps**
1. Tick the LLM checkbox, upload a PDF, analyse.

**Expected**
- `llm` row shows FAIL with message starting "LLM check unavailable (".
- The other 4 checks still render.

---

## 2. State Transitions

### 2.1 Remove selected file
**Steps**
1. Upload a PDF.
2. Click "Remove".

**Expected**
- File chip disappears; "Scan & Analyse" is disabled.

### 2.2 Replacing the file clears previous results
**Steps**
1. Upload PDF A and analyse; verify results render.
2. Upload PDF B.

**Expected**
- Results placeholder "Results will appear here after scanning." is shown again; chip shows B.
- Known gap: "N words analysed" may persist (separate state not reset) — flag as potential bug.

### 2.3 Re-analyse the same file
**Steps**
1. Upload a PDF and analyse.
2. Click "Scan & Analyse" again.

**Expected**
- Previous results clear during loading; new results render.

---

## 3. Negative / Validation

### 3.1 Non-PDF via file picker
**Steps**
1. Set a `.txt` buffer (`mimeType: 'text/plain'`) on the file input.

**Expected**
- Error alert "Only PDF files are supported."
- No file chip; button disabled.

### 3.2 Non-PDF via drag and drop
**Steps**
1. Drop a `.png` file on the drop zone.

**Expected**
- Same error as 3.1; no file selected.

### 3.3 Error clears after a valid upload
**Steps**
1. Trigger 3.1.
2. Upload a valid PDF.

**Expected**
- Error alert disappears.

### 3.4 Fake PDF (PDF MIME, invalid content) *(real backend)*
**Steps**
1. Upload buffer `fake.pdf`, `mimeType: 'application/pdf'`, content `hello`.
2. Analyse.

**Expected**
- 422; alert shows "The uploaded file is not a valid PDF."

### 3.5 Empty PDF *(real backend)*
**Steps**
1. Upload 0-byte `empty.pdf` with `application/pdf`.
2. Analyse.

**Expected**
- 400; alert shows "Uploaded file is empty."

### 3.6 PDF with too little text *(real backend)*
**Steps**
1. Upload a valid PDF with fewer than 50 words.
2. Analyse.

**Expected**
- `length` row shows FAIL.
- `section` rows with missing keywords show FAIL with "Missing expected section(s): …".

### 3.7 Backend unreachable
**Steps**
1. `page.route('**/analyze', route => route.abort())`.
2. Upload a PDF and analyse.

**Expected**
- Error alert shows the network error (e.g. "Failed to fetch").
- Button returns to idle state.

### 3.8 Server error without JSON body
**Steps**
1. Mock `**/analyze` → status 500, plain-text body.
2. Upload a PDF and analyse.

**Expected**
- Error alert shows "Unknown error".

---

## 4. Loading / UX

### 4.1 No double submit while loading
**Steps**
1. Mock `**/analyze` with a 2 s delay.
2. Upload a PDF and click "Scan & Analyse".
3. Click the button again.

**Expected**
- Button disabled with "Analysing…".
- Only one `/analyze` request is sent (count via `page.on('request')`).
