import { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { ArrowUp, BookOpen, Gavel, ShieldCheck, FileSearch, Mail, MessageSquareText, RotateCcw, ScrollText, ShieldAlert } from "lucide-react"
import { Seal } from "@/components/brand"
import { ClaimCheckPanel } from "@/components/ClaimCheckPanel"
import { RequestBuilder } from "@/components/RequestBuilder"
import { API_BASE } from "@/services/api"
import { usePersistentState } from "@/hooks/usePersistentState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Separator } from "@/components/ui/misc"
import {
  CopyButton, DownloadMenu, Dropzone, ErrorNote, Markdown, PageHeader, RailCard, SideRail, ScoreRing, StatusPill, Thinking,
  errorDetail, rise, scoreLabel, stagger,
} from "@/components/ui/kit"
import { cn } from "@/utils/cn"
import type { CitizenAnalysis, PdfAnalysisReport } from "@/types"

const SUGGESTIONS = [
  "What does Zomato do with my data?",
  "Can a company sell my phone number?",
  "How long will Swiggy keep my data?",
  "How do I get an app to delete my data?",
]

function useReferenceCompanies() {
  const [names, setNames] = useState<string[]>([])
  useEffect(() => {
    fetch(`${API_BASE}/api/citizen/reference-companies`).then((r) => (r.ok ? r.json() : [])).then(setNames).catch(() => {})
  }, [])
  return names
}

/** A chat answer as a standalone document: question, answer, what the policy says, sources. */
function answerMarkdown(question: string, d: CitizenAnalysis | undefined, answer: string): string {
  const L = [`## Question`, "", question, "", `## Answer`, "", answer, ""]
  if (d?.policy_analyzed) {
    if (d.trust_score != null) L.push(`## ${d.policy_name}`, "", `**Trust score:** ${d.trust_score}/100 (${scoreLabel(d.trust_score)})`, "")
    L.push("### What the policy says", "")
    L.push(`- **Collects:** ${d.data_collected.join("; ")}`, `- **Uses it for:** ${d.purpose.join("; ")}`, `- **Shares with:** ${d.sharing}`, `- **Keeps it:** ${d.retention}`, "")
    if (d.shortfalls.length) L.push("### Gaps found", "", ...d.shortfalls.map((s) => `- **${s.title}:** ${s.description}`), "")
  }
  if (d?.citations.length) L.push("## Sources", "", ...d.citations.map((c) => `- **${c.source_document} ${c.section ?? ""}** — ${c.text.replace(/\s+/g, " ").slice(0, 220)}`), "")
  L.push("---", "", "*Educational guidance, not legal advice.*")
  return L.join("\n")
}

function reportMarkdown(name: string, r: PdfAnalysisReport): string {
  const s = r.summary_counts
  const L = [
    `**Trust score:** ${r.citizen_trust_score}/100 (${scoreLabel(r.citizen_trust_score)})  `,
    `**DPDP alignment:** ${r.dpdp_alignment_score}/100`, "",
    "## Summary", "", "| Status | Rights |", "|---|---|",
    `| Covered | ${s.satisfied} |`, `| Partial | ${s.partial} |`, `| Missing | ${s.missing} |`, "",
  ]
  if (r.actionable_citizen_guidance.length) L.push("## What you should know", "", ...r.actionable_citizen_guidance.map((g) => `- **${g.dpdp_basis}:** ${g.recommendation}`), "")
  L.push("## Every right checked", "")
  for (const c of r.all_statutory_comparisons) {
    L.push(`### ${c.dpdp_title} — ${c.status === "SATISFIED" ? "Covered" : c.status === "PARTIAL" ? "Partial" : "Missing"}`, "", `*${c.dpdp_section}*`, "", c.plain_language_explanation, "",
      `> ${c.matched_policy_excerpt.replace(/\s+/g, " ").slice(0, 300)}`, "")
  }
  L.push("---", "", "*Educational guidance, not legal advice.*")
  return L.join("\n")
}

function AnswerDetails({ d }: { d: CitizenAnalysis }) {
  const practices: [string, string | string[]][] = [
    ["Collects", d.data_collected], ["Uses it for", d.purpose], ["Shares with", d.sharing], ["Keeps it", d.retention],
  ]
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="space-y-3">
      {d.policy_analyzed && d.trust_score != null && (
        <div className="flex items-center gap-4 rounded-xl border bg-secondary/40 p-3.5">
          <ScoreRing score={d.trust_score} size={52} label="Trust score" />
          <div className="min-w-0 text-sm">
            <div className="break-words font-medium">{d.policy_name}</div>
            <div className="text-muted-foreground">{scoreLabel(d.trust_score)} · based on how fully the policy covers your DPDP rights</div>
          </div>
        </div>
      )}
      {d.claim_check && <ClaimCheckPanel check={d.claim_check} />}
      <Accordion type="multiple" className="space-y-2">
        {d.policy_analyzed && (
          <AccordionItem value="practices" className="shadow-none">
            <AccordionTrigger className="py-3"><ScrollText className="size-4 text-primary" /><span className="flex-1">What the policy says about your data</span></AccordionTrigger>
            <AccordionContent>
              <dl className="grid gap-3 sm:grid-cols-2">
                {practices.map(([k, v]) => (
                  <div key={k} className="space-y-1">
                    <dt className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{k}</dt>
                    <dd className="break-words text-base leading-relaxed">{Array.isArray(v) ? <ul className="list-disc space-y-1 pl-4">{v.map((x, i) => <li key={i}>{x}</li>)}</ul> : v}</dd>
                  </div>
                ))}
              </dl>
            </AccordionContent>
          </AccordionItem>
        )}
        {d.shortfalls.length > 0 && (
          <AccordionItem value="gaps" className="shadow-none">
            <AccordionTrigger className="py-3"><ShieldAlert className="size-4 text-warning" /><span className="flex-1">Gaps found <span className="text-muted-foreground">({d.shortfalls.length})</span></span></AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-2.5">
                {d.shortfalls.map((s, i) => <li key={i} className="text-base"><div className="font-medium">{s.title}</div><div className="break-words text-muted-foreground">{s.description}</div></li>)}
              </ul>
            </AccordionContent>
          </AccordionItem>
        )}
        {d.citations.length > 0 && (
          <AccordionItem value="sources" className="shadow-none">
            <AccordionTrigger className="py-3"><BookOpen className="size-4 text-primary" /><span className="flex-1">Sources <span className="text-muted-foreground">({d.citations.length})</span></span></AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-3">
                {d.citations.map((c, i) => (
                  <li key={i} className="break-words text-base">
                    <div className="font-medium">{c.source_document} {c.section}</div>
                    <div className="line-clamp-3 text-muted-foreground">{c.text}</div>
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>
        )}
      </Accordion>
    </motion.div>
  )
}

type Msg = { role: "user" | "ai"; text: string; data?: CitizenAnalysis; error?: boolean; streaming?: boolean }

function AskPanel() {
  const [msgs, setMsgs] = usePersistentState<Msg[]>("cit.ask.msgs", [])
  const [input, setInput] = usePersistentState("cit.ask.input", "")
  const [loading, setLoading] = usePersistentState("cit.ask.loading", false, { session: false })
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => { if (msgs.length) bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }) }, [msgs, loading])

  const ask = async (q: string) => {
    q = q.trim()
    if (!q || loading) return
    setMsgs((m) => [...m, { role: "user", text: q }])
    setInput(""); setLoading(true)
    // Update the last (AI) message in place as tokens arrive.
    const setLast = (patch: Partial<Msg>) => setMsgs((m) => [...m.slice(0, -1), { ...m[m.length - 1], ...patch }])
    let started = false, text = ""
    const ctl = new AbortController()
    const t = setTimeout(() => ctl.abort(), 120000)
    try {
      const r = await fetch(`${API_BASE}/api/citizen/analyze/stream`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: q }), signal: ctl.signal })
      if (!r.ok || !r.body) throw new Error(await errorDetail(r))
      const reader = r.body.getReader()
      const decoder = new TextDecoder()
      let buf = ""
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let sep
        while ((sep = buf.indexOf("\n\n")) !== -1) {  // one SSE event per blank-line-terminated block
          const line = buf.slice(0, sep).trim()
          buf = buf.slice(sep + 2)
          if (!line.startsWith("data: ")) continue
          const ev = JSON.parse(line.slice(6)) as { type: string; text?: string; data?: CitizenAnalysis }
          if (ev.type === "token" && ev.text) {
            text += ev.text
            if (!started) { started = true; setLoading(false); setMsgs((m) => [...m, { role: "ai", text, streaming: true }]) }
            else setLast({ text })
          } else if (ev.type === "done" && ev.data) {
            if (!started) { started = true; setMsgs((m) => [...m, { role: "ai", text: ev.data!.summary, data: ev.data }]) }
            else setLast({ text: ev.data.summary, data: ev.data, streaming: false })
          } else if (ev.type === "error") {
            throw new Error(ev.text)
          }
        }
      }
      if (!started) throw new Error("The server closed the connection without an answer.")
    } catch (e) {
      const msg = e instanceof Error && e.name !== "AbortError" ? e.message : "The request timed out."
      const note = `Sorry — I couldn't get an answer. ${msg}`
      if (started) setLast({ text: `${text}\n\n_${note}_`, streaming: false })  // keep what already arrived
      else setMsgs((m) => [...m, { role: "ai", text: note, error: true }])
    } finally { clearTimeout(t); setLoading(false) }
  }

  return (
    <div className="space-y-5">
      <AnimatePresence mode="popLayout">
        {msgs.length === 0 && (
          <motion.div key="empty" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }}>
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle className="text-2xl">What would you like to know?</CardTitle>
                <CardDescription>Ask about your rights under the DPDP Act. Name an app — like Zomato or Paytm — to check its privacy policy too.</CardDescription>
              </CardHeader>
              <CardContent>
                <motion.div className="grid gap-2 sm:grid-cols-2" variants={stagger} initial="hidden" animate="show">
                  {SUGGESTIONS.map((s) => (
                    <motion.button key={s} variants={rise} whileTap={{ scale: 0.98 }} onClick={() => ask(s)}
                      className="rounded-lg border-2 px-4 py-3 text-left text-base font-bold transition-colors hover:border-primary hover:bg-accent">
                      {s}
                    </motion.button>
                  ))}
                </motion.div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-5" aria-live="polite">
        {msgs.map((m, i) => m.role === "user" ? (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end gap-2.5">
            <div className="max-w-[85%] break-words rounded-lg bg-primary px-4 py-3 text-lg text-primary-foreground">{m.text}</div>
          </motion.div>
        ) : (
          <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
            <Seal className="size-10 shrink-0" />
            <Card className={cn("min-w-0 flex-1 space-y-4 p-4 sm:p-5", m.error && "border-destructive/30 bg-destructive/5")}>
              <div className="relative">
                <Markdown text={m.text} />
                {m.streaming && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-caret bg-primary align-middle" aria-hidden />}
              </div>
              {m.data && <AnswerDetails d={m.data} />}
              {!m.streaming && !m.error && (
                <>
                  <Separator />
                  <div className="flex flex-wrap items-center justify-end gap-1">
                    <CopyButton text={m.text} />
                    <DownloadMenu size="sm" variant="ghost" markdown={answerMarkdown(msgs[i - 1]?.text ?? "", m.data, m.text)}
                      title={`DPDP answer — ${(msgs[i - 1]?.text ?? "Your question").slice(0, 80)}`} />
                  </div>
                </>
              )}
            </Card>
          </motion.div>
        ))}
        <AnimatePresence>
          {loading && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex gap-2.5">
              <Seal className="size-10 shrink-0" />
              <Card className="px-4 py-3"><Thinking label="Looking this up in the law" /></Card>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottom} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(input) }}
        className="sticky bottom-4 flex items-center gap-2 rounded-lg border-2 bg-background p-2 pl-4 shadow-lift focus-within:border-primary">
        <label htmlFor="ask" className="sr-only">Your question</label>
        <input id="ask" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your question here" disabled={loading} autoComplete="off"
          className="min-w-0 flex-1 bg-transparent text-lg placeholder:text-muted-foreground/80 focus:outline-none" />
        {msgs.length > 0 && (
          <Button type="button" variant="ghost" size="icon" aria-label="New conversation" title="New conversation" disabled={loading} onClick={() => setMsgs([])}>
            <RotateCcw />
          </Button>
        )}
        <Button type="submit" aria-label="Ask" disabled={loading || !input.trim()}>Ask <ArrowUp /></Button>
      </form>
    </div>
  )
}

