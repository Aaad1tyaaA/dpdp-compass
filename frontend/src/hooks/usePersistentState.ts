import { useCallback, useSyncExternalStore, type SetStateAction } from "react"
import { API_BASE } from "@/services/api"

/* State that survives switching pages, a refresh, and (when signed in) a different device.
   Values live in a module-level store, not in the component, so an audit or streamed answer that
   finishes after you navigate away still lands, and is there when you come back.
   - Every value is mirrored to sessionStorage for an instant restore on refresh.
   - When a user is signed in, changes are also saved to their account (debounced) and loaded
     back at sign-in, so work follows the account.
   `session: false` keeps a value in memory only (navigation-safe, reset on refresh, never saved) —
   use it for in-flight flags like "loading", so a refresh mid-request can't leave a spinner stuck on. */

const PREFIX = "dpdp:"
const SAVE_DELAY_MS = 900
const values = new Map<string, unknown>()
const listeners = new Map<string, Set<() => void>>()
const dirty = new Set<string>()
let account: string | null = null
let timer: ReturnType<typeof setTimeout> | undefined

function read<T>(key: string, initial: T, session: boolean): T {
  if (values.has(key)) return values.get(key) as T
  let v = initial
  if (session) {
    try {
      const raw = sessionStorage.getItem(PREFIX + key)
      if (raw !== null) v = JSON.parse(raw) as T
    } catch { /* storage blocked or corrupt: start fresh */ }
  }
  values.set(key, v)
  return v
}

function mirror(key: string, v: unknown) {
  try { sessionStorage.setItem(PREFIX + key, JSON.stringify(v)) } catch { /* quota/blocked: memory copy still works */ }
}

function notifyAll() {
  listeners.forEach((set) => set.forEach((cb) => cb()))
}

function flush() {
  timer = undefined
  if (!account) return dirty.clear()
  for (const key of [...dirty]) {
    dirty.delete(key)
    // keepalive lets the last save finish if the tab is closing. A failed save is retried on the next change.
    fetch(`${API_BASE}/api/me/state/${encodeURIComponent(key)}`, {
      method: "PUT", credentials: "include", keepalive: true,
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ value: values.get(key) }),
    }).catch(() => dirty.add(key))
  }
}

/** Load the signed-in user's saved work into the store. Called once at sign-in. */
export async function loadSavedState(userId: string): Promise<void> {
  if (account !== userId) clearLocal()  // a different person was using this browser tab
  account = userId
  try {
    const res = await fetch(`${API_BASE}/api/me/state`, { credentials: "include" })
    if (!res.ok) return
    for (const [key, v] of Object.entries(await res.json() as Record<string, unknown>)) {
      values.set(key, v)
      mirror(key, v)
    }
    notifyAll()
  } catch { /* offline: the browser's own copy is used */ }
}

function clearLocal() {
  values.clear()
  dirty.clear()
  try {
    for (const k of Object.keys(sessionStorage)) if (k.startsWith(PREFIX)) sessionStorage.removeItem(k)
  } catch { /* storage blocked */ }
}

/** Forget everything held in this browser. Called at sign-out. */
export function clearSavedState(): void {
  if (timer) { clearTimeout(timer); timer = undefined }
  account = null
  clearLocal()
  notifyAll()
}

export function usePersistentState<T>(key: string, initial: T, { session = true } = {}) {
  const subscribe = useCallback((cb: () => void) => {
    const set = listeners.get(key) ?? new Set()
    set.add(cb)
    listeners.set(key, set)
    return () => { set.delete(cb) }
  }, [key])
  const value = useSyncExternalStore(subscribe, () => read(key, initial, session))

  const setValue = useCallback((next: SetStateAction<T>) => {
    const prev = read(key, initial, session)
    const v = typeof next === "function" ? (next as (p: T) => T)(prev) : next
    values.set(key, v)
    if (session) {
      mirror(key, v)
      if (account) {
        dirty.add(key)
        timer ??= setTimeout(flush, SAVE_DELAY_MS)
      }
    }
    listeners.get(key)?.forEach((cb) => cb())
  }, [key, initial, session])

  return [value, setValue] as const
}
