import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { 
  Volume2, 
  VolumeX,
  Mic, 
  MicOff,
  Music,
  Waves,
  Zap,
  Youtube,
  Shield,
  ShieldX,
  Users,
  CheckCircle2,
  XCircle
} from 'lucide-react'

function QuickStatusView({ settings, allVoices }) {
  if (!settings) return null

  // Calculate status values
  const ttsEnabled = settings.ttsControl?.enabled !== false
  const volume = Math.round((settings.volume || 1.0) * 100)
  const audioFiltersEnabled = settings.audioFilters?.enabled || false
  const twitchEnabled = settings.twitch?.enabled || false
  const youtubeEnabled = settings.youtube?.enabled || false
  const filtersEnabled = settings.messageFiltering?.enabled ?? true
  
  // Count configured voices
  const voiceCount = allVoices?.length || 0

  const StatusItem = ({ icon: Icon, label, value, status, variant = 'secondary' }) => (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/10 border border-muted/20">
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${status ? 'text-green-500' : 'text-red-500'}`} />
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      </div>
      <Badge variant={variant} className="text-xs pointer-events-none">
        {value}
      </Badge>
    </div>
  )

  return (
    <Card className="w-full max-w-sm">
      <CardContent className="space-y-3 pt-6">
        <StatusItem
          icon={ttsEnabled ? Mic : MicOff}
          label="TTS"
          value={ttsEnabled ? 'Enabled' : 'Disabled'}
          status={ttsEnabled}
          variant={ttsEnabled ? 'default' : 'destructive'}
        />
        
        <StatusItem
          icon={volume > 0 ? Volume2 : VolumeX}
          label="Volume"
          value={`${volume}%`}
          status={volume > 0}
          variant={volume > 0 ? 'default' : 'secondary'}
        />
        
        <StatusItem
          icon={Users}
          label="Voices"
          value={`${voiceCount} configured`}
          status={voiceCount > 0}
          variant={voiceCount > 0 ? 'default' : 'secondary'}
        />
        
        <StatusItem
          icon={audioFiltersEnabled ? Music : Waves}
          label="Effects"
          value={audioFiltersEnabled ? 'Enabled' : 'Disabled'}
          status={audioFiltersEnabled}
          variant={audioFiltersEnabled ? 'default' : 'secondary'}
        />
        
        <StatusItem
          icon={Zap}
          label="Twitch"
          value={twitchEnabled ? 'Enabled' : 'Disabled'}
          status={twitchEnabled}
          variant={twitchEnabled ? 'default' : 'secondary'}
        />
        
        <StatusItem
          icon={Youtube}
          label="YouTube"
          value={youtubeEnabled ? 'Enabled' : 'Disabled'}
          status={youtubeEnabled}
          variant={youtubeEnabled ? 'default' : 'secondary'}
        />
        
        <StatusItem
          icon={filtersEnabled ? Shield : ShieldX}
          label="Filters"
          value={filtersEnabled ? 'Active' : 'Inactive'}
          status={filtersEnabled}
          variant={filtersEnabled ? 'default' : 'secondary'}
        />
      </CardContent>
    </Card>
  )
}

export default QuickStatusView