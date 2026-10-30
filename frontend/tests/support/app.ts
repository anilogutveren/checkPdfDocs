import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { type APIRequestContext, type Page, test } from '@playwright/test'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(HERE, '../../..')

export const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

export const SAMPLE_PDFS = [
  'sample_order_minibus.pdf',
  'sample_order_pickup.pdf',
  'sample_order_transporter.pdf',
] as const

export type SamplePdf = (typeof SAMPLE_PDFS)[number]

export function samplePdfPath(name: SamplePdf): string {
  return path.join(REPO_ROOT, 'documents/samples', name)
}

interface GroundTruthOrder {
  file_name: string
  expected_checks: boolean[]
}

export function expectedChecksFor(name: SamplePdf): boolean[] | undefined {
  const fixture = path.join(REPO_ROOT, 'tests/fixtures/sample_orders_ground_truth.json')
  const { orders } = JSON.parse(readFileSync(fixture, 'utf-8')) as { orders: GroundTruthOrder[] }
  return orders.find((order) => order.file_name === name)?.expected_checks
}

export function ui(page: Page) {
  return {
    heading: page.getByRole('heading', { name: 'Smart PDF Analyser' }),
    dropZone: page.getByRole('button', { name: 'Drop a PDF file here or click to browse' }),
    fileInput: page.locator('input[type=file]'),
    removeButton: page.getByRole('button', { name: 'Remove' }),
    llmCheckbox: page.getByRole('checkbox', { name: /Use LLM/ }),
    analyseButton: page.getByRole('button', { name: 'Scan & Analyse' }),
    analysingButton: page.getByRole('button', { name: 'Analysing…' }),
    placeholder: page.getByText('Results will appear here after scanning.'),
    wordsAnalysed: page.getByText(/^[\d,.]+ words analysed$/),
    // Rows carry no role/test id; the list container is the only `.space-y-3` on the page.
    resultRows: page.locator('.space-y-3 > div'),
    errorAlert: page.getByRole('alert'),
  }
}

export function rowParts(row: ReturnType<Page['locator']>) {
  return {
    name: row.locator('span.capitalize'),
    badge: row.getByText(/^(PASS|FAIL)$/),
    message: row.locator('p'),
  }
}

export interface MockResult {
  name: string
  passed: boolean
  message: string
}

export const MOCK_BASE_RESULTS: MockResult[] = [
  { name: 'section', passed: true, message: 'Required section(s) found.' },
  { name: 'section', passed: true, message: 'Required section(s) found.' },
  { name: 'section', passed: false, message: 'Missing expected section(s): signature, sign, agreement' },
  { name: 'length', passed: true, message: 'Contract length: 1234 words (minimum 50).' },
]

const CORS_HEADERS = { 'access-control-allow-origin': '*' }

export async function mockAnalyze(page: Page, results: MockResult[] = MOCK_BASE_RESULTS, delayMs = 0) {
  await page.route('**/analyze', async (route) => {
    if (delayMs) await new Promise((resolve) => setTimeout(resolve, delayMs))
    await route.fulfill({
      status: 200,
      headers: CORS_HEADERS,
      contentType: 'application/json',
      body: JSON.stringify({ filename: 'mock.pdf', word_count: 1234, use_llm: false, results }),
    })
  })
}

export async function mockAnalyzePlainTextError(page: Page, status: number) {
  await page.route('**/analyze', (route) =>
    route.fulfill({ status, headers: CORS_HEADERS, contentType: 'text/plain', body: 'Internal Server Error' }),
  )
}

export async function skipUnlessBackendUp(request: APIRequestContext) {
  const isUp = await request
    .get(`${BACKEND_URL}/health`)
    .then((response) => response.ok())
    .catch(() => false)
  test.skip(!isUp, `Backend not reachable at ${BACKEND_URL}`)
  // The first real request after backend start-up can be slow (cold start).
  test.slow()
}

interface DropFile {
  name: string
  mimeType: string
  buffer: Buffer
}

export function pdfFile(name: SamplePdf): DropFile {
  return { name, mimeType: 'application/pdf', buffer: readFileSync(samplePdfPath(name)) }
}

export async function dropFile(page: Page, file: DropFile) {
  const dataTransfer = await page.evaluateHandle(
    ({ base64, name, mimeType }) => {
      const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
      const transfer = new DataTransfer()
      transfer.items.add(new File([bytes], name, { type: mimeType }))
      return transfer
    },
    { base64: file.buffer.toString('base64'), name: file.name, mimeType: file.mimeType },
  )
  const { dropZone } = ui(page)
  await dropZone.dispatchEvent('dragover', { dataTransfer })
  await dropZone.dispatchEvent('drop', { dataTransfer })
}

/** Builds a minimal single-page PDF containing `text` (ASCII only, no parentheses). */
export function buildTinyPdf(text: string): Buffer {
  const content = `BT /F1 12 Tf 72 720 Td (${text}) Tj ET`
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  let pdf = '%PDF-1.4\n'
  const offsets: number[] = []
  objects.forEach((body, index) => {
    offsets.push(pdf.length)
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`
  })
  const xrefOffset = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  pdf += offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`
  return Buffer.from(pdf, 'latin1')
}
