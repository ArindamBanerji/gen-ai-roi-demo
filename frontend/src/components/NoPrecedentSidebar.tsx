import { useEffect, useState } from 'react'
import { getNoPrecedent } from '../lib/api'

type RecordValue = Record<string, any>

export default function NoPrecedentSidebar({ alertId, confidence }: { alertId: string; confidence?: number }) {
  const [data, setData] = useState<RecordValue | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    setError(null)
    void getNoPrecedent(alertId).then((value: any) => setData(value)).catch((err: Error) => setError(err.message))
  }, [alertId])

  const novel = data?.is_novel === true || data?.similar_count === 0
  return <aside className="rounded-xl border border-fuchsia-700/50 bg-slate-950/80 p-4" data-testid="no-precedent-sidebar" aria-label="No precedent assessment">
    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-fuchsia-300">SOC-NOPRECEDENT · honest retrieval</p>
    <h3 className="mt-1 text-lg font-semibold text-white">Similar past cases</h3>
    {error ? <p className="mt-3 text-sm text-slate-400">Precedent search unavailable: {error}</p> : novel ? <p className="mt-3 rounded-lg border border-fuchsia-700/50 bg-fuchsia-950/30 p-3 text-sm font-medium text-fuchsia-100">NONE — unprecedented here.</p> : <p className="mt-3 text-sm text-slate-400">Precedent search unavailable: no verified historical precedent records.</p>}
    {typeof confidence === 'number' && Number.isFinite(confidence) && <p className="mt-3 text-xs text-slate-500">Current confidence: {(confidence * 100).toFixed(1)}%</p>}
  </aside>
}
