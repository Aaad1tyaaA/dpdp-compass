import { motion } from "motion/react"
import { BookOpenText, Search, ShieldCheck, Scale } from "lucide-react"
import { Card } from "@/components/ui/card"
import { FadeIn, PageHeader, rise, stagger } from "@/components/ui/kit"

const STEPS = [
  { icon: BookOpenText, t: "Read the law", d: "The Gazette text of the DPDP Act, 2023 is split clause by clause (keeping section numbers), embedded, and stored with a graph of who-must-do-what." },
  { icon: Search, t: "Find the evidence", d: "Each question or policy is matched against the Act with meaning-based search, keyword search and the graph; the best passages are re-ranked." },
  { icon: Scale, t: "Check obligations", d: "Specialist agents check 14 duties of a Data Fiduciary and mark each covered, partial or missing — always citing the section they relied on." },
  { icon: ShieldCheck, t: "Guard the answer", d: "Automatic checks reject missing citations, made-up sources, prompt-injection attempts and unsupported claims. With too little evidence, the system says so." },
]

const PAPERS = [
  ["PAKTON (EMNLP 2025)", "clause-aware chunking of long legal documents"],
  ["RAGulating (arXiv 2508.09893)", "subject–predicate–object triplets for compliance"],
  ["LegalGraphRAG (ACL 2026)", "layered legal knowledge base"],
  ["RAGAS (Es et al., 2023)", "retrieval and faithfulness metrics"],
]

export function About() {
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <PageHeader eyebrow="Method" title="How it works" subtitle="Every answer starts from the text of the law, not from a language model's memory." />
      <motion.ol className="relative space-y-4 before:absolute before:bottom-6 before:left-[27px] before:top-6 before:w-px before:bg-border"
        variants={stagger} initial="hidden" animate="show">
        {STEPS.map((s, i) => (
          <motion.li key={s.t} variants={rise} className="relative">
            <Card className="flex gap-4 p-5 transition-shadow duration-200 hover:shadow-lift">
              <span className="relative z-10 grid size-8 shrink-0 place-items-center bg-signal font-mono text-signal-foreground ring-4 ring-background">
                <s.icon className="size-4" />
              </span>
              <div className="min-w-0 space-y-1">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Step {i + 1}</div>
                <h2 className="text-base font-semibold">{s.t}</h2>
                <p className="text-base leading-relaxed text-muted-foreground">{s.d}</p>
              </div>
            </Card>
          </motion.li>
        ))}
      </motion.ol>
      <FadeIn>
        <Card className="p-6">
          <h2 className="text-base font-semibold">Research this builds on</h2>
          <ul className="mt-3 space-y-2 text-base text-muted-foreground">
            {PAPERS.map(([p, d]) => <li key={p}><span className="font-medium text-foreground">{p}</span> — {d}</li>)}
          </ul>
        </Card>
      </FadeIn>
      <p className="text-xs text-muted-foreground">Scores are a guide to how completely a policy addresses the Act. They are not legal advice.</p>
    </div>
  )
}
