# Technologie i architektura

## Technologie

| Warstwa | Technologia |
|---|---|
| Backend | Python 3.14, Django 6.1, Django REST Framework, drf-spectacular (OpenAPI), django-simple-history (audyt) |
| Baza danych | PostgreSQL 17 (SQLite w trybie deweloperskim) |
| Frontend | React 19, TypeScript, Vite, TanStack Query, Tailwind CSS; czcionki hostowane lokalnie |
| AI | warstwa `LLMProvider`: OpenAI-compatible (Groq, Gemini, Mistral, vLLM/PLLuM, Ollama/Bielik) lub Claude API |
| Dokumenty | reportlab (PDF), python-docx (DOCX), openpyxl (import modelu), pypdf (baza wiedzy) |
| Wdrożenie | Docker Compose (PostgreSQL + gunicorn), nginx na hoście, GitHub Actions (CI, wdrożenie przez SSH) |

## Schemat

```
 Przeglądarka (komputer / tablet)
        │ HTTPS
 ┌──────▼──────────────────────── serwer ───────────────────────────────────────┐
 │ nginx (host)  ── /static/ ──► ./public/static (SPA React + pliki statyczne)  │
 │      │ proxy_pass 127.0.0.1:WEB_PORT                                          │
 │ ┌────▼──────────── docker compose ─────────────────────────────────────────┐ │
 │ │ web: gunicorn + Django                                                    │ │
 │ │   institutions  role, instytucje (multi-tenant), logowanie                │ │
 │ │   employees     pracownicy, OSP (import .docx)                            │ │
 │ │   competencies  model kompetencji (wersje)                                │ │
 │ │   assessments   arkusze, workflow, scoring, lista kontrolna   ◄── API REST│ │
 │ │   development   IPRZ, działania                                 /api/v1/  │ │
 │ │   deadlines     terminy, przypomnienia, powiadomienia, panel HR           │ │
 │ │   assistant     baza wiedzy (BM25), rozmowy, LLMProvider ────────────────┼─┼─► model LLM
 │ │   documents     PDF / DOCX                                                │ │   (Groq / Gemini /
 │ │ db: PostgreSQL                                                            │ │    PLLuM w „llm” /
 │ │ llm (opcjonalnie, profil pllum): vLLM + PLLuM na GPU                      │ │    Claude)
 │ └───────────────────────────────────────────────────────────────────────────┘ │
 │ cron hosta: manage.py send_reminders (codziennie) ──► powiadomienia + e-mail  │
 └───────────────────────────────────────────────────────────────────────────────┘
```

## Rozwój i skalowanie

- Bezstanowy backend: skalowanie poziome (`WEB_WORKERS`, kolejne repliki za nginx), sesje w bazie.
- Wielu dzierżawców (instytucji) w jednej instalacji; własne wersje modelu kompetencji per instytucja.
- Modułowe aplikacje Django z jasnymi granicami; logika przepisów w czystych funkcjach (scoring, terminy).
- Dostawca AI wymienny konfiguracją; baza wiedzy: część wspólna przebudowywana przy starcie, źródła urzędu
  z panelu „Baza wiedzy” (`08_zmiany_przepisow_i_modyfikowalnosc.md`).

## Interfejsy i integracje

- **API REST** `/api/v1/` z dokumentacją OpenAPI 3 (`/api/v1/schema/`, podgląd Swagger `/api/v1/docs/` dostępny
  bez logowania): wszystkie widoki mają opisane żądania i odpowiedzi, schemat generuje się bez ostrzeżeń
  (`manage.py spectacular --validate`). Uwierzytelnianie sesyjne + CSRF; do integracji systemowych przewidziane
  konto techniczne z rolą i tokenem (rozszerzenie DRF).
- **System kadrowy (np. QNT)**: zasilanie pracowników i komórek przez `/api/v1/employees/` (HR/administrator),
  opisy stanowisk przez `/api/v1/job-descriptions/import-osp/`.
- **EZD**: eksport arkusza do PDF (`/api/v1/assessments/{id}/export/sheet/?fmt=pdf`) gotowy do rejestracji
  w sprawie; integracja przez API EZD jako kolejny moduł.

## Uwierzytelnianie, autoryzacja, role

- Logowanie sesyjne z ochroną CSRF i limitem prób; docelowo SSO urzędu (np. SAML/OIDC z AD/Entra ID).
- Role: przełożony (swoi pracownicy), kierujący komórką (komórka, potwierdzanie pierwszej oceny),
  HR (odczyt wszystkiego w instytucji, dane kadrowe, przypomnienia), administrator.
- Izolacja instytucji na poziomie każdego zapytania; edycja oceny tylko przez oceniającego; blokada po sporządzeniu.

## Testy

`pytest` — 82 testy: przepisy (progi, warunki), terminy, import modelu, pełne ścieżki przez API, uprawnienia,
izolacja instytucji, asystent (brak pól ocen, pseudonimizacja, odmowa bez źródeł na pełnej bazie wiedzy, cytowania), baza wiedzy
urzędu (wgrywanie, izolacja, wyłączanie i zastępowanie źródeł), podgląd wysyłki do AI (brak zapisu, kontrola
danych osobowych), dostawca zgodny
z OpenAI (atrapa serwera), import OSP, PDF/DOCX, powiadomienia, przypomnienia bez duplikatów.
