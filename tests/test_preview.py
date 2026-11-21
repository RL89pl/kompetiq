"""Przejrzystość AI: podgląd wysyłki do modelu — bez wywołania modelu, bez zapisu, z kontrolą danych osobowych."""
from apps.assistant.models import AIInteraction, Conversation, LegalChunk, Message
from apps.employees.models import Employee
from tests.test_api_flow import create

URL = '/api/v1/assistant/preview/'


def _evidence(c, a, situation):
    crit = a['criteria'][0]
    c.post('/api/v1/evidence/', {'criterion': crit['id'], 'situation': situation, 'action': 'Przygotowała zestawienie.',
                                 'result': 'Raport przekazano w terminie.'}, format='json')
    return crit


def test_preview_pseudonymizes_and_writes_nothing(org, api):
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    _evidence(c, a, 'Katarzyna Nowicka przygotowała raport kwartalny dla Nowickiej z innego wydziału.')
    before = (AIInteraction.objects.count(), Conversation.objects.count(), Message.objects.count())
    r = c.post(URL, {'feature': 'interview-script', 'assessment': a['id']}, format='json')
    assert r.status_code == 200, r.data
    d = r.data
    assert d['would_call_model'] is True and len(d['calls']) == 1
    sent = d['calls'][0]['prompt'] + ''.join(d['calls'][0]['system'])
    assert 'Nowick' not in sent and 'Katarzyna' not in sent and 'Oceniany' in sent
    assert all(ch['ok'] for ch in d['checks']), d['checks']
    # schemat odpowiedzi bez pól ocen
    assert 'score' not in str(d['calls'][0]['response_schema']).lower()
    assert (AIInteraction.objects.count(), Conversation.objects.count(), Message.objects.count()) == before


def test_preview_flags_other_persons_name_in_free_text(org, api):
    Employee.objects.create(institution=org.inst, org_unit=org.unit, supervisor=org.sup, first_name='Zbigniew',
                            last_name='Wiśniewski', position='Referent')
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    _evidence(c, a, 'Wspólnie ze Zbigniewem Wiśniewskim przygotowała raport.')
    d = c.post(URL, {'feature': 'interview-script', 'assessment': a['id']}, format='json').data
    check = next(ch for ch in d['checks'] if ch['label'].startswith('Brak nazwisk osób z urzędu'))
    assert check['ok'] is False and 'Wiśniewski' in check['detail']


def test_preview_formal_chat_without_sources_does_not_call_model(org, api):
    LegalChunk.objects.create(kind='FAQ', source='faq', title='Q', page=1, text='sprzeciw od oceny okresowej 7 dni')
    d = api(org.sup).post(URL, {'feature': 'chat-formal', 'question': 'Jaka jest stolica Francji?'}, format='json').data
    assert d['would_call_model'] is False and d['calls'] == [] and 'nie znalazłem' in d['reason']
    assert not Conversation.objects.exists()


def test_preview_formal_chat_shows_sources(org, api, settings):
    settings.ASSISTANT_MIN_RETRIEVAL_SCORE = 0.1  # mini-korpus testowy ma niskie IDF
    LegalChunk.objects.create(kind='FAQ', source='faq', title='Pytania i odpowiedzi: sprzeciw', page=1,
                              text='Termin na sprzeciw od oceny okresowej wynosi 7 dni od zapoznania się z oceną.')
    d = api(org.sup).post(URL, {'feature': 'chat-formal', 'question': 'Jaki jest termin na sprzeciw od oceny?'},
                          format='json').data
    assert d['would_call_model'] is True
    assert d['calls'][0]['documents'][0]['title'].startswith('Pytania i odpowiedzi')


def test_preview_permissions_and_validation(org, api):
    a = create(api, org.sup, org.emp)
    assert api(org.other_sup).post(URL, {'feature': 'interview-script', 'assessment': a['id']},
                                   format='json').status_code in (403, 404)
    c = api(org.sup)
    assert c.post(URL, {'feature': 'nieznana'}, format='json').status_code == 400
    assert c.post(URL, {'feature': 'interview-script'}, format='json').status_code == 400
    assert c.post(URL, {'feature': 'analyze-evidence', 'assessment': a['id']}, format='json').status_code == 400
