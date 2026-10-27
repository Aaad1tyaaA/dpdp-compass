import { useState } from "react"
import { Check, PencilLine, Undo2 } from "lucide-react"
import { API_BASE } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { StatusPill, errorDetail } from "@/components/ui/kit"
import type { Analysis, ComplianceFinding } from "@/types"

const STATUSES = [["SATISFIED", "Covered"], ["PARTIAL", "Partial"], ["MISSING", "Missing"], ["NOT_APPLICABLE", "Not applicable"]] as const

/** A reviewer's accept / override on one finding. The model's verdict stays as it was; the decision is recorded beside it. */
export function ReviewControls({ analysis, finding, onChange }: { analysis: Analysis; finding: ComplianceFinding; onChange: (a: Analysis) => void }) {
  const [editing, setEditing] = useState(false)
  const [status, setStatus] = useState<string>(finding.status)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const review = finding.review

  const send = async (decision: "accept" | "override" | "clear") => {
    setBusy(true); setError(null)
    try {
      const r = await fetch(`${API_BASE}/api/compliance/${analysis.id}/findings/${finding.id}/review`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, status: decision === "override" ? status : undefined, note: note || undefined, rev: analysis.review_rev ?? 0 }),
      })
      if (r.status === 409) {  // someone else reviewed meanwhile: show their version, keep the draft
        const fresh = await fetch(`${API_BASE}/api/compliance/${analysis.id}`)
        if (fresh.ok) onChange(await fresh.json())
        throw new Error("This audit was reviewed elsewhere since you opened it. It has been reloaded; check and try again.")
      }
      if (!r.ok) throw new Error(await errorDetail(r))
      onChange(await r.json()); setEditing(false); setNote("")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the review")
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-2 rounded-lg border border-dashed p-3 text-sm">
      {review ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{review.decision === "accept" ? "Accepted" : "Overridden"} by {review.user_name ?? "a reviewer"}</span>
          {review.decision === "override" && <>to <StatusPill status={review.status ?? ""} /></>}
          <span className="text-xs text-muted-foreground">{new Date(review.at).toLocaleString()}</span>
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => send("clear")}><Undo2 /> Undo</Button>
          {review.note && <p className="w-full break-words text-muted-foreground">“{review.note}”</p>}
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Automated finding, not yet reviewed.</span>
          <Button variant="outline" size="sm" disabled={busy} onClick={() => send("accept")}><Check /> Accept</Button>
          <Button variant="outline" size="sm" disabled={busy} onClick={() => setEditing((v) => !v)}><PencilLine /> Override</Button>
        </div>
      )}
      {editing && !review && (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Correct status</span>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="h-8 w-44" aria-label="Correct status"><SelectValue /></SelectTrigger>
              <SelectContent>{STATUSES.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Reason (required), e.g. which clause covers it" aria-label="Reason for override" />
          <Button size="sm" disabled={busy || !note.trim()} onClick={() => send("override")}>Save override</Button>
        </div>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
