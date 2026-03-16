import { useEffect, useState } from 'react';
import { TrendingUp, DollarSign, Clock, AlertTriangle, CheckCircle, Shield, Download, Image as ImageIcon } from 'lucide-react';
import { getImpactReport, getPolicyCheck, getAdvisingSummary, generateRoadmapImage } from '../../services/api';
import type { ImpactMetrics, PolicyCheckResult } from '../../services/api';
import AgentMemoryPanel from './AgentMemoryPanel';

interface ImpactReportPanelProps {
  sessionId: string;
}

export default function ImpactReportPanel({ sessionId }: ImpactReportPanelProps) {
  const [metrics, setMetrics] = useState<ImpactMetrics | null>(null);
  const [policy, setPolicy] = useState<PolicyCheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [generatingRoadmap, setGeneratingRoadmap] = useState(false);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);

  const [policyLoading, setPolicyLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setPolicyLoading(true);
    // Load metrics first (fast, no LLM) — show UI immediately
    getImpactReport(sessionId)
      .then((m) => setMetrics(m))
      .catch(() => {})
      .finally(() => setLoading(false));
    // Load policy check in background (slow, Nova LLM call)
    getPolicyCheck(sessionId)
      .then((p) => setPolicy(p))
      .catch(() => {})
      .finally(() => setPolicyLoading(false));
  }, [sessionId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const summary = await getAdvisingSummary(sessionId);
      const blob = new Blob([summary], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'advising-summary.txt';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent fail
    } finally {
      setExporting(false);
    }
  };

  const handleGenerateRoadmap = async () => {
    setGeneratingRoadmap(true);
    setRoadmapError(null);
    try {
      const blob = await generateRoadmapImage(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'degree-roadmap.svg';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setRoadmapError(err instanceof Error ? err.message : 'Roadmap generation failed. Please try again.');
    } finally {
      setGeneratingRoadmap(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse">
        <div className="h-4 bg-slate-200 rounded w-1/3 mb-4" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 bg-slate-100 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) return null;

  const riskColor = {
    low: 'text-emerald-600 bg-emerald-50 border-emerald-200',
    medium: 'text-amber-600 bg-amber-50 border-amber-200',
    high: 'text-rose-600 bg-rose-50 border-rose-200',
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Impact Report</h3>
          <p className="text-xs text-slate-500">Quantified outcomes for your academic plan</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerateRoadmap}
            disabled={generatingRoadmap}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
          >
            <ImageIcon className="w-3.5 h-3.5" />
            {generatingRoadmap ? 'Generating...' : 'Roadmap Image'}
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-violet-50 text-violet-700 rounded-lg hover:bg-violet-100 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            {exporting ? 'Exporting...' : 'Export Summary'}
          </button>
        </div>
      </div>
      {roadmapError && (
        <div className="flex items-center gap-2 text-red-600 text-xs bg-red-50 rounded-lg px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          {roadmapError}
        </div>
      )}

      {/* Progress Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">Degree Completion</span>
          <span className="text-sm font-bold text-violet-600">{metrics.completion_percentage}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2.5">
          <div
            className="bg-gradient-to-r from-violet-500 to-violet-600 h-2.5 rounded-full transition-all"
            style={{ width: `${metrics.completion_percentage}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-slate-400">
          <span>{metrics.completed_credits} credits done</span>
          <span>{metrics.remaining_credits} remaining</span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          icon={<TrendingUp className="w-4 h-4 text-emerald-500" />}
          label="Semesters Saved"
          value={String(metrics.semesters_saved)}
          detail="vs. unoptimized plan"
          accent="emerald"
        />
        <MetricCard
          icon={<DollarSign className="w-4 h-4 text-blue-500" />}
          label="Tuition Saved"
          value={`$${metrics.estimated_tuition_saved.toLocaleString()}`}
          detail="estimated savings"
          accent="blue"
        />
        <MetricCard
          icon={<Clock className="w-4 h-4 text-violet-500" />}
          label="Advisor Hours Saved"
          value={`${metrics.advisor_hours_saved}h`}
          detail="manual advising replaced"
          accent="violet"
        />
        <MetricCard
          icon={
            metrics.on_track
              ? <CheckCircle className="w-4 h-4 text-emerald-500" />
              : <AlertTriangle className="w-4 h-4 text-amber-500" />
          }
          label="Status"
          value={metrics.on_track ? 'On Track' : 'At Risk'}
          detail={`${metrics.estimated_semesters_remaining} semesters left`}
          accent={metrics.on_track ? 'emerald' : 'amber'}
        />
      </div>

      {/* Risk & Credits */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Risk Level</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${riskColor[metrics.risk_level]}`}>
            {metrics.risk_level.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Avg Credits/Semester</span>
          <span className="text-sm font-medium text-slate-800">{metrics.credits_per_semester_avg}</span>
        </div>
        {metrics.bottleneck_courses.length > 0 && (
          <div>
            <span className="text-xs font-medium text-slate-500 block mb-1">Bottleneck Courses</span>
            <div className="flex flex-wrap gap-1">
              {metrics.bottleneck_courses.map((code) => (
                <span key={code} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded font-mono">
                  {code}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Policy Check */}
      {policyLoading && !policy && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
            <Shield className="w-4 h-4 text-slate-600" />
            <h4 className="text-sm font-semibold text-slate-800">Policy Agent</h4>
            <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
              <span className="w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
              Analyzing...
            </span>
          </div>
          <div className="px-4 py-3">
            <div className="h-3 bg-slate-100 rounded w-2/3 animate-pulse" />
          </div>
        </div>
      )}
      {policy && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
            <Shield className="w-4 h-4 text-slate-600" />
            <h4 className="text-sm font-semibold text-slate-800">Policy Agent</h4>
            {policy.passed ? (
              <span className="ml-auto text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                ALL PASSED
              </span>
            ) : (
              <span className="ml-auto text-xs font-medium text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full">
                {policy.violations.filter((v) => v.severity === 'error').length} ISSUE(S)
              </span>
            )}
          </div>
          {policy.violations.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {policy.violations.map((v, i) => (
                <div key={i} className="px-4 py-2.5">
                  <div className="flex items-center gap-2 mb-0.5">
                    {v.severity === 'error' ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    )}
                    <span className="text-xs font-semibold text-slate-700">{v.rule}</span>
                  </div>
                  <p className="text-xs text-slate-500 ml-5.5">{v.detail}</p>
                  {v.suggestion && (
                    <p className="text-xs text-violet-600 ml-5.5 mt-0.5">{v.suggestion}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4 py-3 text-xs text-emerald-600 flex items-center gap-2">
              <CheckCircle className="w-3.5 h-3.5" />
              All university policies satisfied. Your plan is compliant.
            </div>
          )}
        </div>
      )}

      {/* Agent Memory — Cross-Session Learning Insights */}
      <AgentMemoryPanel />
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  accent: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <div className="text-lg font-bold text-slate-900">{value}</div>
      <div className="text-xs text-slate-400">{detail}</div>
    </div>
  );
}
