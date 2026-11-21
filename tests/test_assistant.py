import os

import pytest

from apps.assistant import schemas
from apps.assistant.client import AssistantRefused, LLMResult, set_provider
from apps.assistant.models import AIInteraction, GuidingQuestionCache, LegalChunk
from apps.assistant.service import Pseudonymizer
from tests.test_api_flow import create

pytestmark = pytest.mark.django_db

FORBIDDEN = {'score', 'points', 'rating', 'result', 'grade', 'overall_level', 'ocena', 'punkty'}


class FakeProvider:
    def __init__(self, builder=None, refuse=False):
        self.calls = []
        self.builder = builder
        self.refuse = refuse

    def structured(self, *, system, prompt, schema, effort='medium', max_tokens=16000):
        self.calls.append({'system': system, 'prompt': prompt, 'schema': schema})
        if self.refuse:
            raise AssistantRefused()
        return LLMResult(parsed=self.builder(schema, prompt), model='fake', input_tokens=10, output_tokens=5)

    def answer_with_citations(self, *, system, prompt, documents, history=None, **kw):
        self.calls.append({'system': system, 'prompt': prompt, 'documents': documents, 'history': history or []})
        return LLMResult(text='Sprzeciw wnosi się w terminie 7 dni.', citations=[
            {'document_title': documents[0]['title'], 'cited_text': '7 dni', 'document_index': 0}], model='fake')


@pytest.fixture
def fake():
    holder = {}

    def install(builder=None, refuse=False):
        p = FakeProvider(builder, refuse)
        set_provider(p)
        holder['p'] = p
        return p
    yield install
    set_provider(None)


def _fields(model, seen=None):
    seen = seen or set()
    names = set()
    for name, f in model.model_fields.items():
        names.add(name)
        ann = f.annotation
        for sub in getattr(ann, '__args__', ()) + (ann,):
            if isinstance(sub, type) and issubclass(sub, schemas.BaseModel) and sub not in seen:
                seen.add(sub)
                names |= _fields(sub, seen)
    return names


@pytest.mark.parametrize('schema', [schemas.JobAnalysis, schemas.EvidenceAnalysis, schemas.JustificationDraft,
                                    schemas.InterviewScript, schemas.DevelopmentSuggestions, schemas.GuidingQuestions])
def test_schemas_have_no_scoring_fields(schema):
    assert not (_fields(schema) & FORBIDDEN)


def test_pseudonymizer(org):
    anon = Pseudonymizer(org.emp)
    out = anon('Katarzyna Nowicka przygotowała; Pani Nowickiej podziękowano, Katarzynie też.')
    assert 'Nowick' not in out and 'Katarzyn' not in out and out.count('Oceniany') == 3


def test_form_of_address_from_hr_data(org, api, fake):
    from apps.assistant.service import Pseudonymizer
    org.emp.form_of_address = 'PANI'
    org.emp.save()
    assert Pseudonymizer(org.emp)('Katarzyna Nowicka przygotowała raport') == 'Oceniana przygotowała raport'
    p = fake(lambda s, pr: schemas.InterviewScript(goal='g', preparation_checklist=[], opening='o', sections=[],
                                                    strengths_feedback=[], development_feedback=[],
                                                    development_dialogue_questions=[], closing='c',
                                                    formal_reminders=[], difficult_moments_tips=[]))
    a = create(api, org.sup, org.emp)
    assert api(org.sup).post(f"/api/v1/assessments/{a['id']}/assistant/interview-script/", {}, format='json').status_code == 200
    assert '„Pani”' in p.calls[0]['prompt']
    # brak danych kadrowych → forma neutralna, bez zgadywania z imienia
    org.emp.form_of_address = ''
    org.emp.save()
    api(org.sup).post(f"/api/v1/assessments/{a['id']}/assistant/interview-script/", {}, format='json')
    assert 'Nie zgaduj' in p.calls[1]['prompt'] and 'Oceniany' in Pseudonymizer(org.emp)('Nowicka')
    # formę ustawia kadra, nie przełożony
    assert api(org.sup).patch(f'/api/v1/employees/{org.emp.id}/', {'form_of_address': 'PAN'}, format='json').status_code == 403
    assert api(org.hr).patch(f'/api/v1/employees/{org.emp.id}/', {'form_of_address': 'PANI'}, format='json').status_code == 200


