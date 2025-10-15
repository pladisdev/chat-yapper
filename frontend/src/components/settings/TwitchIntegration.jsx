import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import logger from '../../utils/logger'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Button } from '../ui/button'
import { 
  Zap, 
  CheckCircle2
} from 'lucide-react'

function TwitchIntegration({ settings, updateSettings, apiUrl = '' }) {
  const [twitchStatus, setTwitchStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [channelInput, setChannelInput] = useState('');

  // Check Twitch connection status on component mount
  useEffect(() => {
    checkTwitchStatus();
  }, []);

  // Sync channel input with settings
  useEffect(() => {
    if (settings.twitch?.channel !== undefined) {
      setChannelInput(settings.twitch.channel || '');
    }
  }, [settings.twitch?.channel]);

  const checkTwitchStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/twitch/status`);
      const status = await response.json();
      setTwitchStatus(status);
    } catch (error) {
      logger.error('Failed to check Twitch status:', error);
      setTwitchStatus({ connected: false });
    }
  };

  const connectToTwitch = () => {
    // Open OAuth flow - use backend URL for authentication
    window.location.href = `${apiUrl}/auth/twitch`;
  };

  // Check for error parameter in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    
    if (error === 'twitch_not_configured') {
      alert('⚠️ Twitch integration not configured!\n\nThe developer needs to set up Twitch OAuth credentials.\nSee TWITCH_SETUP.md for instructions.');
      // Clear error from URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const disconnectTwitch = async () => {
    if (!confirm('Are you sure you want to disconnect from Twitch?')) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${apiUrl}/api/twitch/disconnect`, { method: 'DELETE' });
      const result = await response.json();
      
      if (result.success) {
        setTwitchStatus({ connected: false });
        // Clear Twitch settings
        updateSettings({ 
          twitch: { 
            ...settings.twitch, 
            enabled: false 
          } 
        });
        logger.info('Successfully disconnected from Twitch');
      } else {
        alert('Failed to disconnect: ' + result.error);
      }
    } catch (error) {
      logger.error('Error disconnecting from Twitch:', error);
      alert('Network error while disconnecting');
    } finally {
      setLoading(false);
    }
  };

  const updateChannel = () => {
    updateSettings({ 
      twitch: { 
        ...settings.twitch, 
        channel: channelInput.trim() 
      } 
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-500" />
          Twitch Integration
        </CardTitle>
        <CardDescription>
          Connect to your Twitch account to enable chat TTS
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {!twitchStatus?.connected ? (
          <div className="text-center space-y-4 py-8">
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Connect to Twitch</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Authorize Chat Yapper to read your Twitch chat. This is secure and you can 
                revoke access at any time in your Twitch settings.
              </p>
            </div>
            
            <Button 
              onClick={connectToTwitch} 
              size="lg"
              className="bg-purple-600 hover:bg-purple-700"
              disabled={loading}
            >
              <Zap className="w-4 h-4 mr-2" />
              {loading ? 'Connecting...' : 'Connect to Twitch'}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Connected Status */}
            <div className="flex items-center justify-between p-4 rounded-lg border bg-emerald-800 text-white">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium">Connected to Twitch</p>
                  <p className="text-sm text-emerald-100">
                    Logged in as: {twitchStatus.display_name} (@{twitchStatus.username})
                  </p>
                </div>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={disconnectTwitch}
                disabled={loading}
                className="border-red-500 text-red-400 hover:bg-red-600 hover:text-white"
              >
                {loading ? 'Disconnecting...' : 'Disconnect'}
              </Button>
            </div>

            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
              <div className="space-y-1">
                <Label htmlFor="twitch-enabled" className="text-base">Enable Chat TTS</Label>
                <p className="text-sm text-muted-foreground">
                  Start reading chat messages from your Twitch channel
                </p>
              </div>
              <Switch
                id="twitch-enabled"
                checked={!!settings.twitch?.enabled}
                onCheckedChange={checked => updateSettings({ 
                  twitch: { 
                    ...settings.twitch, 
                    enabled: checked,
                    // Set the connected username as the channel by default
                    channel: checked && !settings.twitch?.channel ? twitchStatus.username : settings.twitch?.channel
                  } 
                })}
              />
            </div>

            {/* Channel Selection */}
            {settings.twitch?.enabled && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="channel">Channel to Monitor</Label>
                  <div className="flex gap-2">
                    <Input
                      id="channel"
                      placeholder="Enter channel name (without #)"
                      value={channelInput}
                      onChange={e => setChannelInput(e.target.value)}
                      onKeyPress={e => e.key === 'Enter' && updateChannel()}
                      className="flex-1"
                    />
                    <Button
                      onClick={updateChannel}
                      disabled={channelInput.trim() === (settings.twitch?.channel || '')}
                      size="sm"
                    >
                      Update
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Usually your own channel: <code>{twitchStatus.username}</code>
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function SpecialEventVoices({ settings, updateSettings, allVoices }) {
  const events = [
    { key: 'raid', name: 'Raids',  desc: 'When someone raids your stream' },
    { key: 'bits', name: 'Bits/Cheers',  desc: 'When viewers donate bits' },
    { key: 'sub', name: 'Subscriptions',  desc: 'New subscribers' },
    { key: 'highlight', name: 'Highlights', desc: 'Highlighted messages' },
    { key: 'vip', name: 'VIP Messages', desc: 'Messages from VIPs' }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-500" />
          Special Event Voices (Experimental)
        </CardTitle>
        <CardDescription>Assign specific voices to different Twitch events</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map(event => (
            <div key={event.key} className="p-4 rounded-lg border bg-card space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">{event.icon}</span>
                <div>
                  <div className="font-medium text-sm">{event.name}</div>
                  <div className="text-xs text-muted-foreground">{event.desc}</div>
                </div>
              </div>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={settings.specialVoices?.[event.key]?.voiceId || ''}
                onChange={e => updateSettings({
                  specialVoices: { ...settings.specialVoices, [event.key]: { voiceId: e.target.value } }
                })}>
                <option value="">Random Voice</option>
                {allVoices.filter(v => v.enabled).map(v => <option key={v.id} value={v.id}>{v.name} ({v.provider})</option>)}
              </select>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Export both components individually for flexibility, and a combined component as default
export { TwitchIntegration, SpecialEventVoices }

export default function TwitchIntegrationTab({ settings, updateSettings, allVoices, apiUrl }) {
  return (
    <div className="space-y-6">
      <TwitchIntegration settings={settings} updateSettings={updateSettings} apiUrl={apiUrl} />
      <SpecialEventVoices settings={settings} updateSettings={updateSettings} allVoices={allVoices} />
    </div>
  )
}