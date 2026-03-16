import { useState, useCallback } from 'react';
import { Layers, Loader2, AlertCircle, Upload, CheckCircle2, BookOpen, Clock, TrendingUp, GraduationCap } from 'lucide-react';
import { runOverlapAnalysis, uploadDegreePdf } from '../../services/api';

interface OverlapPanelProps {
  sessionId: string;
  onDegreeUploadParse?: (sessionId: string) => Promise<void>;
}

interface ParsedDegreeInfo {
  sessionId: string;
  degreeName: string;
}

export default function OverlapPanel({ sessionId, onDegreeUploadParse }: OverlapPanelProps) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [explanation, setExplanation] = useState('');
  const [error, setError] = useState<string | null>(null);

  // PDF upload state
  const [degreeUploading, setDegreeUploading] = useState(false);
  const [degreeParsing, setDegreeParsing] = useState(false);
  const [degreeUploadError, setDegreeUploadError] = useState<string | null>(null);
  const [parsedDegree, setParsedDegree] = useState<ParsedDegreeInfo | null>(null);

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

  const handleAnalyze = async () => {
    if (!parsedDegree) return;
    setRunning(true);
    setResult(null);
    setExplanation('');
    setError(null);
    try {
      const data = await runOverlapAnalysis(sessionId, parsedDegree.sessionId, (event) => {
        if (event.event_type === 'complete' && event.data) {
          const d = event.data as Record<string, unknown>;
          if (d.explanation) setExplanation(d.explanation as string);
        }
      });
      setResult(data);
    } catch {
      setError('Overlap analysis failed. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  const exactMatches = result && Array.isArray(result.exact_matches)
    ? (result.exact_matches as { code: string; name: string; credits: number }[])
    : [];
  const equivalents = result && Array.isArray(result.equivalent_courses)
    ? (result.equivalent_courses as { degree1_code: string; degree2_code: string; name: string; credits: number; similarity_reason?: string }[])
    : [];
  const totalSharedCredits = result?.total_shared_credits as number | undefined;
  const additionalSemesters = result?.additional_semesters_estimate as number | undefined;
  const additionalCourses = result && Array.isArray(result.additional_courses_needed)
    ? (result.additional_courses_needed as { code: string; name: string; credits: number; from_degree: string }[])
    : [];
  const sharedPrereqs = result && Array.isArray(result.shared_prerequisites)
    ? (result.shared_prerequisites as string[])
    : [];
  const recommendations = result && Array.isArray(result.recommendations)
    ? (result.recommendations as string[])
    : [];

  // Derived numerical insights
  const totalAdditionalCredits = additionalCourses.reduce((sum, c) => sum + (c.credits || 3), 0);
  const totalOverlappingCourses = exactMatches.length + equivalents.length;
  const avgCreditsPerExtraSemester = additionalSemesters && additionalSemesters > 0
    ? (totalAdditionalCredits / additionalSemesters).toFixed(1)
    : null;
  const creditEfficiency = totalSharedCredits && totalAdditionalCredits
    ? Math.round((totalSharedCredits / (totalSharedCredits + totalAdditionalCredits)) * 100)
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Overlap Analysis</h2>
        <p className="text-sm text-slate-500">
          Upload a second degree plan to find shared courses and double-major feasibility.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-violet-600" />
          <h3 className="text-sm font-semibold text-slate-800">Cross-Degree Comparison</h3>
        </div>

        {/* Second degree upload */}
        <div>
          <label className="text-xs text-slate-500 font-medium block mb-1">
            Second Degree Requirements PDF
          </label>
          {parsedDegree ? (
            <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-emerald-800 truncate">{parsedDegree.degreeName}</div>
                <div className="text-xs text-emerald-600">Parsed successfully</div>
              </div>
              <button
                onClick={() => { setParsedDegree(null); setDegreeUploadError(null); setResult(null); }}
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

        {/* Analyze button */}
        <button
          onClick={handleAnalyze}
          disabled={running || !parsedDegree || degreeUploading || degreeParsing}
          className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 disabled:opacity-40 disabled:from-slate-400 disabled:to-slate-400 text-white font-medium py-2.5 rounded-lg transition-all flex items-center justify-center gap-2"
        >
          {running ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing Overlap...
            </>
          ) : (
            <>
              <Layers className="w-4 h-4" />
              Run Overlap Analysis
            </>
          )}
        </button>

        {error && (
          <div className="flex items-start gap-2 text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {running && (
          <div className="flex items-center justify-center py-8 text-sm text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Nova is analyzing course overlap…
          </div>
        )}

        {result && (
          <div className="space-y-4 pt-2 border-t border-slate-100">
            {/* Key metrics grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-violet-50 rounded-lg p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <Layers className="w-3.5 h-3.5 text-violet-500" />
                  <div className="text-xs text-violet-600 font-medium">Overlapping Courses</div>
                </div>
                <div className="text-2xl font-bold text-violet-900">{totalOverlappingCourses}</div>
                <div className="text-[11px] text-violet-500">{exactMatches.length} exact + {equivalents.length} equivalent</div>
              </div>
              <div className="bg-emerald-50 rounded-lg p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
                  <div className="text-xs text-emerald-600 font-medium">Credits You Save</div>
                </div>
                <div className="text-2xl font-bold text-emerald-900">{totalSharedCredits ?? 0}</div>
                {creditEfficiency !== null && (
                  <div className="text-[11px] text-emerald-500">{creditEfficiency}% credit efficiency</div>
                )}
              </div>
              <div className="bg-amber-50 rounded-lg p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <Clock className="w-3.5 h-3.5 text-amber-500" />
                  <div className="text-xs text-amber-600 font-medium">Extra Semesters</div>
                </div>
                <div className="text-2xl font-bold text-amber-900">{additionalSemesters ?? '—'}</div>
                {avgCreditsPerExtraSemester && (
                  <div className="text-[11px] text-amber-500">~{avgCreditsPerExtraSemester} credits/semester</div>
                )}
              </div>
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <BookOpen className="w-3.5 h-3.5 text-blue-500" />
                  <div className="text-xs text-blue-600 font-medium">Additional Courses</div>
                </div>
                <div className="text-2xl font-bold text-blue-900">{additionalCourses.length}</div>
                <div className="text-[11px] text-blue-500">{totalAdditionalCredits} credits to complete</div>
              </div>
            </div>

            {/* Academic load summary banner */}
            {additionalSemesters !== undefined && (
              <div className={`rounded-lg p-3 flex items-center gap-3 ${
                additionalSemesters <= 1 ? 'bg-emerald-50 border border-emerald-200' :
                additionalSemesters <= 2 ? 'bg-amber-50 border border-amber-200' :
                'bg-rose-50 border border-rose-200'
              }`}>
                <GraduationCap className={`w-5 h-5 shrink-0 ${
                  additionalSemesters <= 1 ? 'text-emerald-600' :
                  additionalSemesters <= 2 ? 'text-amber-600' :
                  'text-rose-600'
                }`} />
                <div>
                  <div className={`text-sm font-semibold ${
                    additionalSemesters <= 1 ? 'text-emerald-800' :
                    additionalSemesters <= 2 ? 'text-amber-800' :
                    'text-rose-800'
                  }`}>
                    {additionalSemesters === 0
                      ? 'Dual degree with no extra time — highly feasible!'
                      : additionalSemesters === 1
                        ? 'Just 1 extra semester — very manageable workload'
                        : `${additionalSemesters} extra semesters — plan carefully to stay on track`}
                  </div>
                  <div className={`text-xs ${
                    additionalSemesters <= 1 ? 'text-emerald-600' :
                    additionalSemesters <= 2 ? 'text-amber-600' :
                    'text-rose-600'
                  }`}>
                    {totalAdditionalCredits} additional credits needed · {totalSharedCredits ?? 0} credits shared between programs
                  </div>
                </div>
              </div>
            )}

            {/* Exact matches */}
            {exactMatches.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Exact Course Matches</div>
                <div className="flex flex-wrap gap-1.5">
                  {exactMatches.map((c) => (
                    <span key={c.code} className="text-xs px-2 py-1 bg-violet-100 text-violet-800 rounded-full font-medium">
                      {c.code} — {c.name} ({c.credits} cr)
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Equivalent courses */}
            {equivalents.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Equivalent Courses</div>
                <div className="space-y-1">
                  {equivalents.map((eq) => (
                    <div key={`${eq.degree1_code}-${eq.degree2_code}`} className="text-xs text-slate-700 bg-slate-50 rounded-lg px-3 py-1.5 flex items-center justify-between">
                      <span><span className="font-medium">{eq.degree1_code}</span> ↔ <span className="font-medium">{eq.degree2_code}</span> — {eq.name} ({eq.credits} cr)</span>
                      {eq.similarity_reason && (
                        <span className="text-[10px] text-slate-400 ml-2 shrink-0">{eq.similarity_reason}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Additional courses needed */}
            {additionalCourses.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Additional Courses Needed</div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {additionalCourses.map((c) => (
                    <div key={c.code} className="text-xs bg-blue-50 rounded-lg px-3 py-1.5 flex items-center justify-between">
                      <span className="text-blue-800"><span className="font-medium">{c.code}</span> — {c.name} ({c.credits} cr)</span>
                      <span className="text-[10px] text-blue-500 shrink-0 ml-2">Degree {c.from_degree}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Shared prerequisites */}
            {sharedPrereqs.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Shared Prerequisites</div>
                <div className="flex flex-wrap gap-1.5">
                  {sharedPrereqs.map((code) => (
                    <span key={code} className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded-full">{code}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {recommendations.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Recommendations</div>
                <ul className="text-xs text-slate-700 space-y-1.5">
                  {recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 bg-slate-50 rounded-lg px-3 py-2">
                      <span className="text-violet-500 font-semibold shrink-0">{i + 1}.</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Detailed analysis */}
            {explanation && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Detailed Analysis</div>
                <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap bg-slate-50 rounded-lg px-3 py-2">{explanation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
