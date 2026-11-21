"""Kompletny przykładowy proces oceny okresowej z planem rozwoju (dane fikcyjne).

Marek Kowalczyk, radca (arkusz C): kryteria ustalone, przykłady zachowań i oceny wskaźników dla wszystkich
kryteriów, oceny cząstkowe z uzasadnieniami, rozmowa oceniająca, sporządzenie oceny, zapoznanie ocenianego
i plan rozwoju w trakcie realizacji. Przejścia etapów przez workflow — tak jak w aplikacji.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessments import workflow
from apps.assessments.forms_config import FormType
from apps.assessments.models import BehavioralEvidence, IndicatorRating
from apps.assessments.services import create_assessment, set_additional_criteria
from apps.competencies.models import Competency
from apps.development.models import DevelopmentAction, DevelopmentPlan, ProgressNote
from apps.employees.models import Employee
from apps.institutions.models import Institution, Membership

# kod kompetencji → (ocena cząstkowa, poziomy wskaźników po kolei, przykłady (sytuacja, działanie, rezultat, dni temu),
#                    uzasadnienie)
MATERIAL = {
    'wykorzystywanie-wiedzy': (7, [4, 4, 3], [
        ('Wejście w życie aktu w sprawie sztucznej inteligencji wymagało przygotowania interpretacji nowych obowiązków '
         'dla podmiotów publicznych.',
         'Przeanalizował akt i wytyczne Komisji, przygotował zestawienie obowiązków z podziałem na terminy i omówił je '
         'na spotkaniu wydziału.',
         'Zestawienie przyjęto jako materiał roboczy departamentu; wykorzystano je w trzech odpowiedziach na zapytania.',
         420),
        ('W wydziale brakowało wiedzy o orzecznictwie TSUE w sprawach zautomatyzowanych decyzji.',
         'Z własnej inicjatywy ukończył kurs e-learningowy i przygotował dla zespołu dwustronicową notatkę z wnioskami.',
         'Notatka jest stosowana przy opiniach indywidualnych; dwie osoby z zespołu korzystały z niej przy sprawach.',
         180),
    ], 'Wykorzystuje wiedzę prawniczą w nowych obszarach regulacji i dzieli się nią z zespołem; zachowania '
       'odpowiadają w przeważającej mierze opisowi poziomu „powyżej oczekiwań”.'),
    'rzetelnosc': (5, [3, 3], [
        ('Przygotowanie projektów opinii indywidualnych w ustalonych terminach.',
         'Przygotował 14 projektów opinii; w dwóch przypadkach poprosił o przedłużenie terminu, uprzedzając o tym z '
         'wyprzedzeniem.',
         'Projekty przekazano zgodnie z uzgodnieniami; jeden wymagał poprawek redakcyjnych.',
         250),
    ], 'Zadania wykonuje zgodnie ze standardami i terminami, sygnalizuje ryzyko opóźnień z wyprzedzeniem; poziom '
       'odpowiada standardowi wykonania.'),
    'organizacja-pracy': (5, [3, 3, 2, 3, 3], [
        ('Równoległa praca nad opiniami i przygotowaniem stanowiska na posiedzenie Komisji.',
         'Ustalił z naczelnikiem priorytety i harmonogram; jedno zadanie o niższym priorytecie zostało przesunięte.',
         'Stanowisko przygotowano na czas; przesunięte zadanie zakończono tydzień później.',
         140),
    ], 'Planuje pracę i ustala priorytety z przełożonym; przy dużym obciążeniu potrzebuje wsparcia w doborze '
       'zasobów, co jest obszarem do rozwoju.'),
    'wspolpraca': (7, [4, 3, 4, 4, 3, 4], [
        ('Projekt odpowiedzi na wystąpienie wymagał uzgodnień z Departamentem Prawnym i Departamentem '
         'Cyberbezpieczeństwa.',
         'Zorganizował wspólne spotkanie, przygotował tabelę uwag i zaproponował kompromisowe brzmienie.',
         'Uzgodnienia zakończono w jednej rundzie zamiast zwykle dwóch.',
         300),
        ('Nowa osoba w wydziale przygotowywała pierwszą opinię indywidualną.',
         'Przekazał wzory dokumentów i omówił z nią strukturę opinii oraz typowe błędy.',
         'Opinia nowej osoby została przyjęta bez istotnych uwag merytorycznych.',
         90),
    ], 'Aktywnie wspiera współpracowników i inicjuje uzgodnienia między komórkami; zachowania odpowiadają '
       'opisowi poziomu „powyżej oczekiwań” w większości wskaźników.'),
    'komunikacja': (5, [3, 3, 2, 3], [
        ('Wyjaśnianie skomplikowanych zagadnień prawnych osobom spoza wydziału.',
         'Przygotował krótkie podsumowania opinii dla kierownictwa; w jednym przypadku podsumowanie było zbyt '
         'techniczne i wymagało uproszczenia.',
         'Kierownictwo korzysta z podsumowań; po uwagach forma została skrócona.',
         200),
    ], 'Wypowiada się rzeczowo i precyzyjnie; w pisemnych podsumowaniach dla odbiorców spoza prawa wymaga '
       'jeszcze dopasowania języka — obszar do rozwoju.'),
    'myslenie-analityczne': (7, [4, 4, 3], [
        ('Analiza barier prawnych dla innowacji w obszarze sztucznej inteligencji.',
         'Zebrał dane z konsultacji, porównał rozwiązania trzech państw członkowskich i wskazał dwa warianty działań '
         'z oceną ryzyka.',
         'Analiza stała się podstawą rekomendacji przedstawionej kierownictwu departamentu.',
         110),
    ], 'Analizuje złożone informacje, porównuje warianty i ocenia ryzyko; zachowania odpowiadają poziomowi '
       '„powyżej oczekiwań”.'),
}

INTERVIEW_PLAN = {
    'goal': 'Omówienie realizacji obowiązków i spełniania kryteriów w okresie oceny, przekazanie informacji zwrotnej '
            'oraz uzgodnienie kierunków rozwoju zawodowego.',
    'preparation_checklist': ['Przejrzeć przykłady zachowań dla każdego kryterium',
                              'Przygotować arkusz C i opis stanowiska',
                              'Zarezerwować 60 minut bez przerw, salę bez osób trzecich'],
    'opening': 'Przedstawiam cel i przebieg rozmowy, podkreślam, że to rozmowa o konkretnych zadaniach i dalszym '
               'rozwoju. Zapraszam do samooceny na początek.',
    'sections': [
        {'title': 'Główne obowiązki i ich realizacja',
         'talking_points': ['Opinie indywidualne i informacje dla Komisji', 'Analiza barier prawnych'],
         'questions_to_employee': ['Które zadanie było w tym okresie najtrudniejsze i dlaczego?']},
        {'title': 'Kryteria oceny',
         'talking_points': ['Mocne strony: wykorzystanie wiedzy, współpraca, myślenie analityczne',
                            'Obszary do rozwoju: organizacja pracy przy dużym obciążeniu, język podsumowań'],
         'questions_to_employee': ['Co pomogłoby Panu lepiej planować pracę w okresach spiętrzenia zadań?']},
    ],
    'strengths_feedback': [{'competency': 'Współpraca', 'situation': 'Uzgodnienia odpowiedzi z dwoma departamentami',
                            'behaviour': 'Zorganizował spotkanie i zaproponował kompromisowe brzmienie',
                            'impact': 'Uzgodnienia zakończono w jednej rundzie'}],
    'development_feedback': [{'competency': 'Komunikacja', 'situation': 'Podsumowania opinii dla kierownictwa',
                              'behaviour': 'Część podsumowań była zbyt techniczna',
                              'impact': 'Wymagały dodatkowego uproszczenia przed przekazaniem'}],
    'development_dialogue_questions': ['W jakim obszarze chciałby Pan rozwijać się w najbliższym roku?'],
    'closing': 'Podsumowuję ustalenia i kolejne kroki: sporządzenie oceny na piśmie i uzgodnienie planu rozwoju.',
    'formal_reminders': ['Ocena zostanie sporządzona na piśmie i przekazana do zapoznania',
                         'Od oceny przysługuje sprzeciw do dyrektora generalnego w terminie 7 dni'],
    'difficult_moments_tips': ['Przy różnicy zdań wracać do konkretnych przykładów zachowań'],
}

ACTIONS = [
    # tytuł, opis, kompetencja, forma, miernik, termin (dni od dziś), status, notatki
    ('Prowadzenie uzgodnień międzydepartamentalnych jako koordynator',
     'Samodzielna koordynacja uzgodnień dwóch projektów odpowiedzi z udziałem co najmniej dwóch departamentów.',
     'organizacja-pracy', 'ON_THE_JOB', 'Dwa projekty uzgodnione w terminie, bez eskalacji do naczelnika.', 90,
     'IN_PROGRESS', ['Pierwszy projekt uzgodniony w terminie; drugi w toku.']),
    ('Szkolenie: prosty język w komunikacji urzędowej',
     'Udział w szkoleniu i zastosowanie zasad w podsumowaniach opinii dla kierownictwa.',
     'komunikacja', 'TRAINING', 'Podsumowania do jednej strony, przyjmowane bez poprawek językowych.', -20,
     'DONE', ['Szkolenie ukończone.', 'Trzy kolejne podsumowania przyjęte bez uwag.']),
    ('Mentoring z doświadczonym radcą z Departamentu Prawnego',
     'Spotkania raz w miesiącu: planowanie pracy przy wielu równoległych zadaniach.',
     'organizacja-pracy', 'MENTORING', 'Sześć spotkań; plan tygodniowy stosowany na bieżąco.', 150,
     'IN_PROGRESS', ['Odbyły się dwa spotkania.']),
    ('Wystąpienie na forum departamentu o barierach prawnych dla AI',
     'Przygotowanie i przedstawienie 20-minutowej prezentacji wniosków z analizy.',
     'myslenie-analityczne', 'ON_THE_JOB', 'Prezentacja przedstawiona; co najmniej dwie rekomendacje przyjęte do prac.',
     60, 'PLANNED', []),
]


class Command(BaseCommand):
    help = 'Dodaje kompletny przykładowy proces oceny okresowej z planem rozwoju (Marek Kowalczyk, arkusz C).'

    @transaction.atomic
    def handle(self, **opts):
        inst = Institution.objects.filter(slug='urzad-demo').first()
        if inst is None:
            raise CommandError('Brak instytucji demo — najpierw uruchom seed_demo.')
        emp = Employee.objects.get(institution=inst, first_name='Marek', last_name='Kowalczyk')
        if emp.assessments.exists():
            self.stdout.write('Proces dla Marka Kowalczyka już istnieje — pomijam.')
            return
        sup = emp.supervisor
        m = Membership.objects.get(user=sup, institution=inst)
        today = date.today()
        a = create_assessment(
            institution=inst, employee=emp, evaluator=sup, form_type=FormType.PERIODIC_C,
            criteria_interview_date=today - timedelta(days=700), due_date=today - timedelta(days=20),
            expectations='Terminowe, rzetelne merytorycznie opinie indywidualne i informacje dla Komisji; '
                         'aktywne uzgodnienia z innymi komórkami; zrozumiałe podsumowania dla kierownictwa.',
            goals='Przygotowanie analizy barier prawnych dla innowacji w obszarze AI do końca okresu oceny.',
            previous_result='POSITIVE', previous_level='na poziomie oczekiwań', previous_date=today - timedelta(days=735),
        )
        set_additional_criteria(a, [Competency.objects.get(model=a.competency_model, code='myslenie-analityczne')])
        workflow.perform(a, 'set_criteria', user=sup, membership=m)

        for crit in a.criteria.select_related('competency'):
            score, levels, examples, justification = MATERIAL[crit.competency.code]
            inds = list(crit.selected_indicators.order_by('order'))
            for ind, lv in zip(inds, levels):
                IndicatorRating.objects.create(criterion=crit, indicator=ind, level=lv)
            for i, (sit, act, res, days) in enumerate(examples):
                BehavioralEvidence.objects.create(criterion=crit, indicator=inds[i % len(inds)], situation=sit,
                                                  action=act, result=res, created_by=sup,
                                                  occurred_on=today - timedelta(days=days))
            crit.score, crit.justification = score, justification
            crit.save()

        a.period_from, a.period_to = a.criteria_interview_date, today - timedelta(days=20)
        a.evaluation_interview_date = today - timedelta(days=25)
        a.interview_plan = INTERVIEW_PLAN
        a.interview_notes = ('Oceniany zgodził się z oceną mocnych stron. Zgłosił potrzebę wsparcia w planowaniu '
                             'pracy przy wielu równoległych zadaniach oraz zainteresowanie szkoleniem z prostego języka.')
        a.save()
        workflow.perform(a, 'complete_interview', user=sup, membership=m)

        a.justification = ('Oceniany spełnia kryteria oceny na poziomie oczekiwań. Szczególnie wyróżnia się '
                           'wykorzystaniem wiedzy w nowych obszarach regulacji, współpracą międzydepartamentalną '
                           'i analizą złożonych zagadnień. Obszarami do rozwoju są organizacja pracy przy dużym '
                           'obciążeniu oraz dopasowanie języka podsumowań do odbiorców spoza prawa.')
        a.development_conclusions = ('Rozwój umiejętności planowania i koordynacji przy wielu równoległych '
                                     'zadaniach (zadania koordynacyjne, mentoring) oraz komunikacji pisemnej '
                                     'prostym językiem (szkolenie). Wykorzystanie potencjału analitycznego '
                                     'w wystąpieniach na forum departamentu.')
        a.promotion_request = False
        a.save()
        workflow.perform(a, 'finalize', user=sup, membership=m)
        workflow.perform(a, 'acknowledge', user=sup, membership=m, data={'acknowledged_on': today - timedelta(days=15)})

        plan = DevelopmentPlan.objects.create(assessment=a, summary=a.development_conclusions)
        for title, desc, code, kind, measure, due, status, notes in ACTIONS:
            act = DevelopmentAction.objects.create(
                plan=plan, title=title, description=desc, type=kind, success_measure=measure, owner=emp.full_name,
                competency=Competency.objects.get(model=a.competency_model, code=code),
                due_date=today + timedelta(days=due), status=status)
            for n in notes:
                ProgressNote.objects.create(action=act, text=n, author=sup)

        a.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            f'Utworzono kompletny proces: {emp.full_name}, średnia {a.average}, wynik {a.get_result_display()}, '
            f'plan rozwoju: {plan.actions.count()} działania ({plan.progress()["percent"]}% zrealizowanych).'))
