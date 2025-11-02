import React from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Image, Grid3x3, MessageSquare, Sparkles } from 'lucide-react'
import AvatarPlacementSettings from './AvatarPlacementSettings'
import ChatBubbleSettings from './ChatBubbleSettings'
import GlowEffectSettings from './GlowEffectSettings'

function AvatarConfigurationTabs({ settings, updateSettings, apiUrl }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Image className="w-5 h-5" />
          Avatar Configuration
        </CardTitle>
        <CardDescription>Configure avatar placement and visual effects</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="placement" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="placement" className="flex items-center gap-2">
              <Grid3x3 className="w-4 h-4" />
              Placement
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Chat Bubbles
            </TabsTrigger>
            <TabsTrigger value="glow" className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Glow Effect
            </TabsTrigger>
          </TabsList>

          <TabsContent value="placement" className="mt-4">
            <div className="space-y-6">
              <AvatarPlacementSettings
                settings={settings}
                updateSettings={updateSettings}
                apiUrl={apiUrl}
              />
            </div>
          </TabsContent>

          <TabsContent value="chat" className="mt-4">
            <div className="space-y-6">
              <ChatBubbleSettings
                settings={settings}
                onUpdate={updateSettings}
              />
            </div>
          </TabsContent>

          <TabsContent value="glow" className="mt-4">
            <div className="space-y-6">
              <GlowEffectSettings
                settings={settings}
                onUpdate={updateSettings}
              />
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default AvatarConfigurationTabs
