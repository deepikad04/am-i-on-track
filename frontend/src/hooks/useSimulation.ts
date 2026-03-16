import { useState, useCallback } from 'react';
import { createSimulationStream } from '../services/agentStream';
import type { Scenario, SimulationResult } from '../types/simulation';
import type { AgentEvent } from '../types/agent';

export function useSimulation() {
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [correctionCount, setCorrectionCount] = useState(0);
  const [policyCheck, setPolicyCheck] = useState<Record<string, unknown> | null>(null);
  const cancelRef = { current: null as (() => void) | null };

  const runSimulation = useCallback(
    (
      scenario: Scenario,
      onEvent: (event: AgentEvent) => void,
    ) => {
      setRunning(true);
      setError(null);
      setResult(null);
      setExplanation(null);
      setCorrectionCount(0);
      setPolicyCheck(null);

      const cancel = createSimulationStream(
        scenario,
        (event) => {
          onEvent(event);

          // Capture agent-level errors from the SSE stream
          if (event.event_type === 'error') {
            setError(event.message || 'Simulation failed');
          }

          // Capture final result
          if (event.data && 'simulation' in event.data) {
            const simData = event.data.simulation as unknown as SimulationResult;
            // Attach overlap data if present
            if (event.data.overlap) {
              simData.overlap = event.data.overlap as SimulationResult['overlap'];
            }
            setResult(simData);
            setExplanation((event.data.explanation as string) || null);
            setCorrectionCount((event.data.correction_count as number) || 0);
            setPolicyCheck((event.data.policy_check as Record<string, unknown>) || null);
          }
        },
        () => setRunning(false),
        (err) => {
          setError(err.message);
          setRunning(false);
        },
      );

      cancelRef.current = cancel;
    },
    [],
  );

  const cancelSimulation = useCallback(() => {
    cancelRef.current?.();
    setRunning(false);
  }, []);

  return { result, explanation, running, error, correctionCount, policyCheck, runSimulation, cancelSimulation };
}
