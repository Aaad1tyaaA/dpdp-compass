import { useState } from "react"
import { ArrowRight, Check, FilePenLine, X } from "lucide-react"
import { API_BASE } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { StatusPill, Thinking, errorDetail } from "@/components/ui/kit"
import type { Analysis, AuditComparison, ComplianceFinding, Redline } from "@/types"

/** Propose wording for one finding, let the user edit it, then accept (new version + re-audit) or reject. */
export function RedlinePanel({ analysis, finding, onAccepted, onChange }: {
  analysis: Analysis; finding: ComplianceFinding
  onAccepted: (r: { analysis: Analysis; comparison: AuditComparison }) => void; onChange: (a: Analysis) => void
}) {
  const [proposal, setProposal] = useState<Redline | null>(null)
  const [text, setText] = useState("")
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const base = `${API_BASE}/api/compliance/${analysis.id}/findings/${finding.id}/redline`

  const call = async (label: string, url: string, body?: unknown) => {
    setBusy(label); setError(null)
    try {
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined })
      if (!r.ok) throw new Error(await errorDetail(r))
      return await r.json()
    } catch (e) {
      setError(e instanceof Error ? e.message : "The request failed"); return null
    } finally { setBusy(null) }
  }

  if (!analysis.document) return null
  if (!proposal) {
    return (
      <div className="space-y-1">
        <Button variant="outline" size="sm" disabled={!!busy} onClick={async () => {
          const p = await call("Drafting wording", base)
          if (p) { setProposal(p); setText(p.proposed) }
        }}><FilePenLine /> Propose wording</Button>
        {busy && <Thinking label={busy} />}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
    )
  }
  const unfilled = (text.match(/\[[^\]\n]{2,80}\]/g) ?? [])
  return (
    <div className="space-y-3 rounded-lg border border-primary/30 p-3 text-base">
      <div className="text-xs font-medium text-muted-foreground">
        {proposal.mode === "replace" ? "Replace this sentence" : "Add a new clause"} · drafted by {proposal.source}
      </div>
      {proposal.original && <p className="break-words rounded bg-destructive/10 p-2 text-foreground/80 line-through decoration-destructive/60">{proposal.original}</p>}
      <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} aria-label="Proposed wording" className="bg-success/5" />
      {proposal.explanation && <p className="text-xs text-muted-foreground">{proposal.explanation}</p>}
      {unfilled.length > 0 && (
        <p className="text-xs text-warning">Fill in before publishing: {Array.from(new Set(unfilled)).join(", ")}. Placeholders are kept as written if you accept now.</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" disabled={!!busy || !text.trim()} onClick={async () => {
          const r = await call("Saving a new version and re-auditing", `${base}/accept`, { ...proposal, proposed: text })
          if (r) onAccepted(r)
        }}><Check /> Accept and re-audit</Button>
        <Button variant="ghost" size="sm" disabled={!!busy} onClick={async () => {
          const a = await call("Recording", `${base}/reject`)
          if (a) { onChange(a); setProposal(null) }
        }}><X /> Reject</Button>
      </div>
      {busy && <Thinking label={busy} />}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

const CHANGE_TONE = { improved: "text-success", regressed: "text-destructive", scope: "text-muted-foreground" } as const

/** What an edit changed: the score, each obligation whose status moved, and the sentences that differ. */
export function ComparisonCard({ c, onClose }: { c: AuditComparison; onClose: () => void }) {
  return (
    <Card className="space-y-3 p-5">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Re-audit after your edit</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            Version {c.a.version} <span className="tabular font-semibold">{c.a.score}</span> <ArrowRight className="size-4" /> Version {c.b.version}{" "}
            <span className="tabular font-semibold">{c.b.score}</span>
            <span className="text-muted-foreground">· {c.improved} improved · {c.regressed} regressed</span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Dismiss comparison"><X /></Button>
      </div>
      {!c.comparable && <p className="text-xs text-warning">Not a like-for-like comparison: the {c.differences.join(", ")} differ between the two audits.</p>}
      {c.changes.length > 0 ? (
        <ul className="space-y-1.5 text-base">
          {c.changes.map((x) => (
            <li key={x.obligation_id} className="flex flex-wrap items-center gap-2">
              <span className={`text-xs font-medium ${CHANGE_TONE[x.change]}`}>{x.change}</span> {x.title}
              <StatusPill status={x.from} /> <ArrowRight className="size-3" /> <StatusPill status={x.to} />
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-muted-foreground">No obligation changed status.</p>}
      {c.text_changes.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-xs font-medium text-muted-foreground">{c.text_changes.length} text change{c.text_changes.length > 1 ? "s" : ""}</summary>
          <ul className="mt-2 space-y-2">
            {c.text_changes.map((t, i) => (
              <li key={i} className="space-y-1 break-words">
                {t.a && <p className="rounded bg-destructive/10 p-1.5 line-through decoration-destructive/60">{t.a}</p>}
                {t.b && <p className="rounded bg-success/10 p-1.5">{t.b}</p>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  )
}
