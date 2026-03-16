import { CheckCircle2, BookOpen, AlertTriangle } from 'lucide-react';
import type { DegreeRequirement } from '../../types/degree';

interface ParsedPreviewProps {
  degree: DegreeRequirement;
  onProceed?: () => void;
}

export default function ParsedPreview({ degree }: ParsedPreviewProps) {
  const coreCount = degree.courses.filter((c) => c.is_required).length;
  const electiveCount = degree.courses.length - coreCount;
  const totalCredits = degree.courses.reduce((sum, c) => sum + c.credits, 0);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-violet-600 to-fuchsia-500 px-6 py-4 text-white">
        <div className="flex items-center gap-2 mb-1">
          <CheckCircle2 className="w-5 h-5" />
          <span className="text-sm font-medium opacity-90">Successfully Parsed</span>
        </div>
        <h3 className="text-lg font-bold">{degree.degree_name}</h3>
        {degree.institution && (
          <p className="text-sm opacity-80">{degree.institution}</p>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 border-b border-slate-100">
        {[
          { label: 'Total Courses', value: degree.courses.length },
          { label: 'Required', value: coreCount },
          { label: 'Electives', value: electiveCount },
          { label: 'Total Credits', value: totalCredits },
        ].map((stat) => (
          <div key={stat.label} className="px-4 py-3 text-center border-r border-slate-100 last:border-r-0">
            <div className="text-xl font-bold text-slate-900">{stat.value}</div>
            <div className="text-xs text-slate-500">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Category Breakdown */}
      <div className="px-6 py-4">
        <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <BookOpen className="w-4 h-4" />
          Categories
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {degree.categories.map((cat) => (
            <div
              key={cat.name}
              className="bg-slate-50 rounded-lg px-3 py-2 text-sm"
            >
              <div className="font-medium text-slate-700">{cat.name}</div>
              <div className="text-xs text-slate-500">
                {cat.min_credits} credits / {cat.min_courses} courses
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Course Table */}
      <div className="px-6 pb-4">
        <h4 className="text-sm font-semibold text-slate-700 mb-2">Courses</h4>
        <div className="max-h-60 overflow-y-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 sticky top-0">
              <tr className="text-left text-xs text-slate-500">
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2 text-center">Credits</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Prerequisites</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {degree.courses.map((course) => (
                <tr key={course.code} className="hover:bg-slate-50">
                  <td className="px-3 py-1.5 font-mono text-xs font-medium text-violet-700">
                    {course.code}
                  </td>
                  <td className="px-3 py-1.5 text-slate-700">{course.name}</td>
                  <td className="px-3 py-1.5 text-center text-slate-600">{course.credits}</td>
                  <td className="px-3 py-1.5">
                    <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                      {course.category}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-xs text-slate-500">
                    {course.prerequisites.length > 0
                      ? course.prerequisites.join(', ')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Constraints */}
      {degree.constraints.length > 0 && (
        <div className="px-6 pb-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Constraints
          </h4>
          <ul className="space-y-1">
            {degree.constraints.map((c, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">•</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next step hint */}
      <div className="px-6 py-3 bg-slate-50 border-t border-slate-200">
        <p className="text-xs text-slate-500 text-center">
          Set your current progress below to get an accurate plan.
        </p>
      </div>
    </div>
  );
}
