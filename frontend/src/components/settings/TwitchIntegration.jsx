import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import logger from '../../utils/logger'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Button } from '../ui/button'
import { useWebSocket } from '../../WebSocketContext'
import { 
  Zap, 
  CheckCircle2,
  AlertTriangle
} from 'lucide-react'

function RedeemNamesManager({ redeemNames, onUpdate }) {
  const [newRedeem, setNewRedeem] = useState('')

  const addRedeem = () => {
    const redeemName = newRedeem.trim()
    if (!redeemName) return
    
    if (redeemNames.some(name => name.toLowerCase() === redeemName.toLowerCase())) {
      alert('This redeem name is already in the list')
      return
    }
    
    onUpdate([...redeemNames, redeemName])
    setNewRedeem('')
  }

  const removeRedeem = (redeemToRemove) => {
    onUpdate(redeemNames.filter(name => name !== redeemToRemove))
  }

  const clearAllRedeems = () => {
    if (redeemNames.length === 0) return
    if (confirm(`Are you sure you want to remove all ${redeemNames.length} redeem names?`)) {
      onUpdate([])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="Enter redeem name..."
          value={newRedeem}
          onChange={e => setNewRedeem(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && addRedeem()}
        />
        <Button
          onClick={addRedeem}
          disabled={!newRedeem.trim()}
        >
          Add
        </Button>
      </div>

      {redeemNames.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">
              Allowed Redeems ({redeemNames.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllRedeems}
              className="h-auto py-1 px-2 text-xs text-destructive hover:text-destructive"
            >
              Clear All
            </Button>
          </div>
          
          <div className="max-h-32 overflow-y-auto space-y-1">
            {redeemNames.map((name, index) => (
              <div key={index} className="flex items-center justify-between p-2 rounded-lg border bg-card">
                <span className="text-sm">{name}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeRedeem(name)}
                  className="h-auto py-1 px-2 text-destructive hover:text-destructive"
                  title={`Remove ${name}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {redeemNames.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No redeem names added yet
        </p>
      )}
    </div>
  )
}

function TwitchIntegration({ settings, updateSettings, apiUrl = '' }) {
  const [twitchStatus, setTwitchStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [channelInput, setChannelInput] = useState('');
  const [authError, setAuthError] = useState(null);
  const { addListener } = useWebSocket();

  // Check Twitch connection status and auth errors on component mount
  useEffect(() => {
    checkTwitchStatus();
    checkAuthError();
  }, []);

  const checkAuthError = async () => {
    try {
      logger.info('=== CHECKING FOR AUTH ERRORS ===');
      const response = await fetch(`${apiUrl}/api/twitch/auth-error`);
      const result = await response.json();
      logger.info('Auth error check result:', result);
      
      if (result.has_error && result.error) {
        logger.error('=== PENDING AUTH ERROR FOUND ===');
        logger.error('Auth error details:', result.error);
        setAuthError(result.error.message);
        setTwitchStatus({ connected: false });
      } else {
        logger.info('No auth error found');
      }
    } catch (error) {
      logger.error('Failed to check for auth errors:', error);
    }
  };

  // Listen for WebSocket messages including auth errors
  useEffect(() => {
    const removeListener = addListener((data) => {
      logger.info('WebSocket message received in TwitchIntegration:', data.type);
      if (data.type === 'twitch_auth_error') {
        logger.error('Twitch authentication error received:', data.message);
        setAuthError(data.message);
        // Also update the status to disconnected
        setTwitchStatus({ connected: false });
      }
    });

    return removeListener;
  }, [addListener]);

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
      
      // If connected, test the actual connection to detect auth issues
      if (status.connected && settings.twitch?.enabled) {
        logger.info('Twitch shows connected, testing actual connection...');
        try {
          const testResponse = await fetch(`${apiUrl}/api/twitch/test-connection`, {
            method: 'POST'
          });
          const testResult = await testResponse.json();
          
          if (!testResult.success) {
            logger.warning('Twitch connection test failed:', testResult.error);
            // Don't override the status here, let the test function handle auth errors
            // The WebSocket listener will catch any auth errors that are broadcast
          } else {
            logger.info('Twitch connection test passed');
            // Clear any existing auth errors since connection is working
            if (authError) {
              setAuthError(null);
              try {
                await fetch(`${apiUrl}/api/twitch/auth-error`, { method: 'DELETE' });
              } catch (error) {
                logger.error('Failed to clear auth error on backend:', error);
              }
            }
          }
        } catch (testError) {
          logger.error('Failed to test Twitch connection:', testError);
        }
      }
      
      // Clear auth error if we're now connected
      else if (status.connected && authError) {
        setAuthError(null);
        // Also clear it on the backend
        try {
          await fetch(`${apiUrl}/api/twitch/auth-error`, { method: 'DELETE' });
        } catch (error) {
          logger.error('Failed to clear auth error on backend:', error);
        }
      }
      // If not connected, also check for auth errors
      else if (!status.connected) {
        await checkAuthError();
      }
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
      alert('Twitch integration not configured!\n\nThe developer needs to set up Twitch OAuth credentials.\nSee TWITCH_SETUP.md for instructions.');
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
        {/* Authentication Error Display */}
        {authError && (
          <div className="flex items-center gap-3 p-4 rounded-lg border bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <div className="flex-1">
              <p className="font-medium text-red-900 dark:text-red-100">Authentication Failed</p>
              <p className="text-sm text-red-700 dark:text-red-200">{authError}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  setAuthError(null);
                  // Clear the error on the backend too
                  try {
                    await fetch(`${apiUrl}/api/twitch/auth-error`, { method: 'DELETE' });
                  } catch (error) {
                    logger.error('Failed to clear auth error on backend:', error);
                  }
                }}
                className="border-red-300 text-red-700 hover:bg-red-100 dark:border-red-700 dark:text-red-200 dark:hover:bg-red-900"
              >
                Dismiss
              </Button>
              <Button
                size="sm"
                onClick={async () => {
                  setAuthError(null);
                  // Clear the error on the backend too
                  try {
                    await fetch(`${apiUrl}/api/twitch/auth-error`, { method: 'DELETE' });
                  } catch (error) {
                    logger.error('Failed to clear auth error on backend:', error);
                  }
                  connectToTwitch();
                }}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Reconnect
              </Button>
            </div>
          </div>
        )}

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

              </div>
              <Switch
                id="twitch-enabled"
                checked={!!settings.twitch?.enabled}
                onCheckedChange={async (checked) => {
                  // Update settings first
                  await updateSettings({ 
                    twitch: { 
                      ...settings.twitch, 
                      enabled: checked,
                      // Set the connected username as the channel by default
                      channel: checked && !settings.twitch?.channel ? twitchStatus.username : settings.twitch?.channel
                    } 
                  });
                  
                  // If enabling, check for auth errors after a short delay to let backend start
                  if (checked) {
                    setTimeout(async () => {
                      await checkAuthError();
                    }, 2000); // Give the backend time to attempt connection and fail
                  } else {
                    // If disabling, clear any existing auth error
                    setAuthError(null);
                  }
                }}
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

                {/* Channel Point Redeem Filter */}
                <div className="p-4 rounded-lg border bg-card space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label htmlFor="redeem-filter-enabled" className="text-base">
                        Channel Point Redeem Messages Only
                      </Label>
                    </div>
                    <Switch
                      id="redeem-filter-enabled"
                      checked={!!settings.twitch?.redeemFilter?.enabled}
                      onCheckedChange={checked => updateSettings({
                        twitch: {
                          ...settings.twitch,
                          redeemFilter: {
                            ...settings.twitch?.redeemFilter,
                            enabled: checked
                          }
                        }
                      })}
                    />
                  </div>

                  {settings.twitch?.redeemFilter?.enabled && (
                    <div className="space-y-2">
                      <Label htmlFor="allowed-redeems">
                        Channel Point Reward Names
                      </Label>
                      <RedeemNamesManager
                        redeemNames={settings.twitch?.redeemFilter?.allowedRedeemNames || []}
                        onUpdate={(names) => updateSettings({
                          twitch: {
                            ...settings.twitch,
                            redeemFilter: {
                              ...settings.twitch?.redeemFilter,
                              allowedRedeemNames: names
                            }
                          }
                        })}
                      />
                      <p className="text-sm text-muted-foreground">
                        Enter the exact names of your channel point rewards. Names are case-insensitive. 
                        You can find reward names in your Twitch Dashboard under Channel Points.
                      </p>
                    </div>
                  )}
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
export { TwitchIntegration, SpecialEventVoices, RedeemNamesManager }

export default function TwitchIntegrationTab({ settings, updateSettings, allVoices, apiUrl }) {
  return (
    <div className="space-y-6">
      <TwitchIntegration settings={settings} updateSettings={updateSettings} apiUrl={apiUrl} />
      {/* <SpecialEventVoices settings={settings} updateSettings={updateSettings} allVoices={allVoices} /> */}
    </div>
  )
}