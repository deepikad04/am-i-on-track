import { Upload, GitBranch, FlaskConical, Bot, BarChart3, Swords, Layers } from 'lucide-react';

interface SidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
  hasDegreeParsed: boolean;
}

const sections = [
  { id: 'upload', label: 'Upload Degree', icon: Upload, requiresDegree: false },
  { id: 'map', label: 'Degree Map', icon: GitBranch, requiresDegree: true },
  { id: 'simulate', label: 'What-If Simulator', icon: FlaskConical, requiresDegree: true },
  { id: 'debate', label: 'Agent Debate', icon: Swords, requiresDegree: true },
  { id: 'overlap', label: 'Overlap Analysis', icon: Layers, requiresDegree: true },
  { id: 'impact', label: 'Impact Report', icon: BarChart3, requiresDegree: true },
  { id: 'agents', label: 'Agent Pipeline', icon: Bot, requiresDegree: false },
];

export default function Sidebar({ activeSection, onSectionChange, hasDegreeParsed }: SidebarProps) {
  return (
    <aside className="w-56 border-r border-violet-100/50 bg-white/80 backdrop-blur-md flex flex-col shrink-0">
      <nav className="flex-1 py-4">
        {sections.map((section) => {
          const disabled = section.requiresDegree && !hasDegreeParsed;
          const active = activeSection === section.id;
          return (
            <button
              key={section.id}
              onClick={() => !disabled && onSectionChange(section.id)}
              disabled={disabled}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors
                ${active
                  ? 'bg-violet-50 text-violet-700 border-r-2 border-violet-600'
                  : disabled
                    ? 'text-slate-300 cursor-not-allowed'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
            >
              <section.icon className="w-4 h-4" />
              {section.label}
            </button>
          );
        })}
      </nav>
      <div className="p-4 border-t border-slate-200 text-xs text-slate-400">
        Academic Trajectory Simulator
      </div>
    </aside>
  );
}
