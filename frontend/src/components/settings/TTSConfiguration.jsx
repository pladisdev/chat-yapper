import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Button } from '../ui/button'
import { Checkbox } from '../ui/checkbox'
import { Separator } from '../ui/separator'
import { 
  Mic, 
  Zap, 
  MessageSquare, 
  TestTube2,
  BarChart3,
  CheckCircle2,
  XCircle
} from 'lucide-react'

function TTSConfiguration({ settings, updateSettings }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-500">
            <Mic className="w-5 h-5" />
            MonsterTTS Settings
          </CardTitle>
          <CardDescription>AI voices with rate limiting (1 generation every 2 seconds)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-orange-500">
            <Mic className="w-5 h-5" />
            Google Cloud TTS Settings
          </CardTitle>
          <CardDescription>Google's neural voices. Requires API key and billing account.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-purple-500">
            <Mic className="w-5 h-5" />
            Amazon Polly Settings
          </CardTitle>
          <CardDescription>Amazon's neural and standard voices. Requires AWS account.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
        </CardContent>
      </Card>
    </div>
  )
}

export default TTSConfiguration