import { useMemo, useEffect, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import CourseNodeComponent from './CourseNode';
import SemesterLabel from './SemesterLabel';
import { getLayoutedElements, NODE_WIDTH } from '../../utils/graphLayout';
import type { CourseNode } from '../../types/degree';
import { statusColors, statusIcons, statusLabels } from '../../utils/colorScheme';

interface DegreePathMapProps {
  courseNodes: CourseNode[];
  onCourseSelect: (code: string) => void;
  selectedCourse: string | null;
  affectedCourses?: string[];
  panelOpen?: boolean;
}

const nodeTypes: NodeTypes = {
  course: CourseNodeComponent,
  semesterLabel: SemesterLabel,
};

function DegreePathMapInner({
  courseNodes,
  onCourseSelect,
  selectedCourse,
  affectedCourses = [],
  panelOpen = false,
}: DegreePathMapProps) {
  const { fitView } = useReactFlow();
  const prevPanelOpen = useRef(panelOpen);

  // Re-fit view when panel opens/closes
  useEffect(() => {
    if (prevPanelOpen.current !== panelOpen) {
      prevPanelOpen.current = panelOpen;
      const timer = setTimeout(() => fitView({ duration: 300 }), 280);
      return () => clearTimeout(timer);
    }
  }, [panelOpen, fitView]);

  const { nodes, edges } = useMemo(() => {
    const flowNodes: Node[] = courseNodes.map((cn) => ({
      id: cn.code,
      type: 'course',
      position: { x: 0, y: 0 },
      data: {
        ...cn,
        selected: cn.code === selectedCourse,
        onSelect: onCourseSelect,
      },
    }));

    const flowEdges: Edge[] = [];
    courseNodes.forEach((cn) => {
      cn.prerequisites.forEach((prereq) => {
        if (courseNodes.some((n) => n.code === prereq)) {
          const isAffected =
            affectedCourses.includes(cn.code) || affectedCourses.includes(prereq);
          flowEdges.push({
            id: `${prereq}-${cn.code}`,
            source: prereq,
            target: cn.code,
            animated: isAffected,
            style: {
              stroke: isAffected ? '#f43f5e' : '#cbd5e1',
              strokeWidth: isAffected ? 2.5 : 1.5,
            },
          });
        }
      });
    });

    const layouted = getLayoutedElements(flowNodes, flowEdges, 'LR');

    // Compute semester column positions from laid-out nodes
    const semesterXRanges = new Map<number, { minX: number; maxX: number; minY: number }>();
    layouted.nodes.forEach((node) => {
      const semester = (node.data as any)?.semester as number;
      if (!semester) return;
      const existing = semesterXRanges.get(semester);
      if (existing) {
        existing.minX = Math.min(existing.minX, node.position.x);
        existing.maxX = Math.max(existing.maxX, node.position.x + NODE_WIDTH);
        existing.minY = Math.min(existing.minY, node.position.y);
      } else {
        semesterXRanges.set(semester, {
          minX: node.position.x,
          maxX: node.position.x + NODE_WIDTH,
          minY: node.position.y,
        });
      }
    });

    // Use global minimum Y so all labels sit on the same horizontal line
    const globalMinY = Math.min(...Array.from(semesterXRanges.values()).map((r) => r.minY));

    // Add semester label nodes above each column
    const labelNodes: Node[] = Array.from(semesterXRanges.entries()).map(([sem, range]) => ({
      id: `sem-label-${sem}`,
      type: 'semesterLabel',
      position: { x: (range.minX + range.maxX) / 2 - 50, y: globalMinY - 40 },
      data: { label: `Semester ${sem}` },
      selectable: false,
      draggable: false,
      focusable: false,
    }));

    return {
      nodes: [...labelNodes, ...layouted.nodes],
      edges: layouted.edges,
    };
  }, [courseNodes, selectedCourse, onCourseSelect, affectedCourses]);

  // Count courses per status for legend
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    courseNodes.forEach((cn) => {
      counts[cn.status] = (counts[cn.status] || 0) + 1;
    });
    return counts;
  }, [courseNodes]);

  return (
    <div className="h-full relative" role="region" aria-label="Degree path dependency graph">
      {/* Enhanced Legend */}
      <div className="absolute top-3 left-3 z-10 bg-white/95 backdrop-blur-sm rounded-xl border border-slate-200 shadow-sm px-4 py-3">
        <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Status Legend</div>
        <div className="flex gap-4 text-xs">
          {Object.entries(statusColors).map(([status, colors]) => {
            const Icon = statusIcons[status as keyof typeof statusIcons];
            const count = statusCounts[status] || 0;
            if (count === 0) return null;
            return (
              <div key={status} className="flex items-center gap-1.5">
                <Icon className={`w-3.5 h-3.5 ${colors.text}`} />
                <span className="text-slate-600">
                  {statusLabels[status as keyof typeof statusLabels]}
                </span>
                <span className="text-slate-400">({count})</span>
              </div>
            );
          })}
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        fitView
        minZoom={0.3}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e2e8f0" gap={20} />
        <Controls className="!bg-white !border-slate-200 !shadow-sm" />
        <MiniMap
          nodeColor={(node) => {
            if (node.type === 'semesterLabel') return 'transparent';
            const status = (node.data as any)?.status || 'locked';
            const colors: Record<string, string> = {
              completed: '#10b981',
              scheduled: '#8b5cf6',
              elective: '#f59e0b',
              bottleneck: '#f43f5e',
              locked: '#9ca3af',
            };
            return colors[status] || '#9ca3af';
          }}
          className="!bg-white !border-slate-200"
        />
      </ReactFlow>
    </div>
  );
}

export default function DegreePathMap(props: DegreePathMapProps) {
  return (
    <ReactFlowProvider>
      <DegreePathMapInner {...props} />
    </ReactFlowProvider>
  );
}
