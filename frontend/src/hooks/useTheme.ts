import { useCallback, useEffect, useSyncExternalStore } from "react"

/* Light / dark / system theme. The class is applied before first paint by a script in index.html,
   so there's no light flash on load; this hook keeps it in sync and remembers the choice. */

type Mode = "light" | "dark" | "system"
const KEY = "dpdp-theme"
const listeners = new Set<() => void>()

function getMode(): Mode {
  try { return (localStorage.getItem(KEY) as Mode) || "system" } catch { return "system" }
}
function systemDark() {
  return typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches
}
function apply(mode: Mode) {
  const dark = mode === "dark" || (mode === "system" && systemDark())
  document.documentElement.classList.toggle("dark", dark)
}

export function useTheme() {
  const mode = useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => { listeners.delete(cb) } },
    getMode,
    () => "system" as Mode,
  )
  // Follow OS changes while in "system" mode.
  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => { if (getMode() === "system") apply("system") }
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [])
  const setMode = useCallback((m: Mode) => {
    try { localStorage.setItem(KEY, m) } catch { /* private mode: still applies for this session */ }
    apply(m)
    listeners.forEach((l) => l())
  }, [])
  const resolved: "light" | "dark" = mode === "dark" || (mode === "system" && systemDark()) ? "dark" : "light"
  return { mode, resolved, setMode, toggle: () => setMode(resolved === "dark" ? "light" : "dark") }
}
