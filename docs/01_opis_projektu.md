# Kompas Kompetencji — opis projektu

## Koncepcja

Kompas Kompetencji prowadzi bezpośredniego przełożonego w służbie cywilnej przez cały proces oceny pracownika,
od opisu stanowiska po plan rozwoju. Łączy w jednym miejscu model kompetencji, wymagania formalne z przepisów,
właściwe formularze i asystenta AI.

Ocena opiera się na **obserwowalnych zachowaniach**. Przy każdym wskaźniku behawioralnym przełożony wybiera opis
zachowania, który najlepiej odpowiada temu, co widział u pracownika, i dokumentuje przykłady (sytuacja, działanie,
rezultat). System wylicza z tych wyborów **sugerowany poziom kompetencji**. Ostateczną ocenę cząstkową zawsze
wybiera przełożony.

AI pełni funkcję doradczą: wyjaśnia przepisy z podaniem źródła, porządkuje przykłady, wskazuje braki, pomaga
przygotować rozmowę. Nie wystawia ocen. Wynik pozytywny lub negatywny wynika wprost z przepisów i z ocen przełożonego.

## Dwie ścieżki

| Pierwsza ocena (rozp. PRM z 23.07.2015) | Ocena okresowa (rozp. PRM z 4.04.2016) |
|---|---|
| Opis stanowiska, wskaźniki 5 elementów oceny | Analiza opisu stanowiska, podpowiedź arkusza B lub C (§ 3) |
| Rozmowa wstępna (21 dni), termin sprawozdania (po 8 mies.) | Kryteria obowiązkowe i do 3 dodatkowych, rozmowa (§ 5–7) |
| Ocena zachowań, sugerowany poziom, decyzja przełożonego | Ocena zachowań, sugerowany poziom, decyzja przełożonego |
| Sprawozdanie, egzamin, oceny 3/5/7 pkt | Oceny 1/3/5/7/9 pkt, średnia, poziom ogólny |
| Rozmowa oceniająca, wnioski rozwojowe | Rozmowa oceniająca, wnioski do IPRZ |
| Potwierdzenie przez kierującego komórką, zapoznanie | Sporządzenie oceny, zapoznanie, pouczenie o sprzeciwie |

## Najważniejsze funkcjonalności

- **Kreator krok po kroku** z trasą etapów i automatycznym oznaczaniem ukończonych kroków.
- **Import opisu stanowiska (OSP) z pliku .docx**: rozpoznaje cel, zadania, liczbę podległych pracowników
  (podpowiedź arkusza B/C) oraz kompetencje wskazane w OSP (podpowiedź kryteriów dodatkowych). Bez udziału AI.
- **Model kompetencji**: 14 kompetencji, 49 wskaźników, 5 opisów poziomów; import z pliku xlsx, wersjonowanie.
- **Ocena zachowań**: wybór opisu zachowania przy wskaźniku, „brak podstaw do oceny”, przykłady SDR,
  sugerowany poziom (mediana wyborów przeliczona na skalę arkusza) i decyzja przełożonego.
- **Wyliczenia zgodne z przepisami**: średnia, poziom ogólny, wynik pozytywny/negatywny, warunki pierwszej oceny.
- **Lista kontrolna wymogów formalnych** z podstawą prawną (terminy, obowiązkowe uzasadnienie, właściwy arkusz).
- **Terminy z przepisów** (rozmowa wstępna, sprawozdanie, 24 miesiące, ponowna ocena po negatywnej, sprzeciw).
- **Asystent AI** (rozmowa): tryb zasad formalnych i tryb przygotowania do rozmowy z pracownikiem; odpowiedzi
  ze wskazaniem źródeł; jasna odmowa, gdy baza wiedzy nie zawiera odpowiedzi.
- **Rozmowa oceniająca**: scenariusz (cel, otwarcie, informacja zwrotna sytuacja–zachowanie–wpływ, pytania,
  elementy formalne, trudne momenty), notatki, wydruk.
- **Plan rozwoju (IPRZ)**: propozycje działań 70-20-10, mierniki, terminy, monitorowanie realizacji i notatki.
- **Dokumentacja**: arkusz pierwszej oceny, arkusze B/C (z częścią III), plan rozwoju i scenariusz rozmowy
  w **PDF** (do druku i podpisu) oraz DOCX (wersja edytowalna).
- **Panel HR/administratora**: statusy procesów, etapy, komórki, oceny po terminie, przypomnienia ręczne
  i automatyczne (codzienny cron), komunikacja z oceniającymi.
- **Komunikacja w procesie**: powiadomienia (np. prośba do kierującego komórką o potwierdzenie pierwszej oceny),
  wiadomości oceniający ↔ kierujący ↔ kadry, e-mail z informacją bez danych oceny.
- **Role i uprawnienia**: przełożony, kierujący komórką, HR, administrator; wiele instytucji w jednej instalacji.

## Użytkownicy

- **Przełożony dokonujący oceny** (główny użytkownik): kreator, asystent, dokumenty.
- **Kierujący komórką**: podgląd ocen w komórce, potwierdzanie pierwszej oceny, wiadomości.
- **HR / administrator**: monitorowanie statusów i terminów, przypomnienia, dane kadrowe, konfiguracja.

## Kierunki rozwoju

Integracja z EZD (rejestracja arkusza w sprawie), z systemem kadrowym (np. QNT: dane pracowników, stanowiska,
OSP), podpis kwalifikowany / Profil Zaufany na arkuszu, raporty zbiorcze dla dyrektora generalnego, uczenie się
z przyjętych/odrzuconych sugestii AI, udostępnienie innym urzędom (wielu dzierżawców już w architekturze).
