import { useState, useCallback, useRef } from 'react';
import type { AgentEvent, AgentStatus, AgentStep } from '../types/agent';

const DEFAULT_AGENTS: AgentStatus[] = [
  { name: 'interpreter', display_name: 'Degree Interpreter', status: 'idle', steps: [] },
  { name: 'overlap', display_name: 'Overlap Analyzer', status: 'idle', steps: [] },
  { name: 'simulator', display_name: 'Trajectory Simulator', status: 'idle', steps: [] },
  { name: 'explanation', display_name: 'Explanation Agent', status: 'idle', steps: [] },
  { name: 'advisor', display_name: 'Course Advisor', status: 'idle', steps: [] },
  { name: 'policy', display_name: 'Policy Agent', status: 'idle', steps: [] },
  { name: 'risk_scoring', display_name: 'Risk Scoring Agent', status: 'idle', steps: [] },
  { name: 'debate_fast', display_name: 'Fast Track Advisor', status: 'idle', steps: [] },
  { name: 'debate_safe', display_name: 'Safe Path Advisor', status: 'idle', steps: [] },
  { name: 'jury', display_name: 'Jury Agent', status: 'idle', steps: [] },
];

export function useAgentStream() {
  const [agents, setAgents] = useState<AgentStatus[]>(DEFAULT_AGENTS);
  const abortRef = useRef<(() => void) | null>(null);

  const resetAgents = useCallback(() => {
    setAgents(DEFAULT_AGENTS);
  }, []);

  const handleEvent = useCallback((event: AgentEvent) => {
    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.name !== event.agent) return agent;

        const newStep: AgentStep | null =
          event.event_type === 'thinking' && event.step != null
            ? { step_number: event.step, thought: event.message, timestamp: event.timestamp }
            : null;

        return {
          ...agent,
          status:
            event.event_type === 'start'
              ? 'running'
              : event.event_type === 'complete'
                ? 'complete'
                : event.event_type === 'error'
                  ? 'error'
                  : agent.status,
          steps: event.event_type === 'start'
            ? []
            : newStep
              ? [...agent.steps, newStep]
              : agent.steps,
        };
      }),
    );
  }, []);

  const readSSEStream = useCallback(
    async (url: string): Promise<AgentEvent | null> => {
      resetAgents();
      let lastEvent: AgentEvent | null = null;

      const token = localStorage.getItem('token');
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

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
              handleEvent(event);
              lastEvent = event;
            } catch {
              // skip malformed
            }
          }
        }
      }

      return lastEvent;
    },
    [handleEvent, resetAgents],
  );

  const streamParse = useCallback(
    (sessionId: string) => readSSEStream(`/api/upload/${sessionId}/parse`),
    [readSSEStream],
  );

  const streamParseUrl = useCallback(
    (sessionId: string) => readSSEStream(`/api/upload/${sessionId}/parse-url`),
    [readSSEStream],
  );

  const cancel = useCallback(() => {
    abortRef.current?.();
  }, []);

  return { agents, handleEvent, streamParse, streamParseUrl, resetAgents, cancel };
}
