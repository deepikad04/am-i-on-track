import { motion, AnimatePresence } from 'framer-motion';
import { X, MessageSquareText, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import type { SimulationResult } from '../../types/simulation';

interface ExplanationDrawerProps {
  open: boolean;
  onClose: () => void;
  explanation: string | null;
  result: SimulationResult | null;
}

export default function ExplanationDrawer({ open, onClose, explanation, result }: ExplanationDrawerProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed top-0 right-0 h-full w-[420px] bg-white shadow-2xl z-50 border-l border-slate-200 flex flex-col"
        >
          {/* Header */}
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquareText className="w-5 h-5 text-violet-600" />
              <h3 className="font-semibold text-slate-900">Impact Analysis</h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-slate-100 text-slate-400"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Constraint Checks */}
          {result && result.constraint_checks.length > 0 && (
            <div className="px-5 py-4 border-b border-slate-100">
              <h4 className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">
                Constraint Validation
              </h4>
              <div className="space-y-2">
                {result.constraint_checks.map((check, i) => {
                  const Icon = check.passed
                    ? CheckCircle2
                    : check.severity === 'error'
                      ? XCircle
                      : AlertTriangle;
                  const color = check.passed
                    ? 'text-emerald-600'
                    : check.severity === 'error'
                      ? 'text-rose-600'
                      : 'text-amber-600';

                  return (
                    <div key={i} className="flex items-start gap-2">
                      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${color}`} />
                      <div>
                        <div className="text-sm text-slate-700">{check.label}</div>
                        <div className="text-xs text-slate-500">{check.detail}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {result && result.recommendations.length > 0 && (
            <div className="px-5 py-4 border-b border-slate-100">
              <h4 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">
                Recommendations
              </h4>
              <ul className="space-y-1.5">
                {result.recommendations.map((rec, i) => (
                  <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                    <span className="text-violet-400 mt-0.5 shrink-0">{i + 1}.</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Explanation */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            <h4 className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">
              Plain English Explanation
            </h4>
            {explanation ? (
              <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {explanation}
              </div>
            ) : (
              <div className="text-sm text-slate-400 italic">
                No explanation available yet. Run a simulation to see the analysis.
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
