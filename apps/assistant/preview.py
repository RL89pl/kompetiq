"""Przejrzystość AI: podgląd dokładnej treści, która zostałaby wysłana do modelu, z kontrolą danych osobowych.

Funkcja asystenta wykonuje się normalnie (te same prompty, pseudonimizacja i wyszukiwanie źródeł), ale:
- zamiast dostawcy modelu działa CaptureProvider — zapytanie jest zapisywane, nie wysyłane,
- całość działa w transakcji wycofywanej na końcu — podgląd niczego nie zapisuje (rozmowy, rejestru, pamięci).
"""
import json
import re
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.employees.models import Employee

from . import service
from .client import PreviewCaptured, capture_calls, provider_info
from .models import Conversation

FEATURE_LABELS = {
    'analyze-job-description': 'Analiza opisu stanowiska',
    'guiding-questions': 'Pytania pomocnicze do wskaźników',
    'analyze-evidence': 'Analiza przykładów zachowań',
    'draft-justification': 'Projekt uzasadnienia',
    'interview-script': 'Scenariusz rozmowy oceniającej',
    'development-suggestions': 'Propozycje działań rozwojowych',
    'chat-formal': 'Rozmowa: zasady i wymagania formalne',
    'chat-interview': 'Rozmowa: przygotowanie do rozmowy z pracownikiem',
}
EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PESEL = re.compile(r'(?<!\d)\d{11}(?!\d)')


def destination():
    info = provider_info()
    if info['provider'] == 'anthropic':
        host = 'api.anthropic.com'
    elif info['provider'] == 'openai_compat':
        host = urlparse(settings.LLM_BASE_URL or '').hostname or ''
    else:
        host = ''
    return {'provider': info['provider'], 'model': info['model'], 'host': host, 'enabled': info['enabled']}


def _payload_text(calls):
    parts = []
    for c in calls:
        parts += [s if isinstance(s, str) else json.dumps(s, ensure_ascii=False) for s in c['system']]
        parts.append(c['prompt'])
        parts += [f"{d.get('title', '')}\n{d.get('text', '')}" for d in c['documents']]
        parts += [h.get('content', '') for h in c['history']]
    return '\n'.join(parts)


def _surname_pattern(name):
    """Nazwisko w odmianie (Nowicka, Nowickiej, Nowicką): rdzeń bez 2 ostatnich liter + do 4 liter końcówki."""
    stem = name[:max(4, len(name) - 2)]
    return re.compile(r'\b' + re.escape(stem) + r'\w{0,4}\b', re.I)


def _find(pattern, text):
    m = pattern.search(text)
    if not m:
        return ''
    start = max(0, m.start() - 40)
    return '…' + text[start:m.end() + 40].replace('\n', ' ') + '…'


