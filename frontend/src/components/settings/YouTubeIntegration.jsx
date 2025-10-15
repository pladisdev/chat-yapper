import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import logger from '../../utils/logger'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Button } from '../ui/button'
import { 
  Youtube, 
  CheckCircle2
} from 'lucide-react'

function YouTubeIntegration({ settings, updateSettings, apiUrl = '' }) {
  const [youtubeStatus, setYoutubeStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [channelInput, setChannelInput] = useState('');

  // Check YouTube connection status on component mount
  useEffect(() => {
    checkYouTubeStatus();
  }, []);

  // Sync channel input with settings
  useEffect(() => {
    if (settings.youtube?.channel !== undefined) {
      setChannelInput(settings.youtube.channel || '');
    }
  }, [settings.youtube?.channel]);

  const checkYouTubeStatus = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/youtube/status`);
      const status = await response.json();
      setYoutubeStatus(status);
    } catch (error) {
      logger.error('Failed to check YouTube status:', error);
      setYoutubeStatus({ connected: false });
    }
  };

  const connectToYouTube = () => {
    // Open OAuth flow - use backend URL for authentication
    window.location.href = `${apiUrl}/auth/youtube`;
  };

  // Check for error parameter in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    
    if (error === 'youtube_not_configured') {
      alert('⚠️ YouTube integration not configured!\n\nThe developer needs to set up YouTube OAuth credentials.\nSee YouTube API setup documentation for instructions.');
      // Clear error from URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const disconnectYouTube = async () => {
    if (!confirm('Are you sure you want to disconnect from YouTube?')) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${apiUrl}/api/youtube/disconnect`, { method: 'DELETE' });
      const result = await response.json();
      
      if (result.success) {
        setYoutubeStatus({ connected: false });
        // Clear YouTube settings
        updateSettings({ 
          youtube: { 
            ...settings.youtube, 
            enabled: false 
          } 
        });
        logger.info('Successfully disconnected from YouTube');
      } else {
        alert('Failed to disconnect: ' + result.error);
      }
    } catch (error) {
      logger.error('Error disconnecting from YouTube:', error);
      alert('Network error while disconnecting');
    } finally {
      setLoading(false);
    }
  };

  const updateChannel = () => {
    updateSettings({ 
      youtube: { 
        ...settings.youtube, 
        channel: channelInput.trim() 
      } 
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Youtube className="w-5 h-5 text-red-500" />
          YouTube Integration
        </CardTitle>
        <CardDescription>
          Connect to your YouTube account to enable live chat TTS
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {!youtubeStatus?.connected ? (
          <div className="text-center space-y-4 py-8">
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Connect to YouTube</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Authorize Chat Yapper to read your YouTube live chat. This is secure and you can 
                revoke access at any time in your Google account settings.
              </p>
            </div>
            
            <Button 
              onClick={connectToYouTube} 
              size="lg"
              className="bg-red-600 hover:bg-red-700"
              disabled={loading}
            >
              <Youtube className="w-4 h-4 mr-2" />
              {loading ? 'Connecting...' : 'Connect to YouTube'}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Connected Status */}
            <div className="flex items-center justify-between p-4 rounded-lg border bg-emerald-800 text-white">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium">Connected to YouTube</p>
                  <p className="text-sm text-emerald-100">
                    {youtubeStatus.channel_name ? `Channel: ${youtubeStatus.channel_name}` : 'Connected successfully'}
                  </p>
                </div>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={disconnectYouTube}
                disabled={loading}
                className="border-red-500 text-red-400 hover:bg-red-600 hover:text-white"
              >
                {loading ? 'Disconnecting...' : 'Disconnect'}
              </Button>
            </div>

            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
              <div className="space-y-1">
                <Label htmlFor="youtube-enabled" className="text-base">Enable Live Chat TTS</Label>
                <p className="text-sm text-muted-foreground">
                  Start reading live chat messages from your YouTube streams
                </p>
              </div>
              <Switch
                id="youtube-enabled"
                checked={!!settings.youtube?.enabled}
                onCheckedChange={checked => updateSettings({ 
                  youtube: { 
                    ...settings.youtube, 
                    enabled: checked,
                    // Set the connected channel as the default
                    channel: checked && !settings.youtube?.channel ? youtubeStatus.channel_id : settings.youtube?.channel
                  } 
                })}
              />
            </div>

            {/* Channel/Stream Selection */}
            {settings.youtube?.enabled && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="youtube-channel">Video/Stream ID (optional)</Label>
                  <div className="flex gap-2">
                    <Input
                      id="youtube-channel"
                      placeholder="Enter video/stream ID or leave blank for auto-detect"
                      value={channelInput}
                      onChange={e => setChannelInput(e.target.value)}
                      onKeyPress={e => e.key === 'Enter' && updateChannel()}
                      className="flex-1"
                    />
                    <Button
                      onClick={updateChannel}
                      disabled={channelInput.trim() === (settings.youtube?.channel || '')}
                      size="sm"
                    >
                      Update
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Leave blank to automatically detect your current live stream. 
                    Or enter a specific video ID to monitor that stream's chat.
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

export default YouTubeIntegration
