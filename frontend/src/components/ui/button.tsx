import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/utils/cn"

const buttonVariants = cva(
  // Large, plain buttons: big tap targets, sentence-case labels, a clear colour change on hover.
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-base font-bold transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/85",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/70",
        outline: "border-2 border-primary bg-background text-primary hover:bg-accent",
        ghost: "text-foreground hover:bg-secondary",
        link: "text-primary underline underline-offset-4 hover:no-underline",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/85",
      },
      size: { default: "h-12 px-6", sm: "h-10 px-4 text-base", lg: "h-14 px-8 text-lg", icon: "h-12 w-12" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
)

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
})
Button.displayName = "Button"

export { buttonVariants }
