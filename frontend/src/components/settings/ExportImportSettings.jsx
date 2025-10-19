import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Label } from '../ui/label'
import { 
  Download, 
  Upload, 
  Database, 
  AlertCircle, 
  CheckCircle2,
  Info,
  HardDrive,
  Trash2,
  AlertTriangle
} from 'lucide-react'

export default function ExportImportSettings({ apiUrl = '' }) {
  const [configInfo, setConfigInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Load config info on mount
  useEffect(() => {
    loadConfigInfo()
  }, [])

  const loadConfigInfo = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/config/info`)
      const data = await response.json()
      if (data.success) {
        setConfigInfo(data.info)
      }
    } catch (err) {
      console.error('Failed to load config info:', err)
    }
  }

  const handleExport = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${apiUrl}/api/config/export`)
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`)
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = 'chatyapper_config.zip'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?(.+)"?/)
        if (match) filename = match[1]
      }

      // Download the file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setResult({
        type: 'success',
        message: `Configuration exported successfully: ${filename}`,
        details: `File size: ${(blob.size / 1024 / 1024).toFixed(2)} MB`
      })
    } catch (err) {
      console.error('Export error:', err)
      setError(`Export failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleImportFile = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setImporting(true)
    setError(null)
    setResult(null)

    try {
      // Validate file type
      if (!file.name.endsWith('.zip')) {
        throw new Error('Please select a ZIP file')
      }

      // Create FormData
      const formData = new FormData()
      formData.append('file', file)
      formData.append('merge_mode', 'replace')

      // Upload
      const response = await fetch(`${apiUrl}/api/config/import`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Import failed')
      }

      if (data.success) {
        setResult({
          type: 'success',
          message: 'Configuration imported successfully!',
          details: `Settings: ${data.stats.settings_imported ? '✓' : '✗'} | ` +
                  `Voices: ${data.stats.voices_imported} | ` +
                  `Avatars: ${data.stats.avatars_imported} | ` +
                  `Images: ${data.stats.images_copied}`,
          errors: data.stats.errors
        })
        
        // Reload config info
        setTimeout(() => loadConfigInfo(), 1000)
        
        // Show reload prompt
        setTimeout(() => {
          if (confirm('Configuration imported! Reload the page to apply changes?')) {
            window.location.reload()
          }
        }, 2000)
      }
    } catch (err) {
      console.error('Import error:', err)
      setError(`Import failed: ${err.message}`)
    } finally {
      setImporting(false)
      // Reset file input
      event.target.value = ''
    }
  }

  const handleFactoryReset = async () => {
    setResetting(true)
    setError(null)
    setResult(null)
    setShowResetConfirm(false)

    try {
      const response = await fetch(`${apiUrl}/api/config/reset`, {
        method: 'POST'
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Factory reset failed')
      }

      if (data.success) {
        setResult({
          type: 'success',
          message: 'Factory reset completed successfully!',
          details: `Settings: ${data.stats.settings_deleted} | ` +
                  `Voices: ${data.stats.voices_deleted} | ` +
                  `Avatars: ${data.stats.avatars_deleted} | ` +
                  `Files: ${data.stats.files_deleted}`,
        })
        
        // Clear config info
        setConfigInfo(null)
        
        // Show reload prompt
        setTimeout(() => {
          if (confirm('Factory reset complete! The page will now reload to apply changes.')) {
            window.location.reload()
          }
        }, 2000)
      }
    } catch (err) {
      console.error('Factory reset error:', err)
      setError(`Factory reset failed: ${err.message}`)
    } finally {
      setResetting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Export / Import Configuration
        </CardTitle>
        <CardDescription>
          Backup or restore your complete Chat Yapper configuration including settings, voices, and avatars
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        
        {/* Current Configuration Info */}
        {configInfo && (
          <div className="p-4 rounded-lg border bg-muted/30">
            <div className="flex items-center gap-2 mb-3">
              <HardDrive className="h-4 w-4" />
              <span className="text-sm font-medium">Current Configuration</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">Voices:</span>
                <span className="ml-2 font-medium">{configInfo.voices_count}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Avatars:</span>
                <span className="ml-2 font-medium">{configInfo.avatars_count}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Settings:</span>
                <span className="ml-2 font-medium">{configInfo.settings_count} items</span>
              </div>
              <div>
                <span className="text-muted-foreground">Storage:</span>
                <span className="ml-2 font-medium">{configInfo.avatar_storage_mb} MB</span>
              </div>
            </div>
          </div>
        )}

        {/* Export Section */}
        <div className="space-y-3">
          <div>
            <Label className="text-base font-medium">Export Configuration</Label>
            <p className="text-sm text-muted-foreground mt-1">
              Download a complete backup of your settings, voices, and avatar images as a ZIP file
            </p>
          </div>
          
          <Button
            onClick={handleExport}
            disabled={loading}
            className="w-full"
            variant="default"
          >
            {loading ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full mr-2"></div>
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export Configuration
              </>
            )}
          </Button>
        </div>

        {/* Import Section */}
        <div className="space-y-3">
          <div>
            <Label className="text-base font-medium">Import Configuration</Label>
            <p className="text-sm text-muted-foreground mt-1">
              Restore a previously exported configuration. This will replace your current settings.
            </p>
          </div>

          <div className="border-2 border-dashed rounded-lg p-4 hover:border-primary transition-colors">
            <label className="flex flex-col items-center gap-2 cursor-pointer">
              <input
                type="file"
                accept=".zip"
                onChange={handleImportFile}
                disabled={importing}
                className="hidden"
              />
              <div className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                <span className="font-medium">
                  {importing ? 'Importing...' : 'Click to select ZIP file'}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                Choose a previously exported configuration file
              </span>
              {importing && (
                <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full mt-2"></div>
              )}
            </label>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-border"></div>

        {/* Factory Reset Section */}
        <div className="space-y-3">
          <div>
            <Label className="text-base font-medium text-red-600 dark:text-red-400">Factory Reset</Label>
            <p className="text-sm text-muted-foreground mt-1">
              Delete all settings, voices, avatars, and data. This will reset the application to its default state.
            </p>
          </div>

          {!showResetConfirm ? (
            <Button
              onClick={() => setShowResetConfirm(true)}
              disabled={resetting}
              className="w-full"
              variant="destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Factory Reset
            </Button>
          ) : (
            <div className="space-y-3 p-4 border-2 border-red-500 rounded-lg bg-red-500/5">
              <div className="flex gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm flex-1">
                  <p className="font-bold text-red-600 dark:text-red-400 mb-2">⚠️ WARNING: This action cannot be undone!</p>
                  <p className="text-muted-foreground mb-2">
                    This will permanently delete:
                  </p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1 mb-3">
                    <li>All settings and preferences</li>
                    <li>All configured TTS voices</li>
                    <li>All avatar configurations</li>
                    <li>All uploaded avatar images</li>
                    <li>All authentication tokens</li>
                  </ul>
                  <p className="text-muted-foreground text-xs">
                    A backup will be created automatically before resetting.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleFactoryReset}
                  disabled={resetting}
                  className="flex-1"
                  variant="destructive"
                >
                  {resetting ? (
                    <>
                      <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full mr-2"></div>
                      Resetting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="h-4 w-4 mr-2" />
                      Yes, Delete Everything
                    </>
                  )}
                </Button>
                <Button
                  onClick={() => setShowResetConfirm(false)}
                  disabled={resetting}
                  className="flex-1"
                  variant="outline"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Warning */}
        <div className="flex gap-3 p-4 rounded-lg border border-yellow-500/50 bg-yellow-500/10">
          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <strong>Important:</strong> Importing will create a backup of your current database before making changes. 
            If import fails, the backup will be automatically restored.
          </div>
        </div>

        {/* Info */}
        <div className="flex gap-3 p-4 rounded-lg border border-blue-500/50 bg-blue-500/10">
          <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <strong>What's included:</strong> All settings, TTS voices, avatar configurations, and uploaded avatar images.
            Built-in avatars are not included (they're part of the application).
          </div>
        </div>

        {/* Success Result */}
        {result && result.type === 'success' && (
          <div className="flex gap-3 p-4 rounded-lg border border-green-500 bg-green-500/10">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-green-700 dark:text-green-400">{result.message}</div>
              {result.details && (
                <div className="text-sm text-muted-foreground mt-1">{result.details}</div>
              )}
              {result.errors && result.errors.length > 0 && (
                <div className="mt-2 text-sm">
                  <div className="font-medium text-yellow-600 dark:text-yellow-400">Warnings:</div>
                  <ul className="list-disc list-inside text-muted-foreground">
                    {result.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error Result */}
        {error && (
          <div className="flex gap-3 p-4 rounded-lg border border-red-500 bg-red-500/10">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-700 dark:text-red-400">{error}</div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
