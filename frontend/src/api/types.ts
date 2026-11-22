export type Role = 'SUPERVISOR' | 'UNIT_HEAD' | 'HR' | 'ADMIN'
export type FormType = 'FIRST' | 'PERIODIC_A' | 'PERIODIC_B' | 'PERIODIC_C'
export type Status = 'DRAFT' | 'CRITERIA_SET' | 'INTERVIEW_DONE' | 'FINALIZED' | 'APPROVED' | 'ACKNOWLEDGED' | 'CANCELLED'
export type Action =
  | 'set_criteria' | 'reopen_criteria' | 'complete_interview' | 'finalize' | 'reopen' | 'approve' | 'acknowledge' | 'cancel'

export interface Membership {
  id: number
  institution: number
  institution_name: string
  role: Role
  role_display: string
  org_unit: number | null
  org_unit_name: string
  position: string
}

export interface Me {
  id: number
  username: string
  full_name: string
  memberships: Membership[]
  active_membership: Membership | null
}

export interface JobDescription {
  id: number
  employee: number
  symbol: string
  purpose: string
  subordinates: string
  manages_people: boolean | null
  soft_competencies: string[]
  source_name: string
  main_duties: string
  responsibilities: string
  requirements: string
  valid_from: string | null
  created_at: string
}

export interface Employee {
  id: number
  first_name: string
  last_name: string
  full_name: string
  position: string
  form_of_address: '' | 'PANI' | 'PAN'
  org_unit: number | null
  org_unit_name: string
  supervisor: number | null
  supervisor_name: string
  employment_date: string | null
  contract_end_date: string | null
  is_civil_servant: boolean
  service_grade: string
  appointment_year: number | null
  service_grade_date: string | null
  is_managerial: boolean
  is_office_head: boolean
  suggested_form: FormType
  latest_job_description: JobDescription | null
  active_assessment: { id: number; status: Status; form_type: FormType } | null
  /** Pusty, gdy można rozpocząć pierwszą ocenę; inaczej powód. */
  first_assessment_block: string
}

export interface LevelText { level: number; text: string }
export interface Indicator { id: number; text: string; order: number; levels: LevelText[] }
export interface Competency { id: number; code: string; name: string; order: number; indicators: Indicator[] }
export interface CompetencyModel {
  id: number
  name: string
  version: string
  guidance: string
  competencies: Competency[]
  level_labels: { level: number; label: string }[]
}

export interface ScalePoint { points: number; label: string; model_levels: number[] }
export interface FormConfig {
  form_type: FormType
  label: string
  short_name: string
  mandatory: string[]
  max_additional: number
  is_first: boolean
  scale: ScalePoint[]
}

export interface Evidence {
  id: number
  criterion: number
  indicator: number | null
  situation: string
  action: string
  result: string
  occurred_on: string | null
  is_positive: boolean | null
  created_at: string
}

export interface Rating { id: number; indicator: number; level: number | null; no_basis: boolean }

export interface Criterion {
  id: number
  competency: number
  competency_code: string
  competency_name: string
  is_mandatory: boolean
  order: number
  selected_indicators: number[]
  score: number | null
  justification: string
  evidence: Evidence[]
  ratings: Rating[]
  suggested_points: number | null
}

export interface Summary {
  complete: boolean
  average: string | null
  level: number | null
  level_label: string
  result: 'POSITIVE' | 'NEGATIVE' | null
  reasons: string[]
}

export interface AssessmentListItem {
  id: number
  employee: number
  employee_name: string
  employee_position: string
  evaluator: number
  evaluator_name: string
  form_type: FormType
  form_label: string
  status: Status
  status_label: string
  due_date: string | null
  window_to: string | null
  result: string
  average: string | null
  created_at: string
  updated_at: string
}

export interface Assessment extends AssessmentListItem {
  unit_head: number | null
  criteria_interview_date: string | null
  expectations: string
  goals: string
  report_deadline_from: string | null
  report_deadline_to: string | null
  window_from: string | null
  report_text: string
  report_on_time: boolean | null
  prep_exam: '' | 'PASSED' | 'FAILED' | 'NA'
  period_from: string | null
  period_to: string | null
  evaluation_interview_date: string | null
  interview_notes: string
  interview_plan: InterviewScript | null
  justification: string
  development_conclusions: string
  previous_result: string
  previous_level: string
  previous_date: string | null
  promotion_request: boolean | null
  promotion_grade: string
  promotion_motivation: string
  objection_filed_on: string | null
  competency_model: number
  level: number | null
  finalized_at: string | null
  approved_at: string | null
  acknowledged_on: string | null
  criteria: Criterion[]
  summary: Summary
  available_actions: Action[]
  employee_detail: {
    id: number
    full_name: string
    position: string
    org_unit: string
    employment_date: string | null
    is_civil_servant: boolean
    service_grade: string
    is_managerial: boolean
    form_of_address: '' | 'PANI' | 'PAN'
  }
  can_edit: boolean
}

export interface ChecklistItem {
  key: string
  label: string
  ok: boolean
  basis: string
  hint: string
  severity: 'ok' | 'warning' | 'error' | 'info'
}

export interface Deadline {
  assessment: number
  employee: string
  kind: string
  label: string
  date: string
  days_left: number
  overdue: boolean
  basis: string
}

export interface DevAction {
  id: number
  plan: number
  competency: number | null
  competency_name: string
  title: string
  description: string
  type: string
  type_label: string
  success_measure: string
  owner: string
  due_date: string | null
  status: string
  status_label: string
  from_ai_suggestion: boolean
  notes: { id: number; text: string; author_name: string; created_at: string }[]
}