def evidence_builder(crit_ids):
    def build(schema, prompt):
        assert schema is schemas.EvidenceAnalysis
        return schemas.EvidenceAnalysis(
            overview='ok',
            mappings=[schemas.EvidenceMapping(evidence_id=crit_ids['ev'], indicator_id=crit_ids['ind'],
                                              observed_behaviour='x', closest_anchor_level=4, anchor_rationale='r',
                                              completeness='missing_result'),
                      schemas.EvidenceMapping(evidence_id=999999, indicator_id=None, observed_behaviour='halucynacja',
                                              closest_anchor_level=9, anchor_rationale='', completeness='complete')],
            indicators_without_evidence=[], missing_evidence_prompts=['Jaki był rezultat?'], neutrality_issues=[],
            bias_warnings=[], strengths=[], development_areas=[], interview_topics=[])
    return build


def test_analyze_evidence_filters_and_pseudonymizes(org, api, fake):
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    crit = a['criteria'][0]
    ind = crit['selected_indicators'][0]
    ev = c.post('/api/v1/evidence/', {'criterion': crit['id'], 'indicator': ind,
                                      'situation': 'Katarzyna Nowicka pomogła zespołowi', 'action': 'Podzieliła sprawy'},
                format='json').data
    p = fake(evidence_builder({'ev': ev['id'], 'ind': ind}))
    r = c.post(f"/api/v1/assessments/{a['id']}/assistant/analyze-evidence/", {'criterion': crit['id']}, format='json')
    assert r.status_code == 200, r.data
    res = r.data['result']
    assert [m['evidence_id'] for m in res['mappings']] == [ev['id']]
    assert r.data['ai_generated'] is True
    assert 'Nowicka' not in p.calls[0]['prompt'] and 'Oceniany' in p.calls[0]['prompt']
    assert 'Nie wystawiasz ocen' in p.calls[0]['system'][0]
    assert len(crit['selected_indicators']) - 1 == len(res['indicators_without_evidence'])
    log = AIInteraction.objects.get()
    assert log.feature == 'analyze_evidence' and log.assessment_id == a['id']
    assert c.post(f'/api/v1/assistant/interactions/{log.id}/outcome/', {'outcome': 'ACCEPTED'},
                  format='json').status_code == 204


def test_justification_requires_supervisor_score(org, api, fake):
    fake(lambda s, p: schemas.JustificationDraft(draft='d', consistency_warnings=[], missing_points=[]))
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    crit = a['criteria'][0]
    r = c.post(f"/api/v1/assessments/{a['id']}/assistant/draft-justification/", {'criterion': crit['id']}, format='json')
    assert r.status_code == 400 and 'nie proponuje ocen' in r.data['detail']
    c.patch(f"/api/v1/criteria/{crit['id']}/", {'score': 7}, format='json')
    r = c.post(f"/api/v1/assessments/{a['id']}/assistant/draft-justification/", {'criterion': crit['id']}, format='json')
    assert r.status_code == 200 and r.data['result']['draft'] == 'd'


def test_refusal_and_disabled(org, api, fake):
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    set_provider(None)
    r = c.post(f"/api/v1/assessments/{a['id']}/assistant/interview-script/", {}, format='json')
    assert r.status_code == 503
    fake(refuse=True)
    r = c.post(f"/api/v1/assessments/{a['id']}/assistant/interview-script/", {}, format='json')
    assert r.status_code == 422
    assert AIInteraction.objects.filter(error__startswith='AssistantRefused').exists()


def test_only_evaluator_uses_assistant(org, api, fake):
    fake(lambda s, p: None)
    a = create(api, org.sup, org.emp)
    r = api(org.hr).post(f"/api/v1/assessments/{a['id']}/assistant/interview-script/", {}, format='json')
    assert r.status_code == 403


