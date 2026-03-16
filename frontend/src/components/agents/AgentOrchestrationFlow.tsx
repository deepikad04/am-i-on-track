import { motion } from 'framer-motion';
import { Brain, FileSearch, GitCompare, TrendingUp, MessageSquare, Shield, ArrowDown, ArrowRight, Gauge, Zap, ShieldCheck, Scale, BookOpen } from 'lucide-react';
import type { AgentStatus } from '../../types/agent';

interface AgentOrchestrationFlowProps {
  agents: AgentStatus[];
}

const agentConfig = [
  {
    name: 'interpreter' as const,
    icon: FileSearch,
    color: 'violet',
    label: 'Degree Interpreter',
    desc: 'PDF → Structured JSON via Tool Use',
    model: 'Nova 2 Lite',
    reasoning: 'Low',
  },
  {
    name: 'overlap' as const,
    icon: GitCompare,
    color: 'fuchsia',
    label: 'Overlap Analyzer',
    desc: 'Cross-degree credit matching',
    model: 'Nova 2 Lite + Embeddings',
    reasoning: 'Medium',
  },
  {
    name: 'simulator' as const,
    icon: TrendingUp,
    color: 'cyan',
    label: 'Trajectory Simulator',
    desc: 'Cascading what-if analysis',
    model: 'Dynamic: Lite ↔ Pro',
    reasoning: 'Complexity-routed',
  },
  {
    name: 'policy' as const,
    icon: Shield,
    color: 'amber',
    label: 'Policy Agent',
    desc: 'Self-correction compliance check',
    model: 'Dynamic: Lite ↔ Pro',
    reasoning: 'Complexity-routed',
  },
  {
    name: 'risk_scoring' as const,
    icon: Gauge,
    color: 'rose',
    label: 'Risk Scoring Agent',
    desc: 'Deterministic + memory feedback',
    model: 'No LLM + Agent Memory',
    reasoning: 'Learned',
  },
  {
    name: 'advisor' as const,
    icon: BookOpen,
    color: 'sky',
    label: 'Course Advisor',
    desc: 'Contextual course explanations',
    model: 'Nova ConverseStream',
    reasoning: 'Low',
  },
  {
    name: 'explanation' as const,
    icon: MessageSquare,
    color: 'teal',
    label: 'Explanation Agent',
    desc: 'Plain-English summaries',
    model: 'Nova 2 Lite',
    reasoning: 'Low',
  },
  {
    name: 'debate_fast' as const,
    icon: Zap,
    color: 'orange',
    label: 'Fast Track Advisor',
    desc: 'Aggressive graduation plan',
    model: 'Nova 2 Lite',
    reasoning: 'High',
  },
  {
    name: 'debate_safe' as const,
    icon: ShieldCheck,
    color: 'emerald',
    label: 'Safe Path Advisor',
    desc: 'Conservative GPA-protective plan',
    model: 'Nova 2 Lite',
    reasoning: 'High',
  },
  {
    name: 'jury' as const,
    icon: Scale,
    color: 'indigo',
    label: 'Jury Agent',
    desc: 'Synthesizes both proposals',
    model: 'Nova 2 Pro',
    reasoning: 'Medium',
  },
];

const colorMap: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  violet: { bg: 'bg-violet-50', border: 'border-violet-300', text: 'text-violet-700', glow: 'shadow-violet-200' },
  fuchsia: { bg: 'bg-fuchsia-50', border: 'border-fuchsia-300', text: 'text-fuchsia-700', glow: 'shadow-fuchsia-200' },
  cyan: { bg: 'bg-cyan-50', border: 'border-cyan-300', text: 'text-cyan-700', glow: 'shadow-cyan-200' },
  amber: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700', glow: 'shadow-amber-200' },
  teal: { bg: 'bg-teal-50', border: 'border-teal-300', text: 'text-teal-700', glow: 'shadow-teal-200' },
  rose: { bg: 'bg-rose-50', border: 'border-rose-300', text: 'text-rose-700', glow: 'shadow-rose-200' },
  orange: { bg: 'bg-orange-50', border: 'border-orange-300', text: 'text-orange-700', glow: 'shadow-orange-200' },
  emerald: { bg: 'bg-emerald-50', border: 'border-emerald-300', text: 'text-emerald-700', glow: 'shadow-emerald-200' },
  indigo: { bg: 'bg-indigo-50', border: 'border-indigo-300', text: 'text-indigo-700', glow: 'shadow-indigo-200' },
  sky: { bg: 'bg-sky-50', border: 'border-sky-300', text: 'text-sky-700', glow: 'shadow-sky-200' },
};

