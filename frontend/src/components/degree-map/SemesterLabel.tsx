import { memo } from 'react';

function SemesterLabelComponent({ data }: { data: { label: string } }) {
  return (
    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap select-none pointer-events-none">
      {data.label}
    </div>
  );
}

export default memo(SemesterLabelComponent);
