import { motion, AnimatePresence } from 'framer-motion';
import { Brain, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import type { AgentStatus } from '../../types/agent';

interface AgentThinkingPanelProps {
  agents: AgentStatus[];
}

const statusIcon = {
  idle: <div className="w-5 h-5 rounded-full border-2 border-slate-300" />,
  running: <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />,
  complete: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
  error: <AlertCircle className="w-5 h-5 text-rose-500" />,
};

const statusColor = {
  idle: 'border-slate-200 bg-white',
  running: 'border-violet-300 bg-violet-50',
  complete: 'border-emerald-300 bg-emerald-50',
  error: 'border-rose-300 bg-rose-50',
};

export default function AgentThinkingPanel({ agents }: AgentThinkingPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <Brain className="w-4 h-4" />
        <span>Agent Pipeline</span>
      </div>

      <div className="space-y-2">
        {agents.map((agent) => (
          <motion.div
            key={agent.name}
            layout
            className={`rounded-lg border px-4 py-3 transition-colors ${statusColor[agent.status]}`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                {statusIcon[agent.status]}
                <span className="text-sm font-medium text-slate-800">
                  {agent.display_name}
                </span>
              </div>
              <span className="text-xs text-slate-500 capitalize">{agent.status}</span>
            </div>

            <AnimatePresence mode="wait">
              {agent.status === 'running' && agent.steps.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-2 space-y-1"
                >
                  {agent.steps.map((step, i) => (
                    <motion.div
                      key={step.step_number}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="flex items-start gap-2 text-xs text-slate-600"
                    >
                      <span className="text-violet-400 font-mono shrink-0">
                        {step.step_number}.
                      </span>
                      <span>{step.thought}</span>
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {agent.status === 'complete' && agent.steps.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-1 text-xs text-emerald-700"
                >
                  {agent.steps[agent.steps.length - 1]?.thought}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
