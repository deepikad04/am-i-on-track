import { useState, useCallback } from 'react';
import { getDegreeData, updateProgress } from '../services/api';
import type { DegreeRequirement, CourseNode, StudentProgress } from '../types/degree';

interface DegreeState {
  degree: DegreeRequirement | null;
  courseNodes: CourseNode[];
  completedCourses: string[];
  currentSemester: number;
  degreeId: string | null;
  loading: boolean;
  error: string | null;
}

export function useDegreeData() {
  const [state, setState] = useState<DegreeState>({
    degree: null,
    courseNodes: [],
    completedCourses: [],
    currentSemester: 1,
    degreeId: null,
    loading: false,
    error: null,
  });

  const fetchDegree = useCallback(async (sessionId: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await getDegreeData(sessionId);
      console.log('[fetchDegree]', sessionId, 'status:', data.status, 'hasDegree:', !!data.degree, 'courseNodes:', data.course_nodes?.length);
      setState({
        degree: data.degree,
        courseNodes: data.course_nodes || [],
        completedCourses: data.completed_courses || [],
        currentSemester: data.current_semester || 1,
        degreeId: data.degree_id,
        loading: false,
        error: null,
      });
      return data;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load degree';
      setState((s) => ({ ...s, loading: false, error: msg }));
      return null;
    }
  }, []);

  const toggleCourseComplete = useCallback(
    async (sessionId: string, courseCode: string) => {
      const isCompleted = state.completedCourses.includes(courseCode);
      const newCompleted = isCompleted
        ? state.completedCourses.filter((c) => c !== courseCode)
        : [...state.completedCourses, courseCode];

      setState((s) => ({ ...s, completedCourses: newCompleted }));

      try {
        await updateProgress(sessionId, newCompleted, state.currentSemester);
        await fetchDegree(sessionId);
      } catch {
        // Revert on error
        setState((s) => ({ ...s, completedCourses: state.completedCourses }));
      }
    },
    [state.completedCourses, state.currentSemester, fetchDegree],
  );

  return {
    ...state,
    fetchDegree,
    toggleCourseComplete,
  };
}
