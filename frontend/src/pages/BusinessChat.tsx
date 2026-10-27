import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Building2, CalendarClock, Info, FileSearch, Lightbulb, ClipboardCheck, ListChecks, FilePenLine, Scale, Wand2, ArrowRight } from "lucide-react"
import { API_BASE } from "@/services/api"
import { usePersistentState } from "@/hooks/usePersistentState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input, Textarea } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Progress, Separator, Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/misc"
import {
  CopyButton, DownloadMenu, Dropzone, ErrorNote, Markdown, PageHeader, RailCard, SideRail, ScoreRing, StatusPill, Thinking,
  errorDetail, rise, scoreLabel, stagger,
} from "@/components/ui/kit"
import { EvidenceViewer } from "@/components/EvidenceViewer"
import { ReviewControls } from "@/components/ReviewControls"
import { ComparisonCard, RedlinePanel } from "@/components/Redline"
import type { Analysis, AuditComparison, ComplianceFinding, PolicyGenerateResponse } from "@/types"

const fmtDate = (d?: string | null) => d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : ""
const today = () => new Date().toLocaleDateString("en-CA")
const SOURCES_NOTE = "DPDP Act, 2023 and DPDP Rules, 2025 (G.S.R. 846(E), as corrected by G.S.R. 892(E)); commencement per G.S.R. 843(E)"

const ORDER: Record<string, number> = { MISSING: 0, PARTIAL: 1, SATISFIED: 2, NOT_APPLICABLE: 3 }
const STATUS_TITLE: Record<string, string> = { MISSING: "Missing", PARTIAL: "Partially covered", SATISFIED: "Covered", NOT_APPLICABLE: "Not applicable" }

function useElapsed(running: boolean) {
  const [s, setS] = useState(0)
  useEffect(() => {
    if (!running) return
    setS(0)
    const t = setInterval(() => setS((x) => x + 1), 1000)
    return () => clearInterval(t)
  }, [running])
  return s
}

function useReferenceCompanies() {
  const [names, setNames] = useState<string[]>([])
  useEffect(() => {
    fetch(`${API_BASE}/api/citizen/reference-companies`).then((r) => (r.ok ? r.json() : [])).then(setNames).catch(() => {})
  }, [])
  return names
}

type Question = { id: string; text: string; default: string; options: { value: string; label: string }[] }

function useApplicabilityQuestions() {
  const [qs, setQs] = useState<Question[]>([])
  useEffect(() => {
    fetch(`${API_BASE}/api/compass/applicability`).then((r) => (r.ok ? r.json() : [])).then(setQs).catch(() => {})
  }, [])
  return qs
}

