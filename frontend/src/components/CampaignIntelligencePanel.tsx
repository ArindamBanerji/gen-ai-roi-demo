import { useState, useEffect } from 'react'

interface Campaign {
  campaign_id: string
  first_seen: string
  last_seen: string
  alert_count: number
  category_sequence: string[]
  shared_entities: string[]
  confidence: number
  trigger_rule: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  nl_summary: string
}

const CampaignIntelligencePanel: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [activeCampaigns, setActiveCampaigns] = useState(0)

  useEffect(() => {
    fetch('/api/soc/campaigns')
      .then(r => r.json())
      .then(data => {
        setCampaigns(data.campaigns || [])
        setActiveCampaigns(data.active_campaigns || 0)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const severityColor: Record<string, string> = {
    HIGH: '#dc2626',
    MEDIUM: '#d97706',
    LOW: '#2563eb',
  }

  const formatChain = (cats: string[] | string) => {
    const parsed = typeof cats === 'string'
      ? (() => { try { return JSON.parse(cats) } catch { return [] } })()
      : Array.isArray(cats) ? cats : []
    return parsed.map((c: string) => c.replace(/_/g, ' ')).join(' \u2192 ')
  }

  if (loading) return <div className="text-gray-500 text-xs px-4 py-2">Loading campaigns...</div>

  return (
    <div className="campaign-intelligence-panel mt-6 bg-soc-card rounded-xl border border-gray-800 p-5">
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-sm font-semibold text-gray-200">Campaign Intelligence</h3>
        {activeCampaigns > 0 && (
          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-900 text-red-300 border border-red-700">
            {activeCampaigns} active
          </span>
        )}
        <span className="ml-auto text-xs text-gray-600">F6 · multi-alert correlation</span>
      </div>

      {campaigns.length === 0 ? (
        <div className="text-xs text-gray-500 italic">
          No active campaigns detected. Alerts are being monitored for attack chain patterns.
        </div>
      ) : (
        <div className="space-y-3">
          {campaigns.map(c => (
            <div key={c.campaign_id} className="rounded-lg border border-gray-700 bg-gray-900 p-3">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-xs font-bold"
                  style={{ color: severityColor[c.severity] ?? '#9ca3af' }}
                >
                  ⚠ {c.severity}
                </span>
                <span className="text-xs text-gray-400">{c.alert_count} alerts</span>
                <span className="ml-auto text-xs text-gray-600">
                  {Math.round(c.confidence * 100)}% confidence
                </span>
              </div>

              {Array.isArray(c.category_sequence) && c.category_sequence.length > 0 && (
                <div className="text-xs text-indigo-300 font-mono mb-1">
                  {formatChain(c.category_sequence)}
                </div>
              )}

              {Array.isArray(c.shared_entities) && c.shared_entities.length > 0 && (
                <div className="text-xs text-gray-500">
                  shared: <span className="text-gray-400">{c.shared_entities[0]}</span>
                </div>
              )}

              {c.nl_summary && (
                <div className="text-xs text-gray-500 mt-1 italic">{c.nl_summary}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default CampaignIntelligencePanel
