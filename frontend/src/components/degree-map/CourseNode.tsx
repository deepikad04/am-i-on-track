import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { CourseStatus } from '../../types/degree';
import { statusColors, statusIcons } from '../../utils/colorScheme';

interface CourseNodeData {
  code: string;
  name: string;
  credits: number;
  status: CourseStatus;
  semester: number;
  dependents_count: number;
  category: string;
  prerequisites: string[];
  selected?: boolean;
  onSelect?: (code: string) => void;
}

function CourseNodeComponent({ data }: { data: CourseNodeData }) {
  const colors = statusColors[data.status];
  const StatusIcon = statusIcons[data.status];

  return (
    <>
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-slate-400" />
      <div
        role="button"
        tabIndex={0}
        aria-label={`${data.code} ${data.name}, ${data.credits} credits, ${data.status}, semester ${data.semester}${data.selected ? ', selected' : ''}`}
        aria-pressed={data.selected}
        onClick={() => data.onSelect?.(data.code)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); data.onSelect?.(data.code); } }}
        className={`rounded-lg border border-slate-200 border-l-4 ${colors.borderLeft} px-3 py-2.5 w-[220px] cursor-pointer transition-all bg-white shadow-sm
          ${data.selected ? 'ring-2 ring-violet-500 ring-offset-2 shadow-lg scale-105' : 'hover:shadow-md'}
        `}
      >
        {/* Top row: code + semester badge */}
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1.5">
            <StatusIcon className={`w-3.5 h-3.5 ${colors.text}`} />
            <span className={`text-xs font-bold font-mono ${colors.text}`}>
              {data.code}
            </span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500 font-medium">
            Sem {data.semester}
          </span>
        </div>

        {/* Course name */}
        <div className="text-xs text-slate-700 truncate font-medium" title={data.name}>
          {data.name}
        </div>

        {/* Bottom row: category + credits + prereqs/dependents */}
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[10px] text-slate-400 truncate max-w-[100px]" title={data.category}>
            {data.category}
          </span>
          <div className="flex items-center gap-1.5">
            {data.prerequisites?.length > 0 && (
              <span className="text-[10px] text-slate-400">
                {data.prerequisites.length} prereq{data.prerequisites.length > 1 ? 's' : ''}
              </span>
            )}
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full text-white ${colors.badge}`}>
              {data.credits} cr
            </span>
          </div>
        </div>

        {data.dependents_count > 0 && (
          <div className="text-[10px] text-violet-500 mt-1 font-medium">
            Unlocks {data.dependents_count} course{data.dependents_count > 1 ? 's' : ''}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-slate-400" />
    </>
  );
}

export default memo(CourseNodeComponent);
