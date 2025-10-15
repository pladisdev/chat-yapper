import React from 'react'
import TTSProviderTabs from './TTSProviderTabs'

function TTSConfiguration({ settings, updateSettings, apiUrl = '' }) {
  return (
    <div className="space-y-6">
      <TTSProviderTabs settings={settings} updateSettings={updateSettings} apiUrl={apiUrl} />
    </div>
  )
}

export default TTSConfiguration