import { useEffect, useRef, useState } from "react"
import { ExternalLink, X } from "lucide-react"
import { API_BASE } from "@/services/api"
import { Button } from "@/components/ui/button"
import { StatusPill } from "@/components/ui/kit"
import type { Analysis, ComplianceFinding } from "@/types"

type Mark = { span: [number, number]; kind: "quote" | "conflict" | "passage" }
const MARK_CLASS = { quote: "rounded bg-warning/40 text-foreground", conflict: "rounded bg-destructive/25 text-foreground", passage: "rounded bg-primary/15 text-foreground" }

const RANK = { quote: 3, conflict: 2, passage: 1 } as const

/** Splits the text into runs; where spans overlap, the quote wins over a conflict, and a conflict over a passage. */
function segments(text: string, marks: Mark[]) {
  const kind: (Mark["kind"] | undefined)[] = new Array(text.length)
  for (const m of marks)
    for (let i = Math.max(0, m.span[0]); i < Math.min(text.length, m.span[1]); i++)
      if (!kind[i] || RANK[m.kind] > RANK[kind[i]!]) kind[i] = m.kind
  const out: { text: string; kind?: Mark["kind"] }[] = []
  for (let i = 0; i < text.length; ) {
    let j = i
    while (j < text.length && kind[j] === kind[i]) j++
    out.push({ text: text.slice(i, j), kind: kind[i] })
    i = j
  }
  return out
}

/** The policy text the audit read, with the finding's quote and the passages the judge saw highlighted, next to the law. */
export function EvidenceViewer({ analysis, finding, onClose }: { analysis: Analysis; finding: ComplianceFinding; onClose: () => void }) {
  const [text, setText] = useState<string | null>(analysis.reference_text ?? null)
  const [error, setError] = useState<string | null>(null)
  const first = useRef<HTMLElement | null>(null)
  const doc = analysis.document

  useEffect(() => {
    if (text || !doc) return
    fetch(`${API_BASE}/api/policies/${doc.id}/versions/${doc.version}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("The policy text is no longer available."))))
      .then((v) => setText(v.text))
      .catch((e) => setError(e.message))
  }, [doc, text])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  useEffect(() => { first.current?.scrollIntoView({ block: "center" }) }, [text])

  const quote = finding.policy_evidence[0]?.citation.span
  const marks: Mark[] = [
    ...(quote ? [{ span: quote, kind: "quote" as const }] : []),
    ...(finding.conflicts ?? []).flatMap((c) => [c.a.span, c.b.span]).map((span) => ({ span, kind: "conflict" as const })),
    ...(finding.passages ?? []).filter((p) => p.span).map((p) => ({ span: p.span!, kind: "passage" as const })),
  ]
  const legal = finding.legal_evidence[0]?.citation
  let placed = false

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={(e) => e.target === e.currentTarget && onClose()} role="presentation">
      <aside role="dialog" aria-modal="true" aria-label={`Evidence for ${finding.obligation_title}`}
        className="flex h-full w-full max-w-5xl flex-col bg-background shadow-xl">
        <header className="flex items-center gap-3 border-b px-5 py-3">
          <StatusPill status={finding.status} />
          <div className="min-w-0 flex-1">
            <div className="truncate font-medium">{finding.obligation_title}</div>
            <div className="truncate text-xs text-muted-foreground">
              {doc ? `${doc.name} · version ${doc.version} · sha256 ${doc.sha256.slice(0, 12)}` : analysis.policy_name}
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close"><X /></Button>
        </header>
        <div className="grid min-h-0 flex-1 md:grid-cols-[1fr_340px]">
          <section className="min-h-0 overflow-y-auto px-5 py-4" aria-label="Policy text">
            <div className="mb-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span><mark className="rounded bg-warning/40 px-1 text-foreground">Quoted by the finding</mark></span>
              <span><mark className="rounded bg-primary/15 px-1 text-foreground">Passages the audit read</mark></span>
              {!!finding.conflicts?.length && <span><mark className="rounded bg-destructive/25 px-1 text-foreground">Clauses that contradict each other</mark></span>}
              {!marks.length && <span>No passage of the policy was matched to this obligation.</span>}
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {!text && !error && <p className="text-sm text-muted-foreground">{doc ? "Loading the policy…" : "The policy text was not saved with this audit."}</p>}
            {text && (
              <div className="whitespace-pre-wrap break-words text-base leading-relaxed">
                {segments(text, marks).map((s, i) => {
                  if (!s.kind) return <span key={i}>{s.text}</span>
                  const ref = !placed ? (el: HTMLElement | null) => { first.current = el } : undefined
                  placed = true
                  return <mark key={i} ref={ref} className={MARK_CLASS[s.kind]}>{s.text}</mark>
                })}
              </div>
            )}
          </section>
          <section className="min-h-0 space-y-4 overflow-y-auto border-t bg-secondary/30 px-5 py-4 text-base md:border-l md:border-t-0" aria-label="The law">
            {legal && (
              <div>
                <div className="text-xs font-medium text-muted-foreground">{legal.source_document} · {legal.section}</div>
                <p className="mt-1.5 break-words leading-relaxed">{legal.text}</p>
                {legal.url && (
                  <a className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline" href={`${API_BASE}${legal.url}`} target="_blank" rel="noreferrer">
                    Gazette PDF{legal.page ? `, page ${legal.page}` : ""} <ExternalLink className="size-3" />
                  </a>
                )}
              </div>
            )}
            {(finding.rules ?? []).map((r) => (
              <div key={r.provision}>
                <div className="text-xs font-medium text-muted-foreground">DPDP Rules, 2025 · {r.label}</div>
                <p className="mt-1.5 break-words leading-relaxed">{r.requirement}</p>
                {r.url && (
                  <a className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline" href={`${API_BASE}${r.url}`} target="_blank" rel="noreferrer">
                    Gazette PDF{r.page ? `, page ${r.page}` : ""} <ExternalLink className="size-3" />
                  </a>
                )}
              </div>
            ))}
            {finding.legal_status === "Not yet in force" && <p className="text-xs text-muted-foreground">In force from {finding.in_force_from}.</p>}
          </section>
        </div>
      </aside>
    </div>
  )
}
