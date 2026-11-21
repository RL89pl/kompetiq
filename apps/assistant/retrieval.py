"""Deterministyczny wyszukiwacz w bazie wiedzy (BM25 na rdzeniach wyrazów).

Korpus to kilkaset fragmentów — mieści się w pamięci, bez zależności od rozszerzeń bazy danych.
Zwraca wyniki z oceną dopasowania; poniżej progu asystent komunikuje brak informacji.
"""
import math
import re
from collections import Counter

from .models import LegalChunk, visible_chunks

WORD = re.compile(r'[a-ząćęłńóśźż0-9]+', re.I)
STOP = set('oraz jest który która które przez jeżeli jako także albo może można danego dnia tego tych '
           'się dla nie ich jego jej lub czy jak ale już tym tak jaki jaka jakie kiedy co to być kto czym podaj'.split())
KIND_BOOST = {LegalChunk.Kind.FAQ: 1.25, LegalChunk.Kind.REGULATION: 1.1, LegalChunk.Kind.ACT: 1.1}


def stems(text):
    out = []
    for w in WORD.findall(text.lower()):
        if len(w) < 3 or w in STOP:
            continue
        out.append(w[:6] if not w.isdigit() else w)
    return out


def search_scored(query, k=6, kinds=None, institution=None):
    """institution — urząd użytkownika: wspólne źródła (bez wyłączonych w urzędzie) i źródła własne urzędu."""
    qs = visible_chunks(institution)
    if kinds:
        qs = qs.filter(kind__in=kinds)
    chunks = list(qs)
    if not chunks:
        return []
    docs = [Counter(stems(f'{c.title} {c.text}')) for c in chunks]
    n = len(docs)
    avg = sum(sum(d.values()) for d in docs) / n
    q = set(stems(query))
    df = {t: sum(1 for d in docs if t in d) for t in q}
    scored = []
    for c, d in zip(chunks, docs):
        length = sum(d.values()) or 1
        s = 0.0
        for t in q:
            if t in d:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                tf = d[t]
                s += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / avg))
        if s > 0:
            scored.append((s * KIND_BOOST.get(c.kind, 1.0), c))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def coverage(query, scored, top=3):
    """Największy udział rdzeni pytania obecnych w jednym z najlepszych fragmentów (0–1).

    Sam wynik BM25 nie odróżnia pytań spoza tematu: jedno rzadkie słowo (np. „Warszawa” ze stopki poradnika)
    daje wysoki wynik. Pytanie merytoryczne pokrywa większość swoich słów w jednym fragmencie.
    """
    q = set(stems(query))
    if not q:
        return 0.0
    return max((len(q & set(stems(f'{c.title} {c.text}'))) / len(q) for _, c in scored[:top]), default=0.0)


def search(query, k=6, institution=None):
    return [c for _, c in search_scored(query, k, institution=institution)]


def excerpt(text, query, size=2200):
    """Wycinek tekstu o długości ~size wokół miejsca z największym zagęszczeniem słów z pytania."""
    if len(text) <= size:
        return text
    q = set(stems(query))
    words = [(m.start(), (m.group(0).lower()[:6])) for m in WORD.finditer(text)]
    hits = [pos for pos, w in words if w in q]
    if not hits:
        return text[:size] + ' […]'
    best, best_n = hits[0], 0
    j = 0
    for i, pos in enumerate(hits):
        while hits[j] < pos - size // 2:
            j += 1
        if i - j + 1 > best_n:
            best_n, best = i - j + 1, hits[(i + j) // 2]
    start = max(0, best - size // 2)
    start = text.rfind('\n', 0, start) + 1 if text.rfind('\n', 0, start) > start - 200 else start
    chunk = text[start:start + size]
    return ('[…] ' if start else '') + chunk + (' […]' if start + size < len(text) else '')


def build_context(scored, query, budget):
    """Dokumenty dla modelu w limicie znaków: najlepsze fragmenty, każdy przycięty do wycinka."""
    docs, used = [], 0
    for score, c in scored:
        room = budget - used
        if room < 600:
            break
        text = excerpt(c.text, query, size=min(2400, room))
        docs.append((score, c, text))
        used += len(text)
    return docs
