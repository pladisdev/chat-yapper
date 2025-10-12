import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Button } from '../ui/button'
import { Checkbox } from '../ui/checkbox'
import { Separator } from '../ui/separator'
import { 
  MessageSquare, 
  TestTube2,
  CheckCircle2,
  XCircle
} from 'lucide-react'

function MessageFilterTester({ apiUrl }) {
  const [testMessage, setTestMessage] = useState('')
  const [testUsername, setTestUsername] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const testFilter = async () => {
    if (!testMessage.trim()) return
    
    setTesting(true)
    try {
      const response = await fetch(`${apiUrl}/api/message-filter/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: testMessage,
          username: testUsername 
        })
      })
      const result = await response.json()
      setTestResult(result)
    } catch (error) {
      setTestResult({ success: false, error: error.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <Input
          placeholder="Username (optional)"
          value={testUsername}
          onChange={e => setTestUsername(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && testFilter()}
        />
        <Input
          placeholder="Enter a test message..."
          className="md:col-span-2"
          value={testMessage}
          onChange={e => setTestMessage(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && testFilter()}
        />
      </div>
      <Button
        onClick={testFilter}
        disabled={testing || !testMessage.trim()}
        className="w-full"
      >
        {testing ? 'Testing...' : 'Test Message Filter'}
      </Button>
      
      {testResult && (
        <div className={`p-3 rounded-lg border text-sm ${
          testResult.success 
            ? testResult.should_process 
              ? 'bg-green-500/10 border-green-500/50' 
              : 'bg-yellow-500/10 border-yellow-500/50'
            : 'bg-destructive/10 border-destructive/50'
        }`}>
          {testResult.success ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                {testResult.should_process ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {testResult.should_process ? 'Message will be processed' : 'Message will be filtered out'}
              </div>
              
              {testResult.was_modified && (
                <div className="space-y-1 text-xs">
                  <p>Original: "{testResult.original_message}"</p>
                  <p>Filtered: "{testResult.filtered_message}"</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4" />
              Error: {testResult.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function IgnoredUsersManager({ ignoredUsers, onUpdate }) {
  const [newUser, setNewUser] = useState('')

  const addUser = () => {
    const username = newUser.trim()
    if (!username) return
    
    if (ignoredUsers.some(user => user.toLowerCase() === username.toLowerCase())) {
      alert('User is already in the ignored list')
      return
    }
    
    onUpdate([...ignoredUsers, username])
    setNewUser('')
  }

  const removeUser = (userToRemove) => {
    onUpdate(ignoredUsers.filter(user => user !== userToRemove))
  }

  const clearAllUsers = () => {
    if (ignoredUsers.length === 0) return
    if (confirm(`Are you sure you want to remove all ${ignoredUsers.length} ignored users?`)) {
      onUpdate([])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="Enter username to ignore..."
          value={newUser}
          onChange={e => setNewUser(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && addUser()}
        />
        <Button
          onClick={addUser}
          disabled={!newUser.trim()}
        >
          Add
        </Button>
      </div>

      {ignoredUsers.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">
              Ignored Users ({ignoredUsers.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllUsers}
              className="h-auto py-1 px-2 text-xs text-destructive hover:text-destructive"
            >
              Clear All
            </Button>
          </div>
          
          <div className="max-h-32 overflow-y-auto space-y-1">
            {ignoredUsers.map((user, index) => (
              <div key={index} className="flex items-center justify-between p-2 rounded-lg border bg-card">
                <span className="text-sm font-mono">{user}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeUser(user)}
                  className="h-auto py-1 px-2 text-destructive hover:text-destructive"
                  title={`Remove ${user}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {ignoredUsers.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No users ignored yet
        </p>
      )}
    </div>
  )
}

function ProfanityWordsManager({ words, onUpdate }) {
  const [newWord, setNewWord] = useState('')

  const addWord = () => {
    const word = newWord.trim().toLowerCase()
    if (!word) return
    
    if (words.some(w => w.toLowerCase() === word)) {
      alert('This word is already in the filter list')
      return
    }
    
    onUpdate([...words, word])
    setNewWord('')
  }

  const removeWord = (wordToRemove) => {
    onUpdate(words.filter(w => w !== wordToRemove))
  }

  const clearAllWords = () => {
    if (words.length === 0) return
    if (confirm(`Are you sure you want to remove all ${words.length} filtered words?`)) {
      onUpdate([])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="Enter word to filter..."
          value={newWord}
          onChange={e => setNewWord(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && addWord()}
        />
        <Button
          onClick={addWord}
          disabled={!newWord.trim()}
        >
          Add
        </Button>
      </div>

      {words.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">
              Filtered Words ({words.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllWords}
              className="h-auto py-1 px-2 text-xs text-destructive hover:text-destructive"
            >
              Clear All
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            {words.map((word, index) => (
              <div 
                key={index}
                className="flex items-center gap-1 px-2 py-1 bg-muted rounded text-xs"
              >
                <span>{word}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeWord(word)}
                  className="h-auto py-0 px-1 text-destructive hover:text-destructive"
                  title={`Remove ${word}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {words.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No words filtered yet. Add words to block from messages.
        </p>
      )}
    </div>
  )
}

function MessageFiltering({ settings, updateSettings, apiUrl }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Message Filtering
        </CardTitle>
        <CardDescription>Control which messages get processed for TTS</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
          <div className="space-y-1">
            <Label htmlFor="filtering-enabled" className="text-base">Enable Message Filtering</Label>
            <p className="text-sm text-muted-foreground">Filter messages before TTS processing</p>
          </div>
          <Switch
            id="filtering-enabled"
            checked={settings.messageFiltering?.enabled ?? true}
            onCheckedChange={checked => updateSettings({ 
              messageFiltering: { 
                ...settings.messageFiltering, 
                enabled: checked 
              } 
            })}
          />
        </div>

        {(settings.messageFiltering?.enabled !== false) && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="minLength">Minimum Length</Label>
                <Input
                  id="minLength"
                  type="number"
                  min="1"
                  max="100"
                  value={settings.messageFiltering?.minLength ?? 1}
                  onChange={e => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      minLength: parseInt(e.target.value) || 1 
                    } 
                  })}
                />
                <p className="text-xs text-muted-foreground">Messages shorter than this will be skipped</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="maxLength">Maximum Length</Label>
                <Input
                  id="maxLength"
                  type="number"
                  min="10"
                  max="2000"
                  value={settings.messageFiltering?.maxLength ?? 500}
                  onChange={e => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      maxLength: parseInt(e.target.value) || 500 
                    } 
                  })}
                />
                <p className="text-xs text-muted-foreground">Messages longer than this will be truncated</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="skipCommands"
                  checked={settings.messageFiltering?.skipCommands ?? true}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      skipCommands: checked 
                    } 
                  })}
                />
                <Label htmlFor="skipCommands" className="text-sm font-normal">
                  Skip Commands - Messages starting with ! or / (bot commands)
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="skipEmotes"
                  checked={settings.messageFiltering?.skipEmotes ?? false}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      skipEmotes: checked 
                    } 
                  })}
                />
                <Label htmlFor="skipEmotes" className="text-sm font-normal">
                  Skip Emote-Only Messages (experimental)
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="removeUrls"
                  checked={settings.messageFiltering?.removeUrls ?? true}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      removeUrls: checked 
                    } 
                  })}
                />
                <Label htmlFor="removeUrls" className="text-sm font-normal">
                  Remove URLs from messages before TTS processing
                </Label>
              </div>


            </div>

            <Separator />

            <div className="space-y-6">
              <h4 className="font-medium flex items-center gap-2 text-lg">
                <span>⏱️</span>
                Rate Limiting & Message Control
              </h4>
              
              <div className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Checkbox
                      id="enableSpamFilter"
                      checked={settings.messageFiltering?.enableSpamFilter ?? true}
                      onCheckedChange={checked => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          enableSpamFilter: checked 
                        } 
                      })}
                    />
                    <div className="space-y-1 flex-1">
                      <Label htmlFor="enableSpamFilter" className="text-base font-medium">
                        🚫 Rate Limit Users
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Prevent users from sending too many messages in a short time period. New messages from rate-limited users are completely ignored.
                      </p>
                    </div>
                  </div>

                  {settings.messageFiltering?.enableSpamFilter !== false && (
                    <div className="ml-6 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="spamThreshold">Max Messages</Label>
                          <Input
                            id="spamThreshold"
                            type="number"
                            min="2"
                            max="20"
                            value={settings.messageFiltering?.spamThreshold ?? 5}
                            onChange={e => updateSettings({ 
                              messageFiltering: { 
                                ...settings.messageFiltering, 
                                spamThreshold: parseInt(e.target.value) || 5 
                              } 
                            })}
                          />
                          <p className="text-xs text-muted-foreground">Maximum messages allowed</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="spamTimeWindow">Time Window (seconds)</Label>
                          <Input
                            id="spamTimeWindow"
                            type="number"
                            min="5"
                            max="60"
                            value={settings.messageFiltering?.spamTimeWindow ?? 10}
                            onChange={e => updateSettings({ 
                              messageFiltering: { 
                                ...settings.messageFiltering, 
                                spamTimeWindow: parseInt(e.target.value) || 10 
                              } 
                            })}
                          />
                          <p className="text-xs text-muted-foreground">Within this many seconds</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="ignoreIfUserSpeaking"
                      checked={settings.messageFiltering?.ignoreIfUserSpeaking ?? true}
                      onCheckedChange={checked => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          ignoreIfUserSpeaking: checked 
                        } 
                      })}
                    />
                    <div className="space-y-1">
                      <Label htmlFor="ignoreIfUserSpeaking" className="text-base font-medium">
                        🔊 Ignore New Messages from Speaking User
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        When a user's message is currently playing TTS, ignore any new messages from that same user until the current message finishes. This prevents interrupting or queueing multiple messages from one person.
                      </p>
                    </div>
                  </div>
                </div>
              </div>


            </div>

            <Separator />

            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <span>🤬</span>
                Profanity Filter
              </h4>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="profanityFilterEnabled"
                  checked={settings.messageFiltering?.profanityFilter?.enabled ?? false}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      profanityFilter: {
                        ...settings.messageFiltering?.profanityFilter,
                        enabled: checked
                      }
                    } 
                  })}
                />
                <Label htmlFor="profanityFilterEnabled" className="text-sm font-normal">
                  Enable Profanity Filter
                </Label>
              </div>

              {settings.messageFiltering?.profanityFilter?.enabled && (
                <div className="space-y-4 pl-6 border-l-2">
                  <div className="space-y-2">
                    <Label htmlFor="replacementText">Replacement Text</Label>
                    <Input
                      id="replacementText"
                      value={settings.messageFiltering?.profanityFilter?.replacement ?? 'beep'}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          profanityFilter: {
                            ...settings.messageFiltering?.profanityFilter,
                            replacement: e.target.value
                          }
                        } 
                      })}
                      placeholder="beep"
                    />
                    <p className="text-xs text-muted-foreground">Text to replace filtered words with</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Custom Words to Filter</Label>
                    <ProfanityWordsManager 
                      words={settings.messageFiltering?.profanityFilter?.customWords || []}
                      onUpdate={(words) => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          profanityFilter: {
                            ...settings.messageFiltering?.profanityFilter,
                            customWords: words
                          }
                        } 
                      })}
                    />
                  </div>
                </div>
              )}
            </div>

            <Separator />

            <div className="space-y-3">
              <h4 className="font-medium">Ignored Users</h4>
              <IgnoredUsersManager 
                ignoredUsers={settings.messageFiltering?.ignoredUsers || []}
                onUpdate={(users) => updateSettings({ 
                  messageFiltering: { 
                    ...settings.messageFiltering, 
                    ignoredUsers: users 
                  } 
                })}
              />
            </div>

            <div className="p-4 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <TestTube2 className="w-4 h-4" />
                Test Message Filter
              </h4>
              <MessageFilterTester apiUrl={apiUrl} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Export helper components for flexibility and main component as default
export { MessageFilterTester, IgnoredUsersManager, ProfanityWordsManager }
export default MessageFiltering