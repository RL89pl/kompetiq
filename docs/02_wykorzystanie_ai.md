# Wykorzystanie sztucznej inteligencji

## Zasady

1. **AI doradza, przełożony decyduje.** Asystent nie proponuje ocen punktowych, poziomu ogólnego ani wyniku.
   Wymusza to kod: schematy odpowiedzi AI nie mają pól z punktacją (test automatyczny), a wynik oceny liczy
   deterministyczny moduł `apps/assessments/scoring.py` na podstawie ocen przełożonego i przepisów.
2. **Odpowiedzi ze źródeł.** Asystent formalny dostaje tylko wyszukane fragmenty bazy wiedzy, musi je cytować,
   a gdy wyszukiwanie nie znajdzie dopasowania powyżej progu, system **nie wywołuje modelu** i odpowiada wprost,
   że w bazie wiedzy brak informacji.
3. **Minimalizacja danych.** Imię i nazwisko ocenianego są zastępowane słowem „Oceniany” przed wysłaniem do modelu.
   Do modelu trafia tylko materiał potrzebny do danej funkcji.
4. **Rozliczalność.** Każde wywołanie jest rejestrowane (funkcja, model, tokeny, czas, skrót treści), wraz z decyzją
   przełożonego: sugestia przyjęta, przyjęta po edycji albo odrzucona.
5. **Treść AI jest zawsze oznaczona** („Sugestia AI, do weryfikacji”) i wymaga świadomego wstawienia.

## Gdzie działa AI

| Miejsce | Funkcja | Czego AI nie robi |
|---|---|---|
| Analiza opisu stanowiska | arkusz zgodny z § 3, kryteria dodatkowe, wskaźniki istotne dla stanowiska, projekt oczekiwań i celów | nie zmienia arkusza ani kryteriów bez decyzji przełożonego |
| Ocena zachowań | pytania pomocnicze do wskaźników; analiza przykładów: przypisanie do wskaźników, kompletność SDR, braki, sformułowania nieneutralne, ryzyko błędów oceniania | nie ocenia kompetencji; sugerowany poziom liczy kod z wyborów przełożonego |
| Oceny cząstkowe | projekt uzasadnienia **ustalonej już** oceny, ostrzeżenia o niespójności z materiałem | nie proponuje oceny (bez oceny przełożonego funkcja jest zablokowana) |
| Rozmowa oceniająca | scenariusz rozmowy; rozmowa z asystentem: pytania, kwestie do omówienia, porządkowanie argumentów | nie wymyśla faktów spoza materiału |
| Plan rozwoju | działania 70-20-10 z miernikami, projekt wniosków do arkusza | nie zapisuje działań bez akceptacji |
| Asystent formalny (rozmowa) | wyjaśnianie przepisów i procedury z cytowaniem źródeł | nie odpowiada bez oparcia w bazie wiedzy |

Bez AI działają: import OSP, sugerowany poziom kompetencji, wyliczenia wyniku, lista kontrolna, terminy,
przypomnienia i dokumenty.

## Baza wiedzy

Budowana komendą `manage.py ingest_legal_docs` z `docs_assets/`:
- ustawa o służbie cywilnej, tekst jednolity Dz.U. 2026 poz. 590 (stan prawny na 14.04.2026, pobrany z ISAP/ELI); przy kolejnym tekście jednolitym wystarczy podmienić PDF i ponownie zbudować bazę,
- rozporządzenie o pierwszej ocenie (2015) i o ocenach okresowych (2016) wraz z załącznikiem — wykazem kryteriów,
- poradniki KPRM (pierwsza ocena, oceny okresowe),
- model kompetencji (wszystkie wskaźniki i opisy poziomów),
- zestaw 29 pytań i odpowiedzi z podstawą prawną (`apps/assistant/knowledge/faq.json`).

Wyszukiwanie jest deterministyczne (BM25 na rdzeniach wyrazów, bez zewnętrznych usług). Każda odpowiedź podaje
tytuł źródła i stronę; zestaw pytań i odpowiedzi ma pierwszeństwo przy typowych pytaniach.

## Model językowy — wybór bez zmian w kodzie

Warstwa `apps/assistant/client.py` (`LLMProvider`) obsługuje:
- **dowolny serwer zgodny z OpenAI** (`ASSISTANT_PROVIDER=openai_compat`): Groq, Google Gemini, Mistral,
  OpenRouter, a także model uruchomiony w infrastrukturze urzędu przez vLLM lub Ollama (PLLuM, Bielik).
  Odpowiedzi ustrukturyzowane są walidowane schematem (Pydantic) z automatyczną korektą, a cytowania
  wyznaczane z numerów źródeł;
- **Claude API** (`ASSISTANT_PROVIDER=anthropic`): natywne cytowania i strukturyzowane odpowiedzi.

### Rekomendacja

| Etap | Rozwiązanie | Uzasadnienie |
|---|---|---|
| Hackathon (darmowe narzędzia) | **Groq, plan darmowy**, model `openai/gpt-oss-120b` | bez opłat, szybki; według warunków dane nie są domyślnie używane do treningu, dostępna opcja Zero Data Retention; dane ocenianego i tak pseudonimizowane |
| Alternatywa darmowa | Google Gemini (plan darmowy) | w UE/EOG deklarowane warunki jak w planie płatnym — do potwierdzenia w regulaminie |
| Wdrożenie w MC | **PLLuM** (model MC, licencja otwarta) przez vLLM na serwerze z GPU (`docker compose --profile pllum up`) | dane osobowe nie opuszczają infrastruktury urzędu; polski model dla administracji |
| Wdrożenie — wariant chmurowy | Claude / inny model z umową powierzenia i regionem UE | najwyższa jakość odpowiedzi; wymaga umowy powierzenia przetwarzania |

Przed użyciem jakiegokolwiek planu darmowego potwierdź aktualne warunki przetwarzania danych u dostawcy.

### Rozmiar zapytań

Każda funkcja dostaje tylko potrzebny fragment modelu kompetencji (np. analiza przykładów — jedną kompetencję),
a źródła są przycinane do wycinków wokół szukanych słów (`ASSISTANT_CONTEXT_CHARS`). Pojedyncze wywołanie to
ok. 1–4,5 tys. tokenów promptu, co mieści się w minutowych limitach darmowych planów i w oknie kontekstu
mniejszych modeli uruchamianych lokalnie.

### PLLuM na serwerze bez GPU

Usługa `llm` w `docker-compose.yml` (vLLM) wymaga karty NVIDIA. Na serwerze z samym procesorem PLLuM można
uruchomić w kontenerze Ollama z modelem w formacie GGUF, np. `Llama-PLLuM-8B-instruct` w kwantyzacji Q4_K_M
(ok. 5 GB, licencja Llama 3.1). Odpowiedzi trwają wtedy od kilkudziesięciu sekund do ok. 2 minut, co wystarcza
do pilotażu z niewielką liczbą użytkowników; `LLM_TIMEOUT` i timeouty gunicorn/nginx trzeba odpowiednio zwiększyć.
