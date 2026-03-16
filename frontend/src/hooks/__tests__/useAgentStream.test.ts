import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAgentStream } from '../useAgentStream';
import type { AgentEvent } from '../../types/agent';

function makeEvent(overrides: Partial<AgentEvent>): AgentEvent {
  return {
    agent: 'simulator',
    event_type: 'start',
    step: null,
    message: '',
    data: null,
    timestamp: Date.now(),
    ...overrides,
  };
}

describe('useAgentStream — handleEvent', () => {
  it('initializes all 10 agents as idle', () => {
    const { result } = renderHook(() => useAgentStream());
    expect(result.current.agents).toHaveLength(10);
    result.current.agents.forEach((a) => {
      expect(a.status).toBe('idle');
      expect(a.steps).toEqual([]);
    });
  });

  it('transitions agent from idle to running on start event', () => {
    const { result } = renderHook(() => useAgentStream());
    act(() => {
      result.current.handleEvent(makeEvent({ agent: 'simulator', event_type: 'start' }));
    });
    const sim = result.current.agents.find((a) => a.name === 'simulator')!;
    expect(sim.status).toBe('running');
  });

  it('transitions agent to complete on complete event', () => {
    const { result } = renderHook(() => useAgentStream());
    act(() => {
      result.current.handleEvent(makeEvent({ agent: 'policy', event_type: 'start' }));
      result.current.handleEvent(makeEvent({ agent: 'policy', event_type: 'complete' }));
    });
    const policy = result.current.agents.find((a) => a.name === 'policy')!;
    expect(policy.status).toBe('complete');
  });

  it('transitions agent to error on error event', () => {
    const { result } = renderHook(() => useAgentStream());
    act(() => {
      result.current.handleEvent(makeEvent({ agent: 'interpreter', event_type: 'start' }));
      result.current.handleEvent(makeEvent({ agent: 'interpreter', event_type: 'error', message: 'Parse failed' }));
    });
    const interp = result.current.agents.find((a) => a.name === 'interpreter')!;
    expect(interp.status).toBe('error');
  });

  it('accumulates thinking steps', () => {
    const { result } = renderHook(() => useAgentStream());
    act(() => {
      result.current.handleEvent(makeEvent({ agent: 'simulator', event_type: 'start' }));
      result.current.handleEvent(makeEvent({ agent: 'simulator', event_type: 'thinking', step: 1, message: 'Step 1' }));
      result.current.handleEvent(makeEvent({ agent: 'simulator', event_type: 'thinking', step: 2, message: 'Step 2' }));
    });
    const sim = result.current.agents.find((a) => a.name === 'simulator')!;
    expect(sim.steps).toHaveLength(2);
    expect(sim.steps[0].step_number).toBe(1);
    expect(sim.steps[1].step_number).toBe(2);
  });

  it('resets all agents back to idle', () => {
    const { result } = renderHook(() => useAgentStream());
    act(() => {
      result.current.handleEvent(makeEvent({ agent: 'simulator', event_type: 'start' }));
      result.current.handleEvent(makeEvent({ agent: 'simulator', event_type: 'complete' }));
    });
    expect(result.current.agents.find((a) => a.name === 'simulator')!.status).toBe('complete');
    act(() => {
      result.current.resetAgents();
    });
    result.current.agents.forEach((a) => {
      expect(a.status).toBe('idle');
    });
  });
});
