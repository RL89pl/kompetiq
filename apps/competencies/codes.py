"""Stałe kody kryteriów oceny (zgodne z rozporządzeniami) ↔ nazwy w modelu kompetencji."""

RZETELNOSC = 'rzetelnosc'
KOMUNIKACJA = 'komunikacja'
WIEDZA = 'wykorzystywanie-wiedzy'
ORGANIZACJA = 'organizacja-pracy'
KREATYWNOSC = 'kreatywnosc'
WSPOLPRACA = 'wspolpraca'
ANALITYCZNE = 'myslenie-analityczne'
NEGOCJOWANIE = 'negocjowanie'
WYSTAPIENIA = 'wystapienia-publiczne'
KLIENT = 'orientacja-na-klienta'
KRYZYS = 'sytuacje-kryzysowe'
STRATEGICZNE = 'zarzadzanie-strategiczne'
LUDZMI = 'zarzadzanie-ludzmi'
DECYZJE = 'podejmowanie-decyzji'

# prefiks nazwy (wielkie litery, bez znaków diakrytycznych normalizowanych) -> kod
NAME_TO_CODE = {
    'RZETELNOŚĆ': RZETELNOSC,
    'KOMUNIKACJA': KOMUNIKACJA,
    'WYKORZYSTYWANIE WIEDZY I DOSKONALENIE ZAWODOWE': WIEDZA,
    'ORGANIZACJA PRACY I ORIENTACJA NA OSIĄGANIE CELÓW': ORGANIZACJA,
    'KREATYWNOŚĆ': KREATYWNOSC,
    'WSPÓŁPRACA': WSPOLPRACA,
    'MYŚLENIE ANALITYCZNE': ANALITYCZNE,
    'NEGOCJOWANIE': NEGOCJOWANIE,
    'WYSTĄPIENIA PUBLICZNE': WYSTAPIENIA,
    'ORIENTACJA NA KLIENTA/INTERESANTA': KLIENT,
    'RADZENIE SOBIE W SYTUACJACH KRYZYSOWYCH': KRYZYS,
    'ZARZĄDZANIE STRATEGICZNE': STRATEGICZNE,
    'ZARZĄDZANIE LUDŹMI': LUDZMI,
    'PODEJMOWANIE DECYZJI I ODPOWIEDZIALNOŚĆ': DECYZJE,
}
