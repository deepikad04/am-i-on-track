export type AgentName =
  | 'interpreter'
  | 'overlap'
  | 'simulator'
  | 'explanation'
  | 'advisor'
  | 'policy'
  | 'risk_scoring'
  | 'debate_fast'
  | 'debate_safe'
  | 'jury';

export type AgentEventType =
  | 'start'
  | 'thinking'
  | 'complete'
  | 'error';

export interface AgentEvent {
  agent: AgentName;
  event_type: AgentEventType;
  step: number | null;
  message: string;
  data: Record<string, unknown> | null;
  timestamp: number;
}

export interface AgentStatus {
  name: AgentName;
  display_name: string;
  status: 'idle' | 'running' | 'complete' | 'error';
  steps: AgentStep[];
}

export interface AgentStep {
  step_number: number;
  thought: string;
  timestamp: number;
}
