import { useEffect, useState } from 'react'

const SOC_API = 'http://127.0.0.1:8001'

interface LearningState { verified_decisions?: number; decision_count?: number; iks_v2?: number; iks_interpretation?: string }
interface CentroidSupport { overall_health?: string; warning_count?: number }

function numberValue(value: unknown): number | null { return typeof value === 'number' && Number.isFinite(value) ? value : null }

export default function ContinuityPanel() {
  const [learning, setLearning] = useState<LearningState | null>(null)
  const [support, setSupport] = useState<CentroidSupport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch(`${SOC_API}/api/soc/learning-state`).then((response) => response.ok ? response.json() as Promise<LearningState> : Promise.reject(new Error(String(response.status)))),
      fetch(`${SOC_API}/api/soc/centroid-support`).then((response) => response.ok ? response.json() as Promise<CentroidSupport> : Promise.reject(new Error(String(response.status)))),
    ]).then(([learningState, centroidSupport]) => {
      if (!cancelled) { setLearning(learningState); setSupport(centroidSupport) }
    }).catch(() => {
      if (!cancelled) { setLearning(null); setSupport(null) }
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const verified = numberValue(learning?.verified_decisions) ?? numberValue(learning?.decision_count) ?? 0
  const iks = numberValue(learning?.iks_v2)
  const retainedPct = iks === null ? null : Math.max(0, Math.min(100, iks * 100))
  const health = support?.overall_health ?? 'UNKNOWN'
  const warnings = numberValue(support?.warning_count) ?? 0

  return (
    <section className="rounded-lg border border-indigo-500/40 bg-slate-950 p-5 shadow-sm" aria-label="Continuity and departure" data-testid="continuity-panel">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-300">E6 · continuity under departure</p><h3 className="mt-1 text-lg font-bold text-white">The judgment stays when the expert leaves</h3><p className="mt-1 text-sm text-slate-400">Learning state and centroid support show how much institutional judgment remains inspectable after personnel change.</p></div><span className="rounded border border-indigo-400/40 bg-indigo-400/10 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-indigo-200">measured state</span></div>
      {loading && <p className="mt-4 text-sm text-slate-400">Loading continuity state...</p>}
      {!loading && <><div className="mt-5 grid gap-3 sm:grid-cols-3"><Metric label="$ of judgment retained" value="Unavailable" detail="No monetary valuation is returned by the live SOC endpoints." /><Metric label="Judgment retained" value={retainedPct === null ? 'Unavailable' : `${retainedPct.toFixed(1)}%`} detail={learning?.iks_interpretation ?? 'IKS v2 from learning-state'} /><Metric label="Verified decisions" value={verified.toLocaleString()} detail="Graph-backed learning evidence" /></div><div className="mt-4 flex flex-wrap gap-3 text-sm"><span className={`rounded border px-3 py-1 ${health === 'GREEN' ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-amber-500/40 bg-amber-500/10 text-amber-200'}`}>Centroid support: {health}</span><span className="rounded border border-slate-700 bg-slate-900 px-3 py-1 text-slate-300">Support warnings: {warnings}</span></div></>}
    </section>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="rounded border border-slate-800 bg-slate-900/70 p-3"><div className="text-xs uppercase tracking-wide text-slate-500">{label}</div><div className="mt-1 font-mono text-xl font-bold text-white">{value}</div><div className="mt-1 text-xs text-slate-500">{detail}</div></div> }
