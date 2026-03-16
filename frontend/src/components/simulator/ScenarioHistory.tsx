import { useEffect, useState } from 'react';
import { Clock, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';
import { getSimulationHistory } from '../../services/api';
import type { SimulationHistoryItem } from '../../services/api';

interface ScenarioHistoryProps {
  sessionId: string;
}

export default function ScenarioHistory({ sessionId }: ScenarioHistoryProps) {
  const [history, setHistory] = useState<SimulationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [compareA, setCompareA] = useState<number | null>(null);
  const [compareB, setCompareB] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSimulationHistory(sessionId)
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return null;
  if (history.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Clock className="w-4 h-4" />
          Run simulations to see history here for side-by-side comparison.
        </div>
      </div>
    );
  }

  const a = compareA !== null ? history[compareA] : null;
  const b = compareB !== null ? history[compareB] : null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-600" />
          <h4 className="text-sm font-semibold text-slate-800">Scenario History ({history.length})</h4>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {expanded && (
        <div className="p-4 space-y-3">
          {/* Scenario chips */}
          <div className="flex flex-wrap gap-2">
            {history.map((sim, i) => (
              <button
                key={sim.id}
                onClick={() => {
                  if (compareA === null || (compareA !== null && compareB !== null)) {
                    setCompareA(i);
                    setCompareB(null);
                  } else {
                    setCompareB(i);
                  }
                }}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                  compareA === i
                    ? 'bg-violet-100 text-violet-700 ring-2 ring-violet-300'
                    : compareB === i
                      ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-300'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {sim.scenario_type.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Comparison */}
          {a && b && a.result && b.result && (
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
              <CompareCard label="Scenario A" sim={a} color="violet" />
              <CompareCard label="Scenario B" sim={b} color="blue" />
            </div>
          )}

          {a && !b && (
            <p className="text-xs text-slate-400 italic">Select a second scenario to compare.</p>
          )}
        </div>
      )}
    </div>
  );
}

function CompareCard({
  label,
  sim,
  color,
}: {
  label: string;
  sim: SimulationHistoryItem;
  color: 'violet' | 'blue';
}) {
  const result = sim.result as Record<string, unknown> | null;
  if (!result) return null;

  const borderColor = color === 'violet' ? 'border-violet-200' : 'border-blue-200';
  const bgColor = color === 'violet' ? 'bg-violet-50' : 'bg-blue-50';
  const textColor = color === 'violet' ? 'text-violet-700' : 'text-blue-700';

  return (
    <div className={`rounded-lg border ${borderColor} overflow-hidden`}>
      <div className={`px-3 py-1.5 ${bgColor}`}>
        <span className={`text-xs font-semibold ${textColor}`}>{label}</span>
        <span className="text-xs text-slate-500 ml-2">{sim.scenario_type.replace('_', ' ')}</span>
      </div>
      <div className="px-3 py-2 space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-500">Graduation</span>
          <span className="font-medium">
            {String(result.original_graduation || '?')} <ArrowRight className="w-3 h-3 inline text-slate-300" /> {String(result.new_graduation || '?')}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Semesters Added</span>
          <span className="font-medium">{String(result.semesters_added || 0)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Risk</span>
          <span className="font-medium">{String(result.risk_level || 'low')}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Affected</span>
          <span className="font-medium">{Array.isArray(result.affected_courses) ? result.affected_courses.length : 0} courses</span>
        </div>
      </div>
    </div>
  );
}
