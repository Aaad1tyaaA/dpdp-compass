import { useEffect, useState } from "react"
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom"
import { Building2, Home, Info, LogOut, Menu, MessagesSquare, BarChart3, UserRound, X } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { Logo, ThemeToggle } from "@/components/brand"
import { cn } from "@/utils/cn"

// Plain words for what each page does.
export const NAV = [
  { to: "/dashboard", label: "Home", icon: Home },
  { to: "/business", label: "Check or write a policy", icon: Building2 },
  { to: "/citizen", label: "Ask about your rights", icon: MessagesSquare },
  { to: "/evaluation", label: "How accurate it is", icon: BarChart3 },
  { to: "/about", label: "How it works", icon: Info },
]

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-2">
      <ul className="space-y-1">
        {NAV.map((n) => (
          <li key={n.to}>
            <NavLink to={n.to} onClick={onNavigate}
              className={({ isActive }) => cn("flex items-center gap-3 rounded-lg px-4 py-3 text-[17px] font-bold transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-secondary")}>
              <n.icon className="size-5 shrink-0" />
              <span>{n.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}

function SidebarFooter() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="space-y-2 border-t p-3">
      {user && (
        <div className="px-1 pb-1">
          <div className="text-sm text-muted-foreground">Signed in as</div>
          <div className="truncate font-bold">{user.name}</div>
        </div>
      )}
      <Link to="/account" className="flex items-center gap-3 rounded-lg px-4 py-3 font-bold hover:bg-secondary"><UserRound className="size-5" /> My account</Link>
      {user && (
        <button onClick={() => { void signOut().then(() => navigate("/")) }} className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left font-bold hover:bg-secondary">
          <LogOut className="size-5" /> Sign out
        </button>
      )}
      <div className="flex items-center gap-3 px-1 pt-1"><ThemeToggle /><span className="text-sm text-muted-foreground">Light or dark</span></div>
    </div>
  )
}

/** The app frame: a fixed menu on the left on large screens, a Menu button on small ones. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [pathname])

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-80 flex-col border-r bg-background lg:flex">
        <div className="flex h-20 items-center px-6"><Logo /></div>
        <SidebarNav />
        <SidebarFooter />
      </aside>

      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background px-4 lg:hidden">
        <Logo />
        <button className="flex h-12 items-center gap-2 rounded-lg border-2 px-4 font-bold" aria-expanded={open} onClick={() => setOpen(true)}>
          <Menu className="size-5" /> Menu
        </button>
      </header>
      {open && (
        <>
          <button aria-label="Close menu" className="fixed inset-0 z-40 cursor-default bg-black/40 lg:hidden" onClick={() => setOpen(false)} />
          <aside className="fixed inset-y-0 left-0 z-50 flex w-[88vw] max-w-sm flex-col border-r bg-background lg:hidden" aria-label="Menu">
            <div className="flex h-16 items-center justify-between px-4">
              <Logo />
              <button className="flex h-12 items-center gap-2 rounded-lg border-2 px-4 font-bold" onClick={() => setOpen(false)}><X className="size-5" /> Close</button>
            </div>
            <SidebarNav onNavigate={() => setOpen(false)} />
            <SidebarFooter />
          </aside>
        </>
      )}

      <main className="lg:pl-80">
        <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 sm:py-10">{children}</div>
      </main>
    </div>
  )
}
