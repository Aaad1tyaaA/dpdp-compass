import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { API_BASE } from "@/services/api"
import { clearSavedState, loadSavedState } from "@/hooks/usePersistentState"

export interface User { id: string; email: string; name: string }

interface AuthValue {
  user: User | null
  /** True until the first check of the session cookie has finished. */
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (name: string, email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  /** True when the server stopped accepting this browser's session (e.g. it restarted), so it was signed out. */
  expired: boolean
  /** Re-read the profile after it changes (for example the display name). */
  refresh: () => Promise<void>
}

const Ctx = createContext<AuthValue | null>(null)

/** JSON request to the API; throws an Error carrying the server's message. */
export async function api<T = unknown>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {}
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...rest,
    ...(json !== undefined ? { method: rest.method ?? "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(json) } : {}),
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail
    const first = Array.isArray(detail) ? (detail[0] as { msg?: string; loc?: string[] }) : null
    // Validation errors arrive as a list; turn the first into a sentence a person can act on.
    const message = typeof detail === "string" ? detail
      : first?.loc?.includes("password") ? "Use a password of at least 8 characters."
      : first?.msg ?? "Something went wrong. Please try again."
    throw new Error(message.charAt(0).toUpperCase() + message.slice(1))
  }
  return body as T
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [expired, setExpired] = useState(false)

  const adopt = useCallback(async (u: User | null) => {
    if (u) await loadSavedState(u.id)  // bring the account's saved work into this browser before the app renders
    else clearSavedState()             // never leave one person's work on screen for the next
    setUser(u)
    if (u) setExpired(false)
  }, [])

  // Any API call answered 401 while we think we are signed in means the session is gone (on the free host the
  // server's session store is wiped on restart). Sign out once, so the app shows the sign-in page instead of
  // silently failing every request. One watcher covers every fetch in the app.
  useEffect(() => {
    if (!user) return
    const original = window.fetch
    window.fetch = async (...args) => {
      const res = await original(...args)
      const url = typeof args[0] === "string" ? args[0] : args[0] instanceof Request ? args[0].url : String(args[0])
      if (res.status === 401 && url.includes("/api/") && !url.includes("/api/auth/")) {
        clearSavedState()
        setExpired(true)
        setUser(null)
      }
      return res
    }
    return () => { window.fetch = original }
  }, [user])

  const refresh = useCallback(async () => {
    try {
      const { user: u } = await api<{ user: User | null }>("/api/auth/me")
      await adopt(u)
    } catch {
      setUser(null)  // backend unreachable: treat as signed out; the sign-in page reports the error on submit
    } finally {
      setLoading(false)
    }
  }, [adopt])

  useEffect(() => { void refresh() }, [refresh])

  const value = useMemo<AuthValue>(() => ({
    user, loading, refresh, expired,
    signIn: async (email, password) => adopt(await api<User>("/api/auth/login", { json: { email, password } })),
    signUp: async (name, email, password) => adopt(await api<User>("/api/auth/signup", { json: { name, email, password } })),
    signOut: async () => { await api("/api/auth/logout", { method: "POST" }).catch(() => undefined); await adopt(null) },
  }), [user, loading, refresh, adopt, expired])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx)
  if (!v) throw new Error("useAuth must be used inside <AuthProvider>")
  return v
}
