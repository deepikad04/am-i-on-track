export type ScenarioType =
  | 'drop_course'
  | 'block_semester'
  | 'add_major'
  | 'add_minor'
  | 'set_goal'
  | 'study_abroad'
  | 'coop'
  | 'gap_semester';

export interface Scenario {
  type: ScenarioType;
  parameters: Record<string, unknown>;
  session_id: string;
  degree_id: string;
}

export interface AffectedCourse {
  code: string;
  name: string;
  original_semester: number;
  new_semester: number;
  reason: string;
}

export interface ConstraintCheck {
  label: string;
  passed: boolean;
  severity: 'ok' | 'warning' | 'error';
  detail: string;
  related_courses?: string[];
}

export interface OverlapResult {
  exact_matches: { code: string; name: string; credits: number }[];
  equivalent_courses: { degree1_code: string; degree2_code: string; name: string; credits: number }[];
  total_shared_credits: number;
  additional_semesters_estimate: number;
  recommendations: string[];
}

export interface SimulationResult {
  original_graduation: string;
  new_graduation: string;
  semesters_added: number;
  affected_courses: AffectedCourse[];
  credit_impact: number;
  risk_level: 'low' | 'medium' | 'high';
  reasoning_steps: string[];
  recommendations: string[];
  constraint_checks: ConstraintCheck[];
  plan_comparison: PlanComparison;
  overlap?: OverlapResult;
}

export interface PlanComparison {
  graduation_date: [string, string];
  avg_credits_per_term: [number, number];
  risk_level: [string, string];
  summer_reliance: [string, string];
  gpa_protection_score: [number, number];
}
