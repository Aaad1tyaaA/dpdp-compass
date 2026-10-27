import { Link } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/hooks/useTheme"
import { cn } from "@/utils/cn"

/** Compass mark: a ring and a needle pointing north, in the text colour. */
export function CompassMark({ className }: { className?: string; spin?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden fill="none" stroke="currentColor">
      <circle cx="16" cy="16" r="13" strokeWidth="1.6" />
      <path d="M16 6.5 L19.2 16 L16 25.5 L12.8 16 Z" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M16 6.5 L19.2 16 L12.8 16 Z" fill="currentColor" stroke="none" />
    </svg>
  )
}

/** The app's mark: the compass, in a blue rounded square. */
export function Seal({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn("grid place-items-center rounded-lg bg-primary text-primary-foreground", className)}>
      <CompassMark className="size-[70%]" />
    </span>
  )
}

export function Logo({ to = "/", compact = false }: { to?: string; compact?: boolean }) {
  return (
    <Link to={to} className="group flex shrink-0 items-center gap-2.5" aria-label="DPDP Compass home">
      <Seal className="size-10" />
      {!compact && <span className="text-xl font-bold">DPDP Compass</span>}
    </Link>
  )
}

export function ThemeToggle({ className }: { className?: string }) {
  const { resolved, toggle } = useTheme()
  const dark = resolved === "dark"
  return (
    <button onClick={toggle} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"} title={dark ? "Light mode" : "Dark mode"}
      className={cn("relative grid size-12 place-items-center overflow-hidden rounded-lg border-2 text-foreground transition-colors hover:bg-secondary", className)}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={dark ? "moon" : "sun"} initial={{ y: 14, opacity: 0, rotate: -60 }} animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: -14, opacity: 0, rotate: 60 }} transition={{ duration: 0.25 }}>
          {dark ? <Moon className="size-4" /> : <Sun className="size-4" />}
        </motion.span>
      </AnimatePresence>
    </button>
  )
}
