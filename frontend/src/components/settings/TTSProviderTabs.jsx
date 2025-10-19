import React, { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { 
  Mic, 
  CheckCircle2,
  XCircle,
  RefreshCw
} from 'lucide-react'

function TTSProviderTabs({ settings, updateSettings, apiUrl = '' }) {
  const [pollyRefreshing, setPollyRefreshing] = useState(false)
  const [pollyVoiceCount, setPollyVoiceCount] = useState(null)
  const [pollyLastUpdated, setPollyLastUpdated] = useState(null)
  const [pollyError, setPollyError] = useState(null)
  
  const [googleRefreshing, setGoogleRefreshing] = useState(false)
  const [googleVoiceCount, setGoogleVoiceCount] = useState(null)
  const [googleLastUpdated, setGoogleLastUpdated] = useState(null)
  const [googleError, setGoogleError] = useState(null)
  
  const [monsterRefreshing, setMonsterRefreshing] = useState(false)
  const [monsterVoiceCount, setMonsterVoiceCount] = useState(null)
  const [monsterLastUpdated, setMonsterLastUpdated] = useState(null)
  const [monsterError, setMonsterError] = useState(null)
  
  const [edgeRefreshing, setEdgeRefreshing] = useState(false)
  const [edgeVoiceCount, setEdgeVoiceCount] = useState(null)
  const [edgeLastUpdated, setEdgeLastUpdated] = useState(null)
  const [edgeError, setEdgeError] = useState(null)
  
  const handleRefreshPollyVoices = async () => {
    setPollyRefreshing(true)
    setPollyError(null)
    
    try {
      const response = await fetch(`${apiUrl}/api/available-voices/polly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          accessKey: settings.tts?.polly?.accessKey || '',
          secretKey: settings.tts?.polly?.secretKey || '',
          region: settings.tts?.polly?.region || 'us-east-1',
          refresh: true
        })
      })
      
      const data = await response.json()
      
      if (data.error) {
        setPollyError(data.error)
      } else {
        setPollyVoiceCount(data.voices?.length || 0)
        setPollyLastUpdated(data.last_updated)
      }
    } catch (err) {
      setPollyError(`Failed to fetch voices: ${err.message}`)
    } finally {
      setPollyRefreshing(false)
    }
  }
  
  const handleRefreshGoogleVoices = async () => {
    setGoogleRefreshing(true)
    setGoogleError(null)
    
    try {
      const response = await fetch(`${apiUrl}/api/available-voices/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          apiKey: settings.tts?.google?.apiKey || '',
          refresh: true
        })
      })
      
      const data = await response.json()
      
      if (data.error) {
        setGoogleError(data.error)
      } else {
        setGoogleVoiceCount(data.voices?.length || 0)
        setGoogleLastUpdated(data.last_updated)
      }
    } catch (err) {
      setGoogleError(`Failed to fetch voices: ${err.message}`)
    } finally {
      setGoogleRefreshing(false)
    }
  }
  
  const handleRefreshMonsterVoices = async () => {
    setMonsterRefreshing(true)
    setMonsterError(null)
    
    try {
      const response = await fetch(`${apiUrl}/api/available-voices/monstertts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          apiKey: settings.tts?.monstertts?.apiKey || '',
          refresh: true
        })
      })
      
      const data = await response.json()
      
      if (data.error) {
        setMonsterError(data.error)
      } else {
        setMonsterVoiceCount(data.voices?.length || 0)
        setMonsterLastUpdated(data.last_updated)
      }
    } catch (err) {
      setMonsterError(`Failed to fetch voices: ${err.message}`)
    } finally {
      setMonsterRefreshing(false)
    }
  }
  
  const handleRefreshEdgeVoices = async () => {
    setEdgeRefreshing(true)
    setEdgeError(null)
    
    try {
      const response = await fetch(`${apiUrl}/api/available-voices/edge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          refresh: true
        })
      })
      
      const data = await response.json()
      
      if (data.error) {
        setEdgeError(data.error)
      } else {
        setEdgeVoiceCount(data.voices?.length || 0)
        setEdgeLastUpdated(data.last_updated)
      }
    } catch (err) {
      setEdgeError(`Failed to fetch voices: ${err.message}`)
    } finally {
      setEdgeRefreshing(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mic className="w-5 h-5" />
          TTS Provider Settings
        </CardTitle>
        <CardDescription>Configure your text-to-speech providers</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="edge" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="edge">Edge TTS</TabsTrigger>
            <TabsTrigger value="monster">MonsterTTS</TabsTrigger>
            <TabsTrigger value="google">Google</TabsTrigger>
            <TabsTrigger value="polly">Polly</TabsTrigger>
          </TabsList>

          {/* Edge TTS Tab */}
          <TabsContent value="edge" className="space-y-4 mt-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-green-500" />
                <h3 className="font-semibold text-green-500">Microsoft Edge TTS</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Microsoft's free neural voices (no API key required)
              </p>
            </div>

            <Separator />

            <div className="space-y-3">
              <Label>Voice Cache</Label>
              <Button
                onClick={handleRefreshEdgeVoices}
                disabled={edgeRefreshing}
                variant="outline"
                className="w-full"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${edgeRefreshing ? 'animate-spin' : ''}`} />
                {edgeRefreshing ? 'Fetching Voices...' : 'Fetch Available Voices'}
              </Button>
              
              {edgeVoiceCount !== null && (
                <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Successfully fetched {edgeVoiceCount} voices</span>
                </div>
              )}
              
              {edgeLastUpdated && (
                <p className="text-xs text-muted-foreground">
                  Last updated: {new Date(edgeLastUpdated).toLocaleString()}
                </p>
              )}
              
              {edgeError && (
                <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                  <XCircle className="w-4 h-4" />
                  <span>{edgeError}</span>
                </div>
              )}
              
              <p className="text-xs text-muted-foreground">
                Edge TTS is completely free and requires no API key. 
                Cached voices are stored locally for faster loading. Click refresh to update the voice list.
              </p>
            </div>
          </TabsContent>

          {/* MonsterTTS Tab */}
          <TabsContent value="monster" className="space-y-4 mt-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-blue-500" />
                <h3 className="font-semibold text-blue-500">MonsterTTS</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                AI voices with rate limiting (1 generation every 2 seconds)
              </p>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label htmlFor="monstertts-api-key">API Key</Label>
              <Input
                id="monstertts-api-key"
                type="password"
                placeholder="ttsm_12345-abcdef (leave empty to use configured voices only)"
                value={settings.tts?.monstertts?.apiKey || ''}
                onChange={e => updateSettings({ 
                  tts: { 
                    ...settings.tts, 
                    monstertts: { 
                      ...settings.tts?.monstertts, 
                      apiKey: e.target.value 
                    } 
                  } 
                })}
              />
              <p className="text-sm text-muted-foreground">
                Get your API key at{' '}
                <a href="https://tts.monster/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  tts.monster
                </a>
              </p>
            </div>
            
            <Separator />
            
            <div className="space-y-3">
              <Label>Voice Cache</Label>
              <Button
                onClick={handleRefreshMonsterVoices}
                disabled={!settings.tts?.monstertts?.apiKey || monsterRefreshing}
                variant="outline"
                className="w-full"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${monsterRefreshing ? 'animate-spin' : ''}`} />
                {monsterRefreshing ? 'Fetching Voices...' : 'Fetch Available Voices'}
              </Button>
              
              {monsterVoiceCount !== null && (
                <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Successfully fetched {monsterVoiceCount} voices</span>
                </div>
              )}
              
              {monsterLastUpdated && (
                <p className="text-xs text-muted-foreground">
                  Last updated: {new Date(monsterLastUpdated).toLocaleString()}
                </p>
              )}
              
              {monsterError && (
                <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                  <XCircle className="w-4 h-4" />
                  <span>{monsterError}</span>
                </div>
              )}
              
              <p className="text-xs text-muted-foreground">
                Cached voices are stored locally and reused to minimize API calls. 
                Click refresh to update if you've changed your API key or want the latest voices.
              </p>
            </div>
          </TabsContent>

          {/* Google Cloud TTS Tab */}
          <TabsContent value="google" className="space-y-4 mt-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-orange-500" />
                <h3 className="font-semibold text-orange-500">Google Cloud TTS</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Google's neural voices. Requires API key and billing account.
              </p>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label htmlFor="google-api-key">API Key</Label>
              <Input
                id="google-api-key"
                type="password"
                placeholder="AIzaSy... (Google Cloud API Key)"
                value={settings.tts?.google?.apiKey || ''}
                onChange={e => updateSettings({ 
                  tts: { 
                    ...settings.tts, 
                    google: { 
                      ...settings.tts?.google, 
                      apiKey: e.target.value 
                    } 
                  } 
                })}
              />
              <p className="text-sm text-muted-foreground">
                Create an API key at{' '}
                <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  Google Cloud Console
                </a>
              </p>
            </div>
            
            <Separator />
            
            <div className="space-y-3">
              <Label>Voice Cache</Label>
              <Button
                onClick={handleRefreshGoogleVoices}
                disabled={!settings.tts?.google?.apiKey || googleRefreshing}
                variant="outline"
                className="w-full"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${googleRefreshing ? 'animate-spin' : ''}`} />
                {googleRefreshing ? 'Fetching Voices...' : 'Fetch Available Voices'}
              </Button>
              
              {googleVoiceCount !== null && (
                <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Successfully fetched {googleVoiceCount} voices</span>
                </div>
              )}
              
              {googleLastUpdated && (
                <p className="text-xs text-muted-foreground">
                  Last updated: {new Date(googleLastUpdated).toLocaleString()}
                </p>
              )}
              
              {googleError && (
                <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                  <XCircle className="w-4 h-4" />
                  <span>{googleError}</span>
                </div>
              )}
              
              <p className="text-xs text-muted-foreground">
                Cached voices are stored locally and reused to minimize API calls. 
                Click refresh to update if you've changed your API key or want the latest voices.
              </p>
            </div>
          </TabsContent>

          {/* Amazon Polly Tab */}
          <TabsContent value="polly" className="space-y-4 mt-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-purple-500" />
                <h3 className="font-semibold text-purple-500">Amazon Polly</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Amazon's neural and standard voices. Requires AWS account.
              </p>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label htmlFor="polly-access-key">AWS Access Key ID</Label>
              <Input
                id="polly-access-key"
                type="password"
                placeholder="AKIA... (AWS Access Key ID)"
                value={settings.tts?.polly?.accessKey || ''}
                onChange={e => updateSettings({ 
                  tts: { 
                    ...settings.tts, 
                    polly: { 
                      ...settings.tts?.polly, 
                      accessKey: e.target.value 
                    } 
                  } 
                })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="polly-secret-key">AWS Secret Access Key</Label>
              <Input
                id="polly-secret-key"
                type="password"
                placeholder="Secret Access Key"
                value={settings.tts?.polly?.secretKey || ''}
                onChange={e => updateSettings({ 
                  tts: { 
                    ...settings.tts, 
                    polly: { 
                      ...settings.tts?.polly, 
                      secretKey: e.target.value 
                    } 
                  } 
                })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="polly-region">AWS Region</Label>
              <Input
                id="polly-region"
                type="text"
                placeholder="us-east-1 (default)"
                value={settings.tts?.polly?.region || ''}
                onChange={e => updateSettings({ 
                  tts: { 
                    ...settings.tts, 
                    polly: { 
                      ...settings.tts?.polly, 
                      region: e.target.value 
                    } 
                  } 
                })}
              />
              <p className="text-sm text-muted-foreground">
                Create access keys at{' '}
                <a href="https://console.aws.amazon.com/iam/home#/security_credentials" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  AWS IAM Console
                </a>
                {' '}(Polly permissions required)
              </p>
            </div>
            
            <Separator />
            
            <div className="space-y-3">
              <Label>Voice Cache</Label>
              <Button
                onClick={handleRefreshPollyVoices}
                disabled={pollyRefreshing || !settings.tts?.polly?.accessKey || !settings.tts?.polly?.secretKey}
                variant="outline"
                className="w-full"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${pollyRefreshing ? 'animate-spin' : ''}`} />
                {pollyRefreshing ? 'Fetching Voices...' : 'Fetch Available Voices'}
              </Button>
              
              {pollyVoiceCount !== null && (
                <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Successfully fetched {pollyVoiceCount} voices</span>
                  {pollyLastUpdated && (
                    <span className="text-xs text-muted-foreground">
                      (cached {new Date(pollyLastUpdated).toLocaleString()})
                    </span>
                  )}
                </div>
              )}
              
              {pollyError && (
                <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                  <XCircle className="w-4 h-4" />
                  <span>{pollyError}</span>
                </div>
              )}
              
              <p className="text-xs text-muted-foreground">
                Cached voices are stored locally and reused to minimize API calls. 
                Click refresh to update if you've changed your credentials or want the latest voices.
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default TTSProviderTabs
