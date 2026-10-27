import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Logo, ThemeToggle } from "@/components/brand"
import { useAuth } from "@/auth/AuthContext"

function Nav() {
  const { user } = useAuth()
  return (
    <header className="border-b">
      <div className="mx-auto flex h-20 max-w-5xl items-center gap-4 px-4 sm:px-6">
        <Logo />
        <div className="ml-auto flex items-center gap-3">
          <ThemeToggle />
          {user ? (
            <Button asChild><Link to="/dashboard">Open the app</Link></Button>
          ) : (
            <>
              <Button asChild variant="outline" className="hidden sm:inline-flex"><Link to="/signin">Sign in</Link></Button>
              <Button asChild><Link to="/signup">Create account</Link></Button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t">
      <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
        <h2 className="text-3xl font-bold">{title}</h2>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  )
}

const STEPS = [
  ["Add your privacy policy", "Upload the file, or copy and paste the text."],
  ["Read the results", "For each of the 14 rules in the law, you see whether the policy meets it, in plain words."],
  ["Fix what is missing", "Copy the suggested wording, then check the policy again."],
]

const DATES = [
  ["13 November 2025", "The Rules were published. The Data Protection Board was set up."],
  ["13 November 2026", "Consent Managers can register."],
  ["13 May 2027", "All the main duties and penalties apply to every business."],
]

const FAQ = [
  ["Is this legal advice?", "No. It explains what the law says. Please ask a lawyer before you rely on it."],
  ["Where do the answers come from?", "From the official text of the Digital Personal Data Protection Act, 2023 and its Rules, 2025. Every answer names the section it used."],
  ["Is my policy kept private?", "Yes. It is saved only in your own account. Deleting your account deletes it."],
  ["Which languages can I use?", "You can ask questions in English, Hindi or Marathi."],
]

export function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <Nav />
      <main>
        <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 sm:py-20">
          <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">Check a privacy policy against India's data protection law</h1>
          <p className="mt-6 max-w-2xl text-xl text-muted-foreground">
            Find out what a privacy policy does and does not promise, and what the law requires. Or ask a question about your own data.
          </p>
          <div className="mt-10 flex flex-col gap-4 sm:flex-row">
            <Button asChild size="lg"><Link to="/business">Check a privacy policy <ArrowRight /></Link></Button>
            <Button asChild size="lg" variant="outline"><Link to="/citizen">Ask about your rights</Link></Button>
          </div>
        </section>

        <Section title="How it works">
          <ol className="grid gap-6 sm:grid-cols-3">
            {STEPS.map(([t, d], i) => (
              <li key={t} className="rounded-lg border p-6">
                <div className="grid size-10 place-items-center rounded-full bg-primary text-lg font-bold text-primary-foreground">{i + 1}</div>
                <div className="mt-4 text-xl font-bold">{t}</div>
                <p className="mt-2 text-muted-foreground">{d}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section title="Important dates">
          <dl className="divide-y rounded-lg border">
            {DATES.map(([d, t]) => (
              <div key={d} className="grid gap-1 p-5 sm:grid-cols-[14rem_1fr]">
                <dt className="font-bold">{d}</dt>
                <dd>{t}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section title="Common questions">
          <div className="space-y-3">
            {FAQ.map(([q, a]) => (
              <details key={q} className="group rounded-lg border p-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-bold">
                  {q}<span aria-hidden className="text-2xl text-primary group-open:hidden">+</span><span aria-hidden className="hidden text-2xl text-primary group-open:inline">−</span>
                </summary>
                <p className="mt-3 max-w-2xl text-muted-foreground">{a}</p>
              </details>
            ))}
          </div>
        </Section>
      </main>
      <footer className="border-t">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-8 sm:px-6">
          <Logo />
          <span className="text-muted-foreground">Guidance only, not legal advice.</span>
        </div>
      </footer>
    </div>
  )
}
