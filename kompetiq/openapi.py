"""Serializery opisujące w OpenAPI widoki oparte na APIView (żądania i odpowiedzi budowane ręcznie)."""
from rest_framework import serializers


class Detail(serializers.Serializer):
    detail = serializers.CharField(help_text='Komunikat błędu dla użytkownika')


# ── Uwierzytelnianie ─────────────────────────────────────────────────────────────────────────────
class CsrfOut(serializers.Serializer):
    csrfToken = serializers.CharField(help_text='Token do nagłówka X-CSRFToken przy żądaniach POST/PATCH/DELETE')


class LoginIn(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})


class MembershipOut(serializers.Serializer):
    id = serializers.IntegerField()
    institution = serializers.IntegerField()
    institution_name = serializers.CharField()
    role = serializers.ChoiceField(choices=['SUPERVISOR', 'UNIT_HEAD', 'HR', 'ADMIN'])
    role_display = serializers.CharField()
    org_unit = serializers.IntegerField(allow_null=True)
    org_unit_name = serializers.CharField()
    position = serializers.CharField()


class MeOut(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField()
    memberships = MembershipOut(many=True)
    active_membership = MembershipOut(allow_null=True, help_text='Instytucja, w kontekście której działa sesja')


class SwitchInstitutionIn(serializers.Serializer):
    institution = serializers.IntegerField(help_text='ID instytucji, do której użytkownik ma członkostwo')


class InstitutionUserOut(serializers.Serializer):
    id = serializers.IntegerField(help_text='ID użytkownika')
    full_name = serializers.CharField()
    role = serializers.CharField()
    role_display = serializers.CharField()
    org_unit = serializers.IntegerField(allow_null=True)
    position = serializers.CharField()


# ── Terminy i panel HR ───────────────────────────────────────────────────────────────────────────
class DeadlineOut(serializers.Serializer):
    assessment = serializers.IntegerField()
    employee = serializers.CharField()
    evaluator_id = serializers.IntegerField()
    evaluator = serializers.CharField()
    kind = serializers.ChoiceField(choices=['initial_interview', 'report', 'first_window', 'approval', 'due',
                                            'objection', 'reassessment', 'acknowledge', 'development'])
    label = serializers.CharField()
    date = serializers.DateField()
    days_left = serializers.IntegerField(help_text='Ujemne, gdy termin minął')
    overdue = serializers.BooleanField()
    basis = serializers.CharField(help_text='Podstawa prawna terminu, np. „art. 81 ust. 4 ustawy”')


class HRTotals(serializers.Serializer):
    all = serializers.IntegerField()
    overdue = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    done = serializers.IntegerField()
    negative = serializers.IntegerField()


class HRStatusCount(serializers.Serializer):
    status = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class HRUnit(serializers.Serializer):
    unit = serializers.CharField()
    in_progress = serializers.IntegerField()
    done = serializers.IntegerField()
    overdue = serializers.IntegerField()
    negative = serializers.IntegerField()


class HRNextDeadline(serializers.Serializer):
    label = serializers.CharField()
    date = serializers.DateField()
    days_left = serializers.IntegerField()
    overdue = serializers.BooleanField()


class HRAssessmentRow(serializers.Serializer):
    id = serializers.IntegerField()
    employee = serializers.CharField()
    position = serializers.CharField()
    unit = serializers.CharField()
    evaluator = serializers.CharField()
    evaluator_id = serializers.IntegerField()
    form_type = serializers.CharField()
    status = serializers.CharField()
    status_label = serializers.CharField()
    result = serializers.CharField(allow_null=True)
    updated_at = serializers.DateTimeField()
    next_deadline = HRNextDeadline(allow_null=True)


class HROverviewOut(serializers.Serializer):
    totals = HRTotals()
    by_status = HRStatusCount(many=True)
    by_form = serializers.DictField(child=serializers.IntegerField(), help_text='Liczba ocen wg rodzaju arkusza')
    units = HRUnit(many=True)
    assessments = HRAssessmentRow(many=True)
    deadlines = DeadlineOut(many=True)


class SentOut(serializers.Serializer):
    sent = serializers.IntegerField(help_text='Liczba wysłanych powiadomień')


class MessageIn(serializers.Serializer):
    to = serializers.ChoiceField(choices=['evaluator', 'unit_head', 'hr'])
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    reminder = serializers.BooleanField(required=False, help_text='true = przypomnienie zamiast zwykłej wiadomości')


# ── Asystent AI ──────────────────────────────────────────────────────────────────────────────────
class AssistantFeatureIn(serializers.Serializer):
    criterion = serializers.IntegerField(
        required=False, help_text='ID kryterium — wymagane dla guiding-questions i analyze-evidence, '
                                  'opcjonalne dla draft-justification')


class AssistantFeatureOut(serializers.Serializer):
    interaction_id = serializers.IntegerField(allow_null=True, help_text='Do zgłoszenia, czy sugestię przyjęto')
    ai_generated = serializers.BooleanField()
    notice = serializers.CharField()
    result = serializers.JSONField(help_text='Treść zależna od funkcji; nigdy nie zawiera ocen ani poziomów')


class AssistantStatusOut(serializers.Serializer):
    enabled = serializers.BooleanField()
    provider = serializers.CharField()
    model = serializers.CharField()
    knowledge = serializers.DictField(child=serializers.IntegerField(),
                                      help_text='Liczba fragmentów bazy wiedzy wg rodzaju źródła')


class OutcomeIn(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=['ACCEPTED', 'EDITED', 'REJECTED'])


class ChatIn(serializers.Serializer):
    content = serializers.CharField(max_length=2000)


class PreviewIn(serializers.Serializer):
    feature = serializers.ChoiceField(choices=[
        'analyze-job-description', 'guiding-questions', 'analyze-evidence', 'draft-justification', 'interview-script',
        'development-suggestions', 'chat-formal', 'chat-interview'])
    assessment = serializers.IntegerField(required=False, help_text='Wymagane poza chat-formal')
    criterion = serializers.IntegerField(required=False)
    question = serializers.CharField(required=False, max_length=2000, help_text='Pytanie dla trybów chat-*')


class PreviewCall(serializers.Serializer):
    method = serializers.ChoiceField(choices=['structured', 'answer_with_citations'])
    system = serializers.ListField(child=serializers.CharField())
    prompt = serializers.CharField()
    documents = serializers.ListField(child=serializers.DictField())
    history = serializers.ListField(child=serializers.DictField())
    response_schema = serializers.JSONField(allow_null=True, help_text='Schemat JSON odpowiedzi — bez pól ocen')


class PreviewCheck(serializers.Serializer):
    label = serializers.CharField()
    ok = serializers.BooleanField()
    detail = serializers.CharField()


class PreviewDestination(serializers.Serializer):
    provider = serializers.CharField()
    model = serializers.CharField()
    host = serializers.CharField()
    enabled = serializers.BooleanField()


class PreviewOut(serializers.Serializer):
    feature = serializers.CharField()
    feature_label = serializers.CharField()
    would_call_model = serializers.BooleanField()
    reason = serializers.CharField(help_text='Dlaczego model nie zostałby wywołany (np. brak źródeł)')
    destination = PreviewDestination()
    calls = PreviewCall(many=True)
    characters = serializers.IntegerField()
    checks = PreviewCheck(many=True)
    sent = serializers.ListField(child=serializers.CharField())
    not_sent = serializers.ListField(child=serializers.CharField())
