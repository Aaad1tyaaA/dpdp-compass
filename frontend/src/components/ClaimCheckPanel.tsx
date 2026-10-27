import type { ClaimCheck } from "@/types"

const TONE: Record<string, string> = {
  supported: "text-success", uncertain: "text-warning", absent: "text-muted-foreground", contradicted: "text-destructive",
}
const LABEL: Record<string, string> = {
  supported: "Supported by the sources", uncertain: "Partly supported", absent: "Not found in the sources", contradicted: "Contradicted by the sources",
}

/** Which sentences of an answer its sources actually say. A word-overlap check: read the source where it matters. */
export function ClaimCheckPanel({ check }: { check: ClaimCheck }) {
  if (!check.claims.length) return null
  const c = check.counts
  return (
    <details className="rounded-lg border px-4 py-3 text-base">
      <summary className="cursor-pointer select-none">
        <span className="font-medium">Checked against the sources</span>{" "}
        <span className="text-muted-foreground">
          · {c.supported} supported{c.uncertain ? ` · ${c.uncertain} partly` : ""}{c.absent ? ` · ${c.absent} not found` : ""}
        </span>
        {c.contradicted > 0 && <span className="text-destructive"> · {c.contradicted} contradicted</span>}
      </summary>
      <ul className="mt-3 space-y-2.5">
        {check.claims.map((x, i) => (
          <li key={i} className="break-words">
            <div><span className={`text-xs font-medium ${TONE[x.status]}`}>{LABEL[x.status]}.</span> {x.claim}</div>
            {x.evidence && x.status !== "supported" && <div className="mt-0.5 text-xs text-muted-foreground">Source: “{x.evidence}”</div>}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted-foreground">This compares the words of each sentence with the cited text. It cannot judge paraphrase, so treat it as a pointer, not a verdict.</p>
    </details>
  )
}
