import { useEffect, useRef, useState, type ComponentType, type ReactNode } from "react"
import { animate, motion, useInView, type HTMLMotionProps } from "motion/react"
import { AlertCircle, Check, Copy, Download, FileText, FileType2, FileUp, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { API_BASE } from "@/services/api"
import { cn } from "@/utils/cn"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

/* ── Motion ───────────────────────────────────────────────────────────────── */
export const ease = [0.22, 1, 0.36, 1] as const

/** Fades + lifts content in once it scrolls into view. */
export function FadeIn({ delay = 0, y = 10, className, ...props }: HTMLMotionProps<"div"> & { delay?: number; y?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.45, ease, delay }}
      className={className}
      {...props}
    />
  )
}

/** Parent/child pair for staggered list entrances. */
export const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.045 } } }
export const rise = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0, transition: { duration: 0.35, ease } } }

/* ── Markdown ─────────────────────────────────────────────────────────────
   Renders the subset the backend emits (headings, lists, tables, bold/italic, code, rules) as React
   elements — no dangerouslySetInnerHTML, so model output can't inject HTML. */
// A fill-in-the-blank like [DPO email] (not a [link](url)); marked when the caller asks, so drafts show what is left to fill.
const PLACEHOLDER = /(\[[^\]\n]{3,120}\](?!\())/ // not /g: .test() on a global regex keeps state between calls

