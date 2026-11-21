import { useQueryClient } from '@tanstack/react-query'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api } from './api/client'
import { useMe } from './api/hooks'
import { Layout } from './components/Layout'
import { Link } from 'react-router-dom'
import { Loading, Notice, PageHeader } from './components/ui'
import { AITransparencyPage } from './pages/AITransparencyPage'
import { AssessmentPage } from './pages/assessment/AssessmentPage'
import { AssessmentsPage } from './pages/AssessmentsPage'
import { CompetencyModelPage } from './pages/CompetencyModelPage'
import { DashboardPage } from './pages/DashboardPage'
import { DeadlinesPage } from './pages/DeadlinesPage'
import { DevelopmentPage } from './pages/DevelopmentPage'
import { DevelopmentPlanPage } from './pages/DevelopmentPlanPage'
import { EmployeesPage } from './pages/EmployeesPage'
import { FormalAssistantPage } from './pages/FormalAssistantPage'
import { HRPage } from './pages/HRPage'
import { KnowledgePage } from './pages/KnowledgePage'
import { NotificationsPage } from './pages/NotificationsPage'
import { LoginPage } from './pages/LoginPage'
import { AboutPage } from './pages/AboutPage'
import { TestMailboxPage } from './pages/TestMailboxPage'

const HR_ROLES = ['HR', 'ADMIN']

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { data, isLoading, isError } = useMe()
  const loc = useLocation()
  if (isLoading) return <Loading />
  if (isError || !data) return <Navigate to="/logowanie" state={{ from: loc.pathname }} replace />
  if (!data.active_membership) return <NoInstitution />
  return <>{children}</>
}

/** Strona dostępna tylko dla wskazanych ról — inne role widzą komunikat zamiast pustego wczytywania. */
function RequireRole({ roles, children }: { roles: string[]; children: React.ReactNode }) {
  const { data } = useMe()
  const m = data?.active_membership
  if (m && roles.includes(m.role)) return <>{children}</>
  return (
    <div>
      <PageHeader title="Brak dostępu" />
      <Notice tone="warn" title="Ta strona jest dostępna dla kadr i administratora.">
        Twoja rola w instytucji: {m?.role_display ?? 'brak'}. <Link to="/" className="font-bold underline underline-offset-4">Wróć do pulpitu</Link>
      </Notice>
    </div>
  )
}

function NotFound() {
  return (
    <div>
      <PageHeader title="Nie znaleziono strony" />
      <p>Adres jest nieprawidłowy albo strona została przeniesiona. <Link to="/" className="font-bold underline underline-offset-4">Wróć do pulpitu</Link></p>
    </div>
  )
}

function NoInstitution() {
  const qc = useQueryClient()
  const nav = useNavigate()
  async function logout() {
    await api('/auth/logout/', { method: 'POST' })
    qc.clear()
    nav('/logowanie')
  }
  return (
    <div className="p-10">
      <p>Twoje konto nie jest przypisane do żadnej instytucji. Skontaktuj się z administratorem.</p>
      <button onClick={logout} className="mt-4 underline underline-offset-2">Wyloguj</button>
    </div>
  )
}

export function App() {
  return (
    <Routes>
      <Route path="/logowanie" element={<LoginPage />} />
      <Route path="/o-projekcie" element={<AboutPage />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<DashboardPage />} />
        <Route path="pracownicy" element={<EmployeesPage />} />
        <Route path="oceny" element={<AssessmentsPage />} />
        <Route path="oceny/:id/*" element={<AssessmentPage />} />
        <Route path="rozwoj" element={<DevelopmentPage />} />
        <Route path="rozwoj/:id" element={<DevelopmentPlanPage />} />
        <Route path="terminy" element={<DeadlinesPage />} />
        <Route path="model" element={<CompetencyModelPage />} />
        <Route path="asystent-formalny" element={<FormalAssistantPage />} />
        <Route path="panel-hr" element={<RequireRole roles={HR_ROLES}><HRPage /></RequireRole>} />
        <Route path="powiadomienia" element={<NotificationsPage />} />
        <Route path="skrzynka-testowa" element={<TestMailboxPage />} />
        <Route path="baza-wiedzy" element={<RequireRole roles={HR_ROLES}><KnowledgePage /></RequireRole>} />
        <Route path="przejrzystosc-ai" element={<AITransparencyPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
