import React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"
import { cn } from "../../lib/utils"

const Tabs = React.forwardRef((props, ref) => {
  const { className, ...rest } = props
  return (
    <TabsPrimitive.Root
      ref={ref}
      className={cn("", className)}
      {...rest}
    />
  )
})
Tabs.displayName = "Tabs"

const TabsList = React.forwardRef((props, ref) => {
  const { className, ...rest } = props
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md bg-neutral-900 p-1 text-neutral-400",
        className
      )}
      {...rest}
    />
  )
})
TabsList.displayName = "TabsList"

const TabsTrigger = React.forwardRef((props, ref) => {
  const { className, ...rest } = props
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-neutral-950 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-300 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-neutral-800 data-[state=active]:text-neutral-50 data-[state=active]:shadow-sm",
        className
      )}
      {...rest}
    />
  )
})
TabsTrigger.displayName = "TabsTrigger"

const TabsContent = React.forwardRef((props, ref) => {
  const { className, ...rest } = props
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={cn(
        "mt-2 ring-offset-neutral-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-300 focus-visible:ring-offset-2",
        className
      )}
      {...rest}
    />
  )
})
TabsContent.displayName = "TabsContent"

export { Tabs, TabsList, TabsTrigger, TabsContent }
