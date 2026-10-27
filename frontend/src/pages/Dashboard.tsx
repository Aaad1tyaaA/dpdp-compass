import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Building2, FilePenLine, MessagesSquare } from "lucide-react"
import { API_BASE } from "@/services/api"
import { useAuth } from "@/auth/AuthContext"
import { Skeleton } from "@/components/ui/misc"
import { ErrorNote, PageHeader, scoreLabel, scoreTone } from "@/components/ui/kit"
import { daysUntil } from "@/components/motion"
import type { AnalysisSummary, Policy } from "@/types"

const ACTIONS = [
  { to: "/business", icon: Building2, t: "Check a privacy policy", d: "See which rules of the law it meets." },
  { to: "/business", icon: FilePenLine, t: "Write a privacy policy", d: "Answer some questions and get a complete policy." },
  { to: "/citizen", icon: MessagesSquare, t: "Ask about your rights", d: "Get a plain answer from the law." },
]

export function Dashboard() {
  const { user } = useAuth()
  const [audits, setAudits] = useState<AnalysisSummary[] | null>(null)
  const [policies, setPolicies] = useState<Policy[] | null>(null)
  const [down, setDown] = useState(false)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/compliance?limit=8`).then((r) => r.json()),
      fetch(`${API_BASE}/api/policies`).then((r) => r.json()),
    ]).then(([a, p]) => { setAudits(a); setPolicies(p) }).catch(() => setDown(true))
  }, [])

  return (
    <div className="space-y-10">
      <PageHeader title={`Welcome${user ? `, ${user.name.split(" ")[0]}` : ""}`} subtitle="What would you like to do?" />

      <ul className="grid gap-4 md:grid-cols-3">
        {ACTIONS.map((a) => (
          <li key={a.t}>
            <Link to={a.to} className="flex h-full flex-col gap-3 rounded-lg border-2 p-6 transition-colors hover:border-primary hover:bg-accent">
              <a.icon className="size-8 text-primary" />
              <span className="text-xl font-bold">{a.t}</span>
              <span className="text-muted-foreground">{a.d}</span>
              <span className="mt-auto flex items-center gap-2 font-bold text-primary">Start <ArrowRight className="size-5" /></span>
            </Link>
          </li>
        ))}
      </ul>
      {down && <ErrorNote>The app cannot reach its server right now. Please try again in a minute.</ErrorNote>}

      <p className="rounded-lg bg-secondary p-5 text-lg">
        <strong>{daysUntil("2027-05-13")} days</strong> until the main duties of the law apply to every business (13 May 2027).
      </p>

      <div className="grid gap-10 lg:grid-cols-2">
        <section>
          <h2 className="text-2xl font-bold">Your recent checks</h2>
          {audits === null ? (
            <div className="mt-4 space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}</div>
          ) : audits.length === 0 ? (
            <p className="mt-4 text-muted-foreground">You have not checked a policy yet.</p>
          ) : (
            <ul className="mt-4 divide-y rounded-lg border">
              {audits.map((a) => (
                <li key={a.id} className="flex items-center gap-4 p-4">
                  <span className="w-14 text-center text-2xl font-bold" style={{ color: scoreTone(a.overall_score) }}>{a.overall_score}</span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-bold">{a.policy_name}</div>
                    <div className="text-muted-foreground">{new Date(a.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</div>
                  </div>
                  <span className="font-bold" style={{ color: scoreTone(a.overall_score) }}>{scoreLabel(a.overall_score)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2 className="text-2xl font-bold">Your saved policies</h2>
          {policies === null ? (
            <div className="mt-4 space-y-3">{[0, 1].map((i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : policies.length === 0 ? (
            <p className="mt-4 text-muted-foreground">No saved policies yet.</p>
          ) : (
            <ul className="mt-4 divide-y rounded-lg border">
              {policies.map((p) => (
                <li key={p.id} className="p-4">
                  <div className="truncate font-bold">{p.name}</div>
                  <div className="text-muted-foreground">{new Date(p.uploaded_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
