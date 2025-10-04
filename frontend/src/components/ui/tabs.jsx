import * as TabsPrimitive from '@radix-ui/react-tabs'
import './tabs.css'

export function Tabs({ defaultValue, value, onValueChange, children, className, ...props }) {
  return (
    <TabsPrimitive.Root 
      defaultValue={defaultValue} 
      value={value} 
      onValueChange={onValueChange}
      className={["ui-tabs-container", className].filter(Boolean).join(' ')} 
      {...props}
    >
      {children}
    </TabsPrimitive.Root>
  )
}

export function TabsList({ children, className, ...props }) {
  return (
    <TabsPrimitive.List className={["ui-tabs-list", className].filter(Boolean).join(' ')} {...props}>
      {children}
    </TabsPrimitive.List>
  )
}

export function TabsTrigger({ children, className, ...props }) {
  return (
    <TabsPrimitive.Trigger className={["ui-tabs-trigger", className].filter(Boolean).join(' ')} {...props}>
      {children}
    </TabsPrimitive.Trigger>
  )
}

export function TabsContent({ children, className, ...props }) {
  return (
    <TabsPrimitive.Content className={["ui-tabs-content", className].filter(Boolean).join(' ')} {...props}>
      {children}
    </TabsPrimitive.Content>
  )
}
