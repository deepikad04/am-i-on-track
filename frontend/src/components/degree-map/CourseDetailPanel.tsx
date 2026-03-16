import { X, BookOpen, ArrowRight, Loader2, Sparkles, WifiOff, RefreshCw, Layers } from 'lucide-react';
import { motion } from 'framer-motion';
import type { CourseNode } from '../../types/degree';
import { statusColors, statusIcons, statusLabels } from '../../utils/colorScheme';
import type { SimilarCourse } from '../../services/api';

interface CourseDetailPanelProps {
  course: CourseNode;
  allCourses: CourseNode[];
  onClose: () => void;
  onAskNova: () => void;
  explanation: string | null;
  explanationError: boolean;
  explanationLoading: boolean;
  connected: boolean;
  similarCourses?: SimilarCourse[] | null;
  similarLoading?: boolean;
  onCourseSelect?: (code: string) => void;
}

export default function CourseDetailPanel({
  course,
  allCourses,
  onClose,
  onAskNova,
  explanation,
  explanationError,
  explanationLoading,
  connected,
  similarCourses,
  similarLoading,
  onCourseSelect,
}: CourseDetailPanelProps) {
  const colors = statusColors[course.status];
  const StatusIcon = statusIcons[course.status];

  const prereqCourses = allCourses.filter((c) => course.prerequisites.includes(c.code));
  const dependentCourses = allCourses.filter((c) => c.prerequisites.includes(course.code));

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 360, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className="border-l border-slate-200 bg-white flex flex-col h-full overflow-hidden"
    >
      {/* Header */}
      <div className={`px-5 py-4 border-b border-slate-200 ${colors.bg}`}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <StatusIcon className={`w-4 h-4 ${colors.text} shrink-0`} />
              <span className={`text-sm font-bold font-mono ${colors.text}`}>{course.code}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full text-white ${colors.badge}`}>
                {statusLabels[course.status]}
              </span>
            </div>
            <h3 className="text-base font-semibold text-slate-900 leading-tight">{course.name}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-200/50 rounded-md transition-colors shrink-0 ml-2"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      </div>

      {/* Content — fades on course switch */}
      <div key={course.code} className="flex-1 overflow-y-auto px-5 py-4 space-y-5 min-w-[360px] animate-fade-in">
        {/* Quick Info */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-50 rounded-lg px-3 py-2 text-center">
            <div className="text-lg font-bold text-slate-800">{course.credits}</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Credits</div>
          </div>
          <div className="bg-slate-50 rounded-lg px-3 py-2 text-center">
            <div className="text-lg font-bold text-slate-800">{course.semester}</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Semester</div>
          </div>
          <div className="bg-slate-50 rounded-lg px-3 py-2 text-center">
            <div className="text-lg font-bold text-slate-800">{course.dependents_count}</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Unlocks</div>
          </div>
        </div>

        {/* Category */}
        <div>
          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Category</div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-sm text-slate-700">{course.category}</span>
            {!course.is_required && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700">Optional</span>
            )}
          </div>
        </div>

        {/* Prerequisites */}
        {prereqCourses.length > 0 && (
          <div>
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Prerequisites ({prereqCourses.length})
            </div>
            <div className="space-y-1.5">
              {prereqCourses.map((p) => {
                const pColors = statusColors[p.status];
                return (
                  <div key={p.code} className="flex items-center gap-2 text-sm">
                    <div className={`w-2 h-2 rounded-full ${pColors.badge}`} />
                    <span className="font-mono text-xs text-slate-600">{p.code}</span>
                    <span className="text-slate-400 truncate text-xs">{p.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Dependents */}
        {dependentCourses.length > 0 && (
          <div>
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Unlocks ({dependentCourses.length})
            </div>
            <div className="space-y-1.5">
              {dependentCourses.map((d) => {
                const dColors = statusColors[d.status];
                return (
                  <div key={d.code} className="flex items-center gap-2 text-sm">
                    <ArrowRight className="w-3 h-3 text-slate-300 shrink-0" />
                    <div className={`w-2 h-2 rounded-full ${dColors.badge}`} />
                    <span className="font-mono text-xs text-slate-600">{d.code}</span>
                    <span className="text-slate-400 truncate text-xs">{d.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Availability */}
        {course.available_semesters.length > 0 && (
          <div>
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Offered In</div>
            <div className="flex gap-1.5">
              {course.available_semesters.map((s) => (
                <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 capitalize">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Similar Courses (Nova Embed) */}
        {(similarCourses || similarLoading) && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Layers className="w-3.5 h-3.5 text-fuchsia-500" />
              <span className="text-[10px] font-semibold text-fuchsia-500 uppercase tracking-wider">
                Related Courses
              </span>
              <span className="text-[9px] text-slate-400">(Nova Embed)</span>
            </div>
            {similarLoading && (
              <div className="flex items-center gap-2 py-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-fuchsia-400" />
                <span className="text-xs text-slate-400">Finding similar courses...</span>
              </div>
            )}
            {similarCourses && similarCourses.length > 0 && (
              <div className="space-y-1">
                {similarCourses.map((sc) => {
                  const matchNode = allCourses.find((c) => c.code === sc.code);
                  const scColors = matchNode ? statusColors[matchNode.status] : null;
                  return (
                    <button
                      key={sc.code}
                      onClick={() => onCourseSelect?.(sc.code)}
                      className="w-full flex items-center gap-2 text-sm hover:bg-slate-50 rounded-md px-1.5 py-1 transition-colors text-left"
                    >
                      {scColors && <div className={`w-2 h-2 rounded-full ${scColors.badge} shrink-0`} />}
                      <span className="font-mono text-xs text-slate-600">{sc.code}</span>
                      <span className="text-slate-400 truncate text-xs flex-1">{sc.name}</span>
                      <span className="text-[10px] text-fuchsia-500 font-medium shrink-0">
                        {Math.round(sc.similarity * 100)}%
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Nova Explanation */}
        <div className="border-t border-slate-100 pt-4">
          {!explanation && !explanationLoading && (
            connected ? (
              <button
                onClick={onAskNova}
                className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 text-white font-medium py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 text-sm btn-glow"
              >
                <Sparkles className="w-4 h-4" />
                Ask Nova About This Course
              </button>
            ) : (
              <div className="w-full bg-slate-100 text-slate-400 font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 text-sm">
                <WifiOff className="w-4 h-4" />
                Nova unavailable (no Bedrock connection)
              </div>
            )
          )}

          {explanationLoading && !explanation && (
            <div className="flex flex-col items-center gap-2 py-4">
              <Loader2 className="w-5 h-5 animate-spin text-violet-500" />
              <span className="text-xs text-slate-400">Nova is thinking...</span>
            </div>
          )}

          {explanation && !explanationError && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-violet-500" />
                <span className="text-[10px] font-semibold text-violet-500 uppercase tracking-wider">
                  {explanationLoading ? "Nova is typing..." : "Nova's Insight"}
                </span>
                {explanationLoading && (
                  <Loader2 className="w-3 h-3 animate-spin text-violet-400" />
                )}
              </div>
              <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line bg-violet-50/50 rounded-lg p-3 border border-violet-100">
                {explanation}
              </div>
            </div>
          )}

          {explanation && explanationError && (
            <div className="text-center space-y-2">
              <p className="text-sm text-slate-400">{explanation}</p>
              <button
                onClick={onAskNova}
                className="inline-flex items-center gap-1.5 text-sm text-violet-600 hover:text-violet-700 font-medium transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
