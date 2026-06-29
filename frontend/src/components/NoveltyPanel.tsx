import { type ReactNode, useEffect, useState } from 'react'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'

type Payload = Record<string, unknown>

function numberValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function percent(value: unknown): string {
  const numeric = numberValue(value)
  if (numeric === null) return 'Unavailable'
  const pct = Math.abs(numeric) <= 1 ? numeric * 100 : numeric
  return `${pct.toFixed(1)}%`
}

function Badge({ active, children }: { active: boolean; children: ReactNode }) {
  return (
    <span className={`rounded border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${active ? 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200' : 'border-green-500/40 bg-green-500/10 text-green-200'}`}>
      {children}
    </span>
  )
}

export default function NoveltyPanel() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const response = await fetch(`${S2P_API}/api/s2p/novelty/status`)
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

  const alertActive = Boolean(data?.alert_active)
  const review = Boolean(data?.conservation_review)

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Novelty Detection">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Novelty detection</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Outlier monitor</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F6</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading novelty status...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && data && (
        <>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge active={alertActive}>Alert active: {alertActive ? 'yes' : 'no'}</Badge>
            <Badge active={review}>Conservation review: {review ? 'yes' : 'no'}</Badge>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Novelty rate</div>
              <div className="mt-2 font-mono text-2xl text-gray-100">{percent(data.novelty_rate)}</div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Novelty count</div>
              <div className="mt-2 font-mono text-2xl text-gray-100">{numberValue(data.novelty_count)?.toLocaleString() ?? 'Unavailable'}</div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Distance threshold</div>
              <div className="mt-2 font-mono text-2xl text-gray-100">{numberValue(data.distance_threshold)?.toFixed(2) ?? 'Unavailable'}</div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-300">
            {alertActive || review
              ? `Novelty spike: ${percent(data.novelty_rate)}. Conservation review ${review ? 'triggered' : 'not triggered'}.`
              : `Novelty rate: ${percent(data.novelty_rate)}. Below threshold. No conservation review needed.`}
          </p>
        </>
      )}
    </section>
  )
}
