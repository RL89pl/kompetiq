# Zmiany przepisów i modyfikowalność

Przepisy o ocenach w służbie cywilnej zmieniają się rzadko, ale się zmieniają: nowy tekst jednolity ustawy,
nowe rozporządzenie, nowa wersja modelu kompetencji. KompetIQ rozdziela to, co urząd zmienia sam, od tego,
co wymaga programisty, i przy każdej zmianie mówi, kto ją wykonuje.

## Kto co zmienia

| Co się zmienia | Kto | Jak | Wpływ na trwające oceny |
|---|---|---|---|
| Nowy tekst jednolity ustawy, nowe rozporządzenie, nowy poradnik (dla jednego urzędu) | administrator instytucji | **Baza wiedzy → Dodaj źródło**, z polem „Zastępuje źródło” | asystent od razu cytuje nowe źródło; stare jest wyłączone w urzędzie |
| Wewnętrzne zarządzenie, regulamin, harmonogram ocen | administrator instytucji | **Baza wiedzy → Dodaj źródło** (PDF, DOCX, TXT, MD) | asystent korzysta z nich tylko w tym urzędzie |
| Źródło nieaktualne lub błędne | administrator instytucji | **Wyłącz** (źródło wspólne) albo **Usuń** (źródło urzędu) | bez wpływu na oceny, tylko na odpowiedzi asystenta |
| Ten sam akt dla wszystkich urzędów | operator systemu | podmiana pliku w `docs_assets/` i wdrożenie (baza wiedzy przebudowuje się przy starcie) albo źródło wspólne w panelu `/admin/` | jak wyżej, we wszystkich urzędach; wyłączenia ustawione w urzędach zostają |
| Zestaw pytań i odpowiedzi | operator systemu | `apps/assistant/knowledge/faq.json` (pytanie, odpowiedź, podstawa prawna) | jak wyżej |
| Model kompetencji (nowa wersja) | operator systemu | `import_competency_model plik.xlsx --model-version 2.0`, w `/admin/` aktywna wersja | trwające oceny zostają przy swojej wersji (wersja zapisana w ocenie) |
| Model kompetencji urzędu | operator systemu | wersja modelu z przypisaną instytucją (`/admin/`) | urząd używa własnej wersji zamiast wspólnej |
| Skale, progi wyniku, kryteria obowiązkowe, arkusze | programista | `apps/assessments/forms_config.py`, `scoring.py`, `checklist.py` | zmiana kodu z testami; patrz niżej |
| Terminy (21 dni, 8 miesięcy, 24 miesiące, 7 dni na sprzeciw) | programista | `apps/deadlines/rules.py` | jak wyżej |

## Baza wiedzy asystenta (panel „Baza wiedzy”)

Dostępny dla kadr (podgląd) i administratora instytucji (zmiany). Źródła są dwóch rodzajów:

- **Wspólne**: ustawa, rozporządzenia, poradniki KPRM, model kompetencji, zestaw pytań i odpowiedzi.
  Pochodzą z `docs_assets/` i są przebudowywane przy każdym starcie aplikacji (`ingest_legal_docs`). Urząd ich
  nie usuwa, ale może je **wyłączyć u siebie**.
- **Urzędu**: wgrane przez administratora instytucji, widoczne tylko w tym urzędzie.

Wgranie pliku od razu dzieli tekst na fragmenty (PDF: strony; DOCX/TXT/MD: sekcje ok. 3000 znaków) i włącza je
do wyszukiwania. Plik bez warstwy tekstowej (skan) jest odrzucany z komunikatem, żeby asystent nie miał
„pustego” źródła. Przy wgrywaniu można podać datę „obowiązuje od”, uwagi (np. Dz.U.) i **źródło zastępowane**,
które zostaje wyłączone w urzędzie.

Asystent formalny dalej odpowiada wyłącznie na podstawie źródeł i podaje tytuł źródła ze stroną
(PDF) albo numerem fragmentu (DOCX/TXT). Gdy w aktywnych źródłach nie ma odpowiedzi, mówi o tym wprost
i nie wywołuje modelu.

API: `/api/v1/knowledge-documents/` (lista, wgranie, zmiana opisu, usunięcie) oraz
`/api/v1/knowledge-documents/{id}/disable/` i `/enable/`. Opis w `/api/v1/docs/`.

## Przepisy zapisane w kodzie

Zasady, od których zależy wynik oceny (skala 1–9 i 3/5/7, progi wyniku, kryteria obowiązkowe dla arkuszy A/B/C,
liczba kryteriów dodatkowych, terminy), są zapisane w kodzie celowo:

- każda reguła ma odwołanie do paragrafu lub artykułu w komentarzu,
- każda reguła ma test (`tests/test_scoring.py`, `tests/test_api_flow.py`), więc zmiana przepisu to zmiana
  jednej funkcji i testu, a pomyłkę wykaże CI (`.github/workflows/ci.yml`),
- formularz konfiguracyjny dla takich zmian byłby ryzykowny: błędny próg zmienia wynik oceny pracownika.

Pliki: `apps/assessments/forms_config.py` (arkusze, skale, kryteria obowiązkowe), `apps/assessments/scoring.py`
(wynik i sugerowany poziom), `apps/assessments/checklist.py` (lista kontrolna), `apps/deadlines/rules.py` (terminy).

## Kierunek rozwoju

- **Wersje reguł według daty wejścia w życie.** Dziś ocena liczy się według reguł w aktualnej wersji kodu.
  Przy zmianie rozporządzenia w trakcie cyklu ocen: zapis wersji reguł w ocenie przy jej rozpoczęciu
  (tak jak wersji modelu kompetencji) i wybór zestawu reguł po tej wersji.
- **Nowa wersja modelu kompetencji z panelu** dla administratora instytucji (dziś: operator systemu).
- **Przegląd zmian w bazie wiedzy** przez radcę prawnego przed włączeniem źródła (status „do akceptacji”).
- **OCR** dla skanów PDF bez warstwy tekstowej.
- **Wdrożenie dopiero po zielonym CI.** Dziś `ci.yml` i `deploy.yml` startują równolegle po pushu na `main`.
