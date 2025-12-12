import * as React from "react"
import { cn } from "@/lib/utils"

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    (<input
      type={type}
      className={cn(
        "flex h-10 w-full bg-black/50 border-b-2 border-primary/50 text-center font-mono text-xl focus:border-primary focus:outline-none focus:shadow-[0_10px_30px_-10px_rgba(0,255,148,0.3)] placeholder:text-white/20 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-300",
        className
      )}
      ref={ref}
      {...props} />)
  )
})
Input.displayName = "Input"

export { Input }
