import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import { CheckCircle2, ShieldAlert } from "lucide-react"
import { API_BASE } from "@/services/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress, Skeleton } from "@/components/ui/misc"
import { DownloadMenu, ErrorNote, PageHeader, rise, stagger } from "@/components/ui/kit"
import type { AnalysisSummary, EvaluationMetric, GuardrailResult } from "@/types"

const passes = (m: EvaluationMetric) => (m.direction === "lower_better" ? m.value <= m.threshold : m.value >= m.threshold)

function metricsMarkdown(a: AnalysisSummary, metrics: EvaluationMetric[], guardrails: GuardrailResult[]): string {
  const failed = guardrails.filter((g) => !g.passed)
  return [
    `**Audit:** ${a.policy_name} · ${new Date(a.created_at).toLocaleString()}`, "",
    "## Metrics", "", "| Metric | Value | Target | Result |", "|---|---|---|---|",
    ...metrics.map((m) => `| ${m.name} | ${m.value.toFixed(2)} | ${m.direction === "lower_better" ? "≤" : "≥"} ${m.threshold.toFixed(2)} | ${passes(m) ? "Pass" : "Below target"} |`), "",
    "## Guardrails", "", `${guardrails.length - failed.length} of ${guardrails.length} checks passed.`, "",
    ...failed.map((g) => `- **${g.rule}:** ${g.reason}`),
  ].join("\n")
}

export function Evaluation() {
  const [audits, setAudits] = useState<AnalysisSummary[] | null>(null)
  const [id, setId] = useState<string>("")
  const [metrics, setMetrics] = useState<EvaluationMetric[] | null>(null)
  const [guardrails, setGuardrails] = useState<GuardrailResult[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/compliance?limit=20`).then((r) => r.json())
      .then((list: AnalysisSummary[]) => { setAudits(list); if (list[0]) setId(list[0].id) })
      .catch(() => { setAudits([]); setError("Can't reach the backend.") })
  }, [])

  useEffect(() => {
    if (!id) return
    setMetrics(null)
    Promise.all([
      fetch(`${API_BASE}/api/evaluation/${id}/metrics`).then((r) => r.json()),
      fetch(`${API_BASE}/api/evaluation/${id}/guardrails`).then((r) => r.json()),
    ]).then(([m, g]) => { setMetrics(m); setGuardrails(g) }).catch(() => setError("Couldn't load metrics for this audit."))
  }, [id])

  const failed = guardrails.filter((g) => !g.passed)
  const current = audits?.find((a) => a.id === id)

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Quality" title="How accurate it is" subtitle="How well each check found and quoted the right parts of the law.">
        {audits && audits.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <Select value={id} onValueChange={setId}>
              <SelectTrigger className="w-72 max-w-full" aria-label="Audit"><SelectValue /></SelectTrigger>
              <SelectContent>{audits.map((a) => <SelectItem key={a.id} value={a.id}>{a.policy_name} — {new Date(a.created_at).toLocaleDateString()}</SelectItem>)}</SelectContent>
            </Select>
            {current && metrics && <DownloadMenu markdown={metricsMarkdown(current, metrics, guardrails)} title={`Evaluation — ${current.policy_name}`} />}
          </div>
        )}
      </PageHeader>

      {error && <ErrorNote>{error}</ErrorNote>}
      {audits?.length === 0 && !error && (
        <Card className="p-6 text-sm text-muted-foreground">No audits yet. <Link to="/business" className="font-medium text-primary hover:underline">Run one</Link> to see its metrics.</Card>
      )}

      {(audits === null || (id && metrics === null)) && !error && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-36" />)}</div>
      )}

      {metrics && (
        <motion.div key={id} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" variants={stagger} initial="hidden" animate="show">
          {metrics.map((m) => {
            const ok = passes(m)
            return (
              <motion.div key={m.id} variants={rise}>
                <Card className="h-full p-5 transition-shadow duration-200 hover:shadow-lift">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm font-medium">{m.name}</div>
                    <Badge variant={ok ? "success" : "warning"}>{ok ? "Pass" : "Below target"}</Badge>
                  </div>
                  <div className="tabular mt-3 text-[28px] font-semibold leading-none tracking-tight">{m.value.toFixed(2)}</div>
                  <div className="mt-1.5 text-xs text-muted-foreground">target {m.direction === "lower_better" ? "≤" : "≥"} {m.threshold.toFixed(2)} · {m.description}</div>
                  <Progress className="mt-4" value={m.value * 100} indicatorClassName={ok ? "bg-success" : "bg-warning"} />
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      )}

      {metrics && guardrails.length > 0 && (
        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            {failed.length ? <ShieldAlert className="size-5 text-warning" /> : <CheckCircle2 className="size-5 text-success" />}
            <CardTitle>Guardrails · {guardrails.length - failed.length} of {guardrails.length} checks passed</CardTitle>
          </CardHeader>
          {failed.length > 0 && (
            <CardContent>
              <ul className="space-y-2">
                {failed.map((g) => (
                  <li key={g.id} className="rounded-lg border border-warning/25 bg-warning/5 p-3 text-sm">
                    <div className="font-medium">{g.rule}</div>
                    <div className="break-words text-muted-foreground">{g.reason}</div>
                  </li>
                ))}
              </ul>
            </CardContent>
          )}
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        Add a metric by registering a class with <code className="rounded bg-secondary px-1 font-mono">@register_metric</code> in <code className="rounded bg-secondary px-1 font-mono">backend/app/evaluation/registry.py</code>.
      </p>
    </div>
  )
}
