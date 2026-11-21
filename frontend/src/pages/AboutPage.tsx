import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { CompassMark } from '../components/Layout'

/**
 * Publiczna dokumentacja projektu (bez logowania): /o-projekcie.
 * Link do umieszczenia na stronie rejestracji projektu. Treść odpowiada docs/01–08.
 */

const NAV = [
  ['koncepcja', 'Koncepcja'],
  ['sciezki', 'Dwie ścieżki'],
  ['kreator', 'Kreator'],
  ['zachowania', 'Ocena zachowań'],
  ['ai', 'AI'],
  ['asystent', 'Asystent'],
  ['dokumenty', 'Dokumenty'],
  ['role', 'Role'],
  ['architektura', 'Architektura'],
  ['bezpieczenstwo', 'Bezpieczeństwo'],
  ['zgodnosc', 'Zgodność'],
] as const

function Section({ id, kicker, title, lead, children }: { id: string; kicker: string; title: string; lead?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-20 border-t border-rule py-14 md:py-20">
      <p className="text-sm font-bold uppercase tracking-[0.14em] text-first">{kicker}</p>
      <h2 id={`${id}-t`} className="mt-2 text-3xl md:text-4xl">{title}</h2>
      {lead && <p className="mt-4 max-w-[70ch] text-lg text-ink-soft">{lead}</p>}
      <div className="mt-10">{children}</div>
    </section>
  )
}

function Card({ title, children, tone = 'plain', icon }: { title: string; children: ReactNode; tone?: 'plain' | 'first' | 'periodic' | 'ai' | 'ok' | 'warn'; icon?: ReactNode }) {
  const tones = {
    plain: 'border-rule bg-white',
    first: 'border-first/30 bg-first-tint',
    periodic: 'border-periodic/30 bg-periodic-tint',
    ai: 'border-ai/40 border-dashed bg-ai-tint',
    ok: 'border-ok/30 bg-ok-tint',
    warn: 'border-warn/30 bg-warn-tint',
  }
  return (
    <div className={`rounded-lg border p-5 ${tones[tone]}`}>
      <div className="flex items-center gap-2">{icon}<h3 className="font-sans text-[17px] font-bold">{title}</h3></div>
      <div className="mt-2 text-[15px] leading-relaxed text-ink-soft">{children}</div>
    </div>
  )
}

