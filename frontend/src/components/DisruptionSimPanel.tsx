import { useEffect, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'
// Provenance: default "context" - this endpoint returns simulation output.
// Override: uses data.provenance if S2P backend adds it.
const DEFAULT_TIER = 'context'

type Payload = Record<string, unknown>

function numberValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function money(value: unknown): string {
  const numeric = numberValue(value)
  if (numeric === null) return 'Unavailable'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(numeric)
}

function arrayValue(value: unknown): Payload[] {
  return Array.isArray(value) ? value.filter((item): item is Payload => Boolean(item) && typeof item === 'object' && !Array.isArray(item)) : []
}

export default function DisruptionSimPanel() {
  const [scenarios, setScenarios] = useState<Payload | null>(null)
  const [summary, setSummary] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const [scenarioResponse, summaryResponse] = await Promise.all([
          fetch(`${S2P_API}/api/s2p/simulation/scenarios`),
          fetch(`${S2P_API}/api/s2p/simulation/impact-summary`),
        ])
        if (!scenarioResponse.ok || !summaryResponse.ok) throw new Error('simulation endpoint unavailable')
        const [scenarioPayload, summaryPayload] = await Promise.all([
          scenarioResponse.json() as Promise<Payload>,
          summaryResponse.json() as Promise<Payload>,
        ])
        if (!cancelled) {
          setScenarios(scenarioPayload)
          setSummary(summaryPayload)
        }
      } catch {
        if (!cancelled) {
          setScenarios(null)
          setSummary(null)
          setError(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const rows = arrayValue(scenarios?.scenarios)
  const scenarioCount = numberValue(scenarios?.total) ?? rows.length
  const worst = rows.reduce<unknown>((max, row) => {
    const current = numberValue(row.worst_case_impact ?? row.estimated_cost ?? row.impact ?? row.quarterly_exposure) ?? 0
    const previous = numberValue(max) ?? 0
    return current > previous ? current : max
  }, summary?.worst_case_impact ?? summary?.total_quarterly_exposure)
  const alternatives = rows.reduce((total, row) => total + arrayValue(row.alternatives).length, 0)
  const provenance =
    (typeof summary?.provenance === 'string' && summary.provenance) ||
    (typeof scenarios?.provenance === 'string' && scenarios.provenance) ||
    DEFAULT_TIER

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Disruption Simulation">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Disruption simulation</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Supplier continuity scenarios</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F21</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading disruption scenarios...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && (
        <>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Active scenarios</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-gray-100">
                <span>{scenarioCount.toLocaleString()}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Worst-case impact</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-yellow-200">
                <span>{money(worst)}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Alternatives identified</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-green-300">
                <span>{alternatives.toLocaleString()}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-300">
            {scenarioCount.toLocaleString()} disruption scenarios simulated. {alternatives > 0 ? `${alternatives.toLocaleString()} alternatives identified.` : 'Alternative supplier counts were not returned.'}
          </p>
          {typeof summary?.narrative === 'string' && <p className="mt-2 text-xs leading-5 text-gray-500">{summary.narrative}</p>}
        </>
      )}
    </section>
  )
}
