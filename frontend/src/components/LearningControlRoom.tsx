import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchLearningControlRoom, initializeFrozenComparison } from '../lib/api'
import { ensureArray } from '../lib/guards'

type AnyRecord = Record<string, any>

function num(value: unknown, digits = 3) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—'
}

export function LearningControlRoom() {
  const [data, setData] = useState<AnyRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [freezing, setFreezing] = useState(false)

  const load = () => fetchLearningControlRoom().then(setData).catch((err: Error) => setError(err.message))
  useEffect(() => { void load() }, [])

  if (error) return <section className="rounded-xl border border-red-900/40 bg-red-950/20 p-5 text-sm text-red-200">Learning Control Room unavailable: {error}</section>
  if (!data) return <section className="rounded-xl border border-slate-700 bg-slate-900/60 p-5 text-sm text-slate-400">Loading Learning Control Room…</section>

  const conservation = data.conservation ?? {}
  const iks = data.iks ?? {}
  const verified = data.verified_count ?? {}
  const evolution = data.evolution_summary ?? {}
  const history = ensureArray<AnyRecord>(data.centroid_history)
  const categories = Object.entries((verified.per_category ?? {}) as Record<string, unknown>).map(([category, count]) => ({ category, count }))
  const dk = data.dk_weights ?? {}
  const frozen = data.frozen_comparison as AnyRecord | null

  const freeze = async () => {
    setFreezing(true)
    try { await initializeFrozenComparison(); await load() } finally { setFreezing(false) }
  }

  return <section className="space-y-5 rounded-xl border border-cyan-800/60 bg-slate-950/80 p-5 shadow-lg">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">F16 / proof of learning</p><h2 className="text-2xl font-semibold text-white">Learning Control Room</h2></div>
      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/40 px-3 py-1 text-xs text-emerald-300">{data.evidence?.control_room ?? 'T_O'} · live measurements</span>
    </div>
    <div className="grid gap-3 md:grid-cols-4">
      {[['IKS', num(iks.current)], ['Verified decisions', String(verified.total ?? 0)], ['Conservation', String(conservation.phase ?? conservation.status ?? '—')], ['Promoted variants', String(evolution.promoted ?? 0)]].map(([label, value]) => <div key={label} className="rounded-lg border border-slate-800 bg-slate-900 p-4"><p className="text-xs text-slate-400">{label}</p><p className="mt-1 text-xl font-semibold text-white">{value}</p></div>)}
    </div>
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="mb-3 font-medium text-white">Centroid movement</h3><div className="h-48">{history.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={history}><CartesianGrid stroke="#243244" strokeDasharray="3 3" /><XAxis dataKey="decision_id" hide /><YAxis stroke="#94a3b8" /><Tooltip /><Line type="monotone" dataKey="movement" stroke="#22d3ee" dot={false} name="L2 movement" /></LineChart></ResponsiveContainer> : <p className="text-sm text-slate-400">No centroid movement has been recorded yet.</p>}</div></div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="mb-3 font-medium text-white">IKS trajectory</h3><div className="h-48">{ensureArray<AnyRecord>(iks.trajectory).length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={ensureArray<AnyRecord>(iks.trajectory)}><CartesianGrid stroke="#243244" strokeDasharray="3 3" /><XAxis dataKey="timestamp" hide /><YAxis domain={[0, 1]} stroke="#94a3b8" /><Tooltip /><Line type="monotone" dataKey="iks" stroke="#a78bfa" dot={false} name="IKS" /></LineChart></ResponsiveContainer> : <p className="text-sm text-slate-400">No IKS trajectory points are available.</p>}</div></div>
    </div>
    <div className="grid gap-5 lg:grid-cols-3">
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="font-medium text-white">Conservation state</h3><p className="mt-2 text-2xl font-semibold text-emerald-300">{conservation.phase ?? '—'}</p><p className="text-xs text-slate-400">α {num(conservation.components?.alpha)} · q {num(conservation.components?.q)} · V {num(conservation.components?.V)} · headroom {num(conservation.headroom)}</p></div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="mb-2 font-medium text-white">Verified decision volume</h3>{categories.length ? <div className="h-32"><ResponsiveContainer width="100%" height="100%"><BarChart data={categories}><XAxis dataKey="category" hide /><YAxis hide /><Tooltip /><Bar dataKey="count" fill="#34d399" /></BarChart></ResponsiveContainer></div> : <p className="text-sm text-slate-400">0 verified decisions</p>}</div>
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="mb-2 font-medium text-white">Evolution ledger</h3><p className="text-sm text-slate-300">Tested {evolution.tested ?? 0} · promoted {evolution.promoted ?? 0} · rejected {evolution.rejected ?? 0}</p><p className="mt-2 text-xs text-slate-400">{data.evidence?.evolution_summary ?? 'T_S · measured ledger'}</p></div>
    </div>
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="mb-3 font-medium text-white">Diagonal Kernel weights</h3>{Object.keys(dk.current ?? {}).length ? <div className="grid gap-3 md:grid-cols-2">{Object.entries(dk.current as Record<string, number[]>).map(([category, values]) => <div key={category}><div className="mb-1 flex justify-between text-xs text-slate-400"><span>{category}</span><span>{ensureArray<number>(values).map(value => num(value, 2)).join(' · ')}</span></div><div className="flex h-2 gap-1">{ensureArray<number>(values).map((value, index) => <span key={`${category}-${index}`} className="rounded bg-cyan-500" style={{ width: `${Math.max(4, Math.min(100, Number(value) * 100))}%` }} />)}</div></div>)}</div> : <p className="text-sm text-slate-400">No DK weights are available.</p>}</div>
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4"><h3 className="mb-2 font-medium text-white">Frozen Twin comparison</h3>{frozen ? <div className="grid gap-2 text-sm text-slate-300 md:grid-cols-4"><span>Day 0 IKS: <b>{num(frozen.frozen_iks)}</b></span><span>Current IKS: <b>{num(frozen.current_iks)}</b></span><span>Measured delta: <b>{num(frozen.iks_delta)}</b></span><span>Decisions since freeze: <b>{frozen.decisions_since_freeze ?? 0}</b></span><span>Centroid drift: {num(frozen.centroid_drift)}</span><span>Weight drift: {num(frozen.weight_drift)}</span><span className="text-cyan-300">{frozen.evidence_tier} · {frozen.measured ? 'measured' : 'modelled'}</span></div> : <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400"><span>Frozen Twin is not initialized. Freeze the day-0 scorer to measure compounding.</span><button disabled={freezing} onClick={() => void freeze()} className="rounded-md bg-cyan-700 px-3 py-2 text-white disabled:opacity-50">{freezing ? 'Freezing…' : 'Freeze day 0'}</button></div>}</div>
    <p className="text-xs text-slate-500">DK/kernel values and conservation state are read from the live SOC scorer. Frozen comparison is a separate immutable baseline.</p>
  </section>
}
