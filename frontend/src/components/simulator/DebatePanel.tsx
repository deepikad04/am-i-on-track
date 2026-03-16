import { useState } from 'react';
import { Swords, Zap, Shield, Scale, Loader2 } from 'lucide-react';
import { runDebate } from '../../services/api';

interface DebatePanelProps {
  sessionId: string;
}

export default function DebatePanel({ sessionId }: DebatePanelProps) {
  const [running, setRunning] = useState(false);
  const [fast, setFast] = useState<string | null>(null);
  const [safe, setSafe] = useState<string | null>(null);
  const [jury, setJury] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setFast(null);
    setSafe(null);
    setJury(null);
    setError(null);
    try {
      const result = await runDebate(sessionId, (event) => {
        // Stream partial updates
        if (event.agent === 'debate_fast' && event.event_type === 'complete' && event.data) {
          const data = event.data as Record<string, string>;
          if (data.proposal) setFast(data.proposal);
          // Final combined event has fast + safe + jury
          if (data.fast && data.safe) {
            setFast(data.fast);
            setSafe(data.safe);
            if (data.jury) setJury(data.jury);
          }
        }
        if (event.agent === 'debate_safe' && event.event_type === 'complete' && event.data) {
          setSafe((event.data as Record<string, string>).proposal || '');
        }
        if (event.agent === 'jury' && event.event_type === 'complete' && event.data) {
          setJury((event.data as Record<string, string>).verdict || '');
        }
      });
      if (result.fast) setFast(result.fast);
      if (result.safe) setSafe(result.safe);
      if (result.jury) setJury(result.jury);
    } catch {
      setError('Debate failed. Make sure the backend is running.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden" role="region" aria-label="Agent debate: Fast Track vs Safe Path vs Jury">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Swords className="w-4 h-4 text-slate-600" />
          <h3 className="text-sm font-semibold text-slate-800">Agent Debate</h3>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          aria-label={running ? 'Debate in progress' : 'Start agent debate'}
          aria-busy={running}
          className="text-xs px-3 py-1 bg-violet-600 text-white rounded-md hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Swords className="w-3 h-3" />}
          {running ? 'Debating…' : 'Start Debate'}
        </button>
      </div>

      <div className="p-4">
        <p className="text-xs text-slate-500 mb-3">
          Two AI advisors argue opposing strategies, then a Jury synthesizes the optimal plan.
        </p>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3">{error}</p>
        )}

        {running && !fast && !safe && (
          <div className="flex items-center justify-center py-6 text-sm text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Agents are debating…
          </div>
        )}

        {(fast || safe) && (
          <div className="space-y-3">
            {/* Fast Track vs Safe Path side by side */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-amber-200 overflow-hidden">
                <div className="px-3 py-1.5 bg-amber-50 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-600" />
                  <span className="text-xs font-semibold text-amber-700">Fast Track</span>
                </div>
                <div className="px-3 py-2 text-xs text-slate-700 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                  {fast || <span className="text-slate-400 italic">Waiting…</span>}
                </div>
              </div>

              <div className="rounded-lg border border-emerald-200 overflow-hidden">
                <div className="px-3 py-1.5 bg-emerald-50 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-xs font-semibold text-emerald-700">Safe Path</span>
                </div>
                <div className="px-3 py-2 text-xs text-slate-700 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                  {safe || <span className="text-slate-400 italic">Waiting…</span>}
                </div>
              </div>
            </div>

            {/* Jury Verdict */}
            {jury ? (
              <div className="rounded-lg border-2 border-violet-300 overflow-hidden">
                <div className="px-3 py-2 bg-violet-50 flex items-center gap-1.5">
                  <Scale className="w-4 h-4 text-violet-600" />
                  <span className="text-sm font-semibold text-violet-700">Jury Verdict</span>
                  <span className="text-[10px] text-violet-500 ml-auto">Synthesized from both proposals</span>
                </div>
                <div className="px-4 py-3 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed bg-violet-50/30">
                  {jury}
                </div>
              </div>
            ) : running && fast && safe ? (
              <div className="rounded-lg border border-violet-200 px-4 py-3 flex items-center gap-2 bg-violet-50/50">
                <Loader2 className="w-4 h-4 animate-spin text-violet-500" />
                <span className="text-xs text-violet-600">Jury is synthesizing both proposals…</span>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