function inline(text: string, mark = false): ReactNode[] {
  if (mark && PLACEHOLDER.test(text)) {
    return text.split(PLACEHOLDER).flatMap<ReactNode>((part, i) => i % 2
      ? [<mark key={`p${i}`} data-placeholder="" title="Fill this in before publishing" className="mx-0.5 inline-flex items-baseline gap-1 rounded-md bg-destructive/10 px-1 font-medium text-destructive">
          <span aria-hidden className="inline-block size-2.5 translate-y-px rounded-full border-2 border-destructive" />{part}</mark>]
      : inline(part))
  }
  return text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|(?<!\w)_[^_\s][^_]*_(?!\w)|`[^`]+`|【[^】]+】)/g).map((part, i) => {
    // Model-style source markers 【DPDP_Act_2023.pdf Section 8】 → a quiet citation chip.
    if (part.startsWith("【") && part.endsWith("】")) return <span key={i} className="mx-0.5 inline-flex items-center rounded-md bg-accent px-1.5 py-px align-baseline text-sm font-medium text-accent-foreground">{part.slice(1, -1).replace(/_/g, " ").replace(/\.pdf/i, "")}</span>
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i} className="rounded bg-secondary px-1 py-0.5 font-mono text-[0.85em]">{part.slice(1, -1)}</code>
    if (part.length > 2 && (part[0] === "*" || part[0] === "_") && part.endsWith(part[0])) return <em key={i}>{part.slice(1, -1)}</em>
    return part
  })
}

export function Markdown({ text, className, markPlaceholders = false }: { text: string; className?: string; markPlaceholders?: boolean }) {
  const blocks: ReactNode[] = []
  const lines = text.split("\n")
  let list: { ordered: boolean; items: string[] } | null = null
  const flush = () => {
    if (!list) return
    const Tag = list.ordered ? "ol" : "ul"
    blocks.push(
      <Tag key={blocks.length} className={cn("space-y-1.5 pl-5 marker:text-muted-foreground", list.ordered ? "list-decimal" : "list-disc")}>
        {list.items.map((t, i) => <li key={i} className="pl-1">{inline(t, markPlaceholders)}</li>)}
      </Tag>,
    )
    list = null
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd()
    // Tables: header row + |---| separator
    if (line.trim().startsWith("|") && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1] ?? "")) {
      flush()
      const rows: string[][] = []
      for (; i < lines.length && lines[i].trim().startsWith("|"); i++) {
        if (!/^\s*\|?\s*:?-{3,}/.test(lines[i])) rows.push(lines[i].trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()))
      }
      i--
      blocks.push(
        <div key={blocks.length} className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-secondary/60"><tr>{rows[0].map((c, j) => <th key={j} className="px-3 py-2 font-semibold">{inline(c, markPlaceholders)}</th>)}</tr></thead>
            <tbody>{rows.slice(1).map((r, ri) => <tr key={ri} className="border-t">{r.map((c, j) => <td key={j} className="px-3 py-2 align-top">{inline(c, markPlaceholders)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      )
      continue
    }
    const h = line.match(/^(#{1,4})\s+(.*)$/)
    const ul = line.match(/^\s*[-*•]\s+(.*)$/)
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/)
    if (ul || ol) {
      const ordered = !!ol
      if (!list || list.ordered !== ordered) { flush(); list = { ordered, items: [] } }
      list.items.push((ul || ol)![1])
      continue
    }
    flush()
    if (!line.trim()) continue
    if (h) {
      const level = h[1].length
      blocks.push(
        <div key={blocks.length} role="heading" aria-level={level}
          className={cn("font-semibold tracking-tight text-foreground", level === 1 ? "pt-1 text-lg" : level === 2 ? "pt-2 text-base" : "pt-1 text-sm")}>
          {inline(h[2], markPlaceholders)}
        </div>,
      )
    } else if (/^\*\*\d+\.\s.+\*\*$/.test(line.trim())) {
      // Model answers use "**1. Short Answer**" as section titles — render them as headings.
      blocks.push(<div key={blocks.length} role="heading" aria-level={3} className="pt-2 text-base font-semibold tracking-tight text-foreground">{line.trim().slice(2, -2)}</div>)
    } else if (/^-{3,}$/.test(line.trim())) {
      blocks.push(<hr key={blocks.length} className="border-border" />)
    } else {
      blocks.push(<p key={blocks.length}>{inline(line, markPlaceholders)}</p>)
    }
  }
  flush()
  return <div className={cn("space-y-2.5 break-words text-base leading-relaxed text-foreground/85", className)}>{blocks}</div>
}

/* ── Scores ───────────────────────────────────────────────────────────── */
export const scoreTone = (s: number) => (s >= 75 ? "hsl(var(--success))" : s >= 50 ? "hsl(var(--warning))" : "hsl(var(--destructive))")
export const scoreLabel = (s: number) => (s >= 75 ? "Strong" : s >= 50 ? "Needs work" : "High risk")

/** Counts up from 0 when it scrolls into view. */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const [n, setN] = useState(0)
  useEffect(() => {
    if (!inView) return
    const c = animate(0, value, { duration: 0.9, ease, onUpdate: (v) => setN(Math.round(v)) })
    return () => c.stop()
  }, [inView, value])
  return <span ref={ref} className={cn("tabular", className)}>{n}</span>
}

/** The score as a large plain number in a coloured box, with "out of 100" spelled out. */
export function ScoreRing({ score, size = 76, label }: { score: number; size?: number; label?: string }) {
  const color = scoreTone(score)
  return (
    <div className="grid shrink-0 place-items-center rounded-lg border-[3px] text-center" style={{ width: size, height: size, color, borderColor: color }}
      role="img" aria-label={`${label ?? "Score"} ${score} out of 100`}>
      <div>
        <div className="font-bold leading-none" style={{ fontSize: size * 0.4 }}>{score}</div>
        <div className="mt-1 text-xs font-bold">out of 100</div>
      </div>
    </div>
  )
}

/* ── Status ───────────────────────────────────────────────────────────── */
const STATUS: Record<string, { label: string; variant: "success" | "warning" | "destructive" | "secondary" }> = {
  SATISFIED: { label: "Covered", variant: "success" },
  PARTIAL: { label: "Partial", variant: "warning" },
  MISSING: { label: "Missing", variant: "destructive" },
  NOT_APPLICABLE: { label: "N/A", variant: "secondary" },
}
export function StatusPill({ status }: { status: string }) {
  const s = STATUS[status] ?? { label: status, variant: "secondary" as const }
  return <Badge variant={s.variant} className="shrink-0">{s.label}</Badge>
}

/* ── Feedback ─────────────────────────────────────────────────────────── */
export function Spinner({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin text-primary" />
      {label}
    </div>
  )
}

/** Work in progress: a slow spinner and words saying what is happening. */
export function Thinking({ label = "Working" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-base font-bold text-foreground">
      <Loader2 className="size-5 animate-spin text-primary [animation-duration:1.6s]" />
      {label}… please wait
    </div>
  )
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <motion.div role="alert" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-2.5 rounded-lg border-2 border-destructive bg-destructive/5 px-4 py-3 text-base text-destructive">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <div>{children}</div>
    </motion.div>
  )
}

/** Sticky side column used on wide screens next to the main work area. */
export function SideRail({ children }: { children: ReactNode }) {
  return (
    <motion.aside initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.15, ease }}
      className="hidden space-y-4 xl:sticky xl:top-8 xl:block xl:self-start">
      {children}
    </motion.aside>
  )
}

export function RailCard({ title, icon: Icon, children }: { title: string; icon?: ComponentType<{ className?: string }>; children: ReactNode }) {
  return (
    <div className="rounded-lg border p-5">
      <div className="flex items-center gap-2 text-lg font-bold">{Icon && <Icon className="size-5 text-primary" />}{title}</div>
      <div className="mt-3 text-base text-muted-foreground">{children}</div>
    </div>
  )
}

export function PageHeader({ title, subtitle, children }: { eyebrow?: string; title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 space-y-2">
        <h1 className="text-3xl font-bold sm:text-4xl">{title}</h1>
        {subtitle && <p className="max-w-2xl text-lg text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

/* ── Files ────────────────────────────────────────────────────────────── */
export function Dropzone({ onFile, disabled, fileName, hint = "PDF, DOCX, TXT or MD · up to 10 MB" }: { onFile: (f: File) => void; disabled?: boolean; fileName?: string | null; hint?: string }) {
  const [over, setOver] = useState(false)
  return (
    <motion.label
      whileHover={disabled ? undefined : { scale: 1.005 }}
      onDragOver={(e) => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files?.[0]; if (f && !disabled) onFile(f) }}
      className={cn(
        "group flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors duration-200 focus-within:ring-2 focus-within:ring-ring",
        over ? "border-primary bg-accent" : "border-border bg-secondary/40 hover:border-primary/50 hover:bg-accent/60",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <input type="file" className="sr-only" accept=".pdf,.docx,.txt,.md,.html" disabled={disabled}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = "" }} />
      <span className={cn("grid size-10 place-items-center rounded-full bg-card shadow-soft transition-transform duration-200 group-hover:-translate-y-0.5", over && "-translate-y-0.5")}>
        {fileName ? <FileText className="size-5 text-primary" /> : <FileUp className="size-5 text-primary" />}
      </span>
      <div className="text-sm font-medium text-foreground">{fileName ? <span className="break-all">{fileName}</span> : "Drop a policy here, or click to browse"}</div>
      <div className="text-xs text-muted-foreground">{fileName ? "Click to choose a different file" : hint}</div>
    </motion.label>
  )
}

export async function errorDetail(r: Response): Promise<string> {
  const j = await r.json().catch(() => null)
  return (j && typeof j.detail === "string" && j.detail) || `Request failed (${r.status})`
}

const FORMATS = [
  { fmt: "pdf", label: "PDF document", hint: "Best for sharing & printing", icon: FileType2 },
  { fmt: "docx", label: "Word document", hint: "Editable in Word / Google Docs", icon: FileText },
  { fmt: "md", label: "Markdown", hint: "Plain text, for developers", icon: FileText },
] as const

/** One download button → Word / PDF / Markdown, all rendered server-side from the same Markdown. */
export function DownloadMenu({ markdown, title, subtitle, size = "default", variant = "outline" }: {
  markdown: string; title: string; subtitle?: string; size?: "default" | "sm"; variant?: "outline" | "default" | "ghost"
}) {
  const [busy, setBusy] = useState<string | null>(null)
  const save = async (fmt: string) => {
    setBusy(fmt)
    try {
      const r = await fetch(`${API_BASE}/api/export`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ markdown, title, subtitle: subtitle ?? "", format: fmt }) })
      if (!r.ok) throw new Error(await errorDetail(r))
      const name = /filename="([^"]+)"/.exec(r.headers.get("content-disposition") ?? "")?.[1] ?? `document.${fmt}`
      const url = URL.createObjectURL(await r.blob())
      Object.assign(document.createElement("a"), { href: url, download: name }).click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast.success(`Downloaded ${name}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Download failed")
    } finally { setBusy(null) }
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={variant} size={size} disabled={!!busy}>
          {busy ? <Loader2 className="animate-spin" /> : <Download />} {busy ? "Preparing…" : "Download"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[19rem]">
        <DropdownMenuLabel>Download as</DropdownMenuLabel>
        {FORMATS.map(({ fmt, label, hint, icon: Icon }) => (
          <DropdownMenuItem key={fmt} onSelect={() => save(fmt)}>
            <Icon className="text-muted-foreground" />
            <div className="min-w-0">
              <div className="font-medium">{label}</div>
              <div className="text-xs text-muted-foreground">{hint}</div>
            </div>
            <span className="ml-auto text-sm font-semibold uppercase text-muted-foreground">.{fmt}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false)
  return (
    <Button variant="ghost" size="sm" onClick={() => { navigator.clipboard.writeText(text); setDone(true); toast.success("Copied to clipboard"); setTimeout(() => setDone(false), 1500) }}>
      {done ? <Check className="text-success" /> : <Copy />} {done ? "Copied" : label}
    </Button>
  )
}
