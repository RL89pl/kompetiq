# Elementy wymagające zabezpieczenia lub dostosowania przed wdrożeniem produkcyjnym

| Obszar | Stan w prototypie | Do wykonania przed produkcją |
|---|---|---|
| Model AI | konfigurowalny dostawca; w demo plan darmowy zewnętrznego API | PLLuM w infrastrukturze MC albo dostawca z umową powierzenia (art. 28 RODO), region UE, wyłączone trenowanie i retencja |
| Kontrola wysyłki do AI | podgląd z kontrolą danych osobowych (widok „Przejrzystość AI”), pseudonimizacja ocenianego | ta sama kontrola przed każdą rzeczywistą wysyłką z blokadą przy wykryciu nazwiska innej osoby; słownik osób z systemu kadrowego |
| Dane osobowe w AI | pseudonimizacja imienia i nazwiska, minimalny zakres materiału | DPIA (art. 35 RODO); rozszerzona pseudonimizacja (nazwiska współpracowników w przykładach); polityka retencji rejestru `AIInteraction` |
| Uwierzytelnianie | login i hasło Django, limit prób | SSO urzędu (SAML/OIDC), MFA dla HR/administratora, polityka haseł zgodna z KRI |
| Autoryzacja | role i izolacja instytucji, testy | przegląd uprawnień z kadrami (np. zastępstwa, zmiana przełożonego § 9 ust. 3), konto techniczne do integracji |
| Szyfrowanie | HTTPS na nginx, bezpieczne ciasteczka | HSTS (`SECURE_HSTS_SECONDS`), szyfrowanie kopii zapasowych i wolumenu bazy |
| Audyt | historia zmian ocen, rejestr wywołań AI, powiadomień | centralne logowanie (SIEM), alerty, przegląd dostępu do ocen |
| Kopie zapasowe | wolumen PostgreSQL | codzienne kopie, test odtworzenia, retencja zgodna z instrukcją kancelaryjną |
| Dokumenty | PDF/DOCX do druku i podpisu | podpis kwalifikowany / Profil Zaufany, rejestracja w EZD, wzory zatwierdzone przez komórkę prawną |
| Baza wiedzy | ustawa (t.j. Dz.U. 2026 poz. 590), rozporządzenia, poradniki, model, 29 pytań i odpowiedzi; źródła urzędu z panelu (administrator, PDF/DOCX/TXT/MD do 20 MB, pliki poza publicznym katalogiem) | weryfikacja zestawu pytań i wgrywanych źródeł przez kadry i radcę prawnego (status „do akceptacji”), skan antywirusowy wgrywanych plików, OCR skanów |
| E-mail | backend SMTP konfigurowalny, treść bez danych oceny | serwer poczty urzędu, SPF/DKIM |
| Dostępność | WCAG: kontrast, fokus, etykiety, nawigacja klawiaturą | audyt WCAG 2.1 AA (ustawa o dostępności cyfrowej) |
| Wydajność | gunicorn, przetwarzanie synchroniczne | kolejka zadań (np. Celery) dla długich wywołań AI, limity zapytań per użytkownik (`ASSISTANT_RATE`) |
| Zależności | wersje przypięte, CI | skanowanie podatności (np. pip-audit, npm audit), aktualizacje bezpieczeństwa |

## Uruchomienie produkcyjne (skrót)

```bash
cp .env.example .env        # sekrety, hosty, dostawca AI
docker compose up --build -d   # entrypoint.sh: migrate, collectstatic, model kompetencji, baza wiedzy
docker compose exec web python manage.py createsuperuser
# cron hosta (dni robocze, 7:00):
# 0 7 * * 1-5 cd /srv/services/kompetiq && docker compose exec -T web python manage.py send_reminders
```
