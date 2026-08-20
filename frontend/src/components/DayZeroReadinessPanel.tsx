import { useEffect, useState } from 'react'
import { getEnrichmentSummary, fetchGraphSummary, fetchLearningHealth, getProfileState } from '../lib/api'

type RecordValue = Record<string, any>
type Readiness = { source: RecordValue | null; graph: RecordValue | null; learning: RecordValue | null; profile: RecordValue | null }

const status = (value: unknown) => value === undefined || value === null ? 'Unavailable' : typeof value === 'boolean' ? (value ? 'Ready' : 'Needs attention') : String(value)

export default function DayZeroReadinessPanel() {
  const [data, setData] = useState<Readiness>({ source: null, graph: null, learning: null, profile: null })
  useEffect(() => {
    void Promise.allSettled([getEnrichmentSummary(), fetchGraphSummary(), fetchLearningHealth(), getProfileState()]).then((results) => {
      const value = (index: number) => results[index]?.status === 'fulfilled' && typeof results[index].value === 'object' && results[index].value !== null ? results[index].value as RecordValue : null
      setData({ source: value(0), graph: value(1), learning: value(2), profile: value(3) })
    })
  }, [])

  const connectorHealth = data.source?.connector_health ?? data.source?.connectors ?? data.profile?.connectors
  const connectors = connectorHealth && typeof connectorHealth === 'object' ? Object.entries(connectorHealth as Record<string, unknown>) : []
  return <section className="rounded-xl border border-slate-600 bg-slate-950/80 p-5" data-testid="day-zero-readiness-panel" aria-label="Day-zero readiness">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">SOC-DAY0 · fresh tenant readiness</p><h2 className="mt-1 text-xl font-semibold text-white">Day-zero readiness</h2></div><span className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-300">no fabricated ROI</span></div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><div className="rounded-lg border border-slate-800 bg-slate-900 p-3"><p className="text-xs text-slate-500">Source coverage</p><p className="mt-1 text-lg text-slate-200">{status(data.source?.source_coverage ?? data.source?.coverage)}</p></div><div className="rounded-lg border border-slate-800 bg-slate-900 p-3"><p className="text-xs text-slate-500">Completeness</p><p className="mt-1 text-lg text-slate-200">{status(data.graph?.completeness ?? data.source?.completeness)}</p></div><div className="rounded-lg border border-slate-800 bg-slate-900 p-3"><p className="text-xs text-slate-500">Provenance</p><p className="mt-1 text-lg text-slate-200">{status(data.source?.provenance ?? data.graph?.provenance)}</p></div><div className="rounded-lg border border-slate-800 bg-slate-900 p-3"><p className="text-xs text-slate-500">Learning state</p><p className="mt-1 text-lg text-slate-200">{status(data.learning?.status ?? data.learning?.phase)}</p></div></div>
    <div className="mt-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Connector health</p>{connectors.length > 0 ? <div className="mt-2 grid gap-2 sm:grid-cols-3">{connectors.map(([name, value]) => <div key={name} className="rounded border border-slate-800 bg-slate-900 p-3 text-sm text-slate-300"><span>{name.replace(/_/g, ' ')}</span><span className="ml-2 text-slate-500">{status(value)}</span></div>)}</div> : <p className="mt-2 text-sm text-slate-500">Connector health is unavailable for this tenant.</p>}</div>
    <p className="mt-4 text-xs text-slate-500">Readiness is descriptive only; learned factor-trust weights and ROI are intentionally excluded.</p>
  </section>
}