export interface PlanStats {
  total: number
  done: number
  percent: number
  in_progress: number
  planned: number
  overdue: number
  next_action: { title: string; due_date: string; overdue: boolean } | null
  last_activity: string | null
}

export interface PlanListItem {
  id: number
  assessment: number
  employee_id: number
  employee_name: string
  position: string
  org_unit: string
  evaluator_name: string
  assessment_label: string
  assessment_result: string
  assessment_date: string | null
  stats: PlanStats
  updated_at: string
}

export interface DevPlan extends PlanListItem {
  summary: string
  actions: DevAction[]
  progress: { total: number; done: number; percent: number }
  history: { id: number; label: string; date: string; progress: { total: number; done: number; percent: number } }[]
  can_edit: boolean
}

// --- odpowiedzi asystenta ---
export interface AIResponse<T> { interaction_id: number | null; ai_generated: true; notice: string; result: T }

export interface JobAnalysis {
  manages_people: boolean
  suggested_form: FormType
  form_rationale: string
  key_duties: string[]
  additional_criteria: { competency_code: string; rationale: string }[]
  priority_indicators: { indicator_id: number; rationale: string }[]
  expectations_draft: string
  goals_suggestions: string[]
  caveats: string[]
}

export interface GuidingQuestions { items: { indicator_id: number; questions: string[] }[] }

export interface EvidenceAnalysis {
  overview: string
  mappings: {
    evidence_id: number
    indicator_id: number | null
    observed_behaviour: string
    closest_anchor_level: number | null
    anchor_rationale: string
    completeness: 'complete' | 'missing_action' | 'missing_result' | 'too_general'
  }[]
  indicators_without_evidence: number[]
  missing_evidence_prompts: string[]
  neutrality_issues: { evidence_id: number; fragment: string; issue: string; suggestion: string }[]
  bias_warnings: string[]
  strengths: string[]
  development_areas: string[]
  interview_topics: string[]
}

export interface JustificationDraft { draft: string; consistency_warnings: string[]; missing_points: string[] }

export interface FeedbackItem { competency: string; situation: string; behaviour: string; impact: string }
export interface InterviewScript {
  goal: string
  preparation_checklist: string[]
  opening: string
  sections: { title: string; talking_points: string[]; questions_to_employee: string[] }[]
  strengths_feedback: FeedbackItem[]
  development_feedback: FeedbackItem[]
  development_dialogue_questions: string[]
  closing: string
  formal_reminders: string[]
  difficult_moments_tips: string[]
}

export interface DevelopmentSuggestions {
  conclusions_draft: string
  actions: {
    competency_code: string
    title: string
    description: string
    type: string
    success_measure: string
    timeframe_months: number
  }[]
}

export interface FormalAnswer {
  answer: string
  citations: { document_title: string; cited_text: string; document_index: number | null }[]
  sources: { title: string }[]
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations: { document_title: string; cited_text: string; document_index: number | null }[]
  sources: { title: string }[]
  grounded: boolean
  interaction: number | null
  created_at: string
}

export interface Conversation {
  id: number
  mode: 'FORMAL' | 'INTERVIEW'
  mode_label: string
  assessment: number | null
  title: string
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}

export interface Notification {
  id: number
  kind: 'REMINDER' | 'APPROVAL' | 'STATUS' | 'MESSAGE'
  kind_label: string
  title: string
  body: string
  assessment: number | null
  sender_name: string
  read_at: string | null
  created_at: string
}

export interface HROverview {
  totals: { all: number; overdue: number; in_progress: number; done: number; negative: number }
  by_status: { status: Status; label: string; count: number }[]
  by_form: Record<string, number>
  units: { unit: string; in_progress: number; done: number; overdue: number; negative: number }[]
  assessments: {
    id: number
    employee: string
    position: string
    unit: string
    evaluator: string
    evaluator_id: number
    form_type: FormType
    status: Status
    status_label: string
    result: string
    updated_at: string
    next_deadline: { label: string; date: string; days_left: number; overdue: boolean } | null
  }[]
  deadlines: Deadline[]
}

export interface AssistantStatus { enabled: boolean; provider: string; model: string; knowledge: Record<string, number> }

export type SourceKind = 'ACT' | 'REGULATION' | 'GUIDE' | 'MODEL' | 'FAQ' | 'OTHER'

export interface KnowledgeDocument {
  id: number
  title: string
  kind: SourceKind
  kind_label: string
  source: string
  valid_from: string | null
  note: string
  is_active: boolean
  builtin: boolean
  shared: boolean
  disabled_here: boolean
  chunk_count: number
  replaces: number | null
  replaces_title: string
  uploaded_by_name: string
  created_at: string
  updated_at: string
}

export interface OutgoingEmail {
  id: number
  to: string
  delivered_to: string
  subject: string
  body_text: string
  body_html: string
  status: 'CAPTURED' | 'SENT' | 'REDIRECTED' | 'FAILED'
  status_label: string
  created_at: string
  /** E-mail do innej osoby, wysłany w wyniku Twojego działania (np. Twojej wiadomości). */
  sent_by_me: boolean
  /** Przyczyna nieudanej wysyłki (status FAILED). */
  error: string
}

export interface MessageRecipient { key: 'evaluator' | 'unit_head' | 'hr'; label: string; hint: string; names: string[] }

export interface OrgUnit { id: number; name: string; parent: number | null; head: number | null; head_name: string }
export interface InstitutionUser { id: number; full_name: string; role: Role; role_display: string; org_unit: number | null; position: string }
