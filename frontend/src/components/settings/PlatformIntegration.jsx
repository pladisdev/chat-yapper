import React from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { TwitchIntegration, SpecialEventVoices } from './TwitchIntegration'
import YouTubeIntegration from './YouTubeIntegration'
import { Zap, Youtube } from 'lucide-react'

function PlatformIntegration({ settings, updateSettings, allVoices, apiUrl }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Platform Integrations
        </CardTitle>
        <CardDescription>Connect to streaming platforms to enable chat TTS</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="twitch" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="twitch" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Twitch
            </TabsTrigger>
            <TabsTrigger value="youtube" className="flex items-center gap-2">
              <Youtube className="w-4 h-4" />
              YouTube
            </TabsTrigger>
          </TabsList>

          <TabsContent value="twitch" className="space-y-6 mt-4">
            <TwitchIntegration 
              settings={settings} 
              updateSettings={updateSettings} 
              apiUrl={apiUrl} 
            />
            <SpecialEventVoices 
              settings={settings} 
              updateSettings={updateSettings} 
              allVoices={allVoices} 
            />
          </TabsContent>

          <TabsContent value="youtube" className="space-y-6 mt-4">
            <YouTubeIntegration 
              settings={settings} 
              updateSettings={updateSettings} 
              apiUrl={apiUrl} 
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default PlatformIntegration
