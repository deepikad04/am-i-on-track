import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export async function uploadDegreePdf(file: File): Promise<{ session_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function uploadDegreeUrls(urls: string[]): Promise<{ session_id: string }> {
  const { data } = await api.post('/upload/url', { urls });
  return data;
}

export async function getDegreeData(sessionId: string) {
  const { data } = await api.get(`/degree/${sessionId}`);
  return data;
}

export async function updateProgress(
  sessionId: string,
  completedCourses: string[],
  currentSemester: number,
) {
  const { data } = await api.post(`/degree/${sessionId}/progress`, {
    completed_courses: completedCourses,
    current_semester: currentSemester,
  });
  return data;
}

export async function getSimulationResult(simulationId: string) {
  const { data } = await api.get(`/simulate/${simulationId}/result`);
  return data;
}

export async function checkHealth() {
  const { data } = await api.get('/health');
  return data;
}

export async function explainCourse(
  sessionId: string,
  courseCode: string,
  signal?: AbortSignal,
  onProgress?: (text: string) => void,
): Promise<string> {
  // Pull auth header from the axios instance (set by AuthContext) so it stays in sync
  const authHeader = api.defaults.headers.common['Authorization'] as string | undefined;
  const response = await fetch('/api/explain/course', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    body: JSON.stringify({ session_id: sessionId, course_code: courseCode }),
    signal,
  });

  if (!response.ok) {
    throw new Error('Failed to get course explanation');
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let explanation = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const parsed = JSON.parse(line.slice(6));
        if (parsed.type === 'chunk' && parsed.text) {
          explanation += parsed.text;
          onProgress?.(explanation);
        } else if (parsed.type === 'result' && parsed.explanation) {
          explanation = parsed.explanation;
          onProgress?.(explanation);
        }
      } catch {
        // skip non-JSON lines
      }
    }
  }

  return explanation;
}

export interface SimilarCourse {
  code: string;
  name: string;
  similarity: number;
}

export async function getSimilarCourses(
  sessionId: string,
  courseCode: string,
  topK = 5,
): Promise<SimilarCourse[]> {
  const { data } = await api.post('/degree/similar-courses', {
    session_id: sessionId,
    course_code: courseCode,
    top_k: topK,
  });
  return data.similar || [];
}

export interface ImpactMetrics {
  total_credits: number;
  completed_credits: number;
  remaining_credits: number;
  estimated_semesters_remaining: number;
  semesters_saved: number;
  estimated_tuition_saved: number;
  advisor_hours_saved: number;
  risk_level: 'low' | 'medium' | 'high';
  bottleneck_courses: string[];
  on_track: boolean;
  credits_per_semester_avg: number;
  completion_percentage: number;
}

export async function getImpactReport(sessionId: string): Promise<ImpactMetrics> {
  const { data } = await api.get(`/degree/${sessionId}/impact`);
  return data;
}

export interface PolicyViolation {
  rule: string;
  severity: 'warning' | 'error';
  detail: string;
  affected_courses: string[];
  suggestion: string;
}

export interface PolicyCheckResult {
  violations: PolicyViolation[];
  passed: boolean;
  summary: string;
}

export async function getPolicyCheck(sessionId: string): Promise<PolicyCheckResult> {
  // Policy check is now SSE-streamed; read the final "result" event
  const authHeader = api.defaults.headers.common['Authorization'] as string | undefined;
  const response = await fetch(`/api/degree/${sessionId}/policy-check`, {
    headers: authHeader ? { Authorization: authHeader } : {},
  });
  if (!response.ok) throw new Error('Policy check failed');
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let result: PolicyCheckResult | null = null;
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const parsed = JSON.parse(line.slice(6));
        if (parsed.type === 'result') {
          result = { violations: parsed.violations, passed: parsed.passed, summary: parsed.summary };
        } else if (parsed.data?.violations) {
          result = { violations: parsed.data.violations, passed: parsed.data.passed, summary: parsed.data.summary };
        }
      } catch { /* skip */ }
    }
  }
  return result || { violations: [], passed: true, summary: 'Check complete' };
}

export async function getAdvisingSummary(sessionId: string): Promise<string> {
  const { data } = await api.get(`/degree/${sessionId}/export-summary`);
  return data.summary;
}

export interface SimulationHistoryItem {
  id: string;
  scenario_type: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown> | null;
  explanation: string;
  parent_simulation_id: string | null;
}

export async function getSimulationHistory(sessionId: string): Promise<SimulationHistoryItem[]> {
  const { data } = await api.get(`/simulate/${sessionId}/history`);
  return data;
}

export interface DebateResult {
  fast: string;
  safe: string;
  jury: string;
}

export async function runDebate(
  sessionId: string,
  onEvent?: (event: Record<string, unknown>) => void,
): Promise<DebateResult> {
  const authHeader = api.defaults.headers.common['Authorization'] as string | undefined;
  const response = await fetch('/api/simulate/debate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!response.ok) throw new Error('Debate failed');
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let result: DebateResult = { fast: '', safe: '', jury: '' };
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const parsed = JSON.parse(line.slice(6));
        onEvent?.(parsed);
        if (parsed.data?.fast && parsed.data?.safe) {
          result = { fast: parsed.data.fast, safe: parsed.data.safe, jury: parsed.data.jury || '' };
        }
      } catch { /* skip */ }
    }
  }
  return result;
}

export async function runOverlapAnalysis(
  sessionId1: string,
  sessionId2: string,
  onEvent?: (event: Record<string, unknown>) => void,
): Promise<Record<string, unknown> | null> {
  const authHeader = api.defaults.headers.common['Authorization'] as string | undefined;
  const response = await fetch('/api/degree/overlap', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    body: JSON.stringify({ session_id_1: sessionId1, session_id_2: sessionId2 }),
  });
  if (!response.ok) throw new Error('Overlap analysis failed');
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let result: Record<string, unknown> | null = null;
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const parsed = JSON.parse(line.slice(6));
        onEvent?.(parsed);
        if (parsed.data?.overlap) {
          result = parsed.data.overlap;
        }
      } catch { /* skip */ }
    }
  }
  return result;
}

export interface ScenarioInsight {
  key: string;
  frequency: number;
  semesters_added: number;
  risk_level: string;
  correction_count: number;
  affected_courses: string[];
}

export interface KnownBottleneck {
  course: string;
  frequency: number;
  cascading_delays: number;
  downstream_courses: string[];
}

export interface AgentMemoryInsights {
  scenario_insights: Record<string, ScenarioInsight[]>;
  known_bottlenecks: KnownBottleneck[];
  memory_active: boolean;
}

export async function getAgentMemoryInsights(): Promise<AgentMemoryInsights> {
  const { data } = await api.get('/agent-memory/insights');
  return data;
}

export async function generateRoadmapImage(sessionId: string): Promise<Blob> {
  const authHeader = api.defaults.headers.common['Authorization'] as string | undefined;
  const response = await fetch(`/api/degree/${sessionId}/roadmap-image`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
  });
  if (!response.ok) {
    let detail = 'Roadmap generation failed';
    try {
      const err = await response.json();
      if (err.detail) detail = err.detail;
    } catch { /* ignore parse errors */ }
    throw new Error(detail);
  }
  return response.blob();
}

export default api;
