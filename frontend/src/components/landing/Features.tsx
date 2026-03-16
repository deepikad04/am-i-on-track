import { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileSearch,
  GitCompare,
  TrendingUp,
  MessageSquare,
  Upload,
  GitBranch,
  FlaskConical,
  Zap,
} from 'lucide-react';

interface FeaturesProps {
  onGetStarted: () => void;
}

function RevealOnScroll({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="transition-all duration-700 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(40px)',
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

const agents = [
  {
    icon: FileSearch,
    name: 'Degree Interpreter',
    desc: 'Upload any degree PDF. Nova extracts every course, prerequisite, and constraint into structured data via Tool Use.',
    color: 'violet',
    tag: 'Agent 1',
  },
  {
    icon: GitCompare,
    name: 'Overlap Analyzer',
    desc: 'Considering a double major? This agent finds shared courses, equivalent credits, and the fastest path to both degrees.',
    color: 'fuchsia',
    tag: 'Agent 2',
  },
  {
    icon: TrendingUp,
    name: 'Trajectory Simulator',
    desc: 'Drop a course, take a semester off, add a major — see every cascading effect before you commit.',
    color: 'cyan',
    tag: 'Agent 3',
  },
  {
    icon: MessageSquare,
    name: 'Explanation Agent',
    desc: 'No jargon. Every simulation result is translated into a clear, actionable explanation you can actually use.',
    color: 'teal',
    tag: 'Agent 4',
  },
];

const colorMap: Record<string, { bg: string; icon: string; border: string; tagBg: string }> = {
  violet: { bg: 'bg-violet-50', icon: 'text-violet-600', border: 'border-violet-200', tagBg: 'bg-violet-100 text-violet-700' },
  fuchsia: { bg: 'bg-fuchsia-50', icon: 'text-fuchsia-600', border: 'border-fuchsia-200', tagBg: 'bg-fuchsia-100 text-fuchsia-700' },
  cyan: { bg: 'bg-cyan-50', icon: 'text-cyan-600', border: 'border-cyan-200', tagBg: 'bg-cyan-100 text-cyan-700' },
  teal: { bg: 'bg-teal-50', icon: 'text-teal-600', border: 'border-teal-200', tagBg: 'bg-teal-100 text-teal-700' },
};

const steps = [
  { icon: Upload, title: 'Upload PDF', desc: 'Drag your degree requirements document' },
  { icon: GitBranch, title: 'See Your Map', desc: 'Interactive prerequisite graph renders instantly' },
  { icon: FlaskConical, title: 'Ask "What If?"', desc: 'Drop a course and watch the ripple effects' },
  { icon: Zap, title: 'Get Answers', desc: 'AI explains the impact in plain English' },
];

export default function Features({ onGetStarted }: FeaturesProps) {
  return (
    <div className="relative">
      {/* How It Works */}
      <section className="py-24 px-4 bg-white">
        <div className="max-w-5xl mx-auto">
          <RevealOnScroll>
            <div className="text-center mb-16">
              <span className="text-sm font-semibold text-violet-600 tracking-widest uppercase">How it works</span>
              <h2 className="text-4xl md:text-5xl font-black text-slate-900 mt-3 tracking-tight">
                Four steps. Zero guessing.
              </h2>
            </div>
          </RevealOnScroll>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {steps.map((step, i) => (
              <RevealOnScroll key={step.title} delay={i * 100}>
                <div className="text-center group">
                  <div className="relative mb-5">
                    <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-violet-600 to-fuchsia-500 flex items-center justify-center group-hover:scale-110 group-hover:rotate-6 transition-all shadow-lg shadow-violet-600/25 shimmer">
                      <step.icon className="w-7 h-7 text-white" />
                    </div>
                    <span className="absolute -top-2 -right-2 w-7 h-7 bg-fuchsia-500 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md">
                      {i + 1}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-1">{step.title}</h3>
                  <p className="text-sm text-slate-500">{step.desc}</p>
                </div>
              </RevealOnScroll>
            ))}
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-violet-200 to-transparent" />

      {/* 4 Agents */}
      <section className="py-24 px-4 bg-violet-50/30">
        <div className="max-w-6xl mx-auto">
          <RevealOnScroll>
            <div className="text-center mb-16">
              <span className="text-sm font-semibold text-fuchsia-600 tracking-widest uppercase">
                Multi-Agent Architecture
              </span>
              <h2 className="text-4xl md:text-5xl font-black text-slate-900 mt-3 tracking-tight">
                4 Nova agents. 1 orchestrator.
              </h2>
              <p className="text-lg text-slate-500 mt-4 max-w-2xl mx-auto">
                Not a chatbot wrapper — every agent drives real UI state changes with
                visible reasoning streamed in real time.
              </p>
            </div>
          </RevealOnScroll>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {agents.map((agent, i) => {
              const colors = colorMap[agent.color];
              return (
                <RevealOnScroll key={agent.name} delay={i * 80}>
                  <div
                    className={`${colors.bg} border ${colors.border} rounded-2xl p-6 hover:shadow-xl hover:shadow-violet-500/10 hover:-translate-y-1 transition-all duration-300 group glass`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`shrink-0 w-12 h-12 rounded-xl ${colors.bg} border ${colors.border} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                        <agent.icon className={`w-6 h-6 ${colors.icon}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-bold text-slate-900">{agent.name}</h3>
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${colors.tagBg}`}>
                            {agent.tag}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600 leading-relaxed">{agent.desc}</p>
                      </div>
                    </div>
                  </div>
                </RevealOnScroll>
              );
            })}
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-violet-200 to-transparent" />

      {/* Comparison banner */}
      <section className="py-20 px-4 bg-white">
        <RevealOnScroll>
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-6 bg-slate-50 rounded-2xl border border-slate-200 px-8 py-5 mb-8">
              <div className="text-left">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Degree Audits</div>
                <div className="text-lg text-slate-400 line-through">Track what you've done</div>
              </div>
              <div className="h-12 w-px bg-slate-200" />
              <div className="text-left">
                <div className="text-xs text-violet-600 font-semibold uppercase tracking-wider mb-1">Am I On Track?</div>
                <div className="text-lg font-bold text-slate-900">Simulate what happens next</div>
              </div>
            </div>
          </div>
        </RevealOnScroll>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 bg-gradient-to-b from-violet-950 to-slate-950 relative overflow-hidden">
        {/* Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-fuchsia-500/10 rounded-full blur-[100px]" />

        <RevealOnScroll>
          <div className="relative z-10 max-w-2xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-4">
              Stop guessing.<br />Start simulating.
            </h2>
            <p className="text-lg text-slate-400 mb-10">
              Upload your degree. Explore your options. Plan with confidence.
            </p>
            <button
              onClick={onGetStarted}
              className="bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 text-white font-bold text-lg px-10 py-4 rounded-2xl transition-all hover:scale-105 active:scale-95 shadow-xl shadow-violet-600/25 btn-glow shimmer"
            >
              Get Started — Free
            </button>
            <p className="text-xs text-slate-500 mt-4">
              No credit card required. Built for the Amazon Nova Hackathon.
            </p>
          </div>
        </RevealOnScroll>
      </section>
    </div>
  );
}
