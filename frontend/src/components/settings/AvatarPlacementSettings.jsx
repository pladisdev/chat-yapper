import React from 'react'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Switch } from '../ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { LayoutGrid } from 'lucide-react'

function AvatarPlacementSettings({ settings, updateSettings, apiUrl }) {
  const avatarMode = settings.avatarMode || 'grid'
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <LayoutGrid className="w-5 h-5" />
          Avatar Display Mode
        </CardTitle>
        <CardDescription>
          Choose how avatars appear and configure mode-specific settings
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <Label>Display Mode</Label>
          <div className="flex gap-2 mt-2">
            <Button
              variant={avatarMode === 'grid' ? 'default' : 'outline'}
              onClick={() => updateSettings({ avatarMode: 'grid' })}
              className="flex-1"
            >
              Crowd Mode
            </Button>
            <Button
              variant={avatarMode === 'popup' ? 'default' : 'outline'}
              onClick={() => updateSettings({ avatarMode: 'popup' })}
              className="flex-1"
            >
              Pop-up Mode
            </Button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {avatarMode === 'grid' 
              ? 'Avatars appear in fixed positions on screen with individual size control' 
              : 'Avatars pop up individually when speaking'}
          </p>
        </div>

        {avatarMode === 'popup' && (
          <div className="space-y-4 pt-4 border-t">
            <h4 className="font-medium">Pop-up Mode Settings</h4>
            
            <div className="space-y-2">
              <Label htmlFor="avatarSize">Avatar Size (px)</Label>
              <Input
                id="avatarSize"
                type="number"
                min="20"
                max="200"
                value={settings.avatarSize || 100}
                onChange={e => updateSettings({ avatarSize: parseInt(e.target.value) || 100 })}
              />
              <p className="text-sm text-muted-foreground">
                Size for pop-up avatars
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="popupDirection">Popup Direction</Label>
              <select
                id="popupDirection"
                value={settings.popupDirection || 'bottom'}
                onChange={e => updateSettings({ popupDirection: e.target.value })}
                className="w-full h-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="bottom">Bottom</option>
                <option value="top">Top</option>
                <option value="left">Left</option>
                <option value="right">Right</option>
              </select>
              <p className="text-sm text-muted-foreground">
                Direction from which avatars will appear
              </p>
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="popupFixedEdge">Spawn at Border</Label>
                <p className="text-sm text-muted-foreground">
                  Should the avatar appear at the edge or at a random position
                </p>
              </div>
              <Switch
                id="popupFixedEdge"
                checked={settings.popupFixedEdge || false}
                onCheckedChange={checked => updateSettings({ popupFixedEdge: checked })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="popupRotateToDirection">Rotate to Match Direction</Label>
                <p className="text-sm text-muted-foreground">
                  Rotate avatars to face the direction they're coming from
                </p>
              </div>
              <Switch
                id="popupRotateToDirection"
                checked={settings.popupRotateToDirection || false}
                onCheckedChange={checked => updateSettings({ popupRotateToDirection: checked })}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AvatarPlacementSettings