export default function AgentOrchestrationFlow({ agents }: AgentOrchestrationFlowProps) {
  return (
    <div className="space-y-6" role="region" aria-label="Multi-agent orchestration pipeline">
      {/* Orchestrator Header */}
      <div className="bg-gradient-to-r from-violet-600 to-fuchsia-500 rounded-xl p-5 text-white">
        <div className="flex items-center gap-3 mb-2">
          <Brain className="w-6 h-6" />
          <h3 className="text-lg font-bold">Multi-Agent Orchestrator</h3>
        </div>
        <p className="text-sm opacity-80">
          Supervisor pattern with complexity-based model routing, cross-session memory, and self-correction
        </p>
        <div className="flex gap-4 mt-3 text-xs opacity-70">
          <span>Complexity Router</span>
          <span>•</span>
          <span>Agent Memory</span>
          <span>•</span>
          <span>Parallel Execution</span>
          <span>•</span>
          <span>Tool Use</span>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-2 gap-4" role="list" aria-label="AI agents">
        {agentConfig.map((config, index) => {
          const agentStatus = agents.find((a) => a.name === config.name);
          const status = agentStatus?.status || 'idle';
          const colors = colorMap[config.color];
          const isRunning = status === 'running';
          const isComplete = status === 'complete';
          const Icon = config.icon;

          return (
            <motion.div
              key={config.name}
              role="listitem"
              aria-label={`${config.label}: ${status}`}
              aria-live={isRunning ? 'polite' : 'off'}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`rounded-xl border-2 p-4 transition-all ${colors.bg} ${colors.border}
                ${isRunning ? `shadow-lg ${colors.glow}` : ''}
                ${isComplete ? 'opacity-90' : ''}
              `}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-5 h-5 ${colors.text}`} />
                <h4 className={`font-semibold text-sm ${colors.text}`}>{config.label}</h4>
              </div>
              <p className="text-xs text-slate-600 mb-3">{config.desc}</p>

              <div className="flex justify-between text-[10px]">
                <span className="bg-white/60 px-1.5 py-0.5 rounded text-slate-600">
                  {config.model}
                </span>
                <span className="bg-white/60 px-1.5 py-0.5 rounded text-slate-600">
                  Reasoning: {config.reasoning}
                </span>
              </div>

              {/* Status indicator */}
              <div className="mt-3 flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  isRunning ? 'bg-violet-500 animate-pulse' :
                  isComplete ? 'bg-emerald-500' :
                  status === 'error' ? 'bg-rose-500' : 'bg-slate-300'
                }`} />
                <span className="text-xs text-slate-600 capitalize">{status}</span>
              </div>

              {/* Thinking Steps */}
              {agentStatus && agentStatus.steps.length > 0 && (
                <div className="mt-2 space-y-1 max-h-24 overflow-y-auto">
                  {agentStatus.steps.map((step) => (
                    <div key={step.step_number} className="text-[10px] text-slate-500 flex gap-1">
                      <span className={`font-mono ${colors.text}`}>{step.step_number}.</span>
                      <span>{step.thought}</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Architecture Notes */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
        <h4 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">
          What makes it truly agentic
        </h4>
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
          {[
            'Dynamic routing — orchestrator picks agents per scenario',
            'Parallel execution — overlap + simulation run concurrently',
            'Tool Use — structured, composable JSON output',
            'Visible reasoning — extended thinking streamed via SSE',
            'Shared state — agents communicate through state object',
            'Self-correction — policy violations feed back to simulator for re-planning',
          ].map((point, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className="text-violet-400 mt-0.5">•</span>
              <span>{point}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