def privacy_checks(text, institution, assessment):
    """Kontrole wysyłki. Każda zwraca ok/nie ok i — gdy znaleziono — fragment z miejscem wystąpienia."""
    checks = []

    def add(label, ok, detail):
        checks.append({'label': label, 'ok': ok, 'detail': detail})

    if assessment is not None:
        e = assessment.employee
        found = ''
        for n in (e.last_name,):
            if n and len(n) >= 3:
                found = found or _find(_surname_pattern(n), text)
        if e.first_name and len(e.first_name) >= 3:
            found = found or _find(re.compile(rf'\b{re.escape(e.first_name)}\b', re.I), text)
        label = 'Oceniana' if e.form_of_address == 'PANI' else 'Oceniany'
        n_label = len(re.findall(rf'\b{label}\b', text))
        add(f'Imię i nazwisko ocenianego ({e.full_name}) nie są wysyłane', not found,
            found or (f'W treści użyto słowa „{label}” ({n_label}×).' if n_label else 'Treść nie odnosi się do ocenianego z imienia.'))

    # Nazwiska wszystkich osób w urzędzie: pracowników i użytkowników (oceniający, kierujący, kadry)
    people = {(p.first_name, p.last_name) for p in Employee.objects.filter(institution=institution)}
    people |= {(u.first_name, u.last_name)
               for u in get_user_model().objects.filter(memberships__institution=institution)}
    hits = []
    for first, last in sorted(people, key=lambda x: x[1]):
        if last and len(last) >= 4 and (frag := _find(_surname_pattern(last), text)):
            hits.append(f'{first} {last}: {frag}')
    add(f'Brak nazwisk osób z urzędu (sprawdzono {len(people)} osób)', not hits,
        '; '.join(hits[:3]) or 'Żadne nazwisko pracownika ani użytkownika urzędu nie występuje w treści.')

    org = [institution.name] + list(institution.org_units.values_list('name', flat=True))
    # cała nazwa jako fraza (nie podciąg): „Wydział” nie pasuje do „wydziału” w zwykłym tekście
    org_hits = [n for n in org if n and re.search(rf'(?<!\w){re.escape(n)}(?!\w)', text, re.I)]
    add('Brak nazwy urzędu i komórek organizacyjnych', not org_hits,
        ', '.join(org_hits) or f'Sprawdzono {len(org)} nazw.')

    emails = EMAIL.findall(text)
    add('Brak adresów e-mail', not emails, ', '.join(emails[:3]) or 'Nie znaleziono.')
    pesel = PESEL.findall(text)
    add('Brak numerów PESEL (11 cyfr)', not pesel, ', '.join(pesel[:3]) or 'Nie znaleziono.')

    if assessment is not None and assessment.employee.employment_date:
        d = assessment.employee.employment_date
        found = [s for s in (d.isoformat(), d.strftime('%d.%m.%Y')) if s in text]
        add('Brak daty zatrudnienia ocenianego', not found, ', '.join(found) or 'Nie znaleziono.')
    return checks


def run_preview(request, feature, assessment=None, criterion=None, question=''):
    """Zwraca to, co zostałoby wysłane do modelu, i wynik kontroli. Nic nie zapisuje i nic nie wysyła."""
    reason = ''
    with capture_calls() as cap, transaction.atomic():
        try:
            if feature in ('chat-formal', 'chat-interview'):
                mode = Conversation.Mode.FORMAL if feature == 'chat-formal' else Conversation.Mode.INTERVIEW
                conv = Conversation.objects.create(user=request.user, institution=request.membership.institution,
                                                   assessment=assessment, mode=mode)
                msg = service.chat(request, conv, question)
                if not msg.grounded:
                    reason = msg.content
            else:
                service.run_feature(request, assessment, feature, criterion)
                reason = 'Wynik pochodzi z pamięci podręcznej — model nie zostałby wywołany.'
        except PreviewCaptured:
            reason = ''
        finally:
            transaction.set_rollback(True)

    text = _payload_text(cap.calls)
    return {
        'feature': feature,
        'feature_label': FEATURE_LABELS[feature],
        'would_call_model': bool(cap.calls),
        'reason': '' if cap.calls else reason,
        'destination': destination(),
        'calls': cap.calls,
        'characters': len(text),
        'checks': privacy_checks(text, request.membership.institution, assessment) if cap.calls else [],
        'sent': [
            'stanowisko i opis stanowiska (po pseudonimizacji)',
            'kryteria oceny, wskaźniki i fragmenty modelu kompetencji',
            'przykłady zachowań z datą, cele, oczekiwania, notatki (po pseudonimizacji)',
            'oceny cząstkowe i uzasadnienia ustalone przez przełożonego — tylko w funkcjach, które ich potrzebują',
            'fragmenty ustawy, rozporządzeń, poradników i pytań z odpowiedziami (rozmowa)',
        ],
        'not_sent': [
            'imię i nazwisko ocenianego (zastępowane słowem „Oceniany/Oceniana”)',
            'dane oceniającego i innych osób z urzędu',
            'nazwa urzędu i komórki, daty zatrudnienia i umowy, stopień służbowy',
            'loginy, adresy e-mail, identyfikatory użytkowników',
        ],
    }
