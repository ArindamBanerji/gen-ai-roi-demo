import { useEffect, useState } from 'react'
import { getWhatIf } from '../lib/api'
import { ensureArray } from '../lib/guards'

type RecordValue = Record<string, any>

export default function WhatIfInspectorPanel({ alertId, currentAction }: { alertId: string; currentAction?: string }) {
  const [data, setData] = useState<RecordValue | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    setError(null)
    void getWhatIf(alertId, currentAction).then((value: any) => setData(value)).catch((err: Error) => setError(err.message))
  }, [alertId, currentAction])

  const conditions = ensureArray<RecordValue | string>(data?.flip_conditions ?? data?.per_factor ?? data?.conditions)
  return <section className="rounded-xl border border-cyan-700/50 bg-slate-950/80 p-4" data-testid="what-if-inspector" aria-label="What-if inspector">
    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">SOC-WHATIF · factor sensitivity</p>
    <h3 className="mt-1 text-lg font-semibold text-white">What would change the decision?</h3>
    {error ? <p className="mt-3 text-sm text-slate-400">What-if analysis unavailable: {error}</p> : <>
      {data?.explanation && <p className="mt-3 text-sm text-slate-300">{String(data.explanation)}</p>}
      {conditions.length > 0 ? <ul className="mt-3 space-y-2 text-sm text-cyan-100">{conditions.map((condition, index) => <li key={index} className="rounded border border-cyan-900/70 bg-cyan-950/20 p-2">{typeof condition === 'string' ? condition : String(condition.label ?? condition.factor ?? condition.description ?? 'Condition unavailable')}</li>)}</ul> : !data?.explanation && <p className="mt-3 text-sm text-slate-400">No measured flip conditions are available.</p>}
    </>}
  </section>
}