function Arrow({ down }: { down?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className={`size-6 shrink-0 text-rule-strong ${down ? 'rotate-90' : 'rotate-90 md:rotate-0'}`} aria-hidden>
      <path d="M4 12h14m-5-6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Node({ children, tone = 'plain', sub }: { children: ReactNode; tone?: 'plain' | 'ai' | 'ok' | 'ink' | 'bad' | 'first'; sub?: ReactNode }) {
  const tones = {
    plain: 'border-rule-strong bg-white',
    ai: 'border-dashed border-ai bg-ai-tint text-ai',
    ok: 'border-ok/40 bg-ok-tint text-ok',
    ink: 'border-ink bg-ink text-white',
    bad: 'border-bad/40 bg-bad-tint text-bad',
    first: 'border-first/40 bg-first-tint text-first',
  }
  return (
    <div className={`flex-1 rounded-lg border-2 px-4 py-3 text-center ${tones[tone]}`}>
      <p className="font-bold leading-snug">{children}</p>
      {sub && <p className={`mt-1 text-sm ${tone === 'ink' ? 'text-white/75' : 'text-ink-soft'}`}>{sub}</p>}
    </div>
  )
}

function Flow({ children }: { children: ReactNode }) {
  return <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-center">{children}</div>
}

function Tag({ children, tone = 'ai' }: { children: ReactNode; tone?: 'ai' | 'ok' | 'ink' }) {
  const t = { ai: 'bg-ai-tint text-ai border-ai/40 border-dashed', ok: 'bg-ok-tint text-ok border-ok/30', ink: 'bg-white text-ink-soft border-rule-strong' }
  return <span className={`inline-block rounded border px-2 py-0.5 text-xs font-bold ${t[tone]}`}>{children}</span>
}

const Check = () => (
  <svg viewBox="0 0 20 20" className="mt-1 size-4 shrink-0 text-ok" aria-hidden><path d="m4 10.5 4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
)
const Cross = () => (
  <svg viewBox="0 0 20 20" className="mt-1 size-4 shrink-0 text-bad" aria-hidden><path d="m5 5 10 10M15 5 5 15" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg>
)

function List({ items, cross }: { items: ReactNode[]; cross?: boolean }) {
  return (
    <ul className="space-y-1.5 text-[15px]">
      {items.map((x, i) => <li key={i} className="flex gap-2">{cross ? <Cross /> : <Check />}<span>{x}</span></li>)}
    </ul>
  )
}

const STEPS: { n: number; title: string; first: string; periodic: string; ai: string | null }[] = [
  { n: 1, title: 'Opis stanowiska', first: 'obowiązki i wskaźniki istotne na stanowisku', periodic: 'import OSP z .docx, podpowiedź arkusza A/B/C (§ 3)', ai: 'analiza opisu, propozycja kryteriów dodatkowych' },
  { n: 2, title: 'Kryteria / rozmowa wstępna', first: 'rozmowa wstępna (21 dni), termin sprawozdania', periodic: 'kryteria obowiązkowe + do 3 dodatkowych, cele (§ 5–7)', ai: 'projekt oczekiwań i celów' },
  { n: 3, title: 'Ocena zachowań', first: 'wskaźniki 5 elementów oceny', periodic: 'wskaźniki kryteriów arkusza', ai: 'analiza przykładów: braki, ryzyko błędów oceniania' },
  { n: 4, title: 'Oceny cząstkowe', first: '3 / 5 / 7 pkt, sprawozdanie, egzamin', periodic: '1 / 3 / 5 / 7 / 9 pkt, średnia, poziom', ai: 'projekt uzasadnienia ustalonej oceny' },
  { n: 5, title: 'Rozmowa oceniająca', first: 'omówienie elementów i sprawozdania', periodic: 'omówienie kryteriów i celów', ai: 'scenariusz rozmowy, rozmowa z asystentem' },
  { n: 6, title: 'Rozwój', first: 'wnioski rozwojowe', periodic: 'IPRZ: działania 70-20-10, mierniki', ai: 'propozycje działań i wniosków' },
  { n: 7, title: 'Sporządzenie', first: 'potwierdzenie przez kierującego, zapoznanie', periodic: 'sporządzenie, zapoznanie, pouczenie o sprzeciwie', ai: null },
]

const ROLES = ['Przełożony', 'Kierujący komórką', 'Kadry (HR)', 'Administrator'] as const
const PERMS: [string, (0 | 1 | 2)[]][] = [
  ['Prowadzenie i edycja oceny', [1, 0, 0, 2]],
  ['Przyznawanie ocen cząstkowych', [1, 0, 0, 2]],
  ['Potwierdzenie pierwszej oceny', [0, 1, 0, 2]],
  ['Podgląd ocen', [1, 1, 1, 1]],
  ['Pobieranie arkuszy PDF / DOCX', [1, 1, 1, 1]],
  ['Asystent formalny', [1, 1, 1, 1]],
  ['Asystent przy konkretnej ocenie', [1, 0, 0, 1]],
  ['Panel HR, przypomnienia', [0, 0, 1, 1]],
  ['Dane kadrowe pracowników', [0, 0, 1, 1]],
  ['Zarządzanie bazą wiedzy', [0, 0, 0, 1]],
]
const SCOPE = ['swoi pracownicy', 'komórka, którą kieruje', 'cały urząd (podgląd)', 'cały urząd']

const COMPLIANCE: [string, string][] = [
  ['Prowadzenie krok po kroku', 'Kreator z 7 etapami i trasą postępu'],
  ['Dwie odrębne ścieżki oceny', 'Pierwsza ocena i ocena okresowa (A/B/C) z właściwymi częściami arkusza'],
  ['Ocena przez obserwowalne zachowania', 'Opisy zachowań przy wskaźnikach, przykłady SDR, „brak podstaw do oceny”'],
  ['Sugerowany poziom, decyzja przełożonego', 'Poziom liczony z wyborów; ocenę cząstkową wybiera przełożony'],
  ['Model kompetencji ze wskaźnikami', '14 kompetencji, 49 wskaźników, 5 poziomów, import z xlsx'],
  ['Dokumentacja na właściwych formularzach w PDF', 'Arkusze 1:1 ze wzorami z rozporządzeń, PDF i DOCX'],
  ['Zarządzanie terminami i przypomnienia', 'Terminy z przepisów, lista kontrolna, przypomnienia ręczne i automatyczne'],
  ['Komunikacja w procesie', 'Powiadomienia i wiadomości oceniający ↔ kierujący ↔ kadry'],
  ['Asystent AI, z którym można rozmawiać', 'Dwa tryby: zasady formalne oraz przygotowanie do rozmowy'],
  ['Odpowiedzi ze źródeł, jasny komunikat o braku', 'Cytowania (tytuł, strona); bez źródeł model nie jest wywoływany'],
  ['AI nie decyduje o ocenie', 'Schematy odpowiedzi bez pól ocen (test), wynik liczony kodem'],
  ['Perspektywa HR / administratora', 'Panel HR: statusy, etapy, komórki, przekroczenia terminów'],
  ['Brak dostępności na smartfonach', 'Blokada na telefonach; komputer i tablet'],
  ['Integracje (EZD, system kadrowy)', 'API REST z dokumentacją OpenAPI, import OSP, eksport PDF'],
  ['Ochrona danych', 'Pseudonimizacja, minimalizacja, audyt, podgląd wysyłki do AI'],
  ['Wyłącznie darmowe narzędzia AI', 'Dostawca konfigurowalny; Groq (plan darmowy), docelowo PLLuM'],
]

export function AboutPage() {
  useEffect(() => {
    const prev = document.title
    document.title = 'KompetIQ — dokumentacja projektu'
    return () => { document.title = prev }
  }, [])

  return (
    <div className="min-h-screen bg-paper">
      <a href="#tresc" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">Przejdź do treści</a>

      <header className="sticky top-0 z-30 border-b border-rule bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-3">
          <Link to="/" className="flex items-center gap-2.5" aria-label="KompetIQ — strona główna"><CompassMark className="size-7" /><span className="font-serif text-lg font-semibold">KompetIQ</span></Link>
          <nav aria-label="Sekcje" className="hidden flex-1 xl:block">
            <ul className="flex gap-1 text-sm">
              {NAV.map(([id, label]) => <li key={id}><a href={`#${id}`} className="whitespace-nowrap rounded px-2 py-1 hover:bg-paper">{label}</a></li>)}
            </ul>
          </nav>
          <Link to="/logowanie" className="ml-auto shrink-0 rounded-md bg-ink px-3.5 py-1.5 text-sm font-bold text-white hover:bg-[#25365a]">Zaloguj się</Link>
        </div>
      </header>

      <main id="tresc" className="mx-auto max-w-6xl px-5">
        {/* HERO */}
        <div id="top" className="grid items-center gap-10 py-14 md:grid-cols-[1.25fr_1fr] md:py-24">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.14em] text-first">Kompas Kompetencji · dokumentacja</p>
            <h1 className="mt-3 text-4xl leading-[1.1] md:text-6xl">Rzetelna ocena kompetencji w służbie cywilnej, krok po kroku.</h1>
            <p className="mt-6 max-w-[60ch] text-lg text-ink-soft">
              KompetIQ prowadzi bezpośredniego przełożonego przez pierwszą ocenę i ocenę okresową: od opisu stanowiska,
              przez obserwowane zachowania, po rozmowę oceniającą, plan rozwoju i arkusz gotowy do podpisu.
              Asystent AI porządkuje i podpowiada. <b className="text-ink">Ocenę wystawia przełożony.</b>
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-3">
            {[['2', 'ścieżki oceny'], ['7', 'etapów kreatora'], ['14 / 49', 'kompetencji / wskaźników'], ['4', 'role użytkowników'], ['4', 'arkusze 1:1 ze wzorami'], ['0', 'ocen wystawianych przez AI']].map(([v, l]) => (
              <div key={l} className="rounded-lg border border-rule bg-white p-4">
                <dt className="sr-only">{l}</dt>
                <dd><span className="block font-serif text-3xl font-semibold">{v}</span><span className="text-sm text-ink-soft">{l}</span></dd>
              </div>
            ))}
          </dl>
        </div>

        {/* KONCEPCJA */}
        <Section id="koncepcja" kicker="01 · Koncepcja" title="AI doradza, przełożony decyduje"
          lead="Ocena opiera się na obserwowalnych zachowaniach. System liczy to, co wynika z przepisów, AI pomaga w pracy z tekstem, a każda decyzja o ocenie należy do człowieka.">
          <div className="grid gap-4 md:grid-cols-3">
            <Card title="Przełożony" tone="first" icon={<span className="size-3 rounded-full bg-first" />}>
              Wybiera opisy zachowań, dokumentuje przykłady, <b>przyznaje oceny cząstkowe</b>, pisze uzasadnienie,
              prowadzi rozmowę. Każdą sugestię AI przyjmuje, edytuje albo odrzuca.
            </Card>
            <Card title="System (kod, bez AI)" icon={<span className="size-3 rounded-full bg-ink" />}>
              Liczy sugerowany poziom, średnią, poziom ogólny i <b>wynik pozytywny/negatywny</b> wprost z przepisów.
              Pilnuje terminów i wymogów formalnych, generuje arkusze.
            </Card>
            <Card title="Asystent AI" tone="ai" icon={<span className="size-3 rounded-full bg-ai" />}>
              Wyjaśnia przepisy z podaniem źródła, analizuje przykłady, przygotowuje scenariusz rozmowy i projekty tekstów.
              <b> Nie proponuje ocen ani wyniku</b> — jego odpowiedzi nie mają takich pól.
            </Card>
          </div>
        </Section>

        {/* ŚCIEŻKI */}
        <Section id="sciezki" kicker="02 · Dwie ścieżki" title="Pierwsza ocena i ocena okresowa"
          lead="Każda ścieżka ma własne przepisy, skalę, terminy i arkusz. Kreator sam dobiera kroki i formularz.">
          <div className="grid gap-5 md:grid-cols-2">
            {([
              ['first', 'Pierwsza ocena w służbie cywilnej', 'rozporządzenie PRM z 23 lipca 2015 r.', ['Opis stanowiska, wskaźniki 5 elementów oceny', 'Rozmowa wstępna w 21 dni, sprawozdanie po 8 miesiącach', 'Oceny 3 / 5 / 7 pkt, egzamin, sprawozdanie', 'Rozmowa oceniająca i wnioski rozwojowe', 'Potwierdzenie przez kierującego komórką, zapoznanie']],
              ['periodic', 'Ocena okresowa (arkusze A, B, C)', 'rozporządzenie PRM z 4 kwietnia 2016 r.', ['Podpowiedź arkusza z opisu stanowiska (§ 3)', 'Kryteria obowiązkowe i do 3 dodatkowych (§ 5–7)', 'Oceny 1 / 3 / 5 / 7 / 9 pkt, średnia, poziom ogólny', 'Rozmowa oceniająca, wnioski do IPRZ', 'Sporządzenie, zapoznanie, pouczenie o sprzeciwie']],
            ] as const).map(([tone, title, basis, items]) => (
              <div key={tone} className={`rounded-lg border p-6 ${tone === 'first' ? 'border-first/30 bg-first-tint' : 'border-periodic/30 bg-periodic-tint'}`}>
                <h3 className={`text-2xl ${tone === 'first' ? 'text-first' : 'text-periodic'}`}>{title}</h3>
                <p className="text-sm text-ink-soft">{basis}</p>
                <ol className="mt-5 space-y-3">
                  {items.map((x, i) => (
                    <li key={x} className="flex items-start gap-3">
                      <span className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${tone === 'first' ? 'bg-first' : 'bg-periodic'}`}>{i + 1}</span>
                      <span className="pt-0.5">{x}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </Section>

        {/* KREATOR */}
        <Section id="kreator" kicker="03 · Kreator" title="Siedem etapów od stanowiska do podpisu"
          lead="Trasa postępu pokazuje, co jest zrobione i co dalej. Etap uznaje się za ukończony automatycznie, na podstawie danych w ocenie.">
          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s) => (
              <li key={s.n} className="flex flex-col rounded-lg border border-rule bg-white p-4">
                <span className="flex size-9 items-center justify-center rounded-full bg-ink font-serif text-lg font-semibold text-white">{s.n}</span>
                <h3 className="mt-3 font-sans text-[15px] font-bold leading-snug">{s.title}</h3>
                <p className="mt-2 text-xs text-first"><b>Pierwsza:</b> {s.first}</p>
                <p className="mt-1 text-xs text-periodic"><b>Okresowa:</b> {s.periodic}</p>
                <div className="mt-auto pt-3">{s.ai ? <Tag>AI: {s.ai}</Tag> : <Tag tone="ink">bez AI</Tag>}</div>
              </li>
            ))}
          </ol>
          <p className="mt-6 max-w-[75ch] text-[15px] text-ink-soft">
            Nieaktywne przyciski wyjaśniają w podpowiedzi, czego brakuje (np. „Najpierw wybierz ocenę cząstkową”).
            Po sporządzeniu oceny edycja jest zablokowana; po zapoznaniu się ocenianego — na stałe.
          </p>
        </Section>

        {/* ZACHOWANIA */}
        <Section id="zachowania" kicker="04 · Ocena zachowań" title="Od obserwacji do oceny cząstkowej"
          lead="Przełożony nie zaczyna od punktów. Zaczyna od tego, co widział — a sugerowany poziom liczy się z jego wyborów.">
          <Flow>
            <Node sub="sytuacja, działanie, rezultat (SDR)">Przykłady zachowań</Node>
            <Arrow />
            <Node sub="przy każdym wskaźniku, albo „brak podstaw”">Wybór opisu zachowania</Node>
            <Arrow />
            <Node tone="first" sub="mediana wyborów → skala arkusza">Sugerowany poziom</Node>
            <Arrow />
            <Node tone="ink" sub="może być inna niż sugerowana">Ocena cząstkowa przełożonego</Node>
            <Arrow />
            <Node tone="ok" sub="średnia, poziom, warunki z przepisów">Wynik oceny</Node>
          </Flow>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <Card title="Model kompetencji">14 kompetencji, 49 wskaźników behawioralnych, 5 opisów poziomów. Import z pliku xlsx i wersjonowanie — trwające oceny zostają przy swojej wersji modelu.</Card>
            <Card title="Wsparcie AI przy przykładach" tone="ai">Przypisuje przykłady do wskaźników, sprawdza kompletność SDR, wskazuje braki, sformułowania nieneutralne i ryzyko błędów oceniania (np. efekt świeżości). Nie ocenia kompetencji.</Card>
          </div>
        </Section>

        {/* AI */}
        <Section id="ai" kicker="05 · Sztuczna inteligencja" title="Bezpieczne użycie AI"
          lead="AI działa tylko tam, gdzie pomaga w pracy z tekstem. Dane ocenianego są pseudonimizowane, a każdą wysyłkę można obejrzeć przed jej wykonaniem.">
          <h3 className="font-sans text-lg font-bold">Droga danych do modelu</h3>
          <div className="mt-4">
            <Flow>
              <Node sub="tylko materiał potrzebny danej funkcji">Dane z oceny</Node>
              <Arrow />
              <Node tone="first" sub="imię i nazwisko → „Oceniany”">Pseudonimizacja</Node>
              <Arrow />
              <Node tone="first" sub="nazwiska osób z urzędu, nazwa urzędu, e-mail, PESEL, daty">Kontrola danych osobowych</Node>
              <Arrow />
              <Node tone="ai" sub="Groq / Gemini / PLLuM / Claude">Model językowy</Node>
              <Arrow />
              <Node tone="ink" sub="przyjmij, edytuj albo odrzuć">Sugestia do weryfikacji</Node>
            </Flow>
          </div>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-ok/30 bg-white p-5">
              <h3 className="font-sans text-[17px] font-bold text-ok">Do modelu trafia</h3>
              <div className="mt-3"><List items={['stanowisko i opis stanowiska', 'kryteria i wskaźniki', 'przykłady zachowań, cele, oczekiwania (po pseudonimizacji)', 'oceny i uzasadnienia przełożonego — tylko gdy funkcja ich wymaga', 'fragmenty bazy wiedzy']} /></div>
            </div>
            <div className="rounded-lg border border-bad/30 bg-white p-5">
              <h3 className="font-sans text-[17px] font-bold text-bad">Nie trafia</h3>
              <div className="mt-3"><List cross items={['imię i nazwisko ocenianego', 'dane oceniającego i innych osób', 'nazwa urzędu i komórki', 'daty zatrudnienia i umowy, stopień służbowy', 'loginy i adresy e-mail']} /></div>
            </div>
          </div>
          <h3 className="mt-10 font-sans text-lg font-bold">Zasady</h3>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Card title="Bez pól ocen">Schematy odpowiedzi AI nie mają punktacji, poziomu ani wyniku — sprawdza to test automatyczny. Wynik liczy deterministyczny moduł.</Card>
            <Card title="Rozliczalność">Każde wywołanie jest rejestrowane (funkcja, model, tokeny, czas) razem z decyzją przełożonego: przyjęta, przyjęta po edycji, odrzucona.</Card>
            <Card title="Przejrzystość AI" tone="ai">Widok pokazuje dokładnie to, co trafiłoby do modelu: instrukcje, treść, źródła, adresata i wynik kontroli danych. Podgląd niczego nie wysyła i nie zapisuje.</Card>
          </div>
          <h3 className="mt-10 font-sans text-lg font-bold">Model językowy — wybór bez zmian w kodzie</h3>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Card title="Hackathon">Groq, plan darmowy (<code>gpt-oss-120b</code>). Alternatywa: Google Gemini.</Card>
            <Card title="Wdrożenie w urzędzie" tone="ok">PLLuM w infrastrukturze ministerstwa (vLLM na GPU lub Ollama na CPU) — dane nie opuszczają urzędu.</Card>
            <Card title="Wariant chmurowy">Claude lub inny model z umową powierzenia i regionem UE.</Card>
          </div>
        </Section>

        {/* ASYSTENT */}
        <Section id="asystent" kicker="06 · Asystent" title="Rozmowa z asystentem: dwa tryby"
          lead="Asystent odpowiada wyłącznie na podstawie bazy wiedzy i podaje źródło. Gdy źródła nie wystarczają, mówi o tym wprost — i w ogóle nie wywołuje modelu.">
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Zasady i wymagania" tone="first">Pytania o przepisy i procedurę. Dostępny wszędzie: na osobnej stronie i w panelu bocznym oceny.<br /><i>„Ile kryteriów dodatkowych można wybrać?” → maks. 3, § 2 ust. 2 rozporządzenia z 2016 r.</i></Card>
            <Card title="Przygotowanie do rozmowy" tone="periodic">Przypięty do konkretnej oceny i jej kompetencji. Pytania do pracownika, kwestie do omówienia, porządkowanie argumentów. Tylko dla oceniającego.</Card>
          </div>
          <h3 className="mt-10 font-sans text-lg font-bold">Jak powstaje odpowiedź</h3>
          <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-stretch">
            <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center">
              <Node sub="w trybie formalnym">Pytanie</Node>
              <Arrow />
              <Node tone="first" sub="na serwerze aplikacji, odporne na odmianę słów (kryteria, kryteriów)">Wyszukiwanie w bazie wiedzy</Node>
              <Arrow />
              <Node sub="fragment dobrze pasuje do pytania i zawiera większość jego słów">Dwa warunki</Node>
              <Arrow />
            </div>
            <div className="grid gap-2 md:w-64">
              <Node tone="ok" sub="z cytowaniem: tytuł i strona">Tak → odpowiedź modelu</Node>
              <Node tone="bad" sub="model nie jest wywoływany">Nie → „brak informacji”</Node>
            </div>
          </div>
          <div className="mt-8 rounded-lg border border-rule bg-white p-5">
            <h3 className="font-sans text-[17px] font-bold">Baza wiedzy</h3>
            <div className="mt-3 grid gap-x-8 md:grid-cols-2">
              <List items={['ustawa o służbie cywilnej (t.j. Dz.U. 2026 poz. 590)', 'rozporządzenia z 2015 i 2016 r. z załącznikami', 'poradniki KPRM: pierwsza ocena, oceny okresowe']} />
              <List items={['model kompetencji: wszystkie wskaźniki i poziomy', '29 pytań i odpowiedzi z podstawą prawną', 'źródła urzędu dodawane przez administratora']} />
            </div>
          </div>
        </Section>

        {/* DOKUMENTY */}
        <Section id="dokumenty" kicker="07 · Dokumenty" title="Arkusze 1:1 ze wzorami z rozporządzeń"
          lead="PDF do druku i podpisu oraz DOCX do edycji. Układ, brzmienie pól, przypisy i pola podpisów odpowiadają załącznikom do rozporządzeń.">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Arkusz pierwszej oceny', 'zał. nr 2, rozp. z 2015 r.', 'first'],
              ['Arkusz A', 'kierownik urzędu · zał. nr 2, rozp. z 2016 r.', 'periodic'],
              ['Arkusz B', 'kierowanie pracownikami · zał. nr 3', 'periodic'],
              ['Arkusz C', 'pozostałe stanowiska · zał. nr 4', 'periodic'],
            ].map(([t, s, tone]) => (
              <div key={t} className="rounded-lg border border-rule bg-white p-4">
                <div className="relative mx-auto mb-4 h-36 w-28 rounded-sm border border-rule-strong bg-paper p-2 shadow-[3px_3px_0_var(--color-rule)]" aria-hidden>
                  <div className={`h-2 w-14 rounded-sm ${tone === 'first' ? 'bg-first' : 'bg-periodic'}`} />
                  {[...Array(7)].map((_, i) => <div key={i} className="mt-2 h-1.5 rounded-sm bg-rule-strong" style={{ width: `${90 - (i % 3) * 18}%` }} />)}
                  <div className="absolute bottom-2 left-2 right-2 flex justify-between"><span className="h-px w-9 bg-ink-soft" /><span className="h-px w-9 bg-ink-soft" /></div>
                </div>
                <h3 className="font-sans font-bold">{t}</h3>
                <p className="text-sm text-ink-soft">{s}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <Card title="Część I do podpisu">Po ustaleniu kryteriów — oryginał do akt osobowych, kopia dla ocenianego.</Card>
            <Card title="Plan rozwoju (IPRZ)">Działania 70-20-10, mierniki sukcesu, terminy i status realizacji.</Card>
            <Card title="Scenariusz rozmowy">Cel, otwarcie, informacja zwrotna sytuacja–zachowanie–wpływ, pytania, elementy formalne.</Card>
          </div>
        </Section>

        {/* TERMINY */}
        <Section id="terminy" kicker="08 · Terminy i wymogi" title="Terminy z przepisów, lista kontrolna, przypomnienia"
          lead="Terminy wylicza system. Przed sporządzeniem oceny lista kontrolna sprawdza wymogi formalne i podaje podstawę prawną.">
          <div className="overflow-x-auto">
            <ol className="flex min-w-[720px] items-start">
              {[['21 dni', 'rozmowa wstępna (pierwsza ocena)'], ['8 miesięcy', 'termin sprawozdania'], ['24 miesiące', 'kolejna ocena okresowa'], ['6 miesięcy', 'ponowna ocena po negatywnej'], ['7 dni', 'sprzeciw od oceny okresowej']].map(([v, l], i, arr) => (
                <li key={v} className="relative flex-1 px-2 text-center">
                  {i < arr.length - 1 && <span className="absolute left-1/2 top-5 h-0.5 w-full bg-rule-strong" aria-hidden />}
                  <span className="relative mx-auto flex size-10 items-center justify-center rounded-full border-2 border-first bg-white text-first" aria-hidden>
                    <svg viewBox="0 0 20 20" className="size-5"><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" strokeWidth="1.8" /><path d="M10 6v4l3 2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
                  </span>
                  <p className="mt-3 font-serif text-xl font-semibold">{v}</p>
                  <p className="text-sm text-ink-soft">{l}</p>
                </li>
              ))}
            </ol>
          </div>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <Card title="Lista kontrolna" tone="ok">Terminy, obowiązkowe uzasadnienie przy ocenie negatywnej, właściwy arkusz — każdy punkt z podstawą prawną.</Card>
            <Card title="Przypomnienia">Ręczne (kadry) i automatyczne, codziennie, bez duplikatów. E-mail bez danych oceny.</Card>
            <Card title="Komunikacja">Powiadomienia przy zmianach etapu, np. prośba do kierującego o potwierdzenie pierwszej oceny; wiadomości w sprawie oceny.</Card>
          </div>
        </Section>

        {/* ROLE */}
        <Section id="role" kicker="09 · Role i uprawnienia" title="Każdy widzi tylko to, co do niego należy"
          lead="Rola jest przypisana do osoby w danym urzędzie. Dane instytucji są od siebie odizolowane w każdym zapytaniu.">
          <div className="overflow-x-auto rounded-lg border border-rule bg-white">
            <table className="w-full min-w-[640px] text-[15px]">
              <caption className="sr-only">Macierz uprawnień ról</caption>
              <thead>
                <tr className="border-b border-rule bg-paper text-left">
                  <th scope="col" className="p-3">Czynność</th>
                  {ROLES.map((r, i) => <th key={r} scope="col" className="p-3 text-center">{r}<span className="block text-xs font-normal text-ink-soft">{SCOPE[i]}</span></th>)}
                </tr>
              </thead>
              <tbody>
                {PERMS.map(([label, v]) => (
                  <tr key={label} className="border-b border-rule last:border-0">
                    <th scope="row" className="p-3 text-left font-normal">{label}</th>
                    {v.map((x, i) => (
                      <td key={i} className="p-3 text-center">
                        {x === 1 ? <span className="inline-flex size-6 items-center justify-center rounded-full bg-ok-tint text-ok" title="tak"><Check /><span className="sr-only">tak</span></span>
                          : x === 2 ? <span className="text-xs font-bold text-warn" title="w sytuacjach wyjątkowych, z audytem">wyjątkowo</span>
                          : <span className="text-rule-strong" aria-label="nie">—</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm text-ink-soft">„Wyjątkowo” — administrator może działać za oceniającego (np. przy nieobecności); każda zmiana trafia do historii.</p>
        </Section>

        {/* ARCHITEKTURA */}
        <Section id="architektura" kicker="10 · Architektura" title="Technologie i budowa systemu"
          lead="Bezstanowy backend, moduły z jasnymi granicami i logika przepisów w czystych, przetestowanych funkcjach.">
          <div className="rounded-xl border border-rule bg-white p-5 md:p-8">
            <div className="flex flex-col items-stretch gap-3">
              <Node sub="komputer lub tablet, HTTPS">Przeglądarka — React 19, TypeScript</Node>
              <div className="flex justify-center"><Arrow down /></div>
              <div className="rounded-lg border-2 border-dashed border-rule-strong p-4">
                <p className="mb-3 text-sm font-bold text-ink-soft">Serwer · nginx → Docker Compose</p>
                <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                  <div className="rounded-lg border-2 border-ink p-4">
                    <p className="font-bold">Django 6 + REST API <span className="font-normal text-ink-soft">/api/v1/ · OpenAPI 3</span></p>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                      {[['institutions', 'role, instytucje'], ['employees', 'pracownicy, OSP'], ['competencies', 'model kompetencji'], ['assessments', 'arkusze, wynik, lista'], ['development', 'IPRZ'], ['deadlines', 'terminy, powiadomienia'], ['assistant', 'baza wiedzy, rozmowy'], ['documents', 'PDF / DOCX']].map(([m, d]) => (
                        <div key={m} className={`rounded border px-2 py-1.5 ${m === 'assistant' ? 'border-dashed border-ai bg-ai-tint' : 'border-rule bg-paper'}`}>
                          <code className="text-[13px] font-bold">{m}</code><span className="block text-xs text-ink-soft">{d}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="grid gap-3 md:w-52">
                    <Node sub="audyt zmian (historia)">PostgreSQL 17</Node>
                    <Node tone="ai" sub="opcjonalnie, na GPU">vLLM + PLLuM</Node>
                  </div>
                </div>
              </div>
              <p className="mt-2 text-sm font-bold text-ink-soft">Usługi zewnętrzne i integracje</p>
              <div className="grid gap-3 md:grid-cols-3">
                <Node tone="ai" sub="wymienny konfiguracją">Model językowy</Node>
                <Node sub="pracownicy, komórki, OSP">System kadrowy (np. QNT)</Node>
                <Node sub="eksport arkusza PDF">EZD</Node>
              </div>
            </div>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <Card title="Skalowanie">Bezstanowy backend, kolejne repliki za nginx; wiele instytucji w jednej instalacji.</Card>
            <Card title="Integracje">Udokumentowane API REST — <a className="font-bold text-first underline" href="/api/v1/docs/">podgląd Swagger</a> dostępny bez logowania.</Card>
            <Card title="Jakość" tone="ok">74 testy automatyczne: przepisy, terminy, uprawnienia, izolacja instytucji, AI, dokumenty. Uruchamiane automatycznie przy każdej zmianie kodu.</Card>
          </div>
        </Section>

        {/* BEZPIECZEŃSTWO */}
        <Section id="bezpieczenstwo" kicker="11 · Bezpieczeństwo" title="Ochrona danych i gotowość do wdrożenia"
          lead="Prototyp ma zabezpieczenia potrzebne do pracy na danych testowych. Przed produkcją wskazujemy, co trzeba uzupełnić.">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-ok/30 bg-white p-5">
              <h3 className="font-sans text-[17px] font-bold text-ok">Jest w prototypie</h3>
              <div className="mt-3"><List items={['logowanie sesyjne, CSRF, limit prób', 'role i izolacja instytucji, testy uprawnień', 'pseudonimizacja i kontrola danych przed AI', 'historia zmian ocen, rejestr wywołań AI', 'HTTPS, bezpieczne ciasteczka, brak danych w adresach URL', 'dostępność: kontrast, fokus, etykiety, klawiatura']} /></div>
            </div>
            <div className="rounded-lg border border-warn/30 bg-white p-5">
              <h3 className="font-sans text-[17px] font-bold text-warn">Przed produkcją</h3>
              <ul className="mt-3 space-y-1.5 text-[15px]">
                {['PLLuM w infrastrukturze MC albo dostawca z umową powierzenia (art. 28 RODO)', 'DPIA (art. 35 RODO), polityka retencji rejestru AI', 'SSO urzędu (SAML/OIDC), MFA dla kadr i administratora', 'kopie zapasowe z testem odtworzenia, HSTS', 'podpis kwalifikowany, rejestracja w EZD', 'audyt WCAG 2.1 AA, skanowanie podatności'].map((x) => (
                  <li key={x} className="flex gap-2"><span className="mt-2 size-2 shrink-0 rounded-full bg-warn" aria-hidden />{x}</li>
                ))}
              </ul>
            </div>
          </div>
        </Section>

        {/* ZMIANY */}
        <Section id="zmiany" kicker="12 · Zmiany przepisów" title="Kto co zmienia, gdy zmieniają się przepisy"
          lead="Urząd aktualizuje wiedzę asystenta sam. Reguły wpływające na wynik oceny zmienia programista — z testem, żeby pomyłka nie zmieniła oceny pracownika.">
          <div className="grid gap-4 md:grid-cols-3">
            <Card title="Administrator urzędu" tone="first">Panel „Baza wiedzy”: nowy tekst ustawy, rozporządzenie, zarządzenie wewnętrzne. Pole „zastępuje źródło” wyłącza starą wersję. Asystent od razu cytuje nowe źródło.</Card>
            <Card title="Operator systemu">Wspólne akty dla wszystkich urzędów, zestaw pytań i odpowiedzi, nowa wersja modelu kompetencji (trwające oceny zostają przy swojej).</Card>
            <Card title="Programista" tone="warn">Skale, progi wyniku, kryteria obowiązkowe, terminy. Każda reguła ma odwołanie do paragrafu i własny test automatyczny. Przy każdej zmianie testy uruchamiają się same i wskazują regułę, która przestała się zgadzać z przepisami.</Card>
          </div>
        </Section>

        {/* ZGODNOŚĆ */}
        <Section id="zgodnosc" kicker="13 · Zgodność" title="Wymagania wyzwania i ich realizacja">
          <ul className="grid gap-x-8 gap-y-3 md:grid-cols-2">
            {COMPLIANCE.map(([req, how]) => (
              <li key={req} className="flex gap-3 border-b border-rule pb-3">
                <Check />
                <span><b>{req}</b><span className="block text-[15px] text-ink-soft">{how}</span></span>
              </li>
            ))}
          </ul>
        </Section>
      </main>

      <footer className="border-t border-rule bg-ink text-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-10 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3"><CompassMark className="size-8 text-white" /><div><p className="font-serif text-lg">KompetIQ · Kompas Kompetencji</p><p className="text-sm text-white/70">Asystent AI porządkuje i podpowiada. Ocenę wystawia przełożony.</p></div></div>
          <div className="flex gap-4 text-sm">
            <a href="/api/v1/docs/" className="underline underline-offset-2">Dokumentacja API</a>
            <Link to="/logowanie" className="underline underline-offset-2">Zaloguj się</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
