import { useEffect, useMemo, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'
// Provenance: default "context" - cross-graph returns provenance today.
// Override: uses data.provenance if S2P backend adds it.
const DEFAULT_TIER = 'context'

type Payload = Record<string, unknown>

const stages = ['WHERE', 'WHY', 'WHAT', 'LEARN', 'TRANSFER']

function label(value: unknown): string {
  if (typeof value !== 'string' || value.length === 0) return 'Unavailable'
  return value.split('_').filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}

export default function ProcessFusionPanel() {
  const [signals, setSignals] = useState<Payload | null>(null)
  const [crossGraph, setCrossGraph] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const [signalsResponse, crossGraphResponse] = await Promise.all([
          fetch(`${S2P_API}/api/s2p/insight/process-signals`),
          fetch(`${S2P_API}/api/s2p/insight/cross-graph`),
        ])
        if (!signalsResponse.ok || !crossGraphResponse.ok) throw new Error('process endpoint unavailable')
        const [signalsPayload, crossGraphPayload] = await Promise.all([
          signalsResponse.json() as Promise<Payload>,
          crossGraphResponse.json() as Promise<Payload>,
        ])
        if (!cancelled) {
          setSignals(signalsPayload)
          setCrossGraph(crossGraphPayload)
        }
      } catch {
        if (!cancelled) {
          setSignals(null)
          setCrossGraph(null)
          setError(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const currentStage = useMemo(() => {
    const raw = String(crossGraph?.cycle_state ?? signals?.cycle_state ?? signals?.current_stage ?? '').toUpperCase()
    return stages.find((stage) => raw.includes(stage)) ?? 'WHERE'
  }, [signals, crossGraph])
  const provenance =
    (typeof crossGraph?.provenance === 'string' && crossGraph.provenance) ||
    (typeof signals?.provenance === 'string' && signals.provenance) ||
    (typeof signals?.source === 'string' && signals.source) ||
    DEFAULT_TIER

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Process Fusion">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Process fusion</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Process-tech learning cycle</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F18</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading process signals...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && (
        <>
          <div className="mt-5 grid gap-2 md:grid-cols-5">
            {stages.map((stage) => (
              <div key={stage} className={`rounded border p-3 text-center text-xs font-semibold ${stage === currentStage ? 'border-green-500/40 bg-green-500/10 text-green-200' : 'border-gray-800 bg-slate-950/60 text-gray-400'}`}>
                {stage}
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Current stage</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-xl text-gray-100">
                <span>{currentStage}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Bottleneck activity</div>
              <div className="mt-2 flex items-center gap-2 text-sm text-gray-100">
                <span>{label(crossGraph?.bottleneck_activity ?? signals?.bottleneck_activity)}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-300">
            {typeof crossGraph?.narrative === 'string' ? crossGraph.narrative : 'Process signals connected to exception resolution and supplier learning.'}
          </p>
        </>
      )}
    </section>
  )
}
