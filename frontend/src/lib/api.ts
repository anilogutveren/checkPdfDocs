export interface CheckResultItem {
  name: string
  passed: boolean
  message: string
}

export interface AnalyzeResponse {
  filename: string
  word_count: number
  use_llm: boolean
  results: CheckResultItem[]
}

const API_URL = import.meta.env.PROD ? '' : 'http://localhost:8000'

export async function analyzePdf(
  file: File,
  use_llm: boolean,
): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('use_llm', String(use_llm))

  const response = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Request failed with status ${response.status}`)
  }

  return (await response.json()) as AnalyzeResponse
}
