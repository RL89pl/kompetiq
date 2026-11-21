# Kompas Kompetencji

Asystent przełożonego w służbie cywilnej. Prowadzi przez **pierwszą ocenę** (rozp. PRM z 23.07.2015, Dz.U. poz. 1144)
i **ocenę okresową** (rozp. PRM z 4.04.2016, Dz.U. poz. 470; arkusze B i C, model danych obsługuje też A).
Łączy model kompetencji (14 kompetencji, 49 wskaźników, 5 poziomów), formularze ocen, pomoc formalną,
przygotowanie rozmowy oceniającej i plan rozwoju.

**Zasada nadrzędna:** AI porządkuje materiał, wskazuje braki i proponuje sformułowania, ale **nie wystawia ocen**.
Oceny cząstkowe przyznaje przełożony, a wynik (pozytywna/negatywna) wylicza deterministycznie kod zgodny z przepisami
(`apps/assessments/scoring.py`). Schematy odpowiedzi AI nie mają pól z punktacją, co sprawdzają testy.

## Ścieżka oceny

1. Analiza opisu stanowiska: arkusz (§ 3), kryteria dodatkowe (maks. 3), wskaźniki.
2. Ustalenie kryteriów lub rozmowa wstępna: daty, oczekiwania, cele, terminy wyliczane z przepisów.
3. Przykłady zachowań (sytuacja, działanie, rezultat), pomocnicze oceny wskaźników, „brak podstaw do oceny”.
4. Oceny cząstkowe z uzasadnieniami. Dla pierwszej oceny także sprawozdanie i egzamin.
5. Rozmowa oceniająca: scenariusz (SBI, pytania, elementy formalne, trudne momenty).
6. Wnioski rozwojowe i IPRZ: działania 70-20-10 z miernikami, potem monitorowanie realizacji.
7. Sporządzenie oceny: lista kontrolna, potwierdzenie przez kierującego (pierwsza ocena), zapoznanie, eksport DOCX.

## Struktura

```
kompetiq/          konfiguracja Django (settings z env, urls, widok SPA)
apps/
  institutions/    instytucje (tenant), komórki, role, logowanie, seed_demo
  employees/       pracownicy, opisy stanowisk (import OSP z .docx)
  competencies/    model kompetencji + import z docs_assets/Model_kompetencji.xlsx
  assessments/     arkusze (forms_config), scoring, workflow (maszyna stanów), checklist, API
  development/     plany i działania rozwojowe
  deadlines/       terminy z przepisów, przypomnienia, powiadomienia, panel HR
  assistant/       dostawcy LLM (OpenAI-compatible / Claude), rozmowy, baza wiedzy, pseudonimizacja, log AIInteraction
  documents/       eksport arkuszy, scenariusza rozmowy i planu rozwoju do PDF i DOCX
frontend/          React + TypeScript + Vite + Tailwind (build -> frontend/dist -> /static/spa/)
docs_assets/       materiały źródłowe: rozporządzenia, poradniki, wzory arkuszy, model kompetencji
tests/             pytest (scoring, terminy, import, API, izolacja instytucji, uprawnienia, asystent)
```

Role: `SUPERVISOR` (oceniający, widzi swoich pracowników), `UNIT_HEAD` (kierujący komórką, potwierdza
pierwszą ocenę), `HR` (podgląd wszystkiego w instytucji, zmienia dane kadrowe), `ADMIN`. Każde zapytanie
jest zawężane do aktywnej instytucji. Zmiany ocen są audytowane (`django-simple-history`).

## Uruchomienie lokalne

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
export DJANGO_DEBUG=1
.venv/bin/python manage.py migrate
.venv/bin/python manage.py import_competency_model
.venv/bin/python manage.py ingest_legal_docs
DEMO_PASSWORD='…' .venv/bin/python manage.py seed_demo     # konta: przelozony, kierownik, kadry, admin
.venv/bin/python manage.py runserver

cd frontend && npm install && npm run dev                  # http://localhost:5173 (proxy /api -> :8000)
```

Asystent AI wymaga wskazania dostawcy modelu w `.env` (np. Groq: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`;
PLLuM na własnym GPU; Claude: `ANTHROPIC_API_KEY`). Opcje opisuje `.env.example` i `docs/02_wykorzystanie_ai.md`.
Bez konfiguracji aplikacja działa, a funkcje AI zwracają czytelny komunikat.

Przypomnienia o terminach: `manage.py send_reminders` (codziennie z crona hosta).

Testy: `.venv/bin/pytest -q`. Test z prawdziwym Claude API: `pytest -m live_claude` (wymaga klucza).

## Dokumentacja projektu

- [Opis projektu](docs/01_opis_projektu.md)
- [Wykorzystanie AI](docs/02_wykorzystanie_ai.md) — w tym rekomendacja dostawcy modelu
- [Technologie i architektura](docs/03_architektura.md)
- [Zabezpieczenia przed wdrożeniem produkcyjnym](docs/04_bezpieczenstwo_i_wdrozenie.md)
- [Scenariusz demonstracji](docs/05_scenariusz_demo.md)
- [Zgodność z wymaganiami wyzwania](docs/06_zgodnosc_z_wymaganiami.md)
- [Role i uprawnienia](docs/07_role_i_uprawnienia.md)

## Wdrożenie (Docker + nginx na hoście)

Aplikacja działa w Docker Compose (`db` – PostgreSQL, `web` – gunicorn na `127.0.0.1:${WEB_PORT}`).
nginx działa na hoście poza kontenerami: serwuje `/static/` z `./public/static`, a resztę przekazuje do
kontenera (przykład w `kompetiq.nginx`). Frontend budowany jest w wieloetapowym `Dockerfile` i trafia do
`public/static/spa/` przez `collectstatic`.

```bash
cp .env.example .env    # uzupełnij hasła, SECRET_KEY, hosty, ANTHROPIC_API_KEY
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py collectstatic --noinput
docker compose exec -T web python manage.py import_competency_model --if-missing
docker compose exec -T web python manage.py ingest_legal_docs
docker compose exec web python manage.py createsuperuser
```

Ten sam zestaw kroków wykonuje `.github/workflows/deploy.yml` (SSH, `git reset`, `compose up`).

## Dane osobowe i AI

- Do API wysyłany jest materiał pseudonimizowany: imię i nazwisko ocenianego są zastępowane słowem „Oceniany”.
- Każde wywołanie AI jest rejestrowane (`AIInteraction`): funkcja, model, tokeny, czas, skrót żądania i to,
  czy przełożony przyjął, zredagował czy odrzucił sugestię.
- Asystent formalny odpowiada wyłącznie na podstawie fragmentów rozporządzeń i poradników, z cytowaniem źródeł.
- Dostawcę modelu wybiera konfiguracja (`apps/assistant/client.py`, interfejs `LLMProvider`): serwer zgodny
  z OpenAI (Groq, Gemini, Mistral, vLLM z PLLuM, Ollama z Bielikiem) albo Claude API.
- Gdy wyszukiwanie w bazie wiedzy nie znajdzie źródeł, asystent formalny nie wywołuje modelu i komunikuje brak informacji.
