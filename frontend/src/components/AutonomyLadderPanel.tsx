import { useEffect, useState } from 'react'
import { fetchAuthorityLadder } from '../lib/api'
import { ensureArray } from '../lib/guards'

type RecordValue = Record<string, any>

const rungStyles: Record<string, string> = {
  observed: 'border-sky-700/60 bg-sky-950/30 text-sky-200',
  assisted: 'border-indigo-700/60 bg-indigo-950/30 text-indigo-200',
  'shadow-qualified': 'border-violet-700/60 bg-violet-950/30 text-violet-200',
  'auto-approved': 'border-emerald-700/60 bg-emerald-950/30 text-emerald-200',
  'circuit-broken': 'border-red-700/60 bg-red-950/30 text-red-200',
}

export default function AutonomyLadderPanel() {
  const [items, setItems] = useState<RecordValue[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchAuthorityLadder()
      .then((payload: any) => setItems(ensureArray<RecordValue>(payload?.categories)))
      .catch((err: Error) => setError(err.message))
  }, [])

  return <section className="rounded-xl border border-amber-700/50 bg-slate-950/80 p-5" data-testid="autonomy-ladder-panel" aria-label="Earned autonomy ladder">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">SOC-LADDER · governed authority</p>
        <h2 className="mt-1 text-xl font-semibold text-white">Earned autonomy</h2>
      </div>
      <span className="rounded-full border border-amber-700/60 px-3 py-1 text-xs text-amber-200">promotion state</span>
    </div>
    <p className="mt-2 text-sm text-slate-400">Authority rises only by category, and circuit breaks remain visible.</p>
    {error ? <p className="mt-4 text-sm text-amber-200">Authority ladder unavailable: {error}</p> : items.length === 0 ? <p className="mt-4 text-sm text-slate-400">No authority records are available.</p> : <div className="mt-4 grid gap-3 md:grid-cols-2">
      {items.map((item) => {
        const authority = String(item.authority ?? 'observed').toLowerCase()
        const style = rungStyles[authority] ?? rungStyles.observed
        return <div key={String(item.decision_class ?? item.category)} className={`rounded-lg border p-4 ${style}`}>
          <div className="flex items-center justify-between gap-3"><span className="font-medium">{String(item.decision_class ?? item.category ?? 'unknown').replace(/_/g, ' ')}</span><span className="text-xs font-bold uppercase">{authority}</span></div>
          <div className="mt-3 flex gap-1" aria-label={`Authority rung ${authority}`}>
            {['observed', 'assisted', 'shadow-qualified', 'auto-approved', 'circuit-broken'].map((rung) => <span key={rung} className={`h-1.5 flex-1 rounded ${rung === authority ? 'bg-current' : 'bg-white/15'}`} />)}
          </div>
          {item.reason && <p className="mt-3 text-xs opacity-80">{String(item.reason)}</p>}
        </div>
      })}
    </div>}
  </section>
}
