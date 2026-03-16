export interface Course {
  code: string;
  name: string;
  credits: number;
  prerequisites: string[];
  corequisites: string[];
  category: string;
  typical_semester: number | null;
  is_required: boolean;
  available_semesters: string[];
}

export interface CategoryRequirement {
  name: string;
  min_credits: number;
  min_courses: number;
  courses: string[];
}

export interface DegreeRequirement {
  degree_name: string;
  institution: string | null;
  total_credits_required: number;
  courses: Course[];
  categories: CategoryRequirement[];
  constraints: string[];
  max_credits_per_semester: number;
}

export type CourseStatus =
  | 'completed'
  | 'scheduled'
  | 'elective'
  | 'bottleneck'
  | 'locked';

export interface CourseNode extends Course {
  status: CourseStatus;
  semester: number;
  dependents_count: number;
}

export interface StudentProgress {
  completed_courses: string[];
  current_semester: number;
}
