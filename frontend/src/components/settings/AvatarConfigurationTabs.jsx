import React from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Image, Grid3x3, MessageSquare, Sparkles, Zap } from 'lucide-react'
import AvatarLayoutEditor from './AvatarLayoutEditor'
import AvatarPlacementSettings from './AvatarPlacementSettings'
import ChatBubbleSettings from './ChatBubbleSettings'
import GlowEffectSettings from './GlowEffectSettings'
import CrowdAnimationSettings from './CrowdAnimationSettings'

function AvatarConfigurationTabs({ settings, updateSettings, apiUrl, managedAvatars }) {
  const avatarMode = settings.avatarMode || 'grid'
  
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
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="placement" className="flex items-center gap-2">
              <Grid3x3 className="w-4 h-4" />
              Placement
            </TabsTrigger>
            <TabsTrigger value="animations" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Animations
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
              {/* Mode selector and popup settings */}
              <AvatarPlacementSettings
                settings={settings}
                updateSettings={updateSettings}
                apiUrl={apiUrl}
              />
              
              {/* Layout editor for grid mode */}
              {avatarMode === 'grid' && (
                <AvatarLayoutEditor
                  apiUrl={apiUrl}
                  managedAvatars={managedAvatars}
                />
              )}
            </div>
          </TabsContent>

          <TabsContent value="animations" className="mt-4">
            <div className="space-y-6">
              <CrowdAnimationSettings
                settings={settings}
                onUpdate={updateSettings}
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

