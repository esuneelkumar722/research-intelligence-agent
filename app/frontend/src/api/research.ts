import type { StartResponse, ResultResponse, StreamEvent } from '../types/research'

const BASE = '/v1/research'

export async function startResearch(query: string): Promise<StartResponse> {
  const res = await fetch(`${BASE}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Failed to start research')
  }
  return res.json()
}

export async function getResult(sessionId: string): Promise<ResultResponse> {
  const res = await fetch(`${BASE}/${sessionId}/result`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Failed to fetch result')
  }
  return res.json()
}

/**
 * Opens an SSE connection that resumes the graph (approved=true) and streams
 * live agent events. Calls onEvent for each parsed event, onDone when the
 * stream closes cleanly, onError on failure.
 *
 * Returns a cleanup function that aborts the SSE connection.
 */
export function streamResearch(
  sessionId: string,
  approved: boolean,
  feedback: string,
  onEvent: (e: StreamEvent) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  const params = new URLSearchParams({
    approved: String(approved),
    feedback,
  })
  const url = `${BASE}/${sessionId}/stream?${params}`

  const es = new EventSource(url)

  es.onmessage = (evt) => {
    try {
      const data: StreamEvent = JSON.parse(evt.data)
      onEvent(data)
      if (data.event === 'complete') {
        es.close()
        onDone()
      }
      if (data.event === 'error') {
        es.close()
        onError(data.message ?? 'Stream error')
      }
    } catch {
      // ignore malformed frames
    }
  }

  es.onerror = () => {
    es.close()
    onError('Connection to server lost. Please try again.')
  }

  return () => es.close()
}