def test_job_analysis_filters_invalid_codes(org, api, fake):
    def build(schema, prompt):
        return schemas.JobAnalysis(
            manages_people=False, suggested_form='PERIODIC_C', form_rationale='r', key_duties=['a'],
            additional_criteria=[schemas.CriterionSuggestion(competency_code=x, rationale='r') for x in
                                 ('orientacja-na-klienta', 'rzetelnosc', 'nie-istnieje', 'kreatywnosc', 'negocjowanie')],
            priority_indicators=[schemas.IndicatorPriority(indicator_id=10 ** 6, rationale='x')],
            expectations_draft='e', goals_suggestions=[], caveats=[])
    fake(build)
    a = create(api, org.sup, org.emp)
    r = api(org.sup).post(f"/api/v1/assessments/{a['id']}/assistant/analyze-job-description/", {}, format='json')
    res = r.data['result']
    assert [x['competency_code'] for x in res['additional_criteria']] == ['orientacja-na-klienta', 'kreatywnosc',
                                                                          'negocjowanie']
    assert res['priority_indicators'] == []


def test_guiding_questions_cached(org, api, fake):
    def build(schema, prompt):
        import re
        ids = [int(x) for x in re.findall(r'- \[(\d+)\]', prompt)]
        return schemas.GuidingQuestions(items=[schemas.IndicatorQuestions(indicator_id=i, questions=['q?']) for i in ids])
    p = fake(build)
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    crit = a['criteria'][0]
    url = f"/api/v1/assessments/{a['id']}/assistant/guiding-questions/"
    assert c.post(url, {'criterion': crit['id']}, format='json').status_code == 200
    assert c.post(url, {'criterion': crit['id']}, format='json').status_code == 200
    assert len(p.calls) == 1 and GuidingQuestionCache.objects.count() == len(crit['selected_indicators'])


def test_formal_chat_cites_sources_and_keeps_history(org, api, fake):
    LegalChunk.objects.create(kind='FAQ', source='faq', title='Pytania i odpowiedzi: sprzeciw', page=1,
                              text='Pytanie: termin na sprzeciw od oceny okresowej. Odpowiedź: 7 dni od zapoznania.')
    LegalChunk.objects.create(kind='GUIDE', source='y.pdf', title='Poradnik', page=2, text='egzamin służba przygotowawcza')
    p = fake()
    c = api(org.sup)
    conv = c.post('/api/v1/assistant/conversations/', {'mode': 'FORMAL'}, format='json').data
    r = c.post(f"/api/v1/assistant/conversations/{conv['id']}/messages/", {'content': 'Jaki jest termin na sprzeciw od oceny?'},
               format='json')
    assert r.status_code == 200 and r.data['grounded'] and r.data['citations'][0]['cited_text'] == '7 dni'
    assert p.calls[0]['documents'][0]['title'].startswith('Pytania i odpowiedzi')
    c.post(f"/api/v1/assistant/conversations/{conv['id']}/messages/", {'content': 'A czy termin sprzeciwu się wydłuża?'},
           format='json')
    assert [h['role'] for h in p.calls[1]['history']] == ['user', 'assistant']
    detail = c.get(f"/api/v1/assistant/conversations/{conv['id']}/").data
    assert len(detail['messages']) == 4
    # rozmowy są prywatne
    assert api(org.other_sup).get(f"/api/v1/assistant/conversations/{conv['id']}/").status_code == 404


def test_formal_chat_refuses_without_sources(org, api, fake, settings):
    settings.ASSISTANT_MIN_RETRIEVAL_SCORE = 0.1  # mini-korpus testowy ma niskie IDF
    LegalChunk.objects.create(kind='FAQ', source='faq', title='Q', page=1, text='sprzeciw od oceny okresowej 7 dni')
    p = fake()
    c = api(org.sup)
    conv = c.post('/api/v1/assistant/conversations/', {'mode': 'FORMAL'}, format='json').data
    r = c.post(f"/api/v1/assistant/conversations/{conv['id']}/messages/", {'content': 'Jaka jest stolica Francji?'},
               format='json')
    assert r.status_code == 200 and r.data['grounded'] is False and 'nie znalazłem' in r.data['content']
    assert p.calls == []  # bez wywołania modelu
    # pytanie spoza tematu po pytaniu z tematu nie „pożycza” źródeł
    c.post(f"/api/v1/assistant/conversations/{conv['id']}/messages/", {'content': 'Termin na sprzeciw od oceny?'}, format='json')
    r = c.post(f"/api/v1/assistant/conversations/{conv['id']}/messages/", {'content': 'Jaka jest prognoza pogody na jutro?'},
               format='json')
    assert r.data['grounded'] is False and len(p.calls) == 1


