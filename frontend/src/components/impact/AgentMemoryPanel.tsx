import { useEffect, useState } from 'react';
import { Brain, TrendingUp, AlertTriangle, Zap } from 'lucide-react';
import { getAgentMemoryInsights } from '../../services/api';
import type { AgentMemoryInsights } from '../../services/api';

const SCENARIO_LABELS: Record<string, string> = {
  drop_course: 'Drop Course',
  block_semester: 'Block Semester',
  add_major: 'Add Major',
  add_minor: 'Add Minor',
  set_goal: 'Set Goal',
};

export default function AgentMemoryPanel() {
  const [insights, setInsights] = useState<AgentMemoryInsights | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAgentMemoryInsights()
      .then(setInsights)
      .catch(() => setInsights(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-4 animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/3 mb-3" />
        <div className="h-16 bg-slate-100 rounded" />
      </div>
    );
  }

  if (!insights || !insights.memory_active) return null;

  const hasScenarios = Object.keys(insights.scenario_insights).length > 0;
  const hasBottlenecks = insights.known_bottlenecks.length > 0;

  if (!hasScenarios && !hasBottlenecks) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 bg-gradient-to-r from-violet-50 to-purple-50 border-b border-slate-200 flex items-center gap-2">
          <Brain className="w-4 h-4 text-violet-600" />
          <h4 className="text-sm font-semibold text-slate-800">Agent Memory</h4>
          <span className="ml-auto text-xs text-violet-500 bg-violet-100 px-2 py-0.5 rounded-full">Learning</span>
        </div>
        <div className="px-4 py-3 text-xs text-slate-500 flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-violet-400" />
          No patterns learned yet. Run simulations to build agent memory.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-violet-50 to-purple-50 border-b border-slate-200 flex items-center gap-2">
        <Brain className="w-4 h-4 text-violet-600" />
        <h4 className="text-sm font-semibold text-slate-800">Agent Memory</h4>
        <span className="ml-auto text-xs text-violet-500 bg-violet-100 px-2 py-0.5 rounded-full">
          Cross-Session Learning
        </span>
      </div>

      <div className="divide-y divide-slate-100">
        {/* Scenario Insights */}
        {hasScenarios && (
          <div className="px-4 py-3">
            <p className="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1.5">
              <TrendingUp className="w-3 h-3" />
              Learned Scenario Patterns
            </p>
            <div className="space-y-2">
              {Object.entries(insights.scenario_insights).map(([type, items]) => (
                <div key={type} className="bg-slate-50 rounded-lg p-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-700">
                      {SCENARIO_LABELS[type] || type}
                    </span>
                    <span className="text-xs text-slate-400">
                      {items.length} pattern{items.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  {items.slice(0, 2).map((item, i) => (
                    <div key={i} className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                      <span className="text-violet-600 font-mono">{item.frequency}x</span>
                      <span>avg +{item.semesters_added} sem</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        item.risk_level === 'high' ? 'bg-rose-50 text-rose-600' :
                        item.risk_level === 'medium' ? 'bg-amber-50 text-amber-600' :
                        'bg-emerald-50 text-emerald-600'
                      }`}>
                        {item.risk_level}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bottleneck Courses */}
        {hasBottlenecks && (
          <div className="px-4 py-3">
            <p className="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              Known Bottleneck Courses
            </p>
            <div className="flex flex-wrap gap-1.5">
              {insights.known_bottlenecks.map((b) => (
                <div
                  key={b.course}
                  className="bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5 text-xs"
                  title={`Seen ${b.frequency}x — delays ${b.cascading_delays} downstream courses: ${b.downstream_courses.join(', ')}`}
                >
                  <span className="font-mono font-semibold text-amber-700">{b.course}</span>
                  <span className="text-amber-500 ml-1.5">
                    {b.frequency}x · {b.cascading_delays} delays
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
