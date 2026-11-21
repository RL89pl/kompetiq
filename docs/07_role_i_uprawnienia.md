# Role i uprawnienia

Konta demonstracyjne (`manage.py seed_demo`, hasło wspólne — w `.env`, zmienna `DEMO_PASSWORD`):

| Login | Osoba | Rola w aplikacji | Odpowiednik w urzędzie |
|---|---|---|---|
| `przelozony` | Tomasz Zieliński, kierownik oddziału | **Bezpośredni przełożony** (`SUPERVISOR`) | oceniający |
| `kierownik` | Maria Wójcik, dyrektor wydziału | **Kierujący komórką organizacyjną** (`UNIT_HEAD`) | kierujący komórką (Wydział Spraw Obywatelskich i Oddział Zezwoleń) |
| `kadry` | Ewa Kaczmarek, specjalista ds. kadr | **Kadry** (`HR`) | komórka kadr |
| `admin` | Adam Mazur | **Administrator instytucji** (`ADMIN`) | administrator systemu w urzędzie |

Rola jest przypisana do osoby w danej instytucji (urzędzie). Każdy widzi wyłącznie dane swojej instytucji.

## Bezpośredni przełożony (`przelozony`)

Główny użytkownik. Przeprowadza ocenę od początku do końca.

**Robi:**
- widzi swoich pracowników (tych, dla których jest wpisany jako bezpośredni przełożony);
- rozpoczyna pierwszą ocenę i ocenę okresową swoich pracowników;
- wczytuje lub uzupełnia opis stanowiska (także import OSP z .docx);
- wybiera kryteria dodatkowe i wskaźniki, ustala terminy, oczekiwania i cele;
- dokumentuje przykłady zachowań, ocenia wskaźniki, **przyznaje oceny cząstkowe**, pisze uzasadnienia;
- korzysta z asystenta AI przy swoich ocenach (analiza opisu stanowiska, przykładów, uzasadnienia, scenariusz
  i rozmowa o rozmowie oceniającej, plan rozwoju) oraz z asystenta formalnego;
- przeprowadza etapy: ustalenie kryteriów → rozmowa oceniająca → sporządzenie oceny → zapoznanie ocenianego;
  może otworzyć ponownie sporządzoną ocenę, dopóki oceniany się z nią nie zapoznał;
- prowadzi plan rozwoju (działania, statusy, notatki o postępie), także po zakończeniu oceny;
- pobiera arkusze, plan rozwoju i scenariusz rozmowy (PDF, DOCX);
- pisze wiadomości do kierującego komórką i do kadr w sprawie danej oceny; otrzymuje przypomnienia.

**Nie może:**
- widzieć ani oceniać pracowników innych przełożonych;
- zatwierdzić (potwierdzić) pierwszej oceny — to robi kierujący komórką;
- zmieniać danych kadrowych pracownika (stanowisko, komórka, forma zwracania się, status urzędnika);
- edytować oceny po jej sporządzeniu bez ponownego otwarcia; po zapoznaniu ocenianego — wcale;
- zobaczyć panelu HR ani wysyłać przypomnień innym oceniającym;
- zobaczyć rozmów z asystentem innych użytkowników.

## Kierujący komórką organizacyjną (`kierownik`)

Nadzoruje oceny w swojej komórce i potwierdza pierwszą ocenę.

**Robi:**
- widzi pracowników i oceny w komórkach, którymi kieruje (oraz swoich bezpośrednich podwładnych);
- **potwierdza dokonanie pierwszej oceny** (§ 10 ust. 6 i arkusz pierwszej oceny) — dostaje o to powiadomienie;
- przegląda arkusze, listy kontrolne, terminy i plany rozwoju, pobiera dokumenty;
- wysyła wiadomości i przypomnienia oceniającemu oraz kadrom;
- korzysta z asystenta formalnego;
- jeśli sam jest czyimś bezpośrednim przełożonym — ocenia tę osobę jak przełożony.

