# Zgodność z wymaganiami wyzwania

| Wymaganie (dokument wyzwania) | Realizacja |
|---|---|
| Prowadzenie krok po kroku | Kreator z 7 etapami i trasą postępu; kroki zależne od rodzaju oceny |
| Pomoc w doborze kryteriów | Podpowiedź arkusza (§ 3) z danych i OSP; kryteria obowiązkowe automatycznie; maks. 3 dodatkowe; kompetencje z OSP; analiza AI |
| Ocena przez obserwowalne zachowania | Wybór opisu zachowania przy każdym wskaźniku; przykłady SDR; „brak podstaw do oceny” |
| Sugerowany poziom, decyzja przełożonego | Sugerowany poziom kompetencji z wyborów (mediana → skala arkusza); ocenę cząstkową wybiera przełożony |
| Dwie odrębne ścieżki, właściwe części formularza | Pierwsza ocena (5 elementów, 3/5/7, sprawozdanie, egzamin, kierujący) i okresowa (B/C, 1–9, część I–III) |
| Model kompetencyjny ze wskaźnikami i opisami poziomów | 14 kompetencji, 49 wskaźników, 5 poziomów, import z xlsx, przeglądarka modelu |
| Dokumentacja na właściwych formularzach | Arkusz pierwszej oceny, arkusze B/C, plan rozwoju, scenariusz rozmowy |
| Generowanie dokumentacji w PDF | PDF (domyślnie) oraz DOCX |
| Zarządzanie terminami | Terminy z ustawy i rozporządzeń; widok terminów; lista kontrolna |
| Komunikacja z przełożonymi | Powiadomienia przy zmianach statusu (np. prośba o potwierdzenie), wiadomości oceniający ↔ kierujący ↔ kadry |
| Asystent AI, z którym można rozmawiać | Rozmowa z historią: tryb formalny i tryb przygotowania do rozmowy z pracownikiem |
| Wyjaśnianie zasad formalnych | Odpowiedzi z bazy wiedzy z podaniem źródła |
| Przygotowanie do rozmowy (pytania, kwestie, argumenty) | Scenariusz rozmowy, rozmowa z asystentem, projekty uzasadnień |
| Odpowiedzi ze źródeł, identyfikacja źródła | Cytowania przy każdej odpowiedzi (tytuł, strona) |
| Brak informacji → jasny komunikat | Dwa progi: wynik dopasowania i udział słów pytania w jednym źródle (≥ 60%); bez źródeł nie ma wywołania modelu, jest komunikat o braku informacji (test na pełnej bazie wiedzy) |
| Baza wiedzy: ustawa, rozporządzenia, model, poradniki, pytania i odpowiedzi | Ustawa (t.j. Dz.U. 2026 poz. 590, z ISAP/ELI), rozporządzenia + załącznik, poradniki KPRM, model, 29 pytań i odpowiedzi |
| Aktualizacja bazy wiedzy przy zmianie przepisów | Panel „Baza wiedzy” (administrator instytucji): wgranie PDF/DOCX/TXT/MD, „zastępuje źródło”, „obowiązuje od”, wyłączanie źródeł wspólnych; `docs/08_zmiany_przepisow_i_modyfikowalnosc.md` |
| AI nie decyduje o poziomie oceny | Schematy bez pól ocen (test), wynik liczony kodem z ocen przełożonego |
| Perspektywa HR/administratora | Panel HR: statusy, terminy, komórki, przekroczenia |
| Przypomnienia | Ręczne (HR) i automatyczne (`send_reminders`, codziennie, bez duplikatów), e-mail bez danych oceny |
| Brak dostępności na smartfonach | Ekran blokady poniżej 768 px; interfejs dla komputera i tabletu |
| Czytelny i responsywny interfejs w przeglądarce | Układ od tabletu po monitor, WCAG (kontrast, fokus, etykiety) |
| Architektura do rozwoju i skalowania | Moduły Django, bezstanowy backend, wielu dzierżawców, wymienny dostawca AI |
| Integracja z EZD / systemami kadrowymi (możliwość) | Udokumentowane API REST: OpenAPI 3 z opisem żądań i odpowiedzi wszystkich widoków, publiczny podgląd `/api/v1/docs/`; import OSP, eksport PDF |
| Uwierzytelnianie, autoryzacja, role | Logowanie, 4 role, izolacja instytucji, blokada edycji po sporządzeniu |
| Ochrona danych, minimalizacja | Pseudonimizacja przed AI, e-mail bez treści oceny, audyt, brak danych w adresach URL; widok „Przejrzystość AI”: dokładna treść wysyłki do modelu z automatyczną kontrolą danych osobowych |
| Jakość, wiarygodność i bezpieczeństwo AI (kryterium walidacji) | Źródła z cytowaniem, dwa progi „brak informacji”, schematy bez pól ocen, rejestr wywołań z decyzją przełożonego, podgląd wysyłki bez wywołania modelu (`02_wykorzystanie_ai.md`) |
| Wyłącznie darmowe narzędzia AI (hackathon) | Dostawca konfigurowalny; rekomendacja Groq (plan darmowy), docelowo PLLuM na serwerze MC |
| Wskazanie elementów do zabezpieczenia przed produkcją | `04_bezpieczenstwo_i_wdrozenie.md` |
| Opis projektu, opis AI, technologie i architektura | `01_opis_projektu.md`, `02_wykorzystanie_ai.md`, `03_architektura.md` |
| Prezentacja (maks. 10 slajdów) | `docs/KompetIQ_prezentacja.pdf`: 10 slajdów, zrzuty z aplikacji na danych demo (źródło: `docs/prezentacja/deck.html`); pełna dokumentacja: `/o-projekcie` |
