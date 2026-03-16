import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AgentOrchestrationFlow from '../agents/AgentOrchestrationFlow';
import type { AgentStatus } from '../../types/agent';

function makeAgents(overrides: Partial<Record<string, Partial<AgentStatus>>> = {}): AgentStatus[] {
  const names = [
    'interpreter', 'overlap', 'simulator', 'explanation',
    'advisor', 'policy', 'risk_scoring', 'debate_fast', 'debate_safe', 'jury',
  ] as const;
  return names.map((name) => ({
    name,
    display_name: name,
    status: 'idle' as const,
    steps: [],
    ...overrides[name],
  }));
}

describe('AgentOrchestrationFlow', () => {
  it('renders the orchestrator header', () => {
    render(<AgentOrchestrationFlow agents={makeAgents()} />);
    expect(screen.getByText('Multi-Agent Orchestrator')).toBeInTheDocument();
  });

  it('renders all 10 agent cards', () => {
    render(<AgentOrchestrationFlow agents={makeAgents()} />);
    const list = screen.getByRole('list', { name: /ai agents/i });
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(10);
    expect(list).toBeInTheDocument();
  });

  it('shows agent labels', () => {
    render(<AgentOrchestrationFlow agents={makeAgents()} />);
    expect(screen.getByText('Degree Interpreter')).toBeInTheDocument();
    expect(screen.getByText('Trajectory Simulator')).toBeInTheDocument();
    expect(screen.getByText('Policy Agent')).toBeInTheDocument();
    expect(screen.getByText('Course Advisor')).toBeInTheDocument();
  });

  it('shows model routing info for each agent', () => {
    render(<AgentOrchestrationFlow agents={makeAgents()} />);
    expect(screen.getAllByText('Nova 2 Lite').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Dynamic: Lite ↔ Pro')).toHaveLength(2);
  });

  it('shows feature tags in header', () => {
    render(<AgentOrchestrationFlow agents={makeAgents()} />);
    expect(screen.getByText('Complexity Router')).toBeInTheDocument();
    expect(screen.getByText('Agent Memory')).toBeInTheDocument();
    expect(screen.getByText('Parallel Execution')).toBeInTheDocument();
    expect(screen.getByText('Tool Use')).toBeInTheDocument();
  });

  it('marks running agent with aria-live polite', () => {
    const agents = makeAgents({ simulator: { status: 'running', steps: [] } });
    render(<AgentOrchestrationFlow agents={agents} />);
    const simCard = screen.getByRole('listitem', { name: /trajectory simulator/i });
    expect(simCard).toHaveAttribute('aria-live', 'polite');
  });

  it('shows thinking steps when an agent has steps', () => {
    const agents = makeAgents({
      simulator: {
        status: 'running',
        steps: [
          { step_number: 1, thought: 'Building dependency graph', timestamp: Date.now() },
          { step_number: 2, thought: 'Running constraint solver', timestamp: Date.now() },
        ],
      },
    });
    render(<AgentOrchestrationFlow agents={agents} />);
    expect(screen.getByText('Building dependency graph')).toBeInTheDocument();
    expect(screen.getByText('Running constraint solver')).toBeInTheDocument();
  });

  it('renders complete agent differently from idle', () => {
    const agents = makeAgents({ policy: { status: 'complete', steps: [] } });
    render(<AgentOrchestrationFlow agents={agents} />);
    const card = screen.getByRole('listitem', { name: /policy agent.*complete/i });
    expect(card).toBeInTheDocument();
  });
});