function CheckPanel() {
  const [name, setName] = usePersistentState<string | null>("cit.check.name", null)
  const [busy, setBusy] = usePersistentState("cit.check.busy", false, { session: false })
  const [error, setError] = usePersistentState<string | null>("cit.check.error", null, { session: false })
  const [report, setReport] = usePersistentState<PdfAnalysisReport | null>("cit.check.report", null)
  const companies = useReferenceCompanies()

  const scan = async (label: string, req: () => Promise<Response>) => {
    setName(label); setBusy(true); setError(null); setReport(null)
    try {
      const r = await req()
      if (!r.ok) throw new Error(await errorDetail(r))
      setReport(await r.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : "The check failed. Is the backend running?")
    } finally { setBusy(false) }
  }
  const scanFile = (f: File) => scan(f.name, () => { const fd = new FormData(); fd.append("file", f); return fetch(`${API_BASE}/api/citizen/analyze-pdf`, { method: "POST", body: fd }) })
  const scanCompany = (c: string) => scan(`${c} privacy policy`, () => fetch(`${API_BASE}/api/citizen/compare-similarity`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reference_company: c, filename: `${c}_Privacy_Policy.txt` }),
  }))

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Check an app's privacy policy</CardTitle>
          <CardDescription>See which of your DPDP rights the policy respects — in plain language.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <Dropzone onFile={scanFile} disabled={busy} fileName={name} />
          {companies.length > 0 && (
            <div className="space-y-2.5">
              <div className="text-sm text-muted-foreground">Or check a well-known app</div>
              <motion.div className="flex flex-wrap gap-2" variants={stagger} initial="hidden" animate="show">
                {companies.map((c) => (
                  <motion.button key={c} variants={rise} whileHover={{ y: -1 }} whileTap={{ scale: 0.97 }} disabled={busy} onClick={() => scanCompany(c)}
                    className="rounded-lg border-2 px-4 py-2 text-base font-bold transition-colors hover:border-primary hover:bg-accent disabled:opacity-50">
                    {c}
                  </motion.button>
                ))}
              </motion.div>
            </div>
          )}
        </CardContent>
      </Card>

      <AnimatePresence>{error && <ErrorNote>{error}</ErrorNote>}</AnimatePresence>
      {busy && <Card className="p-5"><Thinking label="Reading the policy and comparing it with the DPDP Act" /></Card>}

      {report && name && (
        <motion.div className="space-y-5" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="flex flex-wrap items-center gap-5 p-5">
            <ScoreRing score={report.citizen_trust_score} label="Trust score" />
            <div className="min-w-[200px] flex-1 space-y-1">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Trust score</div>
              <div className="break-words text-lg font-semibold">{name}</div>
              <div className="text-sm text-muted-foreground">
                {scoreLabel(report.citizen_trust_score)} · {report.summary_counts.satisfied} covered · {report.summary_counts.partial} partial · {report.summary_counts.missing} missing
              </div>
            </div>
            <DownloadMenu markdown={reportMarkdown(name, report)} title={`Privacy check — ${name}`} subtitle="Your DPDP rights, checked against the policy" />
          </Card>

          {report.actionable_citizen_guidance.length > 0 && (
            <Card>
              <CardHeader><CardTitle>What you should know</CardTitle></CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {report.actionable_citizen_guidance.map((g, i) => (
                    <li key={i} className="flex gap-3 text-base">
                      <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
                      <span className="break-words"><span className="font-medium">{g.dpdp_basis}: </span><span className="text-foreground/80">{g.recommendation}</span></span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <div className="space-y-2.5">
            <h2 className="text-sm font-semibold">Every right checked</h2>
            <motion.div variants={stagger} initial="hidden" animate="show">
              <Accordion type="multiple" className="space-y-2">
                {report.all_statutory_comparisons.map((c) => (
                  <motion.div key={c.obligation_id} variants={rise}>
                    <AccordionItem value={c.obligation_id}>
                      <AccordionTrigger>
                        <StatusPill status={c.status} />
                        <span className="min-w-0 flex-1 break-words leading-snug">{c.dpdp_title}</span>
                        <span className="hidden shrink-0 text-xs font-normal text-muted-foreground sm:block">{c.dpdp_section}</span>
                      </AccordionTrigger>
                      <AccordionContent className="space-y-3">
                        <p className="break-words leading-relaxed text-foreground/85">{c.plain_language_explanation}</p>
                        <div className="rounded-lg border bg-secondary/40 p-3">
                          <div className="text-xs font-medium text-muted-foreground">Closest text in the policy</div>
                          <p className="mt-1.5 line-clamp-4 break-words text-base">{c.matched_policy_excerpt}</p>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </motion.div>
                ))}
              </Accordion>
            </motion.div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

const RIGHTS = [
  ["§ 11", "See what data is held about you"],
  ["§ 12", "Correct, complete or erase it"],
  ["§ 13", "Have a grievance answered"],
  ["§ 14", "Nominate someone to act for you"],
  ["§ 6(4)", "Withdraw consent as easily as you gave it"],
]

export function CitizenChat() {
  const [tab, setTab] = usePersistentState<"ask" | "check" | "request">("cit.tab", "ask")
  const companies = useReferenceCompanies()
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="For citizens" title="Ask about your rights" subtitle="Ask a question about your personal data, or check what an app does with it." />
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="min-w-0">
          <TabsList>
            <TabsTrigger value="ask"><MessageSquareText /> Ask a question</TabsTrigger>
            <TabsTrigger value="check"><FileSearch /> Check a policy</TabsTrigger>
            <TabsTrigger value="request"><Mail /> Write a request</TabsTrigger>
          </TabsList>
          <TabsContent value="ask" forceMount className="data-[state=inactive]:hidden"><AskPanel /></TabsContent>
          <TabsContent value="check" forceMount className="data-[state=inactive]:hidden"><CheckPanel /></TabsContent>
          <TabsContent value="request" forceMount className="data-[state=inactive]:hidden"><RequestBuilder companies={companies} /></TabsContent>
        </Tabs>
        <SideRail>
          <RailCard title="Your rights at a glance" icon={Gavel}>
            <ul className="space-y-2.5">
              {RIGHTS.map(([s, t]) => (
                <li key={s} className="flex gap-3"><span className="w-12 shrink-0 font-mono text-xs text-primary">{s}</span><span className="text-foreground/85">{t}</span></li>
              ))}
            </ul>
          </RailCard>
          <RailCard title="How answers are made" icon={ShieldCheck}>
            <ol className="space-y-2">
              {["Your question searches the Act clause by clause", "Only retrieved passages are given to the model", "Guardrails check every citation before you see it"].map((t, i) => (
                <li key={t} className="flex gap-3"><span className="grid size-5 shrink-0 place-items-center bg-foreground font-mono text-background text-sm font-semibold">{i + 1}</span>{t}</li>
              ))}
            </ol>
          </RailCard>
          <div className="rounded-lg border p-5">
            <div className="text-lg font-semibold leading-tight">Fully in force by May 2027</div>
            <p className="mt-1.5 text-sm text-muted-foreground">Every duty of a Data Fiduciary becomes enforceable, with penalties up to ₹250 crore.</p>
          </div>
        </SideRail>
      </div>
    </div>
  )
}
