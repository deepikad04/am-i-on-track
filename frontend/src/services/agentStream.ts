import type { AgentEvent } from '../types/agent';
import type { Scenario } from '../types/simulation';

/** Parse a single SSE line into an AgentEvent, or null if not parseable. */
export function parseSSELine(line: string): AgentEvent | null {
  if (!line.startsWith('data: ')) return null;
  try {
    return JSON.parse(line.slice(6)) as AgentEvent;
  } catch {
    return null;
  }
}

export function createSimulationStream(
  scenario: Scenario,
  onEvent: (event: AgentEvent) => void,
  onComplete: () => void,
  onError: (error: Error) => void,
): () => void {
  const controller = new AbortController();

  const token = localStorage.getItem('token');
  fetch('/api/simulate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(scenario),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const err = await response.json();
          if (err.detail) detail = err.detail;
        } catch { /* ignore parse errors */ }
        throw new Error(detail);
      }
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No readable stream');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: AgentEvent = JSON.parse(line.slice(6));
              onEvent(event);
            } catch {
              // skip malformed lines
            }
          }
        }
      }

      onComplete();
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err);
    });

  return () => controller.abort();
}
