/* Shared display helpers. The app is built for every reader, including older people, so these render
   plainly: no word-by-word reveals, rolling digits, scrambles or tickers. The names stay so pages
   need no special cases. */
import type { ElementType, ReactNode } from "react"
import { cn } from "@/utils/cn"

export const ease = [0.22, 1, 0.36, 1] as const
export const press = [0.65, 0, 0.35, 1] as const

/** A heading or line of text. `accent` words are shown in the action colour. */
export function SplitWords({ text, className, as: Tag = "span", accent }: {
  text: string; className?: string; delay?: number; stagger?: number; as?: ElementType; inView?: boolean; accent?: string[]
}) {
  if (!accent?.length) return <Tag className={className}>{text}</Tag>
  return (
    <Tag className={className}>
      {text.split(" ").map((w, i) => (
        <span key={i} className={cn(accent.includes(w.replace(/[^\w']/g, "")) && "text-primary")}>{w}{" "}</span>
      ))}
    </Tag>
  )
}

export function Reveal({ children, className, as: Tag = "div" }: { children: ReactNode; className?: string; delay?: number; y?: number; as?: "div" | "li" | "section" }) {
  return <Tag className={className}>{children}</Tag>
}

export function Stamp({ children, className }: { children: ReactNode; className?: string; delay?: number; tilt?: number }) {
  return <div className={cn("stamp inline-block", className)}>{children}</div>
}

export function Odometer({ value, className }: { value: number; className?: string; pad?: number }) {
  return <span className={cn("tabular", className)}>{Math.max(0, Math.round(value))}</span>
}

export function Scramble({ text, className }: { text: string; className?: string; speed?: number; loop?: boolean }) {
  return <span className={className}>{text}</span>
}

/** Days from today until a date. */
export function daysUntil(iso: string): number {
  return Math.max(0, Math.ceil((new Date(iso + "T00:00:00").getTime() - Date.now()) / 86_400_000))
}
