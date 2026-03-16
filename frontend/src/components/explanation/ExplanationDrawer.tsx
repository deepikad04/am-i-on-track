import { useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MessageSquareText, CheckCircle2, AlertTriangle, XCircle, TrendingDown, TrendingUp, Minus, Shield } from 'lucide-react';
import type { SimulationResult } from '../../types/simulation';

interface ExplanationDrawerProps {
  open: boolean;
  onClose: () => void;
  explanation: string | null;
  result: SimulationResult | null;
}

/** Highlight key terms in text: numbers, risk words, course codes, time references */
function highlightText(text: string): (string | JSX.Element)[] {
  // Pattern matches: numbers with units, course codes, risk/impact words, semester references
  const pattern = /(\b\d+[\.\d]*\s*(?:credits?|cr|semesters?|courses?|%|hours?|years?)\b)|(\b[A-Z]{2,5}\s?\d{3,4}[A-Z]?\b)|(\b(?:high risk|medium risk|low risk|critical|warning|violation|delayed|accelerated|on[- ]track|at[- ]risk)\b)|(\b(?:Spring|Fall|Summer|Winter)\s+\d{4}\b)/gi;

  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const matched = match[0];
    const isRisk = match[3] !== undefined;
    const isCourse = match[2] !== undefined;
    const isDate = match[4] !== undefined;

    let className = 'font-semibold text-violet-700 bg-violet-50 px-1 rounded';
    if (isRisk) {
      const lower = matched.toLowerCase();
      if (lower.includes('high') || lower.includes('critical') || lower.includes('violation') || lower.includes('delayed') || lower.includes('at')) {
        className = 'font-semibold text-rose-700 bg-rose-50 px-1 rounded';
      } else if (lower.includes('medium') || lower.includes('warning')) {
        className = 'font-semibold text-amber-700 bg-amber-50 px-1 rounded';
      } else {
        className = 'font-semibold text-emerald-700 bg-emerald-50 px-1 rounded';
      }
    } else if (isCourse) {
      className = 'font-mono font-semibold text-blue-700 bg-blue-50 px-1 rounded';
    } else if (isDate) {
      className = 'font-semibold text-slate-800 bg-slate-100 px-1 rounded';
    }

    parts.push(
      <span key={match.index} className={className}>{matched}</span>
    );
    lastIndex = match.index + matched.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

export default function ExplanationDrawer({ open, onClose, explanation, result }: ExplanationDrawerProps) {
  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  }, [onClose]);

  const riskConfig = {
    low: { color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', Icon: CheckCircle2 },
    medium: { color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', Icon: AlertTriangle },
    high: { color: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', Icon: XCircle },
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={handleBackdropClick}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-violet-100 flex items-center justify-center">
                  <MessageSquareText className="w-5 h-5 text-violet-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 text-lg">Full Analysis Report</h3>
                  <p className="text-xs text-slate-500">AI-generated impact analysis of your scenario</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto">
              {/* Impact summary banner */}
              {result && (
                <div className={`mx-6 mt-4 rounded-xl p-4 flex items-center gap-4 border ${
                  result.semesters_added > 0 ? 'bg-rose-50 border-rose-200' :
                  result.semesters_added < 0 ? 'bg-emerald-50 border-emerald-200' :
                  'bg-slate-50 border-slate-200'
                }`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    result.semesters_added > 0 ? 'bg-rose-100' :
                    result.semesters_added < 0 ? 'bg-emerald-100' :
                    'bg-slate-100'
                  }`}>
                    {result.semesters_added > 0 ? (
                      <TrendingDown className="w-5 h-5 text-rose-600" />
                    ) : result.semesters_added < 0 ? (
                      <TrendingUp className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <Minus className="w-5 h-5 text-slate-500" />
                    )}
                  </div>
                  <div>
                    <div className={`text-base font-semibold ${
                      result.semesters_added > 0 ? 'text-rose-800' :
                      result.semesters_added < 0 ? 'text-emerald-800' :
                      'text-slate-800'
                    }`}>
                      {result.semesters_added > 0
                        ? `Graduation delayed by ${result.semesters_added} semester${result.semesters_added > 1 ? 's' : ''}`
                        : result.semesters_added < 0
                          ? `Graduate ${Math.abs(result.semesters_added)} semester${Math.abs(result.semesters_added) > 1 ? 's' : ''} earlier!`
                          : 'No change to your graduation timeline'}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {result.original_graduation} → {result.new_graduation} · {result.affected_courses.length} courses affected · {Math.abs(result.credit_impact)} credit impact
                    </div>
                  </div>
                </div>
              )}

              {/* Risk badge */}
              {result && (
                <div className="mx-6 mt-3">
                  {(() => {
                    const rc = riskConfig[result.risk_level];
                    return (
                      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${rc.bg} ${rc.color} border ${rc.border}`}>
                        <rc.Icon className="w-4 h-4" />
                        {result.risk_level.toUpperCase()} RISK
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Constraint Checks */}
              {result && result.constraint_checks.length > 0 && (
                <div className="px-6 py-4">
                  <h4 className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wider flex items-center gap-2">
                    <Shield className="w-3.5 h-3.5" />
                    Constraint Validation
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {result.constraint_checks.map((check, i) => {
                      const Icon = check.passed
                        ? CheckCircle2
                        : check.severity === 'error'
                          ? XCircle
                          : AlertTriangle;
                      const colors = check.passed
                        ? 'bg-emerald-50 border-emerald-200'
                        : check.severity === 'error'
                          ? 'bg-rose-50 border-rose-200'
                          : 'bg-amber-50 border-amber-200';
                      const iconColor = check.passed
                        ? 'text-emerald-600'
                        : check.severity === 'error'
                          ? 'text-rose-600'
                          : 'text-amber-600';

                      return (
                        <div key={i} className={`flex items-start gap-2.5 rounded-lg border p-3 ${colors}`}>
                          <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconColor}`} />
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-slate-800">{check.label}</div>
                            <div className="text-xs text-slate-600 mt-0.5">{highlightText(check.detail)}</div>
                            {check.related_courses && check.related_courses.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {check.related_courses.map((code) => (
                                  <span key={code} className="text-[10px] font-mono font-medium px-1.5 py-0.5 bg-white/60 rounded text-slate-600">{code}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {result && result.recommendations.length > 0 && (
                <div className="px-6 py-4 border-t border-slate-100">
                  <h4 className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wider">
                    Recommendations
                  </h4>
                  <div className="space-y-2">
                    {result.recommendations.map((rec, i) => (
                      <div key={i} className="flex items-start gap-3 bg-violet-50/50 border border-violet-100 rounded-lg p-3">
                        <span className="w-5 h-5 rounded-full bg-violet-200 text-violet-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                        <span className="text-sm text-slate-700 leading-relaxed">{highlightText(rec)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Reasoning steps */}
              {result && result.reasoning_steps && result.reasoning_steps.length > 0 && (
                <div className="px-6 py-4 border-t border-slate-100">
                  <h4 className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wider">
                    Reasoning Steps
                  </h4>
                  <div className="space-y-1.5">
                    {result.reasoning_steps.map((step, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-slate-400 font-mono text-xs mt-0.5 shrink-0">{i + 1}.</span>
                        <span className="text-slate-700">{highlightText(step)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Plain English Explanation */}
              <div className="px-6 py-4 border-t border-slate-100">
                <h4 className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wider">
                  Plain English Explanation
                </h4>
                {explanation ? (
                  <div className="text-sm text-slate-700 leading-relaxed bg-slate-50 rounded-xl p-4">
                    {highlightText(explanation)}
                  </div>
                ) : (
                  <div className="text-sm text-slate-400 italic">
                    No explanation available yet. Run a simulation to see the analysis.
                  </div>
                )}
              </div>

              {/* Bottom padding */}
              <div className="h-4" />
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 shrink-0 flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
