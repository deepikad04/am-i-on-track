import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import { AnimatePresence } from 'framer-motion';
import MainLayout from './components/layout/MainLayout';
import PdfUploader from './components/upload/PdfUploader';
import AgentThinkingPanel from './components/upload/AgentThinkingPanel';
import ParsedPreview from './components/upload/ParsedPreview';
import ProgressSelector from './components/upload/ProgressSelector';
import { AlertCircle } from 'lucide-react';
import { checkHealth, explainCourse, getSimilarCourses, updateProgress } from './services/api';
import type { SimilarCourse } from './services/api';

// Lazy-loaded heavy sections
const AuthPage = lazy(() => import('./components/auth/AuthPage'));
const LandingPage = lazy(() => import('./components/landing/LandingPage'));
const DegreePathMap = lazy(() => import('./components/degree-map/DegreePathMap'));
const CourseDetailPanel = lazy(() => import('./components/degree-map/CourseDetailPanel'));
const ScenarioPanel = lazy(() => import('./components/simulator/ScenarioPanel'));
const TimelineCompare = lazy(() => import('./components/simulator/TimelineCompare'));
const ScenarioHistory = lazy(() => import('./components/simulator/ScenarioHistory'));
const ScenarioTree = lazy(() => import('./components/simulator/ScenarioTree'));
const DebatePanel = lazy(() => import('./components/simulator/DebatePanel'));
const OverlapPanel = lazy(() => import('./components/overlap/OverlapPanel'));
const ExplanationDrawer = lazy(() => import('./components/explanation/ExplanationDrawer'));
const AgentOrchestrationFlow = lazy(() => import('./components/agents/AgentOrchestrationFlow'));
const ImpactReportPanel = lazy(() => import('./components/impact/ImpactReportPanel'));
import { useAgentStream } from './hooks/useAgentStream';
import { useDegreeData } from './hooks/useDegreeData';
import { useSimulation } from './hooks/useSimulation';
import { useAuth } from './contexts/AuthContext';
import type { ScenarioType } from './types/simulation';

interface CachedExplanation {
  text: string;
  isError: boolean;
}

const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center bg-slate-50">
    <div className="animate-spin w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full" />
  </div>
);

function App() {
  const { user, loading: authLoading } = useAuth();
  const [showAuth, setShowAuth] = useState(false);

  if (authLoading) {
    return <LoadingSpinner />;
  }

  if (!user && !showAuth) {
    return (
      <Suspense fallback={<LoadingSpinner />}>
        <LandingPage onGetStarted={() => setShowAuth(true)} />
      </Suspense>
    );
  }

  if (!user) {
    return (
      <Suspense fallback={<LoadingSpinner />}>
        <AuthPage onBack={() => setShowAuth(false)} />
      </Suspense>
    );
  }

  return <AppContent />;
}

