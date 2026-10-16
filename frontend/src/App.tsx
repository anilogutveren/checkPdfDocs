import {
  AlertCircle,
  CheckCircle,
  FileText,
  Loader2,
  Upload,
  XCircle,
} from 'lucide-react'
import { useCallback, useRef, useState } from 'react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { analyzePdf, type CheckResultItem } from '@/lib/api'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / k ** i).toFixed(1).replace(/\.0$/, '')} ${sizes[i]}`
}

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [use_llm, setUse_llm] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<CheckResultItem[] | null>(null)
  const [wordCount, setWordCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((selected: File | null) => {
    setError(null)
    setResults(null)
    if (selected && selected.type !== 'application/pdf') {
      setError('Only PDF files are supported.')
      setFile(null)
      return
    }
    setFile(selected)
  }, [])

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      setIsDragging(false)
      const dropped = event.dataTransfer.files?.[0] ?? null
      handleFile(dropped)
    },
    [handleFile],
  )

  const onFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      handleFile(event.target.files?.[0] ?? null)
    },
    [handleFile],
  )

  const onAnalyze = useCallback(async () => {
    if (!file) {
      setError('Please drop or select a PDF file first.')
      return
    }
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const data = await analyzePdf(file, use_llm)
      setResults(data.results)
      setWordCount(data.word_count)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed.')
    } finally {
      setLoading(false)
    }
  }, [file, use_llm])

  return (
    <div className="min-h-screen bg-background p-6 md:p-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Smart PDF Analyser
          </h1>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Drag a PDF contract here and click <strong>Scan & Analyse</strong> to
            verify required sections, minimum length, and optional AI
            plausibility.
          </p>
        </div>

        {error ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Upload contract</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                  isDragging
                    ? 'border-primary bg-primary/5'
                    : 'border-muted-foreground/25 hover:border-primary/50'
                }`}
                role="button"
                tabIndex={0}
                aria-label="Drop a PDF file here or click to browse"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    fileInputRef.current?.click()
                  }
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={onFileInputChange}
                />
                <Upload className="mx-auto h-10 w-10 text-muted-foreground" />
                <p className="mt-4 text-sm text-muted-foreground">
                  Drop a PDF here, or click to browse
                </p>
              </div>

              {file ? (
                <div className="flex items-center gap-3 rounded-md border p-3">
                  <FileText className="h-5 w-5 text-primary" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatBytes(file.size)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleFile(null)}
                    className="text-xs text-destructive hover:underline"
                  >
                    Remove
                  </button>
                </div>
              ) : null}

              <div className="flex items-center justify-between gap-4 flex-wrap">
                <Checkbox
                  id="use-llm"
                  label="Use LLM (requires local Ollama)"
                  checked={use_llm}
                  onChange={(e) => setUse_llm(e.target.checked)}
                />
                <Button
                  onClick={onAnalyze}
                  disabled={!file || loading}
                  className="min-w-[140px]"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Analysing…
                    </>
                  ) : (
                    'Scan & Analyse'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Results</CardTitle>
              {wordCount !== null ? (
                <p className="text-sm text-muted-foreground">
                  {wordCount.toLocaleString()} words analysed
                </p>
              ) : null}
            </CardHeader>
            <CardContent>
              {results === null ? (
                <p className="text-sm text-muted-foreground">
                  Results will appear here after scanning.
                </p>
              ) : (
                <div className="space-y-3">
                  {results.map((result) => (
                    <div
                      key={result.name + result.message}
                      className="flex items-start gap-3 rounded-lg border p-3"
                    >
                      {result.passed ? (
                        <CheckCircle className="mt-0.5 h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="mt-0.5 h-5 w-5 text-destructive" />
                      )}
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium capitalize">
                            {result.name}
                          </span>
                          <Badge
                            variant={result.passed ? 'success' : 'destructive'}
                          >
                            {result.passed ? 'PASS' : 'FAIL'}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {result.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
