import * as React from "react"
import { cn } from "@/utils/cn"

const field =
  "flex w-full rounded-lg border-2 border-input bg-card px-4 text-base placeholder:text-muted-foreground/80 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-destructive"

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(field, "h-12", className)} {...props} />
))
Input.displayName = "Input"

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(field, "min-h-[96px] py-3 leading-relaxed", className)} {...props} />
))
Textarea.displayName = "Textarea"
