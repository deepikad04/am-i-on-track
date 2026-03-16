import { useState, useMemo } from 'react';
import { GraduationCap, CheckSquare, Square, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import type { DegreeRequirement } from '../../types/degree';

interface ProgressSelectorProps {
  degree: DegreeRequirement;
  onConfirm: (currentSemester: number, completedCourses: string[]) => Promise<void>;
}

export default function ProgressSelector({ degree, onConfirm }: ProgressSelectorProps) {
  const maxSemester = Math.max(
    ...degree.courses.map((c) => c.typical_semester ?? 0),
    8,
  );
  const semesters = Array.from({ length: maxSemester }, (_, i) => i + 1);

  const [currentSemester, setCurrentSemester] = useState(1);
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [expandedSemesters, setExpandedSemesters] = useState<Set<number>>(new Set());
  const [saving, setSaving] = useState(false);

  // Group courses by typical_semester
  const coursesBySemester = useMemo(() => {
    const map = new Map<number, typeof degree.courses>();
    for (const c of degree.courses) {
      const sem = c.typical_semester ?? 0;
      if (!map.has(sem)) map.set(sem, []);
      map.get(sem)!.push(c);
    }
    return map;
  }, [degree.courses]);

  // When semester changes, auto-complete all courses from prior semesters
  const handleSemesterChange = (newSem: number) => {
    setCurrentSemester(newSem);
    const autoCompleted = new Set<string>();
    for (const course of degree.courses) {
      const sem = course.typical_semester ?? 0;
      if (sem > 0 && sem < newSem) {
        autoCompleted.add(course.code);
      }
    }
    setCompleted(autoCompleted);
    // Expand current and prior semesters for review
    const expanded = new Set<number>();
    for (let s = 1; s < newSem; s++) expanded.add(s);
    setExpandedSemesters(expanded);
  };

  const toggleCourse = (code: string) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  const toggleSemesterExpand = (sem: number) => {
    setExpandedSemesters((prev) => {
      const next = new Set(prev);
      if (next.has(sem)) next.delete(sem);
      else next.add(sem);
      return next;
    });
  };

  const toggleAllInSemester = (sem: number) => {
    const semCourses = coursesBySemester.get(sem) || [];
    const allChecked = semCourses.every((c) => completed.has(c.code));
    setCompleted((prev) => {
      const next = new Set(prev);
      for (const c of semCourses) {
        if (allChecked) next.delete(c.code);
        else next.add(c.code);
      }
      return next;
    });
  };

  const handleConfirm = async () => {
    setSaving(true);
    try {
      await onConfirm(currentSemester, Array.from(completed));
    } finally {
      setSaving(false);
    }
  };

  const completedCredits = degree.courses
    .filter((c) => completed.has(c.code))
    .reduce((sum, c) => sum + c.credits, 0);
  const totalCredits = degree.courses.reduce((sum, c) => sum + c.credits, 0);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="bg-gradient-to-r from-violet-600 to-fuchsia-500 px-6 py-4 text-white">
        <div className="flex items-center gap-2 mb-1">
          <GraduationCap className="w-5 h-5" />
          <span className="text-sm font-medium opacity-90">Set Your Progress</span>
        </div>
        <p className="text-sm opacity-80">
          Tell us where you are so we can build an accurate plan.
        </p>
      </div>

      {/* Semester Picker */}
      <div className="px-6 py-4 border-b border-slate-100">
        <label className="text-sm font-semibold text-slate-700 block mb-2">
          What semester are you currently in?
        </label>
        <select
          value={currentSemester}
          onChange={(e) => handleSemesterChange(Number(e.target.value))}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-violet-300 focus:border-violet-400 outline-none"
        >
          {semesters.map((sem) => (
            <option key={sem} value={sem}>
              Semester {sem} ({sem % 2 === 1 ? 'Fall' : 'Spring'})
            </option>
          ))}
        </select>
        {currentSemester > 1 && (
          <p className="text-xs text-slate-500 mt-2">
            Courses from semesters 1–{currentSemester - 1} have been auto-marked as completed.
            Uncheck any you haven't taken yet.
          </p>
        )}
      </div>

      {/* Completed Course Selection */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-700">Completed Courses</h4>
          <span className="text-xs text-slate-500">
            {completed.size} courses · {completedCredits}/{totalCredits} credits
          </span>
        </div>

        <div className="max-h-72 overflow-y-auto space-y-1 rounded-lg border border-slate-200 p-2">
          {semesters.map((sem) => {
            const semCourses = coursesBySemester.get(sem) || [];
            if (semCourses.length === 0) return null;
            const checkedCount = semCourses.filter((c) => completed.has(c.code)).length;
            const allChecked = checkedCount === semCourses.length;
            const isExpanded = expandedSemesters.has(sem);
            const isPrior = sem < currentSemester;

            return (
              <div key={sem} className="rounded-lg overflow-hidden">
                {/* Semester header */}
                <button
                  onClick={() => toggleSemesterExpand(sem)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
                    isPrior
                      ? 'bg-violet-50 hover:bg-violet-100'
                      : 'bg-slate-50 hover:bg-slate-100'
                  }`}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  )}
                  <span className="font-medium text-slate-700 flex-1">
                    Semester {sem}
                  </span>
                  <span className="text-xs text-slate-500">
                    {checkedCount}/{semCourses.length}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleAllInSemester(sem);
                    }}
                    className="text-xs text-violet-600 hover:text-violet-800 underline ml-2"
                  >
                    {allChecked ? 'Uncheck all' : 'Check all'}
                  </button>
                </button>

                {/* Course list */}
                {isExpanded && (
                  <div className="divide-y divide-slate-100">
                    {semCourses.map((course) => {
                      const isChecked = completed.has(course.code);
                      return (
                        <label
                          key={course.code}
                          className="flex items-center gap-3 px-3 py-1.5 cursor-pointer hover:bg-slate-50 transition-colors"
                        >
                          <button
                            type="button"
                            role="checkbox"
                            aria-checked={isChecked}
                            onClick={() => toggleCourse(course.code)}
                            className="shrink-0"
                          >
                            {isChecked ? (
                              <CheckSquare className="w-4 h-4 text-violet-600" />
                            ) : (
                              <Square className="w-4 h-4 text-slate-300" />
                            )}
                          </button>
                          <span className="font-mono text-xs text-violet-700 w-20 shrink-0">
                            {course.code}
                          </span>
                          <span className="text-sm text-slate-700 flex-1 truncate">
                            {course.name}
                          </span>
                          <span className="text-xs text-slate-400 shrink-0">
                            {course.credits}cr
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          {/* Courses with no typical_semester */}
          {(coursesBySemester.get(0) || []).length > 0 && (
            <div className="rounded-lg overflow-hidden">
              <button
                onClick={() => toggleSemesterExpand(0)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left text-sm bg-slate-50 hover:bg-slate-100 transition-colors"
              >
                {expandedSemesters.has(0) ? (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                )}
                <span className="font-medium text-slate-700 flex-1">Electives / Unassigned</span>
                <span className="text-xs text-slate-500">
                  {(coursesBySemester.get(0) || []).filter((c) => completed.has(c.code)).length}/
                  {(coursesBySemester.get(0) || []).length}
                </span>
              </button>
              {expandedSemesters.has(0) && (
                <div className="divide-y divide-slate-100">
                  {(coursesBySemester.get(0) || []).map((course) => {
                    const isChecked = completed.has(course.code);
                    return (
                      <label
                        key={course.code}
                        className="flex items-center gap-3 px-3 py-1.5 cursor-pointer hover:bg-slate-50 transition-colors"
                      >
                        <button
                          type="button"
                          role="checkbox"
                          aria-checked={isChecked}
                          onClick={() => toggleCourse(course.code)}
                          className="shrink-0"
                        >
                          {isChecked ? (
                            <CheckSquare className="w-4 h-4 text-violet-600" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-300" />
                          )}
                        </button>
                        <span className="font-mono text-xs text-violet-700 w-20 shrink-0">
                          {course.code}
                        </span>
                        <span className="text-sm text-slate-700 flex-1 truncate">
                          {course.name}
                        </span>
                        <span className="text-xs text-slate-400 shrink-0">
                          {course.credits}cr
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Action */}
      <div className="px-6 py-4 bg-slate-50 border-t border-slate-200">
        <button
          onClick={handleConfirm}
          disabled={saving}
          className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-500 hover:from-violet-500 hover:to-fuchsia-400 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-all flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            'Confirm & View Degree Map'
          )}
        </button>
      </div>
    </div>
  );
}