function AppContent() {
  const [activeSection, setActiveSection] = useState('upload');
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [similarCourses, setSimilarCourses] = useState<SimilarCourse[] | null>(null);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [scenarioParsing, setScenarioParsing] = useState(false);
  const [progressSet, setProgressSet] = useState(false);

  // Cache explanations in state so updates trigger re-renders
  const [explanationCache, setExplanationCache] = useState<Record<string, CachedExplanation>>({});
  const explanationCacheRef = useRef(explanationCache);
  explanationCacheRef.current = explanationCache;
  const abortRef = useRef<AbortController | null>(null);

  const { agents, handleEvent, streamParse, streamParseUrl } = useAgentStream();
  const degreeState = useDegreeData();
  const simulation = useSimulation();

  useEffect(() => {
    checkHealth()
      .then((data) => setConnected(data.bedrock_connected))
      .catch(() => setConnected(false));
  }, []);

  // Fetch similar courses via Nova Embed when a course is selected
  useEffect(() => {
    if (!sessionId || !selectedCourse || !connected) {
      setSimilarCourses(null);
      return;
    }
    let cancelled = false;
    setSimilarLoading(true);
    getSimilarCourses(sessionId, selectedCourse)
      .then((results) => {
        if (!cancelled) setSimilarCourses(results);
      })
      .catch(() => {
        if (!cancelled) setSimilarCourses(null);
      })
      .finally(() => {
        if (!cancelled) setSimilarLoading(false);
      });
    return () => { cancelled = true; };
  }, [sessionId, selectedCourse, connected]);

  const handleUploadComplete = useCallback(
    async (sid: string) => {
      setSessionId(sid);
      setParsing(true);
      setUploadError(null);
      try {
        await streamParse(sid);
        const result = await degreeState.fetchDegree(sid);
        if (!result?.degree) {
          console.warn('[handleUploadComplete] degree null on first fetch, retrying...');
          await new Promise(r => setTimeout(r, 1500));
          await degreeState.fetchDegree(sid);
        }
      } catch (err) {
        console.error('[handleUploadComplete]', err);
        setUploadError(err instanceof Error ? err.message : 'Upload processing failed');
      } finally {
        setParsing(false);
      }
    },
    [streamParse, degreeState],
  );

  const handleUrlUploadComplete = useCallback(
    async (sid: string) => {
      setSessionId(sid);
      setParsing(true);
      setUploadError(null);
      try {
        await streamParseUrl(sid);
        const result = await degreeState.fetchDegree(sid);
        if (!result?.degree) {
          console.warn('[handleUrlUploadComplete] degree null on first fetch, retrying...');
          await new Promise(r => setTimeout(r, 1500));
          await degreeState.fetchDegree(sid);
        }
      } catch (err) {
        console.error('[handleUrlUploadComplete]', err);
        setUploadError(err instanceof Error ? err.message : 'URL processing failed');
      } finally {
        setParsing(false);
      }
    },
    [streamParseUrl, degreeState],
  );

  const handleUseSample = useCallback(async () => {
    setSessionId('demo_session');
    await degreeState.fetchDegree('demo_session');
  }, [degreeState]);

  const handleProgressConfirm = useCallback(
    async (currentSemester: number, completedCourses: string[]) => {
      if (!sessionId) return;
      await updateProgress(sessionId, completedCourses, currentSemester);
      await degreeState.fetchDegree(sessionId);
      setProgressSet(true);
      setActiveSection('map');
    },
    [sessionId, degreeState],
  );

  const handleProceedToMap = useCallback(() => {
    setActiveSection('map');
  }, []);

  const handleRunScenario = useCallback(
    (type: ScenarioType, params: Record<string, unknown>) => {
      if (!sessionId || !degreeState.degreeId) return;
      simulation.runSimulation(
        {
          type,
          parameters: params,
          session_id: sessionId,
          degree_id: degreeState.degreeId,
        },
        handleEvent,
      );
    },
    [sessionId, degreeState.degreeId, simulation, handleEvent],
  );

  const handleScenarioDegreeUploadParse = useCallback(
    async (sid: string) => {
      setScenarioParsing(true);
      try {
        await streamParse(sid);
      } finally {
        setScenarioParsing(false);
      }
    },
    [streamParse],
  );

  const handleAskNova = useCallback(async () => {
    if (!sessionId || !selectedCourse) return;
    // Skip if already cached successfully (read from ref to avoid dep churn)
    const cached = explanationCacheRef.current[selectedCourse];
    if (cached && !cached.isError) return;
    // Clear any previous error for this course
    if (cached?.isError) {
      setExplanationCache((prev) => {
        const next = { ...prev };
        delete next[selectedCourse];
        return next;
      });
    }
    // Abort any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setExplanationLoading(true);
    // Capture course code so the streaming callback targets the right key
    const courseCode = selectedCourse;
    try {
      const explanation = await explainCourse(
        sessionId,
        courseCode,
        controller.signal,
        (progressText) => {
          // Stream partial text into cache so the panel updates live
          setExplanationCache((prev) => ({
            ...prev,
            [courseCode]: { text: progressText, isError: false },
          }));
        },
      );
      setExplanationCache((prev) => ({
        ...prev,
        [courseCode]: { text: explanation, isError: false },
      }));
      setExplanationLoading(false);
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        // Don't clear loading — a new request may already be in-flight
        return;
      }
      setExplanationCache((prev) => ({
        ...prev,
        [courseCode]: {
          text: 'Unable to get explanation at this time.',
          isError: true,
        },
      }));
      setExplanationLoading(false);
    }
  }, [sessionId, selectedCourse]);

  const hasDegreeParsed = degreeState.degree !== null;
  const affectedCodes = simulation.result?.affected_courses.map((ac) => ac.code) || [];

  const selectedCourseNode = selectedCourse
    ? degreeState.courseNodes.find((cn) => cn.code === selectedCourse) || null
    : null;

  const currentCached = selectedCourse ? explanationCache[selectedCourse] || null : null;

  return (
    <MainLayout
      activeSection={activeSection}
      onSectionChange={setActiveSection}
      hasDegreeParsed={hasDegreeParsed}
      connected={connected}
    >
      <Suspense fallback={null}>
      {/* Upload Section */}
      {activeSection === 'upload' && (
        <div className="max-w-2xl mx-auto space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">
              Upload Degree Requirements
            </h2>
            <p className="text-slate-500">
              Upload your degree requirement PDF and let our AI agents parse it into a
              structured plan.
            </p>
          </div>

          {!hasDegreeParsed && !parsing && (
            <PdfUploader
              onUploadComplete={handleUploadComplete}
              onUrlUploadComplete={handleUrlUploadComplete}
              onUseSample={handleUseSample}
            />
          )}

          {parsing && <AgentThinkingPanel agents={agents} />}

          {uploadError && !parsing && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-lg px-4 py-3">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          {hasDegreeParsed && degreeState.degree && !progressSet && (
            <>
              <ParsedPreview degree={degreeState.degree} />
              <ProgressSelector
                degree={degreeState.degree}
                onConfirm={handleProgressConfirm}
              />
            </>
          )}

          {hasDegreeParsed && degreeState.degree && progressSet && (
            <div className="text-center space-y-3">
              <p className="text-sm text-emerald-600 font-medium">
                Progress saved — {degreeState.completedCourses.length} courses completed, semester {degreeState.currentSemester}
              </p>
              <button
                onClick={handleProceedToMap}
                className="bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 text-white font-medium py-2.5 px-8 rounded-lg transition-all"
              >
                View Degree Map
              </button>
            </div>
          )}
        </div>
      )}

      {/* Degree Map Section */}
      {activeSection === 'map' && hasDegreeParsed && (
        <div className="h-full flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Degree Path Map</h2>
              <p className="text-sm text-slate-500">
                {degreeState.degree?.degree_name} — {degreeState.courseNodes.length} courses
                {selectedCourse ? '' : ' · Click a course for details'}
              </p>
            </div>
          </div>
          <div className="flex-1 flex bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="flex-1">
              <DegreePathMap
                courseNodes={degreeState.courseNodes}
                onCourseSelect={setSelectedCourse}
                selectedCourse={selectedCourse}
                affectedCourses={affectedCodes}
                panelOpen={!!selectedCourseNode}
              />
            </div>
            <AnimatePresence mode="wait">
              {selectedCourseNode && (
                <CourseDetailPanel
                  key="detail-panel"
                  course={selectedCourseNode}
                  allCourses={degreeState.courseNodes}
                  onClose={() => setSelectedCourse(null)}
                  onAskNova={handleAskNova}
                  explanation={currentCached?.text || null}
                  explanationError={currentCached?.isError || false}
                  explanationLoading={explanationLoading && selectedCourse !== null}
                  connected={connected}
                  similarCourses={similarCourses}
                  similarLoading={similarLoading}
                  onCourseSelect={setSelectedCourse}
                />
              )}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Simulator Section */}
      {activeSection === 'simulate' && hasDegreeParsed && (
        <div className="grid grid-cols-3 gap-6 h-full">
          {/* Left: Degree Map */}
          <div className="col-span-2 flex flex-col">
            <h2 className="text-2xl font-bold text-slate-900 mb-1">What-If Simulator</h2>
            <p className="text-sm text-slate-500 mb-3">
              See the impact of your academic decisions before you make them.
            </p>
            <div className="flex-1 bg-white rounded-xl border border-slate-200 overflow-hidden">
              <DegreePathMap
                courseNodes={degreeState.courseNodes}
                onCourseSelect={setSelectedCourse}
                selectedCourse={selectedCourse}
                affectedCourses={affectedCodes}
              />
            </div>
          </div>

          {/* Right: Controls & Results */}
          <div className="space-y-4 overflow-y-auto">
            <ScenarioPanel
              courseNodes={degreeState.courseNodes}
              selectedCourse={selectedCourse}
              onRunScenario={handleRunScenario}
              running={simulation.running}
              onDegreeUploadParse={handleScenarioDegreeUploadParse}
            />

            {(simulation.running || scenarioParsing) && <AgentThinkingPanel agents={agents} />}

            {simulation.error && !simulation.running && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-lg px-4 py-3 border border-red-200">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{simulation.error}</span>
              </div>
            )}

            {simulation.result && (
              <>
                <TimelineCompare result={simulation.result} />
                <button
                  onClick={() => setDrawerOpen(true)}
                  className="w-full bg-violet-50 hover:bg-violet-100 text-violet-700 font-medium py-2 rounded-lg transition-colors text-sm"
                >
                  View Full Analysis
                </button>
              </>
            )}

            {sessionId && <ScenarioTree sessionId={sessionId} />}
            {sessionId && <ScenarioHistory sessionId={sessionId} />}
          </div>
        </div>
      )}

      {/* Agent Debate Section */}
      {activeSection === 'debate' && hasDegreeParsed && sessionId && (
        <div className="max-w-3xl mx-auto">
          <DebatePanel sessionId={sessionId} />
        </div>
      )}

      {/* Overlap Analysis Section */}
      {activeSection === 'overlap' && hasDegreeParsed && sessionId && (
        <div className="max-w-2xl mx-auto">
          <OverlapPanel sessionId={sessionId} onDegreeUploadParse={handleScenarioDegreeUploadParse} />
        </div>
      )}

      {/* Impact Report Section */}
      {activeSection === 'impact' && hasDegreeParsed && sessionId && (
        <div className="max-w-2xl mx-auto">
          <ImpactReportPanel sessionId={sessionId} />
        </div>
      )}

      {/* Agent Pipeline Section */}
      {activeSection === 'agents' && (
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Agent Pipeline</h2>
          <p className="text-slate-500 mb-6">
            Watch Nova agents reason about your academic plan in real time.
          </p>
          <AgentOrchestrationFlow agents={agents} />
        </div>
      )}

      {/* Explanation Drawer */}
      <ExplanationDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        explanation={simulation.explanation}
        result={simulation.result}
      />
      </Suspense>
    </MainLayout>
  );
}

export default App;
