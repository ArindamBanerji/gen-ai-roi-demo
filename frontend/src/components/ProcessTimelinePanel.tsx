import { useEffect, useState } from 'react'
import CelonisBadge from './CelonisBadge'
import SAPDataBadge from './SAPDataBadge'
import { ensureArray, ensureObject, ensureString } from '../lib/guards'

interface TimelineRow { stage?: string; detail?: string; source?: string }
interface TimelinePayload { sources?: unknown; timeline?: unknown }

export default function ProcessTimelinePanel() {
  const [payload, setPayload] = useState<TimelinePayload | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch('/api/enterprise/process-timeline')
      .then((response) => {
        if (!response.ok) throw new Error('enterprise process endpoint unavailable')
        return response.json() as Promise<unknown>
      })
      .then((value) => { if (!cancelled) setPayload(ensureObject<Record<string, unknown>>(value) as TimelinePayload) })
      .catch(() => { if (!cancelled) setError(true) })
    return () => { cancelled = true }
  }, [])

  const sources = ensureArray<Record<string, unknown>>(payload?.sources)
  const timeline = ensureArray<TimelineRow>(payload?.timeline)
  const sap = sources.find((source) => source.source === 'sap_s4hana')
  const celonis = sources.find((source) => source.source === 'celonis')

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Enterprise process timeline">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">Enterprise connectors</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">SAP + Celonis process timeline</h3>
        </div>
        <div className="flex gap-2"><SAPDataBadge mode={ensureString(sap?.mode, 'fixture')} /><CelonisBadge mode={ensureString(celonis?.mode, 'fixture')} /></div>
      </div>
      {error ? <p className="mt-4 text-sm text-red-300">Enterprise process data unavailable</p> : (
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {timeline.map((row, index) => (
            <div key={`${ensureString(row.stage, 'stage')}-${index}`} className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs uppercase tracking-wide text-gray-500">{ensureString(row.stage, 'Unavailable')}</div>
              <div className="mt-2 text-sm text-gray-100">{ensureString(row.detail, 'Unavailable')}</div>
              <div className="mt-2 text-xs text-gray-500">{ensureString(row.source, 'Unavailable')}</div>
            </div>
          ))}
        </div>
      )}
      <p className="mt-4 text-xs text-gray-500">Live API proof is used when credentials are configured; cached demo data keeps the narrative responsive.</p>
    </section>
  )
}