**Nie może:**
- edytować cudzej oceny (kryteria, przykłady, oceny cząstkowe, uzasadnienia) — tylko oceniający;
- korzystać z asystenta AI w trybie konkretnej oceny, której nie jest oceniającym;
- potwierdzać oceny okresowej (przepisy nie przewidują potwierdzenia przez kierującego);
- zmieniać danych kadrowych ani widzieć panelu HR.

## Kadry (`kadry`)

Organizuje i monitoruje proces w całym urzędzie.

**Robi:**
- widzi **wszystkich** pracowników i wszystkie oceny w instytucji (podgląd);
- **panel HR**: statusy i etapy procesów, komórki, oceny po terminie, oceny negatywne;
- wysyła przypomnienia: ręcznie przy wybranej ocenie oraz zbiorczo („Wyślij przypomnienia o terminach”);
- zmienia dane kadrowe pracowników (np. **forma zwracania się**: Pani / Pan), dodaje opisy stanowisk;
- pobiera arkusze i dokumenty; otrzymuje powiadomienia o sporządzeniu i zapoznaniu z oceną;
- wysyła wiadomości oceniającym i kierującym; korzysta z asystenta formalnego.

**Nie może:**
- prowadzić ani edytować oceny (kryteria, przykłady, oceny cząstkowe, uzasadnienia, etapy);
- rozpocząć oceny za przełożonego;
- edytować planów rozwoju;
- korzystać z asystenta AI w trybie konkretnej oceny.

## Administrator instytucji (`admin`)

Konfiguracja i obsługa wyjątkowych sytuacji w urzędzie.

**Robi:**
- wszystko, co kadry (podgląd całej instytucji, panel HR, przypomnienia, dane kadrowe);
- w sytuacjach wyjątkowych (np. nieobecność oceniającego) może wykonać każdą czynność w ocenie, w tym
  rozpocząć ocenę, edytować ją, zmienić etap i potwierdzić pierwszą ocenę — wszystkie zmiany trafiają do historii
  (audyt: kto i kiedy);
- korzysta ze wszystkich funkcji asystenta AI.

**Nie może:**
- widzieć danych innych instytucji;
- edytować oceny po zapoznaniu się z nią ocenianego (blokada dotyczy wszystkich ról);
- czytać rozmów z asystentem innych użytkowników.

Uwaga: panel techniczny Django (`/admin/` — import modelu kompetencji, instytucje, konta, przypisanie ról) wymaga
osobnego konta superużytkownika (`manage.py createsuperuser`); konto demo `admin` nie ma do niego dostępu.

## Zestawienie

| Czynność | Przełożony | Kierujący | Kadry | Administrator |
|---|:-:|:-:|:-:|:-:|
| Widok pracowników i ocen | swoi | swoja komórka | cała instytucja | cała instytucja |
| Rozpoczęcie oceny | swoi | swoi bezpośredni | — | tak |
| Edycja oceny, przykłady, oceny cząstkowe | tak (swoje) | — | — | tak |
| Sporządzenie oceny, zapoznanie | tak (swoje) | — | — | tak |
| Potwierdzenie pierwszej oceny | — | tak | — | tak |
| Asystent AI w ocenie | tak (swoje) | — | — | tak |
| Asystent formalny | tak | tak | tak | tak |
| Plan rozwoju — edycja | tak (swoje) | — | — | tak |
| Pobieranie dokumentów | tak | tak | tak | tak |
| Dane kadrowe pracownika | — | — | tak | tak |
| Opis stanowiska (dodanie, import OSP) | tak | tak | tak | tak |
| Panel HR, przypomnienia zbiorcze | — | — | tak | tak |
| Przypomnienie / wiadomość do oceniającego | — | tak | tak | tak |
| Wiadomość do kierującego i kadr | tak | tak | tak (do kierującego) | tak |
| Edycja po zapoznaniu ocenianego | — | — | — | — |
