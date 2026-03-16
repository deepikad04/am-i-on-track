import { useState, useCallback } from 'react';
import { Layers, Loader2, AlertCircle, Upload, CheckCircle2 } from 'lucide-react';
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
    ? (result.equivalent_courses as { degree1_code: string; degree2_code: string; name: string; credits: number }[])
    : [];
  const totalSharedCredits = result?.total_shared_credits as number | undefined;
  const additionalSemesters = result?.additional_semesters_estimate as number | undefined;
  const recommendations = result && Array.isArray(result.recommendations)
    ? (result.recommendations as string[])
    : [];

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
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-violet-50 rounded-lg p-3">
                <div className="text-xs text-violet-600 font-medium">Exact Matches</div>
                <div className="text-lg font-bold text-violet-900">{exactMatches.length}</div>
              </div>
              <div className="bg-emerald-50 rounded-lg p-3">
                <div className="text-xs text-emerald-600 font-medium">Shared Credits</div>
                <div className="text-lg font-bold text-emerald-900">{totalSharedCredits ?? '—'}</div>
              </div>
              <div className="bg-amber-50 rounded-lg p-3">
                <div className="text-xs text-amber-600 font-medium">Extra Semesters</div>
                <div className="text-lg font-bold text-amber-900">{additionalSemesters ?? '—'}</div>
              </div>
            </div>

            {exactMatches.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Exact Course Matches</div>
                <div className="flex flex-wrap gap-1.5">
                  {exactMatches.map((c) => (
                    <span key={c.code} className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded-full">
                      {c.code} — {c.name} ({c.credits} cr)
                    </span>
                  ))}
                </div>
              </div>
            )}

            {equivalents.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Equivalent Courses</div>
                <div className="space-y-1">
                  {equivalents.map((eq) => (
                    <div key={`${eq.degree1_code}-${eq.degree2_code}`} className="text-xs text-slate-700 bg-slate-50 rounded-lg px-2 py-1">
                      {eq.degree1_code} ↔ {eq.degree2_code} — {eq.name} ({eq.credits} cr)
                    </div>
                  ))}
                </div>
              </div>
            )}

            {recommendations.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Recommendations</div>
                <ul className="text-xs text-slate-700 space-y-1 list-disc list-inside">
                  {recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}

            {explanation && (
              <div>
                <div className="text-xs font-medium text-slate-600 mb-1.5">Analysis</div>
                <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{explanation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
