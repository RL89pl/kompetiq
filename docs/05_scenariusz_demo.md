# Scenariusz demonstracji (ok. 10 minut)

Dane fikcyjne z `manage.py seed_demo`; opisy stanowisk pochodzą ze wzorów OSP (`docs_assets/OSP_word`).
Konta: `przelozony` (bezpośredni przełożony), `kierownik` (kierujący komórką), `kadry` (HR), `admin`.

## Przed pokazem: dane od nowa

Żeby kilka razy przejść całą ścieżkę: **/admin/ → Instytucje → „Przywróć dane demonstracyjne”** (konto
superużytkownika) albo `manage.py seed_demo --reset`. Oceny, przykłady, plany rozwoju, rozmowy z asystentem,
powiadomienia i skrzynka testowa wracają do stanu początkowego; konta demo dostają hasło z `DEMO_PASSWORD`.

## Skrzynka testowa (e-maile)

Konta demo mają adresy `@urzad-demo.test`: ich e-maile nie wychodzą na zewnątrz, tylko trafiają do
**Skrzynki testowej** w menu (każdy widzi swoje, administrator — całą pocztę urzędu). Przykład: po dokonaniu
pierwszej oceny przez `przelozony` zaloguj się jako `kierownik` → Skrzynka testowa → e-mail „Potwierdź ocenę”.
E-maile mają wersję HTML i tekstową, link do oceny i nie zawierają treści oceny.

## Ścieżka 1: ocena okresowa (arkusz C), od początku do dokumentu

1. **Kompas** jako `przelozony`: dwie ścieżki, oceny w toku, najbliższe terminy.
2. **Pracownicy → Rozpocznij: Okresowa, arkusz C** dla Marka Kowalczyka (radca). Arkusz podpowiada § 3 rozporządzenia
   i opis stanowiska: brak podległych pracowników.
3. **Analiza opisu stanowiska**: dane z OSP (symbol, cel, zadania, kompetencje z OSP). Kliknij „Ustaw jako kryteria
   dodatkowe” (kompetencje z OSP spoza obowiązkowych) albo „Przeanalizuj opis z asystentem”. Dobierz wskaźniki.
4. **Ustalenie kryteriów**: data rozmowy, termin oceny, oczekiwania (można wstawić projekt AI).
   „Potwierdź: kryteria ustalone” waliduje wymogi z § 5–7. Pobierz część I arkusza (PDF).
5. **Ocena zachowań** (Współpraca): dodaj przykład (sytuacja, działanie, rezultat). Przy wskaźnikach wybierz opis
   zachowania najlepiej odpowiadający obserwacjom. **Sugerowany poziom kompetencji** aktualizuje się na bieżąco.
   Wybierz ocenę cząstkową, także inną niż sugerowana: decyzja należy do przełożonego.
   „Przeanalizuj przykłady” pokazuje braki, sformułowania do zmiany i ryzyko błędów oceniania.
6. **Oceny cząstkowe**: pozostałe kryteria, uzasadnienia (projekt AI tylko dla ustalonej oceny), wynik według § 11.
7. **Rozmowa oceniająca**: scenariusz z asystentem, rozmowa w trybie „Przygotowanie do rozmowy”, wydruk.
8. **Program rozwoju**: działania 70-20-10 z sugestii AI, wnioski do arkusza.
9. **Sporządzenie oceny**: lista kontrolna z podstawami prawnymi, sporządzenie, zapoznanie, PDF arkusza z pouczeniem.

## Ścieżka 2: pierwsza ocena — potwierdzenie przez kierującego

Julia Sadowska (referent): terminy wyliczone automatycznie (rozmowa wstępna do 21 dni, sprawozdanie po 8 miesiącach).
Po dokonaniu oceny `kierownik` dostaje powiadomienie z prośbą o potwierdzenie.

## Asystent formalny: przykładowe pytania jurorów

- Ile kryteriów dodatkowych można wybrać i kiedy? (§ 2 ust. 2, § 5 ust. 2 rozp. 2016 — maks. 3)
- Kiedy pierwsza ocena jest negatywna? (§ 10 rozp. 2015)
- Jaki jest termin na sprzeciw od oceny okresowej? (art. 83 ust. 1 ustawy — 7 dni)
- Co z terminem oceny przy nieobecności pracownika dłuższej niż miesiąc? (art. 81 ust. 7 ustawy)
- Kiedy po negatywnej ocenie przeprowadza się kolejną? (art. 81 ust. 9 — po 6 miesiącach)
- Pytanie spoza zakresu (np. o pogodę): asystent odpowiada, że w bazie wiedzy brak informacji.

## Przejrzystość AI: co wysyłamy do modelu

`przelozony`, menu **Przejrzystość AI**:
1. Funkcja „Scenariusz rozmowy oceniającej”, ocena Katarzyny Nowickiej (arkusz C) → **Pokaż, co zostałoby wysłane**.
2. Wynik kontroli: adresat (host i model), brak imienia i nazwiska ocenianej (w treści „Oceniana”), brak nazwisk osób
   z urzędu, nazwy urzędu, e-maili, PESEL, daty zatrudnienia.
3. Treść zapytania z podświetlonymi słowami „Oceniana”; pola odpowiedzi bez oceny punktowej i poziomu.
4. Pokaz kontroli: w przykładzie zachowania dopisz nazwisko innej osoby z urzędu (np. „z Tomaszem Zielińskim”),
   ponów podgląd: kontrola wskazuje nazwisko i miejsce wystąpienia.
5. „Rozmowa: zasady i wymagania formalne” z pytaniem o pogodę: model nie zostałby wywołany (brak źródeł).

Podgląd nie wywołuje modelu i nic nie zapisuje — działa także bez dostępu do sieci.

## Panel HR

`kadry`: statusy, etapy, komórki, oceny po terminie, „Przypomnij” przy ocenie, „Wyślij przypomnienia o terminach”.
