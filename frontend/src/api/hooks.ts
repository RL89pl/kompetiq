import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  AIResponse, Action, Assessment, AssessmentListItem, ChecklistItem, CompetencyModel, Deadline, DevPlan, Employee, PlanListItem,
  FormConfig, FormType, HROverview, Me, Notification, AssistantStatus,
} from './types'

export const qk = {
  me: ['me'],
  model: ['competency-model'],
  forms: ['forms'],
  employees: ['employees'],
  assessments: (params = '') => ['assessments', params],
  assessment: (id: number) => ['assessment', id],
  checklist: (id: number) => ['checklist', id],
  deadlines: ['deadlines'],
  plan: (assessmentId: number) => ['plan', assessmentId],
  plans: ['plans'],
  notifications: ['notifications'],
  hr: ['hr-overview'],
  assistantStatus: ['assistant-status'],
}

export const useNotifications = () =>
  useQuery({ queryKey: qk.notifications, queryFn: () => api<Notification[]>('/notifications/'), refetchInterval: 60_000 })

export const useHROverview = () => useQuery({ queryKey: qk.hr, queryFn: () => api<HROverview>('/hr/overview/') })

export const useAssistantStatus = () =>
  useQuery({ queryKey: qk.assistantStatus, queryFn: () => api<AssistantStatus>('/assistant/status/'), staleTime: 300_000 })

export const useMe = () =>
  useQuery({ queryKey: qk.me, queryFn: () => api<Me>('/auth/me/'), retry: false, staleTime: 60_000 })

export const useCompetencyModel = () =>
  useQuery({ queryKey: qk.model, queryFn: () => api<CompetencyModel>('/competency-models/active/'), staleTime: Infinity })

export const useForms = () =>
  useQuery({ queryKey: qk.forms, queryFn: () => api<FormConfig[]>('/assessments/forms/'), staleTime: Infinity })

export const useEmployees = () => useQuery({ queryKey: qk.employees, queryFn: () => api<Employee[]>('/employees/') })

export const useAssessments = (params = '') =>
  useQuery({ queryKey: qk.assessments(params), queryFn: () => api<AssessmentListItem[]>(`/assessments/${params}`) })

export const useAssessment = (id: number) =>
  useQuery({ queryKey: qk.assessment(id), queryFn: () => api<Assessment>(`/assessments/${id}/`) })

export const useChecklist = (id: number) =>
  useQuery({ queryKey: qk.checklist(id), queryFn: () => api<ChecklistItem[]>(`/assessments/${id}/checklist/`) })

export const useDeadlines = () =>
  useQuery({ queryKey: qk.deadlines, queryFn: () => api<Deadline[]>('/deadlines/upcoming/?days=90') })

export const usePlans = () => useQuery({ queryKey: qk.plans, queryFn: () => api<PlanListItem[]>('/development-plans/') })

export const usePlanDetail = (id: number) =>
  useQuery({ queryKey: ['plan-detail', id], queryFn: () => api<DevPlan>(`/development-plans/${id}/`) })

export function usePlan(assessmentId: number) {
  return useQuery({
    queryKey: qk.plan(assessmentId),
    queryFn: () => api<DevPlan>('/development-plans/', { method: 'POST', body: { assessment: assessmentId } }),
  })
}

/** Odświeża wszystko, co zależy od oceny. */
export function useInvalidateAssessment(id: number) {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: qk.assessment(id) })
    qc.invalidateQueries({ queryKey: qk.checklist(id) })
    qc.invalidateQueries({ queryKey: ['assessments'] })
    qc.invalidateQueries({ queryKey: qk.deadlines })
  }
}

export function usePatchAssessment(id: number) {
  const qc = useQueryClient()
  const invalidate = useInvalidateAssessment(id)
  return useMutation({
    mutationFn: (body: Partial<Assessment>) => api<Assessment>(`/assessments/${id}/`, { method: 'PATCH', body }),
    onSuccess: (data) => {
      qc.setQueryData(qk.assessment(id), data)
      invalidate()
    },
  })
}

export function useTransition(id: number) {
  const qc = useQueryClient()
  const invalidate = useInvalidateAssessment(id)
  return useMutation({
    mutationFn: (v: { action: Action; acknowledged_on?: string }) =>
      api<Assessment>(`/assessments/${id}/transition/`, { method: 'POST', body: v }),
    onSuccess: (data) => {
      qc.setQueryData(qk.assessment(id), data)
      invalidate()
    },
  })
}

export function useCreateAssessment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { employee: number; form_type: FormType }) =>
      api<Assessment>('/assessments/', { method: 'POST', body: v }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.employees })
      qc.invalidateQueries({ queryKey: ['assessments'] })
    },
  })
}

export function useAssistant<T>(assessmentId: number, feature: string) {
  return useMutation({
    mutationFn: (body: { criterion?: number } = {}) =>
      api<AIResponse<T>>(`/assessments/${assessmentId}/assistant/${feature}/`, { method: 'POST', body }),
  })
}

export function reportOutcome(interactionId: number | null, outcome: 'ACCEPTED' | 'EDITED' | 'REJECTED') {
  if (!interactionId) return
  api(`/assistant/interactions/${interactionId}/outcome/`, { method: 'POST', body: { outcome } }).catch(() => {})
}
