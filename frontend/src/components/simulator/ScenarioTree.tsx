import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  GitBranch,
  ChevronRight,
  GraduationCap,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  Eye,
  EyeOff,
} from 'lucide-react';
import { getSimulationHistory } from '../../services/api';
import type { SimulationHistoryItem } from '../../services/api';

interface ScenarioTreeProps {
  sessionId: string;
  currentGraduation?: string;
}

interface TreeNode {
  sim: SimulationHistoryItem;
  children: TreeNode[];
  depth: number;
}

const RISK_COLORS = {
  low: { bg: 'bg-emerald-50', border: 'border-emerald-300', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  medium: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700', dot: 'bg-amber-500' },
  high: { bg: 'bg-rose-50', border: 'border-rose-300', text: 'text-rose-700', dot: 'bg-rose-500' },
};

const SCENARIO_LABELS: Record<string, string> = {
  drop_course: 'Drop Course',
  block_semester: 'Block Semester',
  add_major: 'Add 2nd Major',
  add_minor: 'Add Minor',
  set_goal: 'Set Goal',
  study_abroad: 'Study Abroad',
  coop: 'Co-op',
  gap_semester: 'Gap Semester',
};

function buildTree(items: SimulationHistoryItem[]): TreeNode[] {
  const byId = new Map(items.map((item) => [item.id, item]));
  const childrenMap = new Map<string | null, SimulationHistoryItem[]>();

  for (const item of items) {
    const parentId = item.parent_simulation_id;
    if (!childrenMap.has(parentId)) childrenMap.set(parentId, []);
    childrenMap.get(parentId)!.push(item);
  }

  function build(parentId: string | null, depth: number): TreeNode[] {
    const children = childrenMap.get(parentId) || [];
    return children.map((sim) => ({
      sim,
      children: build(sim.id, depth + 1),
      depth,
    }));
  }

  return build(null, 0);
}

function flattenTree(nodes: TreeNode[]): TreeNode[] {
  const result: TreeNode[] = [];
  for (const node of nodes) {
    result.push(node);
    result.push(...flattenTree(node.children));
  }
  return result;
}

export default function ScenarioTree({ sessionId, currentGraduation }: ScenarioTreeProps) {
  const [history, setHistory] = useState<SimulationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [collapsedBranches, setCollapsedBranches] = useState<Set<string>>(new Set());
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    getSimulationHistory(sessionId)
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId]);

  const tree = useMemo(() => buildTree(history), [history]);
  const flatNodes = useMemo(() => flattenTree(tree), [tree]);

  const visibleNodes = useMemo(() => {
    const hidden = new Set<string>();
    function markHidden(nodes: TreeNode[]) {
      for (const node of nodes) {
        if (collapsedBranches.has(node.sim.id)) {
          // Hide all descendants
          function hideDescendants(children: TreeNode[]) {
            for (const child of children) {
              hidden.add(child.sim.id);
              hideDescendants(child.children);
            }
          }
          hideDescendants(node.children);
        }
        markHidden(node.children);
      }
    }
    markHidden(tree);
    return flatNodes.filter((n) => !hidden.has(n.sim.id));
  }, [flatNodes, tree, collapsedBranches]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleBranch = useCallback((id: string) => {
    setCollapsedBranches((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const togglePin = useCallback((id: string) => {
    setPinnedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 4) next.add(id);
      return next;
    });
  }, []);

  const pinned = history.filter((s) => pinnedIds.has(s.id));

  if (loading) return null;

  if (history.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <GitBranch className="w-4 h-4" />
          Run simulations to see your scenario tree here.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-violet-500" />
          Scenario Tree
          <span className="text-xs font-normal text-slate-400">({history.length} futures)</span>
        </h3>
      </div>

      {/* Pinned comparison strip */}
      {pinned.length >= 2 && (
        <div className="px-4 py-3 bg-violet-50 border-b border-violet-100">
          <div className="text-xs font-semibold text-violet-700 mb-2">Comparing {pinned.length} Scenarios</div>
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(pinned.length, 4)}, 1fr)` }}>
            {pinned.map((sim) => {
              const result = sim.result;
              const risk = (result?.risk_level as string) || 'low';
              const colors = RISK_COLORS[risk as keyof typeof RISK_COLORS] || RISK_COLORS.low;
              return (
                <div key={sim.id} className={`rounded-lg border ${colors.border} ${colors.bg} p-2`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-700 truncate">
                      {SCENARIO_LABELS[sim.scenario_type] || sim.scenario_type}
                    </span>
                    <span className={`text-[10px] font-bold uppercase ${colors.text}`}>{risk}</span>
                  </div>
                  <div className="text-xs text-slate-600 space-y-0.5">
                    <div className="flex justify-between">
                      <span>Grad</span>
                      <span className="font-medium">{String(result?.new_graduation || '?')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Delay</span>
                      <span className="font-medium">
                        {(result?.semesters_added as number) > 0 ? '+' : ''}
                        {String(result?.semesters_added || 0)} sem
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Courses</span>
                      <span className="font-medium">
                        {Array.isArray(result?.affected_courses) ? result.affected_courses.length : 0} affected
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tree body */}
      <div className="relative">
        {/* Current state node */}
        <div className="relative flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          <div className="relative z-10 w-5 h-5 rounded-full bg-violet-500 flex items-center justify-center ring-4 ring-violet-100">
            <GraduationCap className="w-3 h-3 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-800">Current Plan</div>
            <div className="text-xs text-slate-500">
              {currentGraduation ? `Graduation: ${currentGraduation}` : 'Baseline trajectory'}
            </div>
          </div>
        </div>

        {/* Tree branches */}
        {visibleNodes.map((node) => {
          const { sim, depth, children } = node;
          const result = sim.result;
          const risk = (result?.risk_level as string) || 'low';
          const colors = RISK_COLORS[risk as keyof typeof RISK_COLORS] || RISK_COLORS.low;
          const isExpanded = expandedIds.has(sim.id);
          const isPinned = pinnedIds.has(sim.id);
          const isBranchCollapsed = collapsedBranches.has(sim.id);
          const hasChildren = children.length > 0;
          const semAdded = (result?.semesters_added as number) || 0;
          const params = sim.parameters || {};

          const indentPx = 12 + depth * 24;

          return (
            <div key={sim.id} className={`relative border-b border-slate-50 ${isPinned ? 'bg-violet-50/30' : ''}`}>
              {/* Trunk line for this depth */}
              <div
                className="absolute top-0 bottom-0 w-px bg-slate-200"
                style={{ left: `${indentPx}px` }}
              />

              {/* Branch connector */}
              <div
                className="absolute top-0 w-4 h-5 border-b-2 border-l-2 border-slate-200 rounded-bl-lg"
                style={{ left: `${indentPx}px` }}
              />

              {/* Branch node */}
              <div style={{ paddingLeft: `${indentPx + 20}px` }} className="pr-4 py-3">
                <div className="flex items-center gap-2">
                  {/* Collapse/expand branch toggle for nodes with children */}
                  {hasChildren ? (
                    <button
                      onClick={() => toggleBranch(sim.id)}
                      className="w-4 h-4 flex items-center justify-center text-slate-400 hover:text-violet-600 transition-colors"
                      title={isBranchCollapsed ? 'Expand branch' : 'Collapse branch'}
                    >
                      <ChevronRight className={`w-3 h-3 transition-transform ${isBranchCollapsed ? '' : 'rotate-90'}`} />
                    </button>
                  ) : (
                    <div className="w-4" />
                  )}

                  {/* Risk dot */}
                  <div className={`w-2.5 h-2.5 rounded-full ${colors.dot} shrink-0`} />

                  {/* Title */}
                  <button
                    onClick={() => toggleExpand(sim.id)}
                    className="flex-1 flex items-center gap-2 text-left group"
                  >
                    <span className="text-sm font-medium text-slate-800 group-hover:text-violet-700 transition-colors">
                      {SCENARIO_LABELS[sim.scenario_type] || sim.scenario_type}
                    </span>
                    {params.course_code && (
                      <span className="text-xs font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {String(params.course_code)}
                      </span>
                    )}
                    {params.semester && (
                      <span className="text-xs text-slate-400">Sem {String(params.semester)}</span>
                    )}
                    {hasChildren && (
                      <span className="text-[10px] text-slate-400 bg-slate-100 px-1 rounded">
                        {children.length} branch{children.length !== 1 ? 'es' : ''}
                      </span>
                    )}
                  </button>

                  {/* Quick metrics */}
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-xs font-medium flex items-center gap-1 ${
                      semAdded > 0 ? 'text-rose-600' : semAdded < 0 ? 'text-emerald-600' : 'text-slate-500'
                    }`}>
                      {semAdded > 0 ? <TrendingDown className="w-3 h-3" /> : semAdded < 0 ? <TrendingUp className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                      {semAdded > 0 ? `+${semAdded}` : semAdded} sem
                    </span>
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                      {risk}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); togglePin(sim.id); }}
                      className={`p-1 rounded transition-colors ${isPinned ? 'text-violet-600 bg-violet-100' : 'text-slate-400 hover:text-violet-500'}`}
                      title={isPinned ? 'Unpin from comparison' : 'Pin to compare (max 4)'}
                    >
                      {isPinned ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded detail */}
                {isExpanded && result && (
                  <div className="mt-3 ml-5 space-y-3">
                    {/* Parent breadcrumb */}
                    {sim.parent_simulation_id && (
                      <div className="text-[10px] text-slate-400 flex items-center gap-1">
                        <GitBranch className="w-3 h-3" />
                        Branched from previous simulation
                      </div>
                    )}

                    {/* Impact summary */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="bg-slate-50 rounded-lg p-2 text-center">
                        <div className="text-[10px] text-slate-500 uppercase">Graduation</div>
                        <div className="text-sm font-bold text-slate-800">{String(result.new_graduation || '?')}</div>
                      </div>
                      <div className="bg-slate-50 rounded-lg p-2 text-center">
                        <div className="text-[10px] text-slate-500 uppercase">Courses Affected</div>
                        <div className="text-sm font-bold text-slate-800">
                          {Array.isArray(result.affected_courses) ? result.affected_courses.length : 0}
                        </div>
                      </div>
                      <div className="bg-slate-50 rounded-lg p-2 text-center">
                        <div className="text-[10px] text-slate-500 uppercase">Credit Impact</div>
                        <div className="text-sm font-bold text-slate-800">{String(result.credit_impact || 0)}</div>
                      </div>
                    </div>

                    {/* Constraint checks */}
                    {Array.isArray(result.constraint_checks) && result.constraint_checks.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-slate-600">Constraint Checks</div>
                        {(result.constraint_checks as { label: string; passed: boolean; severity: string; detail: string }[]).map((cc, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs">
                            {cc.passed ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                            ) : (
                              <AlertTriangle className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${cc.severity === 'error' ? 'text-rose-500' : 'text-amber-500'}`} />
                            )}
                            <div>
                              <span className="font-medium text-slate-700">{cc.label}</span>
                              <span className="text-slate-500 ml-1">— {cc.detail}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Recommendations */}
                    {Array.isArray(result.recommendations) && result.recommendations.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-slate-600">Recommendations</div>
                        <ul className="text-xs text-slate-600 space-y-0.5 list-disc list-inside">
                          {(result.recommendations as string[]).slice(0, 3).map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Affected courses table */}
                    {Array.isArray(result.affected_courses) && (result.affected_courses as { code: string; original_semester: number; new_semester: number; reason: string }[]).length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-slate-600">Affected Courses</div>
                        <div className="max-h-32 overflow-y-auto space-y-1">
                          {(result.affected_courses as { code: string; original_semester: number; new_semester: number; reason: string }[]).map((ac) => (
                            <div key={ac.code} className="flex items-center gap-2 text-xs">
                              <span className="font-mono font-medium text-slate-700 w-16">{ac.code}</span>
                              <span className="text-slate-400">Sem {ac.original_semester}</span>
                              <ChevronRight className="w-3 h-3 text-rose-400" />
                              <span className="text-rose-600 font-medium">Sem {ac.new_semester}</span>
                              <span className="text-slate-400 truncate flex-1" title={ac.reason}>{ac.reason}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Explanation */}
                    {sim.explanation && (
                      <div className="text-xs text-slate-600 bg-slate-50 rounded-lg p-3 leading-relaxed">
                        {sim.explanation.slice(0, 300)}
                        {sim.explanation.length > 300 && '...'}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Summary footer */}
        <div className="relative flex items-center gap-3 px-4 py-3 bg-slate-50">
          <div className="relative z-10 w-5 h-5 rounded-full bg-slate-300 flex items-center justify-center">
            <Clock className="w-3 h-3 text-white" />
          </div>
          <div className="text-xs text-slate-500">
            {history.length} scenario{history.length !== 1 ? 's' : ''} explored
            {pinned.length >= 2 && ` | ${pinned.length} pinned for comparison`}
          </div>
        </div>
      </div>
    </div>
  );
}
