import { useEffect, useMemo, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'
// Provenance: default "context" - this endpoint computes from real decisions.
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

function label(value: string): string {
  return value.split('_').filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}

function categoryRows(value: unknown): Array<[string, number]> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.entries(value as Record<string, unknown>)
    .map(([name, raw]) => [name, numberValue(typeof raw === 'object' && raw ? (raw as Payload).net_savings ?? (raw as Payload).total_recovered ?? (raw as Payload).amount : raw) ?? 0] as [string, number])
    .sort((left, right) => Math.abs(right[1]) - Math.abs(left[1]))
}

export default function FinancialImpactPanel() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const response = await fetch(`${S2P_API}/api/s2p/financial-impact`)
        if (!response.ok) throw new Error(String(response.status))
        const payload = await response.json() as Payload
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) {
          setData(null)
          setError(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const topCategories = useMemo(() => categoryRows(data?.by_category).slice(0, 3), [data])
  const provenance = typeof data?.provenance === 'string' ? data.provenance : DEFAULT_TIER

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Financial Impact">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Financial impact</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Invoice exception value</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F10</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading financial impact...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && data && (
        <>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Net savings</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-green-300">
                <span>{money(data.net_savings)}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Total amount processed</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-gray-100">
                <span>{money(data.total_amount)}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-2">
            {topCategories.map(([name, value]) => (
              <div key={name} className="flex items-center justify-between rounded border border-gray-800 bg-slate-950/60 px-3 py-2 text-sm">
                <span className="text-gray-300">{label(name)}</span>
                <span className="font-mono text-gray-100">{money(value)}</span>
              </div>
            ))}
            {topCategories.length === 0 && <div className="rounded border border-gray-800 bg-slate-950/60 px-3 py-2 text-sm text-gray-500">No category impact returned.</div>}
          </div>

          <p className="mt-4 text-sm leading-6 text-gray-300">
            Invoice exceptions prevented {money(data.net_savings)} in overpayment this quarter.
          </p>
        </>
      )}
    </section>
  )
}
