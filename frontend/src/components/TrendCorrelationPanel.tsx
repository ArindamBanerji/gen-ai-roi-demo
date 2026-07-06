import { useEffect, useMemo, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'
// Provenance: default "sample" - suppliers/trends currently returns fixture data.
// Override: uses data.source if S2P backend adds it.
const DEFAULT_TIER = 'sample'

type Payload = Record<string, unknown>

function numberValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function arrayValue(value: unknown): Payload[] {
  return Array.isArray(value) ? value.filter((item): item is Payload => Boolean(item) && typeof item === 'object' && !Array.isArray(item)) : []
}

function text(value: unknown, fallback = 'Unavailable'): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

export default function TrendCorrelationPanel() {
  const [trends, setTrends] = useState<Payload | null>(null)
  const [warnings, setWarnings] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const [trendsResponse, warningsResponse] = await Promise.all([
          fetch(`${S2P_API}/api/s2p/suppliers/trends`),
          fetch(`${S2P_API}/api/s2p/suppliers/early-warnings`),
        ])
        if (!trendsResponse.ok || !warningsResponse.ok) throw new Error('trend endpoint unavailable')
        const [trendsPayload, warningsPayload] = await Promise.all([
          trendsResponse.json() as Promise<Payload>,
          warningsResponse.json() as Promise<Payload>,
        ])
        if (!cancelled) {
          setTrends(trendsPayload)
          setWarnings(warningsPayload)
        }
      } catch {
        if (!cancelled) {
          setTrends(null)
          setWarnings(null)
          setError(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const trendRows = useMemo(() => arrayValue(trends?.trends ?? trends?.suppliers), [trends])
  const warningRows = useMemo(() => arrayValue(warnings?.warnings ?? warnings?.active_warnings), [warnings])
  const top = warningRows[0] ?? trendRows.find((row) => String(row.recent_trend ?? row.trend ?? '').toLowerCase().includes('declin')) ?? trendRows[0]
  const activeTrendCount = numberValue(trends?.total ?? trends?.declining_count) ?? trendRows.length
  const warningCount = numberValue(warnings?.active_warnings ?? warnings?.patterns_detected) ?? warningRows.length
  const provenance =
    (typeof trends?.provenance === 'string' && trends.provenance) ||
    (typeof trends?.source === 'string' && trends.source) ||
    (typeof warnings?.provenance === 'string' && warnings.provenance) ||
    (typeof warnings?.source === 'string' && warnings.source) ||
    DEFAULT_TIER

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Trend Correlation">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Trend correlation</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Supplier early warnings</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F15</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading supplier trends...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && (
        <>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Active trends</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-gray-100">
                <span>{activeTrendCount.toLocaleString()}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Early warnings</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-yellow-200">
                <span>{warningCount.toLocaleString()}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Top distress archetype</div>
              <div className="mt-2 flex items-center gap-2 text-sm text-gray-100">
                <span>{text(top?.archetype ?? top?.pattern ?? top?.warning_type ?? top?.trend)}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-300">
            Supplier {text(top?.supplier_name ?? top?.supplier_id, 'profile')}: {text(top?.summary ?? top?.narrative ?? top?.reason ?? top?.trend, 'early warning signal returned')}.
          </p>
        </>
      )}
    </section>
  )
}