function Applicability({ answers, onChange, disabled }: { answers: Record<string, string>; onChange: (a: Record<string, string>) => void; disabled: boolean }) {
  const qs = useApplicabilityQuestions()
  if (!qs.length) return null
  const changed = qs.filter((q) => answers[q.id] && answers[q.id] !== q.default).length
  return (
    <details className="group rounded-lg border px-4 py-3">
      <summary className="cursor-pointer select-none text-sm font-medium">
        About your organisation <span className="font-normal text-muted-foreground">· decides which obligations apply{changed ? ` · ${changed} answered` : ""}</span>
      </summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {qs.map((q) => (
          <div key={q.id} className="space-y-1.5">
            <Label className="text-xs font-normal text-muted-foreground">{q.text}</Label>
            <Select disabled={disabled} value={answers[q.id] ?? q.default} onValueChange={(v) => onChange({ ...answers, [q.id]: v })}>
              <SelectTrigger className="h-9" aria-label={q.text}><SelectValue /></SelectTrigger>
              <SelectContent>{q.options.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">Exemptions that need a government notification are never applied from an answer; they are listed for you to verify.</p>
    </details>
  )
}

/** The audit as a report: executive summary, then findings grouped by status (Missing first). */
function reportMarkdown(a: Analysis): string {
  const c = a.status_counts
  const L: string[] = [
    `# DPDP compliance audit — ${a.policy_name}`, "",
    `**Compliance score:** ${a.overall_score}/100 (${scoreLabel(a.overall_score)})  `,
    `**Audited:** ${new Date(a.created_at).toLocaleString()}  `,
    ...(a.document ? [`**Document:** ${a.document.name}, version ${a.document.version} (sha256 ${a.document.sha256.slice(0, 12)})  `] : []),
    ...(a.assessed_on ? [`**Assessed as of:** ${fmtDate(a.assessed_on)} against the ${SOURCES_NOTE}`] : []), "",
    "## Executive summary", "",
    "| Status | Obligations |", "|---|---|",
    `| Covered | ${c.SATISFIED} |`, `| Partially covered | ${c.PARTIAL} |`, `| Missing | ${c.MISSING} |`, "",
  ]
  const groups = ["MISSING", "PARTIAL", "SATISFIED", "NOT_APPLICABLE"]
  for (const g of groups) {
    const items = a.findings.filter((f) => f.status === g)
    if (!items.length) continue
    L.push(`## ${STATUS_TITLE[g]} (${items.length})`, "")
    for (const f of items) {
      L.push(`### ${f.obligation_title}`, "", `*${f.obligation_id} · ${f.principle}*`, "", f.reasoning, "")
      const legal = f.legal_evidence[0]
      if (legal) L.push(`- **What the law says** (${legal.citation.source_document} ${legal.citation.section ?? ""}): ${legal.excerpt.replace(/\s+/g, " ").slice(0, 320)}`)
      const policy = f.policy_evidence[0]
      if (policy) L.push(`- **What the policy says:** ${policy.excerpt.replace(/\s+/g, " ").slice(0, 320)}`)
      L.push(f.review ? `- **Review:** ${f.review.decision === "accept" ? "accepted" : `overridden to ${STATUS_TITLE[f.review.status ?? ""] ?? f.review.status}`} by ${f.review.user_name ?? "a reviewer"}${f.review.note ? ` — ${f.review.note}` : ""}` : "- **Review:** automated finding, not reviewed")
      for (const c of f.conflicts ?? []) L.push(`- **Contradiction on ${c.topic}:** “${c.a.text}” vs “${c.b.text}”`)
      for (const r of f.rules ?? []) L.push(`- **${r.label}, DPDP Rules 2025:** ${r.requirement}`)
      if (f.legal_status === "Not yet in force") L.push(`- **In force from:** ${fmtDate(f.in_force_from)}`)
      if (f.status !== "SATISFIED") L.push(`- **Action:** ${f.recommended_action}`)
      for (const x of f.status !== "SATISFIED" ? f.fixes ?? [] : []) L.push(`  - ${x}`)
      if (f.suggested_rewrite) L.push(`- **Suggested wording:** ${f.suggested_rewrite}`)
      L.push("")
    }
  }
  if (a.method) L.push(`*Scoring method ${a.method.id} v${a.method.version}: ${a.method.score}.*`, "")
  L.push("---", "", "*Educational guidance, not legal advice. Have counsel review before relying on this report.*")
  return L.join("\n")
}

function Evidence({ label, source, text }: { label: string; source?: string; text: string }) {
  return (
    <div className="rounded-lg border bg-secondary/40 p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        {label}{source && <span className="text-foreground/70">· {source}</span>}
      </div>
      <p className="mt-1.5 line-clamp-4 break-words text-base leading-relaxed text-foreground/85">{text}</p>
    </div>
  )
}

function Finding({ f, analysis, onView, onChange, onAccepted }: {
  f: ComplianceFinding; analysis: Analysis; onView: () => void; onChange: (a: Analysis) => void
  onAccepted: (r: { analysis: Analysis; comparison: AuditComparison }) => void
}) {
  const legal = f.legal_evidence[0]
  const policy = f.policy_evidence[0]
  return (
    <motion.div variants={rise}>
      <AccordionItem value={f.id}>
        <AccordionTrigger>
          <StatusPill status={f.status} />
          <span className="min-w-0 flex-1 break-words leading-snug">{f.obligation_title}</span>
          {f.legal_status === "Not yet in force" && (
            <span className="hidden shrink-0 items-center gap-1 rounded-md border px-2 py-0.5 text-sm font-normal text-muted-foreground md:inline-flex"
              title={`Not in force on ${fmtDate(f.assessed_on)}`}><CalendarClock className="size-3" /> From {fmtDate(f.in_force_from)}</span>
          )}
          {f.review && <span className="shrink-0 text-sm font-normal text-success">{f.review.decision === "accept" ? "Accepted" : "Overridden"}</span>}
          <span className="hidden shrink-0 font-mono text-xs font-normal text-muted-foreground sm:block">{f.obligation_id}</span>
        </AccordionTrigger>
        <AccordionContent className="space-y-3">
          <p className="break-words leading-relaxed text-foreground/85">{f.reasoning}</p>
          <Button variant="outline" size="sm" onClick={onView}><FileSearch /> Show evidence in the document</Button>
          <ReviewControls analysis={analysis} finding={f} onChange={onChange} />
          {legal && <Evidence label="What the law says" source={`${legal.citation.source_document} ${legal.citation.section ?? ""}`} text={legal.excerpt} />}
          {policy ? <Evidence label="What your policy says" text={policy.excerpt} />
            : f.status !== "SATISFIED" && <p className="text-xs text-muted-foreground">No matching clause found in your policy.</p>}
          {!!f.conflicts?.length && f.conflicts.map((c) => (
            <div key={c.topic} className="rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
              <div className="font-medium text-warning">The policy contradicts itself on {c.topic}</div>
              <p className="mt-1 break-words">“{c.a.text}”</p>
              <p className="mt-1 break-words">“{c.b.text}”</p>
            </div>
          ))}
          {f.support === "not quoted" && (
            <p className="text-xs text-muted-foreground">This verdict is not backed by a quotation from the policy, so check it against the document.</p>
          )}
          {f.guardrail_flags?.includes("quote_verbatim") && (
            <p className="text-xs text-warning">The quoted wording could not be found word for word in your policy, so this finding was downgraded.</p>
          )}
          {f.guardrail_flags?.includes("instruction_like") && (
            <p className="text-xs text-warning">A clause used for this finding contains text that reads like an instruction to an AI system. It was treated as policy text only.</p>
          )}
          {!!f.rules?.length && (
            <div className="rounded-lg border p-3 text-sm">
              <div className="text-xs font-medium text-muted-foreground">What the DPDP Rules, 2025 add</div>
              <ul className="mt-1.5 space-y-1">
                {f.rules.map((r) => <li key={r.provision} className="break-words"><span className="font-medium">{r.label}.</span> {r.requirement}</li>)}
              </ul>
            </div>
          )}
          {f.legal_status === "Not yet in force" && (
            <p className="text-xs text-muted-foreground">This obligation comes into force on {fmtDate(f.in_force_from)}. On {fmtDate(f.assessed_on)} it is not yet binding, so treat the gap as preparation work.</p>
          )}
          {!!f.exemptions?.length && (
            <p className="text-xs text-muted-foreground">Exemptions that may apply: Section {f.exemptions.join(", Section ")} of the Act.</p>
          )}
          {!!f.rule_checks?.length && (
            <div className="rounded-lg border p-3 text-sm">
              <div className="text-xs font-medium text-muted-foreground">
                Rule book · {f.rule_checks.filter((c) => c.passed).length} of {f.rule_checks.length} requirements met
              </div>
              <ul className="mt-1.5 space-y-1">
                {f.rule_checks.map((c) => (
                  <li key={c.rule} className="flex gap-2">
                    <span aria-label={c.passed ? "met" : "not met"} className={c.passed ? "text-success" : "text-destructive"}>{c.passed ? "✓" : "✗"}</span>
                    <span className="min-w-0 break-words">{c.rule}{c.basis && <span className="ml-1.5 font-mono text-sm text-muted-foreground">{c.basis}</span>}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {f.status !== "SATISFIED" && (
            <div className="flex gap-2 rounded-lg border border-primary/20 bg-accent/60 p-3 text-base">
              <Wand2 className="mt-0.5 size-4 shrink-0 text-primary" />
              <div className="min-w-0">
                <span className="font-medium text-foreground">Action · </span>{f.recommended_action}
                {!!f.fixes?.length && (
                  <ul className="mt-1.5 list-disc space-y-1 pl-4">{f.fixes.map((x) => <li key={x} className="break-words">{x}</li>)}</ul>
                )}
              </div>
            </div>
          )}
          {f.status !== "SATISFIED" && f.status !== "NOT_APPLICABLE" && <RedlinePanel analysis={analysis} finding={f} onAccepted={onAccepted} onChange={onChange} />}
          {f.suggested_rewrite && (
            <div className="rounded-lg border p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-muted-foreground">Suggested wording</span>
                <CopyButton text={f.suggested_rewrite} />
              </div>
              <p className="mt-1 break-words text-base">{f.suggested_rewrite}</p>
            </div>
          )}
        </AccordionContent>
      </AccordionItem>
    </motion.div>
  )
}

function AuditPanel() {
  const [fileName, setFileName] = usePersistentState<string | null>("biz.audit.fileName", null)
  const [uploadedId, setUploadedId] = usePersistentState<string | null>("biz.audit.uploadedId", null)
  const [uploading, setUploading] = usePersistentState("biz.audit.uploading", false, { session: false })
  const [pasted, setPasted] = usePersistentState("biz.audit.pasted", "")
  const [running, setRunning] = usePersistentState("biz.audit.running", false, { session: false })
  const [error, setError] = usePersistentState<string | null>("biz.audit.error", null, { session: false })
  const [analysis, setAnalysis] = usePersistentState<Analysis | null>("biz.audit.analysis", null)
  const [filter, setFilter] = usePersistentState<"ALL" | "MISSING" | "PARTIAL" | "SATISFIED" | "NOT_APPLICABLE">("biz.audit.filter", "ALL")
  const [asOf, setAsOf] = usePersistentState("biz.audit.asOf", today())
  const [viewing, setViewing] = useState<ComplianceFinding | null>(null)
  const [comparison, setComparison] = usePersistentState<AuditComparison | null>("biz.audit.comparison", null)
  const [answers, setAnswers] = usePersistentState<Record<string, string>>("biz.audit.answers", {})
  const [autorun, setAutorun] = usePersistentState<string | null>("biz.audit.autorun", null)
  const elapsed = useElapsed(running)
  const companies = useReferenceCompanies()
  const resultsRef = useRef<HTMLDivElement>(null)
  const justRan = useRef(false)
  // Bring fresh results into view (not when returning to the page with old results).
  useEffect(() => { if (analysis && justRan.current) { justRan.current = false; resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }) } }, [analysis])

  const upload = async (f: File) => {
    setError(null); setFileName(f.name); setUploadedId(null); setUploading(true)
    try {
      const fd = new FormData(); fd.append("file", f)
      const r = await fetch(`${API_BASE}/api/policies/upload`, { method: "POST", body: fd })
      if (!r.ok) throw new Error(await errorDetail(r))
      setUploadedId((await r.json()).id)
    } catch (e) {
      setFileName(null); setError(e instanceof Error ? e.message : "Upload failed")
    } finally { setUploading(false) }
  }

  const run = async (body: Record<string, string | undefined>) => {
    setError(null); setRunning(true); setAnalysis(null); setFilter("ALL"); setComparison(null)
    try {
      const r = await fetch(`${API_BASE}/api/compliance/analyze`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...body, as_of: asOf || undefined, applicability: answers }) })
      if (!r.ok) throw new Error(await errorDetail(r))
      justRan.current = true
      setAnalysis(await r.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : "The audit failed. Is the backend running?")
    } finally { setRunning(false) }
  }

  const canRun = !running && !uploading && (!!uploadedId || pasted.trim().length > 40)
  const runOwn = () => run(uploadedId && !pasted.trim()
    ? { policy_id: uploadedId, policy_name: fileName ?? undefined }
    : { policy_id: "pasted", policy_name: "Pasted policy", text: pasted })

  // "Audit this draft" on the Create tab hands over a saved policy id.
  useEffect(() => {
    if (!autorun) return
    setAutorun(null); setUploadedId(autorun); setPasted("")
    void run({ policy_id: autorun, policy_name: fileName ?? undefined })
  }, [autorun]) // eslint-disable-line react-hooks/exhaustive-deps

  const counts = analysis?.status_counts
  const findings = analysis ? [...analysis.findings].sort((a, b) => ORDER[a.status] - ORDER[b.status]).filter((f) => filter === "ALL" || f.status === filter) : []
  const total = analysis ? analysis.findings.length || 1 : 1

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Your privacy policy</CardTitle>
          <CardDescription>Upload the document, paste its text, or try one of the bundled Indian app policies.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Dropzone onFile={upload} disabled={running} fileName={uploading ? `Uploading ${fileName}…` : fileName} />
          <div className="space-y-2">
            <Label htmlFor="pasted" className="text-muted-foreground">Or paste the policy text</Label>
            <Textarea id="pasted" value={pasted} onChange={(e) => setPasted(e.target.value)} rows={4} placeholder="Paste the full privacy policy…" />
          </div>
          <Applicability answers={answers} onChange={setAnswers} disabled={running} />
          <Separator />
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={runOwn} disabled={!canRun}><ClipboardCheck /> Run audit</Button>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Label htmlFor="as-of" className="font-normal">Assess as of</Label>
              <Input id="as-of" type="date" className="h-9 w-40" value={asOf} min="2023-08-11" disabled={running}
                onChange={(e) => setAsOf(e.target.value)} />
              {asOf !== "2027-05-13" && <button type="button" className="text-xs underline-offset-2 hover:underline" onClick={() => setAsOf("2027-05-13")}>13 May 2027</button>}
            </div>
            {companies.length > 0 && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                or try a sample
                <Select disabled={running} value="" onValueChange={(v) => run({ reference_company: v })}>
                  <SelectTrigger className="h-9 w-44" aria-label="Sample company"><SelectValue placeholder="Choose a company" /></SelectTrigger>
                  <SelectContent>{companies.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>{error && <ErrorNote>{error}</ErrorNote>}</AnimatePresence>
      <AnimatePresence>
        {running && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            <Card className="space-y-3 p-5">
              <Thinking label={`Checking the policy against DPDP obligations · ${elapsed}s`} />
              <Progress value={Math.min(92, elapsed * 9)} />
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {analysis && counts && (
        <motion.div ref={resultsRef} className="scroll-mt-24 space-y-5" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
          {comparison && comparison.b.id === analysis.id && <ComparisonCard c={comparison} onClose={() => setComparison(null)} />}
          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center gap-5 p-5">
              <ScoreRing score={analysis.overall_score} size={112} label="Compliance score" />
              <div className="min-w-[200px] flex-1 space-y-1">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Compliance score</div>
                <div className="break-words text-lg font-semibold">{analysis.policy_name}</div>
                <div className="text-sm text-muted-foreground">{scoreLabel(analysis.overall_score)} · {analysis.findings.length} obligations checked</div>
                {!!analysis.reviewed_count && (
                  <div className="text-xs text-muted-foreground">
                    Reviewed {analysis.reviewed_count} of {analysis.findings.length}{analysis.reviewed_score != null ? ` · score after review ${analysis.reviewed_score}/100` : ""}
                  </div>
                )}
                {analysis.assessed_on && (
                  <div className="text-xs text-muted-foreground">
                    {analysis.document && <>Version {analysis.document.version} · <span className="font-mono" title={analysis.document.sha256}>{analysis.document.sha256.slice(0, 8)}</span> · </>}
                    As of {fmtDate(analysis.assessed_on)} · {analysis.findings.filter((f) => f.legal_status === "In force").length} of {analysis.findings.length} obligations in force · {SOURCES_NOTE}
                  </div>
                )}
              </div>
              <DownloadMenu markdown={reportMarkdown(analysis)} title={`DPDP compliance audit — ${analysis.policy_name}`}
                subtitle={`Score ${analysis.overall_score}/100 · ${new Date(analysis.created_at).toLocaleDateString()}`} />
            </div>
            {!!analysis.input_notes?.length && (
              <div role="status" className="space-y-1 border-t bg-accent/40 px-5 py-3 text-sm">
                {analysis.input_notes.map((n) => <p key={n}>{n}</p>)}
              </div>
            )}
            {!!analysis.applicability?.notes.length && (
              <div className="space-y-1 border-t px-5 py-3 text-sm text-muted-foreground">
                {analysis.applicability.notes.map((n) => <p key={n}>{n}</p>)}
              </div>
            )}
            {analysis.evidence?.degraded && (
              <div role="status" className="border-t bg-warning/10 px-5 py-3 text-sm text-warning">
                The language model was unavailable, so this audit used keyword matching only. Treat it as a rough first pass and run it again later.
              </div>
            )}
            <div className="grid grid-cols-3 border-t">
              {([["Covered", counts.SATISFIED, "bg-success"], ["Partial", counts.PARTIAL, "bg-warning"], ["Missing", counts.MISSING, "bg-destructive"]] as const).map(([label, n, bar]) => (
                <div key={label} className="space-y-2 border-r p-4 last:border-r-0">
                  <div className="flex items-baseline justify-between"><span className="text-xs text-muted-foreground">{label}</span><span className="tabular text-lg font-semibold">{n}</span></div>
                  <Progress value={(n / total) * 100} indicatorClassName={bar} />
                </div>
              ))}
            </div>
          </Card>

          <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
            <TabsList>
              <TabsTrigger value="ALL">All <span className="tabular text-muted-foreground">{analysis.findings.length}</span></TabsTrigger>
              <TabsTrigger value="MISSING">Missing <span className="tabular text-muted-foreground">{counts.MISSING}</span></TabsTrigger>
              <TabsTrigger value="PARTIAL">Partial <span className="tabular text-muted-foreground">{counts.PARTIAL}</span></TabsTrigger>
              <TabsTrigger value="SATISFIED">Covered <span className="tabular text-muted-foreground">{counts.SATISFIED}</span></TabsTrigger>
              {!!counts.NOT_APPLICABLE && <TabsTrigger value="NOT_APPLICABLE">Not applicable <span className="tabular text-muted-foreground">{counts.NOT_APPLICABLE}</span></TabsTrigger>}
            </TabsList>
          </Tabs>
          <motion.div key={filter} variants={stagger} initial="hidden" animate="show">
            <Accordion type="multiple" className="space-y-2">
              {/* Findings are set one line at a time, like type going onto a page. */}
              {findings.map((f, i) => (
                <motion.div key={`${analysis.id}-${filter}-${f.id}`} initial={{ opacity: 0, x: -28 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay: 0.2 + i * 0.05 }}>
                  <Finding f={f} analysis={analysis} onView={() => setViewing(f)} onChange={setAnalysis}
                    onAccepted={(r) => { setAnalysis(r.analysis); setComparison(r.comparison); resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }) }} />
                </motion.div>
              ))}
            </Accordion>
            {viewing && analysis && <EvidenceViewer analysis={analysis} finding={viewing} onClose={() => setViewing(null)} />}
            {!findings.length && <p className="py-6 text-center text-sm text-muted-foreground">Nothing in this category.</p>}
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}

// help: what the field expects, shown in the (i) tooltip. Fields without required add detail; the rest the draft cannot do without.
const FIELDS = [
  { key: "company", label: "Company legal name", placeholder: "Acme Payments Pvt Ltd", required: true,
    help: "The registered legal name of the business that decides why and how data is processed (the Data Fiduciary), exactly as on your incorporation certificate." },
  { key: "service", label: "What your service does", placeholder: "A mobile app for grocery delivery in Bengaluru", required: true,
    help: "One sentence on the goods or services the data is used for. Rule 3(b)(ii) requires the notice to describe them specifically." },
  { key: "website", label: "Website or app privacy link", placeholder: "https://acme.in/privacy", required: true,
    help: "The link where people read this notice, withdraw consent, use their rights and learn how to complain. Rule 3(c) requires the notice to give it." },
  { key: "address", label: "Registered address", placeholder: "12 MG Road, Bengaluru 560001",
    help: "Optional. Your registered office address, published next to the contact details so people can write to you." },
  { key: "dpo_name", label: "DPO / privacy contact name", placeholder: "Priya Rao, Data Protection Officer", required: true,
    help: "The name or designation of the person who answers privacy questions and grievances (Section 8(9), Rule 9). A role such as Grievance Officer is fine if you prefer not to name a person." },
  { key: "contact", label: "Privacy contact email and phone", placeholder: "dpo@acme.in, +91 80 1234 5678", required: true,
    help: "A working email address and, ideally, a phone number for privacy questions and grievances. Use a monitored inbox, not a no-reply address." },
  { key: "grievance_days", label: "Grievance response time (days)", placeholder: "30", required: true,
    help: "The number of days within which you promise to answer a grievance. Rule 14(3) allows at most 90 days; a shorter period builds trust." },
  { key: "children", label: "Users under 18", placeholder: "No, users must be 18 or over; age checked at sign-up", required: true,
    help: "Can anyone under 18 use the service? If yes, say how you get and verify a parent's or guardian's consent (for example DigiLocker). If no, say how you stop minors signing up." },
  { key: "data", label: "Personal data you collect", placeholder: "Name, mobile number, email, PAN, delivery address, order history", required: true, long: true,
    help: "Every item of personal data people give you, one by one, separated by commas. Include sensitive items such as Aadhaar, health, financial or location data. Anything left out is not covered by consent." },
  { key: "data_auto", label: "Data collected automatically", placeholder: "Device ID, IP address, approximate location, cookies", long: true,
    help: "Optional but recommended. Data your app or website gathers without the person typing it: device identifiers, IP address, location, cookies, usage analytics." },
  { key: "purpose", label: "Why you collect it", placeholder: "Deliver orders, take payment, verify identity (KYC), prevent fraud, answer support requests", required: true, long: true,
    help: "Each specific purpose you use the data for. Avoid vague phrases such as 'business purposes' or 'improve services'; consent is valid only for a stated purpose (Section 6(1))." },
  { key: "consent_method", label: "How people give consent", placeholder: "Ticking an unticked box on the sign-up screen after reading the notice", required: true, long: true,
    help: "Describe the screen and the action. Consent must be a clear affirmative action, such as an unticked box or an I agree button. Pre-ticked boxes or 'by using this app you agree' do not count." },
  { key: "withdraw_method", label: "How people withdraw consent", placeholder: "Settings > Privacy > Withdraw consent, or email privacy@acme.in", required: true,
    help: "The exact place or address where someone withdraws consent. It must be as easy as giving consent (Section 6(4))." },
  { key: "languages", label: "Languages the notice is available in", placeholder: "English, Hindi, Tamil",
    help: "Optional. The languages you already offer the notice in. People can ask for English or any language in the Eighth Schedule to the Constitution (Section 6(3))." },
  { key: "sharing", label: "Who you share it with", placeholder: "Razorpay (payments), AWS Mumbai (hosting), MSG91 (SMS)", required: true, long: true,
    help: "Each service provider (Data Processor) that receives personal data and what it does, e.g. Razorpay (payments). Write 'not shared' if no one outside your company gets it." },
  { key: "storage_location", label: "Where the data is stored", placeholder: "India (AWS Mumbai region)",
    help: "Optional. The country or cloud region where personal data is stored. Say so if any of it leaves India (Section 16)." },
  { key: "security", label: "Security safeguards", placeholder: "AES-256 encryption at rest, TLS in transit, role-based access control, daily backups", required: true, long: true,
    help: "The actual technical and organisational measures you use: encryption, access control, multi-factor login, logging, backups, audits. 'We keep data safe' is not enough (Section 8(5), Rule 6)." },
  { key: "retention", label: "How long you keep it", placeholder: "Invoices 8 years (GST law); KYC 5 years after closure (PMLA); support chats 12 months", required: true, long: true,
    help: "A period for each kind of data, and the law that requires it where one does. Avoid 'forever' or 'as long as necessary'; data must be erased once the purpose ends (Section 8(7))." },
  { key: "rights_channel", label: "Where people send rights requests", placeholder: "Email privacy@acme.in or use the form at acme.in/privacy",
    help: "Optional; defaults to the privacy contact email. The email, web form or app setting through which people ask for a summary of their data, correction, erasure or to nominate someone (Rule 14)." },
] as const
type FormKey = (typeof FIELDS)[number]["key"] | "sector"
const EMPTY_FORM = { ...Object.fromEntries(FIELDS.map((f) => [f.key, ""])), sector: "Fintech" } as Record<FormKey, string>

/** A small (i) next to a label; hover or keyboard focus shows what the field expects. */
function InfoTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" aria-label="What to enter here" className="ml-1 inline-grid size-4 place-items-center rounded-full align-middle text-muted-foreground hover:text-foreground focus-visible:text-foreground">
          <Info className="size-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="leading-relaxed">{text}</TooltipContent>
    </Tooltip>
  )
}

const SECTORS = ["Fintech", "Healthtech", "Edtech", "E-commerce", "SaaS", "D2C", "Other"]

function Recommendations({ items }: { items: NonNullable<PolicyGenerateResponse["recommendations"]> }) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recommended</div>
      <motion.ul className="space-y-2" variants={stagger} initial="hidden" animate="show">
        {items.map((r) => (
          <motion.li key={r.title} variants={rise} className="flex gap-3 rounded-lg border p-3 text-base">
            <Lightbulb className="mt-0.5 size-4 shrink-0 text-primary" />
            <div className="min-w-0">
              <div className="font-medium">{r.title} <span className="ml-1 rounded bg-secondary px-1.5 py-0.5 font-mono text-sm text-muted-foreground">{r.basis}</span></div>
              <div className="break-words text-muted-foreground">{r.detail}</div>
            </div>
          </motion.li>
        ))}
      </motion.ul>
    </div>
  )
}

/** The assistant's turn when answers are too thin: specific questions, why each matters, an example, and advice. */
function FollowUpCard({ data, labels, onAnswer, onProceed }: {
  data: PolicyGenerateResponse; labels: Record<string, string>; onAnswer: (field: string) => void; onProceed: () => void
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 16, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}>
      <Card className="overflow-hidden border-primary/30">
        <div className="flex gap-3 border-b bg-accent/50 p-5">
          <div className="grid size-10 shrink-0 place-items-center rounded-full bg-primary text-xl font-bold text-primary-foreground">?</div>
          <div className="min-w-0">
            <div className="font-semibold">A few questions before I draft this</div>
            <p className="text-sm text-muted-foreground">{data.message}</p>
          </div>
        </div>
        <motion.ol className="divide-y" variants={stagger} initial="hidden" animate="show">
          {(data.questions ?? []).map((q, i) => (
            <motion.li key={q.field + i} variants={rise} className="flex gap-3 p-5">
              <span className="mt-0.5 font-mono text-xs text-muted-foreground">{String(i + 1).padStart(2, "0")}</span>
              <div className="min-w-0 flex-1 space-y-1">
                <div className="font-medium">{q.question}</div>
                <div className="text-xs text-muted-foreground">{labels[q.field] ?? q.field} · {q.why}</div>
                {q.example && <div className="text-xs text-muted-foreground">For example: <span className="italic">{q.example}</span></div>}
              </div>
              <Button variant="outline" size="sm" onClick={() => onAnswer(q.field)}>Answer</Button>
            </motion.li>
          ))}
        </motion.ol>
        {!!data.recommendations?.length && <div className="border-t p-5"><Recommendations items={data.recommendations} /></div>}
        <div className="flex flex-wrap items-center gap-3 border-t px-5 py-3 text-xs text-muted-foreground">
          <span className="flex-1">Prefer to fill these in later? The draft will mark each gap as a [placeholder] rather than guess.</span>
          <Button variant="ghost" size="sm" onClick={onProceed}>Draft anyway with placeholders</Button>
        </div>
      </Card>
    </motion.div>
  )
}

function CreatePanel() {
  const [form, setForm] = usePersistentState<Record<FormKey, string>>("biz.create.form", EMPTY_FORM)
  const [missing, setMissing] = usePersistentState<string[]>("biz.create.missing", [])
  const [busy, setBusy] = usePersistentState("biz.create.busy", false, { session: false })
  const [error, setError] = usePersistentState<string | null>("biz.create.error", null, { session: false })
  const [result, setResult] = usePersistentState<PolicyGenerateResponse | null>("biz.create.result", null)
  const [followUp, setFollowUp] = usePersistentState<PolicyGenerateResponse | null>("biz.create.followUp", null)
  const [, setTab] = usePersistentState<"audit" | "create">("biz.tab", "audit")
  const [, setAuditFile] = usePersistentState<string | null>("biz.audit.fileName", null)
  const [, setAutorun] = usePersistentState<string | null>("biz.audit.autorun", null)
  const auditDraft = () => {
    if (!result?.policy_id) return
    setAuditFile(`Generated policy — ${result.company ?? "draft"}`); setAutorun(result.policy_id); setTab("audit")
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  // The server reads the answers: thin ones come back as questions (with why they matter) and recommendations.
  const generate = async (proceed = false) => {
    setError(null)
    setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/api/policies/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, proceed }) })
      if (!r.ok) throw new Error(await errorDetail(r))
      const j: PolicyGenerateResponse = await r.json()
      if (j.needs_more) { setFollowUp(j); setMissing(j.missing_fields ?? []); setResult(null) }
      else { setResult(j); setFollowUp(null); setMissing([]) }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed")
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Tell us about your data practices</CardTitle>
          <CardDescription>Be specific: your answers go into the policy as written. Hover the (i) beside a field to see what it expects. The draft is checked against the same rule book the audit uses.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="f-sector">Sector<InfoTip text="Your industry. It decides sector advice, such as the Third Schedule erasure periods for large e-commerce, gaming and social media platforms." /></Label>
              <Select value={form.sector} onValueChange={(v) => setForm({ ...form, sector: v })}>
                <SelectTrigger id="f-sector"><SelectValue /></SelectTrigger>
                <SelectContent>{SECTORS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            {FIELDS.map((f) => {
              const props = {
                id: `f-${f.key}`, value: form[f.key] ?? "", placeholder: f.placeholder, "aria-invalid": missing.includes(f.key),
                onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { setForm({ ...form, [f.key]: e.target.value }); setMissing((m) => m.filter((x) => x !== f.key)) },
              }
              return (
                <div key={f.key} className={"long" in f ? "space-y-2 sm:col-span-2" : "space-y-2"}>
                  <Label htmlFor={`f-${f.key}`}>{f.label}{"required" in f && <span className="text-destructive"> *</span>}<InfoTip text={f.help} /></Label>
                  {"long" in f ? <Textarea rows={2} {...props} /> : <Input {...props} />}
                </div>
              )
            })}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => generate()} disabled={busy}>{busy ? "Reading your answers…" : followUp ? "Check my answers again" : "Draft the policy"} <ArrowRight /></Button>
            <Button variant="ghost" onClick={() => { setForm(EMPTY_FORM); setMissing([]); setResult(null); setFollowUp(null) }} disabled={busy}>Clear</Button>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>{error && <ErrorNote>{error}</ErrorNote>}</AnimatePresence>
      <AnimatePresence>
        {followUp && !busy && (
          <FollowUpCard key="follow" data={followUp} labels={Object.fromEntries(FIELDS.map((f) => [f.key, f.label]))}
            onAnswer={(field) => { const el = document.getElementById(`f-${field}`); el?.scrollIntoView({ behavior: "smooth", block: "center" }); el?.focus() }}
            onProceed={() => generate(true)} />
        )}
      </AnimatePresence>
      {busy && <Card className="p-5"><Thinking label="Drafting your policy" /></Card>}
      <AnimatePresence>
        {result?.draft && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b p-5">
                <div className="space-y-0.5">
                  <div className="text-base font-semibold">Privacy policy draft — {result.company}</div>
                  <div className="text-sm text-muted-foreground">
                    {result.rulebook ? `Passes ${result.rulebook.filter((r) => r.met).length} of ${result.rulebook.length} audit rules · ` : ""}{result.dpdp_sections_cited?.length ?? 0} DPDP sections cited{result.llm_refined ? " · refined by AI" : ""}{result.reference_benchmarks_used ? " · sector benchmarks consulted" : ""}
                  </div>
                </div>
                <div className="flex gap-2">
                  {result.policy_id && <Button variant="outline" size="sm" onClick={auditDraft}><ClipboardCheck /> Audit this draft</Button>}
                  <CopyButton text={result.draft} />
                  <DownloadMenu variant="default" markdown={result.draft} title={`Privacy Policy — ${result.company || "Draft"}`}
                    subtitle={`${result.sector ?? ""} · Drafted with DPDP Compass · Review with counsel before publishing`} />
                </div>
              </div>
              {!!result.placeholders?.length && (
                <div className="border-b bg-warning/10 px-5 py-3 text-sm text-warning">
                  {result.placeholders.length} item{result.placeholders.length > 1 ? "s" : ""} marked with a red circle still need your facts before you publish; the audit will flag them until you do.
                </div>
              )}
              <div className="p-5 sm:p-7"><Markdown text={result.draft} markPlaceholders /></div>
              {!!result.recommendations?.length && <div className="border-t p-5"><Recommendations items={result.recommendations} /></div>}
              <div className="border-t px-5 py-3 text-xs text-muted-foreground">Have counsel review before publishing — then run it through Audit.</div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const OBLIGATIONS = ["Notice of data and purpose", "Free, specific consent", "Plain language", "Withdrawal of consent", "Processors under contract",
  "Accuracy of data", "Security safeguards", "Breach intimation", "Erasure and retention", "Published contact", "Grievance redressal",
  "Children's data", "Access and correction", "Right to nominate"]

export function BusinessChat() {
  const [tab, setTab] = usePersistentState<"audit" | "create">("biz.tab", "audit")
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="For businesses" title="Check or write a privacy policy" subtitle="Check a privacy policy against the law, or answer some questions to get a new one." />
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-4">
          <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
            <TabsList>
              <TabsTrigger value="audit"><Scale /> Check a policy</TabsTrigger>
              <TabsTrigger value="create"><FilePenLine /> Write a new policy</TabsTrigger>
            </TabsList>
            {/* forceMount keeps both panels mounted, so switching tabs never interrupts work */}
            <TabsContent value="audit" forceMount className="data-[state=inactive]:hidden"><AuditPanel /></TabsContent>
            <TabsContent value="create" forceMount className="data-[state=inactive]:hidden"><CreatePanel /></TabsContent>
          </Tabs>
          <p className="flex items-center gap-2 text-xs text-muted-foreground"><Building2 className="size-3.5" /> Audits are saved to your dashboard.</p>
        </div>
        <SideRail>
          <RailCard title="What we check" icon={ListChecks}>
            <ul className="grid gap-1.5">
              {OBLIGATIONS.map((o, i) => (
                <li key={o} className="flex items-center gap-2.5"><span className="w-5 font-mono text-sm text-muted-foreground">{String(i + 1).padStart(2, "0")}</span><span className="text-foreground/85">{o}</span></li>
              ))}
            </ul>
          </RailCard>
          <RailCard title="How the score works" icon={Scale}>
            <div className="space-y-2">
              {[["Covered", "counts fully", "bg-success"], ["Partial", "counts half", "bg-warning"], ["Missing", "counts zero", "bg-destructive"]].map(([l, d, c]) => (
                <div key={l} className="flex items-center gap-2.5"><span className={`size-2.5 rounded-full ${c}`} /><span className="font-medium text-foreground">{l}</span><span>{d}</span></div>
              ))}
              <p className="pt-1 text-xs">Duties that don't apply to you are left out of the score.</p>
            </div>
          </RailCard>
          <div className="rounded-lg border p-5">
            <div className="text-lg font-semibold leading-tight">Up to ₹250 crore</div>
            <p className="mt-1.5 text-sm text-muted-foreground">Penalty for failing to protect personal data. All obligations apply from May 2027.</p>
          </div>
        </SideRail>
      </div>
    </div>
  )
}
