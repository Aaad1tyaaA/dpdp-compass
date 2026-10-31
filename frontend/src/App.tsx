import { Component, lazy, Suspense, type ReactNode } from "react"
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from "react-router-dom"
import { MotionConfig } from "motion/react"
import { Toaster } from "sonner"
import { RotateCcw } from "lucide-react"
import { AppShell } from "@/components/layout/Layout"
import { Button } from "@/components/ui/button"
import { Skeleton, TooltipProvider } from "@/components/ui/misc"
import { useTheme } from "@/hooks/useTheme"
import { AuthProvider, useAuth } from "@/auth/AuthContext"

// Route-level code splitting: each page is its own chunk.
const Landing = lazy(() => import("@/pages/Landing").then(m => ({ default: m.Landing })))
const Dashboard = lazy(() => import("@/pages/Dashboard").then(m => ({ default: m.Dashboard })))
const BusinessChat = lazy(() => import("@/pages/BusinessChat").then(m => ({ default: m.BusinessChat })))
const CitizenChat = lazy(() => import("@/pages/CitizenChat").then(m => ({ default: m.CitizenChat })))
const About = lazy(() => import("@/pages/About").then(m => ({ default: m.About })))
const Evaluation = lazy(() => import("@/pages/Evaluation").then(m => ({ default: m.Evaluation })))
const AuthPage = lazy(() => import("@/pages/AuthPage").then(m => ({ default: m.AuthPage })))
const Account = lazy(() => import("@/pages/Account").then(m => ({ default: m.Account })))

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="mx-auto my-16 max-w-md space-y-4 rounded-lg border-2 bg-card p-8 text-center" role="alert">
        <div className="text-lg font-semibold">Something went wrong on this page</div>
        <p className="break-words text-sm text-muted-foreground">{this.state.error.message}</p>
        <Button onClick={() => this.setState({ error: null })}><RotateCcw /> Try again</Button>
      </div>
    )
  }
}

function NotFound() {
  return (
    <div className="mx-auto my-20 max-w-md space-y-4 text-center">
      <h1 className="text-3xl font-bold">Page not found</h1>
      <p className="text-muted-foreground">The page you're looking for doesn't exist.</p>
      <Button asChild variant="outline"><Link to="/">Back to home</Link></Button>
    </div>
  )
}

function PageSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-56" /><Skeleton className="h-4 w-80" /><Skeleton className="h-48 w-full" />
    </div>
  )
}

/** Pages simply appear: no transition to wait for or be distracted by. */
function Page({ children }: { children: ReactNode }) {
  return <>{children}</>
}

function AppRoutes() {
  const location = useLocation()
  const { user, loading, expired } = useAuth()
  if (location.pathname === "/") {
    return <ErrorBoundary key="/"><Suspense fallback={null}><Landing /></Suspense></ErrorBoundary>
  }
  if (location.pathname === "/signin" || location.pathname === "/signup") {
    return <ErrorBoundary key="auth"><Suspense fallback={null}><AuthPage mode={location.pathname === "/signup" ? "signup" : "signin"} /></Suspense></ErrorBoundary>
  }
  // The app is for signed-in users: work is saved to the account. Remember where the person was going.
  if (loading) return <div className="grid min-h-screen place-items-center bg-background" aria-busy="true" aria-label="Loading"><Skeleton className="h-10 w-40" /></div>
  if (!user) return <Navigate to={`/signin?next=${encodeURIComponent(location.pathname + location.search)}${expired ? "&expired=1" : ""}`} replace />
  return (
    <AppShell>
      {/* keyed by path: an error on one page clears when you navigate away */}
      <ErrorBoundary key={location.pathname}>
        <>
          <Page key={location.pathname}>
            <Suspense fallback={<PageSkeleton />}>
              <Routes location={location}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/business" element={<BusinessChat />} />
                <Route path="/citizen" element={<CitizenChat />} />
                <Route path="/about" element={<About />} />
                <Route path="/evaluation" element={<Evaluation />} />
                <Route path="/account" element={<Account />} />
                <Route path="/app" element={<Navigate to="/dashboard" replace />} />
                {/* Uploaded policies now live on the Dashboard */}
                <Route path="/policies" element={<Navigate to="/dashboard" replace />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </Page>
        </>
      </ErrorBoundary>
    </AppShell>
  )
}

function ThemedToaster() {
  const { resolved } = useTheme()
  return <Toaster theme={resolved} position="bottom-right" richColors closeButton toastOptions={{ className: "font-sans" }} />
}

export default function App() {
  return (
    <MotionConfig reducedMotion="always">
      <TooltipProvider delayDuration={200}>
        <BrowserRouter>
          <AuthProvider>
            <AppRoutes />
            <ThemedToaster />
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </MotionConfig>
  )
}
