import { useEffect, useState } from 'react'
import { fetchAutoApproveStats, fetchLearningControlRoom } from '../lib/api'
import { ensureArray } from '../lib/guards'

type RecordValue = Record<string, any>
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export default function CoverageAtSafetyBarPanel() {
  const [coverage, setCoverage] = useState<RecordValue | null>(null)
  const [control, setControl] = useState<RecordValue | null>(null)

  useEffect(() => {
    void fetchAutoApproveStats().then((value: any) => setCoverage(value)).catch(() => setCoverage(null))
    void fetchLearningControlRoom().then((value: any) => setControl(value)).catch(() => setControl(null))
  }, [])

  const categoryRows = Object.entries((coverage?.by_category ?? {}) as Record<string, RecordValue>)
  const convergence = ensureArray<RecordValue>(control?.convergence)
  const overall = finite(coverage?.coverage_pct) ? `${coverage.coverage_pct.toFixed(1)}%` : 'Unavailable'

  return <section className="rounded-xl border border-emerald-700/50 bg-slate-950/80 p-5" data-testid="coverage-safety-bar-panel" aria-label="Coverage at fixed safety bar">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">SOC-FRONTIER · fixed safety bar</p><h2 className="mt-1 text-xl font-semibold text-white">Coverage grows without lowering the bar</h2></div><span className="rounded-full border border-emerald-700/60 px-3 py-1 text-xs text-emerald-200">measured coverage</span></div>
    <div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><p className="text-xs text-slate-400">Safe auto-approve coverage</p><p className="mt-1 text-3xl font-semibold text-emerald-300">{overall}</p><p className="mt-1 text-xs text-slate-500">Safety bar remains governed by the live authority state.</p></div><div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><p className="text-xs text-slate-400">Recovery half-life</p><p className="mt-1 text-3xl font-semibold text-white">Unavailable</p><p className="mt-1 text-xs text-slate-500">No measured regime-break recovery field is returned by the current endpoint.</p></div></div>
    {categoryRows.length > 0 && <div className="mt-4 space-y-2"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Per-category frontier</p>{categoryRows.map(([name, row]) => <div key={name} className="rounded border border-slate-800 bg-slate-900 p-3"><div className="flex justify-between text-sm text-slate-300"><span>{name.replace(/_/g, ' ')}</span><span>{finite(row.coverage_pct) ? `${row.coverage_pct.toFixed(1)}%` : 'Unavailable'}</span></div><div className="mt-2 h-1.5 rounded bg-slate-800"><div className="h-1.5 rounded bg-emerald-500" style={{ width: `${Math.max(0, Math.min(100, finite(row.coverage_pct) ? row.coverage_pct : 0))}%` }} /></div></div>)}</div>}
    {convergence.length > 0 && <p className="mt-4 text-xs text-slate-500">Convergence records available for {convergence.length} categories; recovery timing is not inferred from them.</p>}
  </section>
}
