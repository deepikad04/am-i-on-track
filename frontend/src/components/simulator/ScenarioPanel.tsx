import { useState, useCallback } from 'react';
import {
  FlaskConical,
  XCircle,
  CalendarOff,
  GraduationCap,
  Loader2,
  BookPlus,
  BookMarked,
  Globe,
  Briefcase,
  PauseCircle,
  Upload,
  CheckCircle2,
} from 'lucide-react';
import type { ScenarioType } from '../../types/simulation';
import type { CourseNode } from '../../types/degree';
import { uploadDegreePdf } from '../../services/api';

interface ScenarioPanelProps {
  courseNodes: CourseNode[];
  selectedCourse: string | null;
  onRunScenario: (type: ScenarioType, params: Record<string, unknown>) => void;
  running: boolean;
  onDegreeUploadParse?: (sessionId: string) => Promise<void>;
}

interface ParsedDegreeInfo {
  sessionId: string;
  degreeName: string;
}

export default function ScenarioPanel({
  courseNodes,
  selectedCourse,
  onRunScenario,
  running,
  onDegreeUploadParse,
}: ScenarioPanelProps) {
  const [scenarioType, setScenarioType] = useState<ScenarioType>('drop_course');
  const [selectedSemester, setSelectedSemester] = useState<number>(3);
  const [goalSemester, setGoalSemester] = useState<string>('Spring 2027');

  // Study abroad
  const [abroadCredits, setAbroadCredits] = useState<number>(12);

  // Co-op
  const [coopDuration, setCoopDuration] = useState<number>(1);

  // Add major/minor - inline PDF upload
  const [degreeUploading, setDegreeUploading] = useState(false);
  const [degreeUploadError, setDegreeUploadError] = useState<string | null>(null);
  const [parsedDegree, setParsedDegree] = useState<ParsedDegreeInfo | null>(null);
  const [degreeParsing, setDegreeParsing] = useState(false);

  const scenarios: { type: ScenarioType; label: string; icon: typeof FlaskConical; description: string }[] = [
    {
      type: 'drop_course',
      label: 'Drop a Course',
      icon: XCircle,
      description: 'See what happens if you drop a specific course',
    },
    {
      type: 'block_semester',
      label: 'Block Semester',
      icon: CalendarOff,
      description: 'Simulate taking a semester off',
    },
    {
      type: 'set_goal',
      label: 'Set Graduation Goal',
      icon: GraduationCap,
      description: 'Check if a target graduation date is feasible',
    },
    {
      type: 'add_major',
      label: 'Add 2nd Major',
      icon: BookPlus,
      description: 'Upload a second degree and see combined plan',
    },
    {
      type: 'add_minor',
      label: 'Add Minor',
      icon: BookMarked,
      description: 'Upload a minor program and merge it in',
    },
    {
      type: 'study_abroad',
      label: 'Study Abroad',
      icon: Globe,
      description: 'Block a semester for study abroad with transfer credits',
    },
    {
      type: 'coop',
      label: 'Co-op',
      icon: Briefcase,
      description: 'Block 1-2 semesters for a co-op experience',
    },
    {
      type: 'gap_semester',
      label: 'Gap Semester',
      icon: PauseCircle,
      description: 'Take a semester off with no courses',
    },
  ];

  const handleDegreeFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setDegreeUploading(true);
    setDegreeUploadError(null);
    setParsedDegree(null);

    try {
      const { session_id } = await uploadDegreePdf(file);
      setDegreeParsing(true);
      setDegreeUploading(false);

      if (onDegreeUploadParse) {
        await onDegreeUploadParse(session_id);
      }

      // Fetch the degree name from the parsed data (retry once if not yet committed)
      const token = localStorage.getItem('token');
      const fetchDegree = async () => {
        const res = await fetch(`/api/degree/${session_id}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        return res.json();
      };
      let data = await fetchDegree();
      if (!data.degree) {
        await new Promise((r) => setTimeout(r, 1500));
        data = await fetchDegree();
      }
      if (!data.degree) {
        throw new Error('Degree parsing failed. Please try uploading again.');
      }
      setParsedDegree({
        sessionId: session_id,
        degreeName: data.degree.degree_name || 'Uploaded Degree',
      });
    } catch (err) {
      setDegreeUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setDegreeUploading(false);
      setDegreeParsing(false);
    }
  }, [onDegreeUploadParse]);

  const handleRun = () => {
    let params: Record<string, unknown> = {};
    switch (scenarioType) {
      case 'drop_course':
        if (!selectedCourse) return;
        params = { course_code: selectedCourse };
        break;
      case 'block_semester':
        params = { semester: selectedSemester };
        break;
      case 'set_goal':
        params = { target_semester: goalSemester };
        break;
      case 'add_major':
      case 'add_minor':
        if (!parsedDegree) return;
        params = { degree_session_id: parsedDegree.sessionId };
        break;
      case 'study_abroad':
        params = { semester: selectedSemester, credits_earned: abroadCredits };
        break;
      case 'coop':
        params = { semester: selectedSemester, duration: coopDuration };
        break;
      case 'gap_semester':
        params = { semester: selectedSemester };
        break;
    }
    onRunScenario(scenarioType, params);
  };

  const canRun = () => {
    if (running) return false;
    if (scenarioType === 'drop_course' && !selectedCourse) return false;
    if ((scenarioType === 'add_major' || scenarioType === 'add_minor') && !parsedDegree) return false;
    if (degreeUploading || degreeParsing) return false;
    return true;
  };

  const needsDegreeUpload = scenarioType === 'add_major' || scenarioType === 'add_minor';
  const needsSemesterPicker = ['block_semester', 'study_abroad', 'coop', 'gap_semester'].includes(scenarioType);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <FlaskConical className="w-4 h-4 text-violet-500" />
        What-If Scenarios
      </h3>

      <div className="space-y-2 mb-5 max-h-64 overflow-y-auto pr-1" role="radiogroup" aria-label="Scenario type selection">
        {scenarios.map((s) => (
          <button
            key={s.type}
            role="radio"
            aria-checked={scenarioType === s.type}
            aria-label={`${s.label}: ${s.description}`}
            onClick={() => {
              setScenarioType(s.type);
              if (s.type !== 'add_major' && s.type !== 'add_minor') {
                setParsedDegree(null);
                setDegreeUploadError(null);
              }
            }}
            className={`w-full flex items-start gap-3 px-3 py-2 rounded-lg text-left transition-colors
              ${scenarioType === s.type
                ? 'bg-violet-50 border border-violet-300'
                : 'bg-slate-50 border border-transparent hover:bg-slate-100'
              }`}
          >
            <s.icon className={`w-4 h-4 mt-0.5 shrink-0 ${scenarioType === s.type ? 'text-violet-600' : 'text-slate-400'}`} />
            <div>
              <div className={`text-sm font-medium ${scenarioType === s.type ? 'text-violet-800' : 'text-slate-700'}`}>
                {s.label}
              </div>
              <div className="text-xs text-slate-500">{s.description}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Scenario-specific inputs */}
      <div className="mb-5 space-y-3">
        {scenarioType === 'drop_course' && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Selected Course</label>
            {selectedCourse ? (
              <div className="bg-violet-50 border border-violet-200 rounded-lg px-3 py-2 text-sm font-mono text-violet-800">
                {selectedCourse}
                <span className="text-violet-500 text-xs ml-2">
                  (click a course on the map to change)
                </span>
              </div>
            ) : (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-700">
                Click a course on the degree map to select it
              </div>
            )}
          </div>
        )}

        {needsSemesterPicker && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              {scenarioType === 'study_abroad' ? 'Semester Abroad' :
               scenarioType === 'coop' ? 'Co-op Start Semester' :
               scenarioType === 'gap_semester' ? 'Gap Semester' :
               'Semester to Block'}
            </label>
            <select
              value={selectedSemester}
              onChange={(e) => setSelectedSemester(Number(e.target.value))}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              {Array.from({ length: 8 }, (_, i) => i + 1).map((sem) => (
                <option key={sem} value={sem}>
                  Semester {sem} ({sem % 2 === 1 ? 'Fall' : 'Spring'})
                </option>
              ))}
            </select>
          </div>
        )}

        {scenarioType === 'study_abroad' && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Transfer Credits Earned</label>
            <input
              type="number"
              value={abroadCredits}
              onChange={(e) => setAbroadCredits(Math.max(0, Math.min(24, Number(e.target.value))))}
              min={0}
              max={24}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-slate-400 mt-1">Credits that transfer back toward your degree</p>
          </div>
        )}

        {scenarioType === 'coop' && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Duration</label>
            <select
              value={coopDuration}
              onChange={(e) => setCoopDuration(Number(e.target.value))}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value={1}>1 Semester</option>
              <option value={2}>2 Semesters</option>
            </select>
          </div>
        )}

        {scenarioType === 'set_goal' && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Target Graduation</label>
            <select
              value={goalSemester}
              onChange={(e) => setGoalSemester(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              {['Spring 2026', 'Fall 2026', 'Spring 2027', 'Fall 2027', 'Spring 2028'].map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>
        )}

        {needsDegreeUpload && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              {scenarioType === 'add_major' ? '2nd Major' : 'Minor'} Requirements PDF
            </label>
            {parsedDegree ? (
              <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-emerald-800 truncate">{parsedDegree.degreeName}</div>
                  <div className="text-xs text-emerald-600">Parsed successfully</div>
                </div>
                <button
                  onClick={() => { setParsedDegree(null); setDegreeUploadError(null); }}
                  className="text-xs text-emerald-600 hover:text-emerald-800 underline"
                >
                  Change
                </button>
              </div>
            ) : (
              <label className={`flex items-center justify-center gap-2 border-2 border-dashed rounded-lg px-3 py-4 cursor-pointer transition-colors
                ${degreeUploading || degreeParsing
                  ? 'border-violet-300 bg-violet-50/50 cursor-wait'
                  : 'border-slate-300 hover:border-violet-400 hover:bg-violet-50/30'}`}
              >
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleDegreeFileUpload}
                  disabled={degreeUploading || degreeParsing}
                  className="hidden"
                />
                {degreeUploading || degreeParsing ? (
                  <>
                    <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />
                    <span className="text-sm text-violet-600">
                      {degreeParsing ? 'Parsing degree...' : 'Uploading...'}
                    </span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 text-slate-400" />
                    <span className="text-sm text-slate-500">Upload PDF</span>
                  </>
                )}
              </label>
            )}
            {degreeUploadError && (
              <p className="text-xs text-red-600 mt-1">{degreeUploadError}</p>
            )}
          </div>
        )}
      </div>

      <button
        onClick={handleRun}
        disabled={!canRun()}
        aria-label={running ? 'Simulation in progress' : `Run ${scenarioType.replace('_', ' ')} simulation`}
        aria-busy={running}
        className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 disabled:opacity-40 disabled:from-slate-400 disabled:to-slate-400 text-white font-medium py-2.5 rounded-lg transition-all flex items-center justify-center gap-2"
      >
        {running ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Running Simulation...
          </>
        ) : (
          <>
            <FlaskConical className="w-4 h-4" />
            Run Simulation
          </>
        )}
      </button>
    </div>
  );
}
