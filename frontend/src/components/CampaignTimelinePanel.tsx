import { useEffect, useMemo, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

type CampaignState = 'ACTIVE' | 'CONTINUES' | 'RESOLVED'

interface CampaignTimelineEvent {
  type: 'CREATED' | 'ALERT_ADDED' | 'STATE_CHANGE' | 'RESOLVED'
  at: number
  alert_id?: string
  from?: CampaignState
  to?: CampaignState
}

interface CampaignTimelineItem {
  campaign_id: string
  entity_key: string
  state: CampaignState
  created_at: number
  last_alert_at: number
  resolved_at: number | null
  alert_count: number
  events: CampaignTimelineEvent[]
  provenance: string
}

const stateMeta: Record<CampaignState, { label: string; dot: string; line: string; badge: string }> = {
  ACTIVE: {
    label: 'Active',
    dot: 'bg-green-400',
    line: 'bg-green-500',
    badge: 'border-green-500/40 bg-green-500/10 text-green-300',
  },
  CONTINUES: {
    label: 'Continuing',
    dot: 'bg-amber-400',
    line: 'bg-amber-500',
    badge: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  },
  RESOLVED: {
    label: 'Resolved',
    dot: 'bg-gray-400',
    line: 'bg-gray-500',
    badge: 'border-gray-500/40 bg-gray-500/10 text-gray-300',
  },
}

function formatDate(epoch?: number | null) {
  if (!epoch) return 'unknown'
  return new Date(epoch * 1000).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function eventLabel(event: CampaignTimelineEvent) {
  if (event.type === 'CREATED') return 'Created'
  if (event.type === 'ALERT_ADDED') return '+Alert'
  if (event.type === 'RESOLVED') return 'Resolved'
  return event.to === 'CONTINUES' ? 'Continues' : event.to === 'RESOLVED' ? 'Resolved' : 'State'
}

function openAlertTriage() {
  window.dispatchEvent(new CustomEvent('vis2:navigate', {
    detail: { tab: 'triage' },
  }))
}

export default function CampaignTimelinePanel() {
  const [campaigns, setCampaigns] = useState<CampaignTimelineItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetch('/api/soc/campaign-timeline')
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json()
      })
      .then(data => {
        if (cancelled) return
        setCampaigns(Array.isArray(data) ? data.slice(0, 10) : [])
        setError(false)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const summary = useMemo(() => {
    return campaigns.reduce(
      (acc, campaign) => {
        if (campaign.state === 'ACTIVE') acc.active += 1
        else if (campaign.state === 'CONTINUES') acc.continuing += 1
        else if (campaign.state === 'RESOLVED') acc.resolved += 1
        return acc
      },
      { active: 0, continuing: 0, resolved: 0 },
    )
  }, [campaigns])

  const summaryProvenance = campaigns.some(c => c.provenance === 'sample')
    ? 'sample'
    : campaigns[0]?.provenance || 'learned'

  return (
    <section className="bg-soc-card rounded-lg border border-gray-800 p-5" data-testid="campaign-timeline-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">Campaign Timeline</h3>
          <p className="mt-1 text-xs text-gray-500">Lifecycle view of correlated alert campaigns.</p>
        </div>
        {!loading && !error && campaigns.length > 0 && (
          <ProvenanceBadge source={summaryProvenance} />
        )}
      </div>

      {loading && (
        <div className="mt-4 rounded border border-gray-800 bg-soc-bg px-4 py-3 text-xs text-gray-500">
          Loading campaign timeline...
        </div>
      )}

      {!loading && error && (
        <div className="mt-4 rounded border border-gray-800 bg-soc-bg px-4 py-3 text-xs text-gray-500">
          Campaign timeline unavailable.
        </div>
      )}

      {!loading && !error && campaigns.length === 0 && (
        <div className="mt-4 rounded border border-gray-800 bg-soc-bg px-4 py-3 text-xs text-gray-500">
          No campaigns detected. The graph is monitoring alerts for correlated campaign patterns.
        </div>
      )}

      {!loading && !error && campaigns.length > 0 && (
        <>
          <div className="mt-4 space-y-4">
            {campaigns.map(campaign => {
              const meta = stateMeta[campaign.state] || stateMeta.ACTIVE
              const events = (campaign.events || []).slice(0, 5)
              return (
                <button
                  key={campaign.campaign_id}
                  type="button"
                  onClick={openAlertTriage}
                  className="w-full rounded border border-gray-800 bg-soc-bg p-3 text-left hover:border-soc-secondary/50"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-gray-200">
                      {campaign.campaign_id}
                    </span>
                    <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${meta.badge}`}>
                      {meta.label}
                    </span>
                    <span className="text-xs text-gray-500">{campaign.alert_count} alerts</span>
                    <ProvenanceBadge source={campaign.provenance} className="ml-auto" />
                  </div>

                  <div className="mt-3 overflow-x-auto pb-1">
                    <div className="flex min-w-[520px] items-start">
                      {events.map((event, index) => (
                        <div key={`${campaign.campaign_id}-${event.type}-${event.at}-${index}`} className="flex flex-1 items-start">
                          <div className="flex flex-col items-center">
                            <span className={`h-3 w-3 rounded-full ${meta.dot}`} />
                            <span className="mt-1 text-[11px] font-medium text-gray-300">{eventLabel(event)}</span>
                            <span className="text-[10px] text-gray-600">{formatDate(event.at)}</span>
                          </div>
                          {index < events.length - 1 && (
                            <div className={`mx-2 mt-1.5 h-px flex-1 ${meta.line} ${campaign.state === 'CONTINUES' ? 'border-t border-dashed border-amber-400 bg-transparent' : ''}`} />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-2 truncate text-xs text-gray-500">
                    Entity: <span className="text-gray-400">{campaign.entity_key}</span>
                  </div>
                </button>
              )
            })}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3 rounded border border-gray-800 bg-gray-900/40 px-3 py-2 text-xs">
            <span className="text-green-300">Active: {summary.active}</span>
            <span className="text-gray-700">|</span>
            <span className="text-amber-300">Continuing: {summary.continuing}</span>
            <span className="text-gray-700">|</span>
            <span className="text-gray-300">Resolved: {summary.resolved}</span>
            <ProvenanceBadge source={summaryProvenance} className="ml-auto" />
          </div>
        </>
      )}
    </section>
  )
}
