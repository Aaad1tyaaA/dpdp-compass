import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { KeyRound, Loader2, Trash2, UserRound } from "lucide-react"
import { api, useAuth } from "@/auth/AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ErrorNote, PageHeader } from "@/components/ui/kit"

function message(e: unknown) {
  return e instanceof Error ? e.message : "Something went wrong. Please try again."
}

export function Account() {
  const { user, refresh, signOut } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState(user?.name ?? "")
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const [busy, setBusy] = useState<"name" | "password" | "delete" | null>(null)
  const [error, setError] = useState<{ where: "password" | "delete"; text: string } | null>(null)
  const [deleting, setDeleting] = useState(false)
  if (!user) return null

  async function saveName(e: FormEvent) {
    e.preventDefault()
    setBusy("name")
    try {
      await api("/api/auth/me", { method: "PATCH", json: { name: name.trim() } })
      await refresh()
      toast.success("Name updated")
    } catch (err) { toast.error(message(err)) } finally { setBusy(null) }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault()
    if (next.length < 8) return setError({ where: "password", text: "Use a new password of at least 8 characters." })
    setBusy("password")
    setError(null)
    try {
      await api("/api/auth/password", { json: { current_password: current, new_password: next } })
      setCurrent("")
      setNext("")
      toast.success("Password changed. Other devices have been signed out.")
    } catch (err) { setError({ where: "password", text: message(err) }) } finally { setBusy(null) }
  }

  async function deleteAccount(e: FormEvent) {
    e.preventDefault()
    setBusy("delete")
    setError(null)
    try {
      await api("/api/auth/delete", { json: { password: confirm } })
      await signOut()
      toast.success("Account deleted")
      navigate("/", { replace: true })
    } catch (err) { setError({ where: "delete", text: message(err) }) } finally { setBusy(null) }
  }

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader eyebrow="Account" title="Your account" subtitle="Your questions, audits and drafts are saved to this account and follow you across devices." />

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><UserRound className="size-4 text-primary" /> Profile</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={saveName} className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5"><Label htmlFor="acc-name">Name</Label><Input id="acc-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required /></div>
            <div className="space-y-1.5"><Label htmlFor="acc-email">Email</Label><Input id="acc-email" value={user.email} readOnly disabled /></div>
            <div className="sm:col-span-2"><Button type="submit" disabled={busy === "name" || !name.trim() || name.trim() === user.name}>{busy === "name" && <Loader2 className="animate-spin" />}Save name</Button></div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><KeyRound className="size-4 text-primary" /> Password</CardTitle>
          <CardDescription>Changing your password signs you out on every other device.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={changePassword} className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5"><Label htmlFor="acc-current">Current password</Label><Input id="acc-current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required /></div>
            <div className="space-y-1.5"><Label htmlFor="acc-new">New password</Label><Input id="acc-new" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} required /></div>
            {error?.where === "password" && <div className="sm:col-span-2"><ErrorNote>{error.text}</ErrorNote></div>}
            <div className="sm:col-span-2"><Button type="submit" variant="outline" disabled={busy === "password" || !current || !next}>{busy === "password" && <Loader2 className="animate-spin" />}Change password</Button></div>
          </form>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive"><Trash2 className="size-4" /> Delete account</CardTitle>
          <CardDescription>Deletes your account, saved conversations, drafts and audits. This cannot be undone.</CardDescription>
        </CardHeader>
        <CardContent>
          {!deleting ? (
            <Button variant="destructive" onClick={() => setDeleting(true)}>Delete my account</Button>
          ) : (
            <form onSubmit={deleteAccount} className="max-w-sm space-y-4">
              <div className="space-y-1.5"><Label htmlFor="acc-confirm">Enter your password to confirm</Label><Input id="acc-confirm" type="password" autoComplete="current-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required /></div>
              {error?.where === "delete" && <ErrorNote>{error.text}</ErrorNote>}
              <div className="flex gap-2">
                <Button type="submit" variant="destructive" disabled={busy === "delete" || !confirm}>{busy === "delete" && <Loader2 className="animate-spin" />}Delete permanently</Button>
                <Button type="button" variant="ghost" onClick={() => { setDeleting(false); setConfirm(""); setError(null) }}>Cancel</Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
