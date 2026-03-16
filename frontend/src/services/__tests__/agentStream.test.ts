import { describe, it, expect } from 'vitest';
import { parseSSELine } from '../agentStream';

describe('parseSSELine', () => {
  it('parses a valid agent event', () => {
    const event = {
      agent: 'simulator',
      event_type: 'start',
      step: null,
      message: 'Starting simulation',
      data: null,
      timestamp: 1700000000,
    };
    const result = parseSSELine(`data: ${JSON.stringify(event)}`);
    expect(result).toEqual(event);
  });

  it('returns null for lines without data: prefix', () => {
    expect(parseSSELine('')).toBeNull();
    expect(parseSSELine('event: message')).toBeNull();
    expect(parseSSELine(': heartbeat')).toBeNull();
  });

  it('returns null for malformed JSON after data: prefix', () => {
    expect(parseSSELine('data: {not valid json')).toBeNull();
  });

  it('parses a thinking event with step number', () => {
    const event = {
      agent: 'policy',
      event_type: 'thinking',
      step: 2,
      message: 'Checking prerequisites',
      data: null,
      timestamp: 1700000001,
    };
    const result = parseSSELine(`data: ${JSON.stringify(event)}`);
    expect(result).not.toBeNull();
    expect(result!.step).toBe(2);
    expect(result!.event_type).toBe('thinking');
  });

  it('parses an event with data payload', () => {
    const event = {
      agent: 'risk_scoring',
      event_type: 'complete',
      step: null,
      message: 'Done',
      data: { risk_score: 0.75, risk_level: 'medium' },
      timestamp: 1700000002,
    };
    const result = parseSSELine(`data: ${JSON.stringify(event)}`);
    expect(result).not.toBeNull();
    expect(result!.data).toEqual({ risk_score: 0.75, risk_level: 'medium' });
  });
});
