import { useEffect, useState } from "react"
import { Mail } from "lucide-react"
import { API_BASE } from "@/services/api"
import { usePersistentState } from "@/hooks/usePersistentState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input, Textarea } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CopyButton, DownloadMenu, ErrorNote, errorDetail } from "@/components/ui/kit"

type RequestType = { id: string; title: string }
type Draft = {
  title: string; subject: string; to: string; letter: string
  contact: { email: string; context: string; source: string } | null
  basis: { provision: string; label: string; status: string; in_force_from: string | null }[]
  notes: string[]
}

/** Rights-request letter: pick a company and a right, preview the letter, edit it, then copy or download. Nothing is sent. */
export function RequestBuilder({ companies }: { companies: string[] }) {
  const [types, setTypes] = useState<RequestType[]>([])
  const [form, setForm] = usePersistentState("cit.request.form", { type: "access", company: "", name: "", contact: "", account: "", details: "" })
  const [draft, setDraft] = usePersistentState<Draft | null>("cit.request.draft", null)
  const [letter, setLetter] = usePersistentState("cit.request.letter", "")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (v: string) => setForm({ ...form, [k]: v })

  useEffect(() => {
    fetch(`${API_BASE}/api/citizen/requests/types`).then((r) => (r.ok ? r.json() : [])).then(setTypes).catch(() => {})
  }, [])

  const preview = async () => {
    setBusy(true); setError(null)
    try {
      const r = await fetch(`${API_BASE}/api/citizen/requests/draft`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) })
      if (!r.ok) throw new Error(await errorDetail(r))
      const d: Draft = await r.json()
      setDraft(d); setLetter(d.letter)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not prepare the letter")
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Write a request to a company</CardTitle>
          <CardDescription>A letter citing the DPDP Act for you to send yourself. Nothing is sent from here.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="req-company">Company</Label>
            <Input id="req-company" list="req-companies" value={form.company} onChange={(e) => set("company")(e.target.value)} placeholder="e.g. Zomato" />
            <datalist id="req-companies">{companies.map((c) => <option key={c} value={c} />)}</datalist>
          </div>
          <div className="space-y-1.5">
            <Label>What do you want?</Label>
            <Select value={form.type} onValueChange={set("type")}>
              <SelectTrigger aria-label="Request type"><SelectValue /></SelectTrigger>
              <SelectContent>{types.map((t) => <SelectItem key={t.id} value={t.id}>{t.title}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="req-name">Your name</Label>
            <Input id="req-name" value={form.name} onChange={(e) => set("name")(e.target.value)} autoComplete="name" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="req-contact">Email or phone you use with them</Label>
            <Input id="req-contact" value={form.contact} onChange={(e) => set("contact")(e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="req-account">Account ID, order number or registered mobile (optional)</Label>
            <Input id="req-account" value={form.account} onChange={(e) => set("account")(e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="req-details">{form.type === "nominate" ? "Nominee's name and relationship" : "What this concerns (optional)"}</Label>
            <Textarea id="req-details" value={form.details} onChange={(e) => set("details")(e.target.value)} rows={3} />
          </div>
          <div className="sm:col-span-2">
            <Button onClick={preview} disabled={busy || !form.company.trim()}><Mail /> {busy ? "Preparing…" : "Preview letter"}</Button>
          </div>
        </CardContent>
      </Card>
      {error && <ErrorNote>{error}</ErrorNote>}
      {draft && (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start gap-3">
              <div className="min-w-0 flex-1">
                <CardTitle>{draft.title}</CardTitle>
                <CardDescription>
                  {draft.contact ? <>To {draft.contact.email}. Found in the {draft.contact.source}: “{draft.contact.context}”</>
                    : "No contact for this company in the policies we hold. Find the grievance officer or DPO in its privacy policy and replace the placeholder."}
                </CardDescription>
              </div>
              <CopyButton text={letter} />
              <DownloadMenu markdown={letter.split("\n").map((l) => l + "  ").join("\n")} title={draft.subject} size="sm" />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea value={letter} onChange={(e) => setLetter(e.target.value)} rows={18} className="font-mono text-sm" aria-label="Letter text" />
            <div className="text-xs text-muted-foreground">
              Basis: {draft.basis.map((b) => `${b.label}${b.status === "Not yet in force" ? ` (in force from ${b.in_force_from})` : ""}`).join(", ")}
            </div>
            <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">{draft.notes.map((n) => <li key={n}>{n}</li>)}</ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
