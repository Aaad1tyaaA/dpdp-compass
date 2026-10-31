import { useState, type FormEvent } from "react"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom"
import { Eye, EyeOff, Loader2 } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { Logo, ThemeToggle } from "@/components/brand"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ErrorNote } from "@/components/ui/kit"

/** Only same-site paths are followed after sign-in, so a crafted link cannot send people elsewhere. */
function safeNext(raw: string | null): string {
  return raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : "/dashboard"
}

export function AuthPage({ mode }: { mode: "signin" | "signup" }) {
  const { user, loading, signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get("next"))
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const signup = mode === "signup"
  const nextQuery = params.get("next") ? `?next=${encodeURIComponent(next)}` : ""

  if (!loading && user) return <Navigate to={next} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (signup && password.length < 8) return setError("Use a password of at least 8 characters.")
    setBusy(true)
    setError(null)
    try {
      await (signup ? signUp(name.trim(), email.trim(), password) : signIn(email.trim(), password))
      navigate(next, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="flex h-20 items-center justify-between border-b px-4 sm:px-8">
        <Logo />
        <ThemeToggle />
      </header>
      <main className="flex flex-1 items-start justify-center px-4 pt-12 sm:pt-20">
        <div>
        <div className="w-full max-w-md">
          <h1 className="text-4xl font-bold">{signup ? "Create an account" : "Sign in"}</h1>
          <p className="mt-2 text-lg text-muted-foreground">
            {signup ? "Your audits, documents and questions are saved to it." : "Pick up where you left off."}
          </p>
          {!signup && params.get("expired") && (
            <p role="status" className="mt-4 rounded-lg border bg-muted px-4 py-3 text-lg">You were signed out because the server restarted. Please sign in again.</p>
          )}
          <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
            {signup && (
              <div className="space-y-1.5">
                <Label htmlFor="name">Name</Label>
                <Input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input id="password" type={show ? "text" : "password"} autoComplete={signup ? "new-password" : "current-password"} required
                  value={password} onChange={(e) => setPassword(e.target.value)} className="pr-12" aria-describedby={signup ? "password-hint" : undefined} />
                <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 grid w-12 place-items-center text-muted-foreground hover:text-foreground">
                  {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {signup && <p id="password-hint" className="text-base text-muted-foreground">At least 8 characters.</p>}
            </div>
            {error && <ErrorNote>{error}</ErrorNote>}
            <Button type="submit" className="w-full" disabled={busy || !email || !password}>
              {busy && <Loader2 className="animate-spin" />}
              {signup ? "Create account" : "Sign in"}
            </Button>
          </form>
          <p className="mt-6 text-lg text-muted-foreground">
            {signup ? "Already have an account? " : "No account yet? "}
            <Link to={`${signup ? "/signin" : "/signup"}${nextQuery}`} className="font-medium text-foreground underline underline-offset-4">
              {signup ? "Sign in" : "Create one"}
            </Link>
          </p>
        </div>
        </div>
      </main>
    </div>
  )
}
