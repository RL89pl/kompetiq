"""Schematy odpowiedzi asystenta (structured outputs).

Celowo NIE zawierają pól z oceną punktową ani wynikiem oceny — decyzja należy do przełożonego.
"""
from typing import Literal

from pydantic import BaseModel, Field


class CriterionSuggestion(BaseModel):
    competency_code: str
    rationale: str


class IndicatorPriority(BaseModel):
    indicator_id: int
    rationale: str


class JobAnalysis(BaseModel):
    manages_people: bool
    suggested_form: Literal['PERIODIC_A', 'PERIODIC_B', 'PERIODIC_C', 'FIRST']
    form_rationale: str
    key_duties: list[str]
    additional_criteria: list[CriterionSuggestion] = Field(description='najwyżej 3, tylko spoza obowiązkowych')
    priority_indicators: list[IndicatorPriority]
    expectations_draft: str
    goals_suggestions: list[str]
    caveats: list[str]


class IndicatorQuestions(BaseModel):
    indicator_id: int
    questions: list[str]


class GuidingQuestions(BaseModel):
    items: list[IndicatorQuestions]


class EvidenceMapping(BaseModel):
    evidence_id: int
    indicator_id: int | None
    observed_behaviour: str = Field(description='neutralny opis zachowania w 1 zdaniu')
    closest_anchor_level: int | None = Field(description='poziom (1–5) opisu w modelu, któremu przykład najbardziej odpowiada; null gdy nie da się ocenić')
    anchor_rationale: str
    completeness: Literal['complete', 'missing_action', 'missing_result', 'too_general']


class NeutralityIssue(BaseModel):
    evidence_id: int
    fragment: str
    issue: str
    suggestion: str


class EvidenceAnalysis(BaseModel):
    overview: str
    mappings: list[EvidenceMapping]
    indicators_without_evidence: list[int]
    missing_evidence_prompts: list[str]
    neutrality_issues: list[NeutralityIssue]
    bias_warnings: list[str]
    strengths: list[str]
    development_areas: list[str]
    interview_topics: list[str]


class JustificationDraft(BaseModel):
    draft: str
    consistency_warnings: list[str]
    missing_points: list[str]


class TalkingSection(BaseModel):
    title: str
    talking_points: list[str]
    questions_to_employee: list[str]


class FeedbackItem(BaseModel):
    competency: str
    situation: str
    behaviour: str
    impact: str


class InterviewScript(BaseModel):
    goal: str
    preparation_checklist: list[str]
    opening: str
    sections: list[TalkingSection]
    strengths_feedback: list[FeedbackItem]
    development_feedback: list[FeedbackItem]
    development_dialogue_questions: list[str]
    closing: str
    formal_reminders: list[str]
    difficult_moments_tips: list[str]


class DevelopmentActionSuggestion(BaseModel):
    competency_code: str
    title: str
    description: str
    type: Literal['ON_THE_JOB', 'MENTORING', 'COACHING', 'TRAINING', 'SELF_STUDY', 'FEEDBACK']
    success_measure: str
    timeframe_months: int


class DevelopmentSuggestions(BaseModel):
    conclusions_draft: str
    actions: list[DevelopmentActionSuggestion]
