import { ArrowRight, TrendingUp, TrendingDown, Minus, Layers } from 'lucide-react';
import type { SimulationResult } from '../../types/simulation';

interface TimelineCompareProps {
  result: SimulationResult;
}

export default function TimelineCompare({ result }: TimelineCompareProps) {
  const comparison = result.plan_comparison;
  const riskColor = {
    low: 'text-emerald-600 bg-emerald-50',
    medium: 'text-amber-600 bg-amber-50',
    high: 'text-rose-600 bg-rose-50',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">Plan Comparison</h3>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${riskColor[result.risk_level]}`}>
          {result.risk_level.toUpperCase()} RISK
        </span>
      </div>

      {/* Impact Banner */}
      <div className={`px-5 py-3 ${result.semesters_added > 0 ? 'bg-rose-50' : 'bg-emerald-50'}`}>
        <div className="flex items-center gap-2">
          {result.semesters_added > 0 ? (
            <TrendingDown className="w-5 h-5 text-rose-500" />
          ) : result.semesters_added < 0 ? (
            <TrendingUp className="w-5 h-5 text-emerald-500" />
          ) : (
            <Minus className="w-5 h-5 text-slate-400" />
          )}
          <span className={`text-sm font-medium ${result.semesters_added > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
            {result.semesters_added > 0
              ? `+${result.semesters_added} semester${result.semesters_added > 1 ? 's' : ''} to graduation`
              : result.semesters_added < 0
                ? `${result.semesters_added} semester${result.semesters_added < -1 ? 's' : ''} (faster graduation!)`
                : 'No change to graduation timeline'}
          </span>
        </div>
      </div>

      {/* Comparison Table */}
      {comparison && (
        <div className="divide-y divide-slate-100">
          {[
            { label: 'Graduation Date', before: comparison.graduation_date[0], after: comparison.graduation_date[1] },
            { label: 'Avg Credits/Term', before: comparison.avg_credits_per_term[0].toFixed(1), after: comparison.avg_credits_per_term[1].toFixed(1) },
            { label: 'Risk Level', before: comparison.risk_level[0], after: comparison.risk_level[1] },
            { label: 'Summer Reliance', before: comparison.summer_reliance[0], after: comparison.summer_reliance[1] },
            { label: 'GPA Protection', before: `${comparison.gpa_protection_score[0]}/100`, after: `${comparison.gpa_protection_score[1]}/100` },
          ].map((row) => (
            <div key={row.label} className="px-5 py-2.5 flex items-center text-sm">
              <div className="w-36 text-slate-500 text-xs">{row.label}</div>
              <div className="flex-1 text-slate-700 font-medium">{row.before}</div>
              <ArrowRight className="w-4 h-4 text-slate-300 mx-3" />
              <div className={`flex-1 font-medium ${row.before !== row.after ? 'text-violet-700' : 'text-slate-700'}`}>
                {row.after}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Overlap Analysis (for add_major/add_minor) */}
      {result.overlap && (
        <div className="px-5 py-3 border-t border-slate-200">
          <h4 className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-violet-500" />
            Overlap Analysis
          </h4>
          <div className="grid grid-cols-3 gap-2 mb-2">
            <div className="bg-violet-50 rounded-lg p-2 text-center">
              <div className="text-xs text-violet-600">Shared Courses</div>
              <div className="text-lg font-bold text-violet-900">{result.overlap.exact_matches?.length || 0}</div>
            </div>
            <div className="bg-emerald-50 rounded-lg p-2 text-center">
              <div className="text-xs text-emerald-600">Credits Saved</div>
              <div className="text-lg font-bold text-emerald-900">{result.overlap.total_shared_credits || 0}</div>
            </div>
            <div className="bg-amber-50 rounded-lg p-2 text-center">
              <div className="text-xs text-amber-600">Extra Semesters</div>
              <div className="text-lg font-bold text-amber-900">{result.overlap.additional_semesters_estimate ?? '—'}</div>
            </div>
          </div>
          {result.overlap.exact_matches && result.overlap.exact_matches.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {result.overlap.exact_matches.map((m) => (
                <span key={m.code} className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded-full">
                  {m.code} ({m.credits}cr)
                </span>
              ))}
            </div>
          )}
          {result.overlap.recommendations && result.overlap.recommendations.length > 0 && (
            <ul className="text-xs text-slate-600 space-y-0.5 list-disc list-inside">
              {result.overlap.recommendations.slice(0, 3).map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Affected Courses */}
      {result.affected_courses.length > 0 && (
        <div className="px-5 py-3 border-t border-slate-200">
          <h4 className="text-xs font-semibold text-slate-600 mb-2">
            Affected Courses ({result.affected_courses.length})
          </h4>
          <div className="space-y-1.5 max-h-40 overflow-y-auto">
            {result.affected_courses.map((ac) => (
              <div key={ac.code} className="flex items-center gap-2 text-xs">
                <span className="font-mono font-medium text-slate-700 w-16">{ac.code}</span>
                <span className="text-slate-400">Sem {ac.original_semester}</span>
                <ArrowRight className="w-3 h-3 text-rose-400" />
                <span className="text-rose-600 font-medium">Sem {ac.new_semester}</span>
                <span className="text-slate-400 truncate flex-1" title={ac.reason}>
                  {ac.reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