def test_interview_chat_uses_assessment_material(org, api, fake):
    p = fake()
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    crit = a['criteria'][0]
    c.post('/api/v1/evidence/', {'criterion': crit['id'], 'situation': 'Katarzyna Nowicka przygotowała raport'},
           format='json')
    assert c.post('/api/v1/assistant/conversations/', {'mode': 'INTERVIEW'}, format='json').status_code == 400
    conv = c.post('/api/v1/assistant/conversations/', {'mode': 'INTERVIEW', 'assessment': a['id']}, format='json').data
    r = c.post(f"/api/v1/assistant/conversations/{conv['id']}/messages/",
               {'content': 'Jakie pytania zadać Katarzynie na rozmowie?'}, format='json')
    assert r.status_code == 200
    call = p.calls[0]
    assert call['documents'][0]['title'] == 'Materiał z oceny' and 'Nowicka' not in call['documents'][0]['text']
    assert 'Katarzyn' not in call['prompt']
    # inny przełożony nie otworzy rozmowy do cudzej oceny
    r = api(org.other_sup).post('/api/v1/assistant/conversations/', {'mode': 'INTERVIEW', 'assessment': a['id']},
                                format='json')
    assert r.status_code in (403, 404)


@pytest.mark.live_claude
@pytest.mark.skipif(not os.environ.get('ANTHROPIC_API_KEY'), reason='brak ANTHROPIC_API_KEY')
def test_live_analyze_evidence(org, api, settings):
    settings.ASSISTANT_ENABLED = True
    settings.ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    crit = next(x for x in a['criteria'] if x['competency_code'] == 'wspolpraca')
    c.post('/api/v1/evidence/', {'criterion': crit['id'], 'indicator': crit['selected_indicators'][0],
                                 'situation': 'Zaległości w zespole w marcu.',
                                 'action': 'Zaproponowała podział wniosków i przejęła sprawy wymagające uzgodnień.',
                                 'result': 'Zaległości zlikwidowano w 3 tygodnie.'}, format='json')
    r = c.post(f"/api/v1/assessments/{a['id']}/assistant/analyze-evidence/", {'criterion': crit['id']}, format='json')
    assert r.status_code == 200, r.data
    assert r.data['result']['mappings']


def test_formal_gate_on_real_knowledge_base(org, api, fake):
    """Na pełnej bazie wiedzy: pytania merytoryczne idą do modelu, pytania spoza tematu — nie."""
    from django.core.management import call_command
    call_command('ingest_legal_docs', stdout=open(os.devnull, 'w'))
    p = fake()
    c = api(org.sup)
    conv = c.post('/api/v1/assistant/conversations/', {'mode': 'FORMAL'}, format='json').data
    url = f"/api/v1/assistant/conversations/{conv['id']}/messages/"
    for q in ('Jaka jest jutro pogoda w Warszawie?', 'Kto wygrał mundial w 2022?', 'Jak upiec sernik?'):
        r = c.post(url, {'content': q}, format='json')
        assert r.data['grounded'] is False, q
    assert p.calls == []
    for q in ('Ile kryteriów dodatkowych można wybrać i kiedy?', 'Kiedy pierwsza ocena jest negatywna?',
              'Jaki jest termin na sprzeciw od oceny okresowej?', 'Kiedy po negatywnej ocenie przeprowadza się kolejną?',
              'Co z terminem oceny przy nieobecności pracownika dłuższej niż miesiąc?'):
        n = len(p.calls)
        c.post(url, {'content': q}, format='json')
        assert len(p.calls) == n + 1, q
