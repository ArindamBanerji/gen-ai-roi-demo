import { useEffect, useState } from 'react'
import { CheckCircle, XCircle } from 'lucide-react'
import { fetchDayZeroReadiness } from '../lib/api'

type CategoryReadiness = {
  category?: string
  decision_count?: number
  coverage?: string
  ready?: boolean
  missing?: string[]
}

type DayZeroReadiness = {
  ready?: boolean
  categories?: CategoryReadiness[]
  coverage_gaps?: string[]
  checklist?: string[]
  source?: string
}

const statusText = (ready: boolean | undefined) => ready ? 'Ready' : 'Needs evidence'
const label = (value: unknown) => String(value ?? '').replace(/_/g, ' ')

export default function DayZeroReadinessPanel() {
  const [data, setData] = useState<DayZeroReadiness | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    fetchDayZeroReadiness()
      .then((payload) => {
        if (mounted) setData(payload as DayZeroReadiness)
      })
      .catch((err) => {
        if (mounted) setError(err instanceof Error ? err.message : 'Readiness unavailable')
      })
    return () => { mounted = false }
  }, [])

  const categories = Array.isArray(data?.categories) ? data.categories : []
  const gaps = Array.isArray(data?.coverage_gaps) ? data.coverage_gaps : []
  const checklist = Array.isArray(data?.checklist) ? data.checklist : []

  return <section className="rounded-xl border border-slate-600 bg-slate-950/80 p-5" data-testid="day-zero-readiness-panel" aria-label="Day-zero readiness">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">SOC-DAY0 · fresh tenant readiness</p>
        <h2 className="mt-1 text-xl font-semibold text-white">Day-zero readiness</h2>
      </div>
      <span className={`rounded-full border px-3 py-1 text-xs ${data?.ready ? 'border-emerald-500/50 text-emerald-300' : 'border-amber-500/50 text-amber-300'}`}>
        {data ? statusText(data.ready) : error ? 'Unavailable' : 'Loading'}
      </span>
    </div>

    {error ? <p className="mt-4 rounded border border-red-500/30 bg-red-950/30 px-3 py-2 text-sm text-red-200">{error}</p> : null}

    <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
        <p className="text-xs text-slate-500">Categories ready</p>
        <p className="mt-1 text-lg text-slate-200">{categories.filter((item) => item.ready).length}/{categories.length}</p>
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
        <p className="text-xs text-slate-500">Coverage gaps</p>
        <p className="mt-1 text-lg text-slate-200">{gaps.length}</p>
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
        <p className="text-xs text-slate-500">Readiness source</p>
        <p className="mt-1 text-sm text-slate-200">{data?.source ?? 'live AGE GraphStore'}</p>
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
        <p className="text-xs text-slate-500">Checklist</p>
        <p className="mt-1 text-lg text-slate-200">{checklist.length}</p>
      </div>
    </div>

    <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {categories.map((item) => (
        <div key={item.category ?? 'unknown'} className="rounded border border-slate-800 bg-slate-900 p-3 text-sm text-slate-300">
          <div className="flex items-center justify-between gap-3">
            <span className="font-medium capitalize">{label(item.category)}</span>
            {item.ready ? <CheckCircle className="h-4 w-4 text-emerald-400" /> : <XCircle className="h-4 w-4 text-amber-400" />}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
            <span>{label(item.coverage || 'gap')}</span>
            <span>{Number(item.decision_count ?? 0)} decisions</span>
          </div>
          {!item.ready && Array.isArray(item.missing) && item.missing.length > 0 ? (
            <p className="mt-2 text-xs text-amber-300">{item.missing.map(label).join(', ')}</p>
          ) : null}
        </div>
      ))}
    </div>
  </section>
}
