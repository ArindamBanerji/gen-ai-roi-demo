/**
 * SimulationPanel — SIM-2
 *
 * Runs batch GAE simulations and shows real-time learning curves.
 * Placed at the top of Tab 4 (CompoundingTab) above existing charts.
 *
 * API wired to:
 *   POST /api/simulation/start
 *   GET  /api/simulation/progress/{id}   — polled every 500 ms
 *   GET  /api/simulation/result/{id}     — fetched once on complete
 *   GET  /api/simulation/experiment-log/{id} — for download + smooth chart
 */

import { useState, useRef, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { Play, Download, Activity, CheckCircle, AlertCircle, Square } from 'lucide-react'
import {
  startSimulation, getSimulationProgress,
  getSimulationResult, getSimulationExperimentLog,
} from '../lib/api'

// ── Constants ─────────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  credential_access:  '#3b82f6',   // blue
  threat_intel_match: '#10b981',   // green
  lateral_movement:   '#f97316',   // orange
  data_exfiltration:  '#ef4444',   // red
  insider_threat:     '#8b5cf6',   // purple
}

const CATEGORY_LABELS: Record<string, string> = {
  credential_access:  'Credential Access',
  threat_intel_match: 'Threat Intel Match',
  lateral_movement:   'Lateral Movement',
  data_exfiltration:  'Data Exfiltration',
  insider_threat:     'Insider Threat',
}

// Round-robin order matches alert_pool.py interleaving
const CAT_ORDER = [
  'credential_access', 'threat_intel_match',
  'lateral_movement',  'data_exfiltration', 'insider_threat',
]

// ── Types ──────────────────────────────────────────────────────────────────

interface ProgressSnap {
  step: number
  total: number
  status: 'running' | 'complete' | 'error'
  current_accuracy: number
  category_accuracy: Record<string, number>
}

interface SimResult {
  n_decisions: number
  overall_accuracy: number
  ground_truth_accuracy: number
  category_accuracy: Record<string, number>
  category_ground_truth: Record<string, number>
  duration_seconds: number
}

interface ChartPoint extends Record<string, number | undefined> {
  step: number
}

export interface SimulationPanelProps {
  onSimulationComplete?: () => void
}

// ── Helpers ────────────────────────────────────────────────────────────────

/** Reconstruct per-category cumulative accuracy from the experiment log. */
function buildChartFromLog(log: any[]): ChartPoint[] {
  const counts: Record<string, { correct: number; total: number }> = {}
  return log.map((record) => {
    const cat: string = record.category
    if (!counts[cat]) counts[cat] = { correct: 0, total: 0 }
    counts[cat].total++
    if (record.correct) counts[cat].correct++
    const point: ChartPoint = { step: (record.step as number) + 1 }
    for (const c of CAT_ORDER) {
      const v = counts[c]
      point[c] = v ? v.correct / v.total : undefined
    }
    return point
  })
}

function pct(v: number) {
  return `${(v * 100).toFixed(0)}%`
}

// ── Component ──────────────────────────────────────────────────────────────

export default function SimulationPanel({ onSimulationComplete }: SimulationPanelProps) {
  const [nDecisions, setNDecisions]     = useState(25)
  const [speedMs,    setSpeedMs]        = useState(200)
  const [simId,      setSimId]          = useState<string | null>(null)
  const [simStatus,  setSimStatus]      = useState<'idle' | 'running' | 'complete' | 'error'>('idle')
  const [progress,   setProgress]       = useState<ProgressSnap | null>(null)
  const [chartData,  setChartData]      = useState<ChartPoint[]>([])
  const [result,     setResult]         = useState<SimResult | null>(null)
  const [currentCat, setCurrentCat]     = useState<string | null>(null)
  const [errorMsg,   setErrorMsg]       = useState<string | null>(null)
  const [downloading, setDownloading]   = useState(false)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Cleanup on unmount
  useEffect(() => () => {
    if (intervalRef.current !== null) clearInterval(intervalRef.current)
  }, [])

  const handleStart = async () => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setSimStatus('running')
    setChartData([])
    setResult(null)
    setProgress(null)
    setErrorMsg(null)
    setCurrentCat(null)
    setSimId(null)

    let id: string
    try {
      const resp = await startSimulation(nDecisions, speedMs) as { simulation_id: string }
      id = resp.simulation_id
      setSimId(id)
    } catch (e) {
      console.error('[SIM] Failed to start:', e)
      setSimStatus('error')
      setErrorMsg('Failed to start simulation — is the backend running on port 8000?')
      return
    }

    // Polling — id captured from closure (no stale-ref issue)
    const interval = setInterval(async () => {
      try {
        const p = await getSimulationProgress(id) as ProgressSnap
        setProgress(p)

        if (p.step > 0) {
          // Current category from round-robin step index
          setCurrentCat(CAT_ORDER[(p.step - 1) % CAT_ORDER.length])

          // Accumulate chart data points (append only if step is new)
          setChartData(prev => {
            const lastStep = prev.length > 0 ? prev[prev.length - 1].step : -1
            if (p.step <= lastStep) return prev
            const point: ChartPoint = { step: p.step }
            for (const c of CAT_ORDER) {
              const v = p.category_accuracy[c]
              if (v !== undefined) point[c] = v
            }
            return [...prev, point]
          })
        }

        if (p.status === 'complete') {
          clearInterval(interval)
          intervalRef.current = null
          setSimStatus('complete')
          setCurrentCat(null)

          // Fetch final result + experiment log for smooth chart
          try {
            const [r, log] = await Promise.all([
              getSimulationResult(id) as Promise<SimResult>,
              getSimulationExperimentLog(id) as Promise<any[]>,
            ])
            setResult(r)
            setChartData(buildChartFromLog(log))
            onSimulationComplete?.()
          } catch (e) {
            console.error('[SIM] Failed to fetch final data:', e)
          }

        } else if (p.status === 'error') {
          clearInterval(interval)
          intervalRef.current = null
          setSimStatus('error')
          setErrorMsg('Simulation failed — check backend logs.')
        }

      } catch (e) {
        console.error('[SIM] Poll error:', e)
      }
    }, 500)

    intervalRef.current = interval
  }

  const handleDownload = async () => {
    if (!simId) return
    setDownloading(true)
    try {
      const log = await getSimulationExperimentLog(simId) as any[]
      const blob = new Blob([JSON.stringify(log, null, 2)], { type: 'application/json' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `simulation_log_${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('[SIM] Download failed:', e)
    } finally {
      setDownloading(false)
    }
  }

  const progressPct = progress ? Math.round((progress.step / progress.total) * 100) : 0
  const isRunning   = simStatus === 'running'
  const isComplete  = simStatus === 'complete'
  const isError     = simStatus === 'error'

  return (
    <div className="bg-slate-900 rounded-lg border border-blue-500/60 shadow-2xl overflow-hidden">

      {/* ── Header bar ─────────────────────────────────────────────────── */}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            GAE Batch Simulation
            <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/40">
              LIVE
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Run N decisions through the full 15-step pipeline and watch the weight matrix adapt
          </p>
        </div>

        {/* Status pill */}
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
              Running…
            </span>
          )}
          {isComplete && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/20 text-green-300 border border-green-500/40">
              <CheckCircle className="w-3 h-3" />
              Complete
            </span>
          )}
          {isError && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/40">
              <AlertCircle className="w-3 h-3" />
              Error
            </span>
          )}
          {simStatus === 'idle' && (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-700 text-slate-400 border border-slate-600">
              Ready
            </span>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6">

        {/* ── Controls ─────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-end gap-4">
          {/* N selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
              Decisions (N)
            </label>
            <select
              value={nDecisions}
              onChange={e => setNDecisions(Number(e.target.value))}
              disabled={isRunning}
              className="bg-slate-800 border border-slate-600 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          {/* Speed selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
              Speed
            </label>
            <select
              value={speedMs}
              onChange={e => setSpeedMs(Number(e.target.value))}
              disabled={isRunning}
              className="bg-slate-800 border border-slate-600 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value={50}>Fast (50 ms)</option>
              <option value={200}>Medium (200 ms)</option>
              <option value={500}>Slow (500 ms)</option>
            </select>
          </div>

          {/* Run button */}
          <button
            onClick={handleStart}
            disabled={isRunning}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors shadow-md"
          >
            {isRunning ? (
              <>
                <Square className="w-4 h-4 animate-pulse" />
                Running…
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Simulation
              </>
            )}
          </button>

          {/* Download button — visible after completion */}
          {isComplete && simId && (
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-gray-200 text-sm font-semibold rounded-lg transition-colors border border-slate-600"
            >
              <Download className="w-4 h-4" />
              {downloading ? 'Downloading…' : 'Download Experiment Log'}
            </button>
          )}
        </div>

        {/* ── Progress bar (visible while running) ─────────────────────── */}
        {(isRunning || (isComplete && progress)) && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-300 font-medium">
                {isRunning ? 'Processing decisions…' : 'Complete'}
              </span>
              <span className="text-slate-400 tabular-nums">
                {progress?.step ?? 0} / {progress?.total ?? nDecisions} decisions
                {isRunning && currentCat && (
                  <span className="ml-2 text-xs" style={{ color: CATEGORY_COLORS[currentCat] }}>
                    [{CATEGORY_LABELS[currentCat] ?? currentCat}]
                  </span>
                )}
              </span>
            </div>
            <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${isComplete ? 100 : progressPct}%`,
                  background: isComplete
                    ? 'linear-gradient(90deg, #10b981, #3b82f6)'
                    : 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                }}
              />
            </div>
          </div>
        )}

        {/* ── Error message ─────────────────────────────────────────────── */}
        {isError && errorMsg && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {errorMsg}
          </div>
        )}

        {/* ── Category Learning Curve chart ─────────────────────────────── */}
        {(chartData.length > 0 || isRunning) && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                Category Learning Curve
              </h4>
              <span className="text-xs text-slate-500 italic">
                cumulative accuracy per alert category
              </span>
            </div>

            {chartData.length === 0 ? (
              <div className="h-64 flex items-center justify-center text-slate-500 text-sm italic">
                Waiting for first decisions…
              </div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis
                      dataKey="step"
                      stroke="#64748b"
                      style={{ fontSize: '11px' }}
                      label={{ value: 'Decision #', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 11 }}
                    />
                    <YAxis
                      domain={[0, 1]}
                      tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                      stroke="#64748b"
                      style={{ fontSize: '11px' }}
                      width={42}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '6px' }}
                      labelStyle={{ color: '#94a3b8', fontSize: '12px' }}
                      formatter={(value: any, name: string) => [
                        pct(value as number),
                        CATEGORY_LABELS[name] ?? name,
                      ]}
                    />
                    <Legend
                      formatter={(name: string) => (
                        <span style={{ color: '#cbd5e1', fontSize: '12px' }}>
                          {CATEGORY_LABELS[name] ?? name}
                        </span>
                      )}
                    />
                    {CAT_ORDER.map(cat => (
                      <Line
                        key={cat}
                        type="monotone"
                        dataKey={cat}
                        stroke={CATEGORY_COLORS[cat]}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                        connectNulls
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* ── Summary card (after completion) ──────────────────────────── */}
        {isComplete && result && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2 border-t border-slate-700">

            {/* Overall accuracy */}
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                Oracle Accuracy
              </div>
              <div className="text-3xl font-bold text-blue-400">
                {pct(result.overall_accuracy)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Bernoulli oracle correct / total
              </div>
            </div>

            {/* Ground truth accuracy */}
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                Ground Truth Accuracy
              </div>
              <div className="text-3xl font-bold text-green-400">
                {pct(result.ground_truth_accuracy)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                vs expert-defined optimal action
              </div>
            </div>

            {/* Duration */}
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                Duration
              </div>
              <div className="text-3xl font-bold text-purple-400">
                {result.duration_seconds.toFixed(1)}s
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {result.n_decisions} decisions at {speedMs} ms/step
              </div>
            </div>

            {/* Per-category accuracy table */}
            <div className="sm:col-span-2 lg:col-span-3 bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-3">
                Per-Category Results
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {CAT_ORDER.map(cat => {
                  const acc = result.category_accuracy[cat]
                  const gt  = result.category_ground_truth[cat]
                  if (acc === undefined) return null
                  return (
                    <div key={cat} className="text-center">
                      <div
                        className="text-xs font-semibold mb-1"
                        style={{ color: CATEGORY_COLORS[cat] }}
                      >
                        {CATEGORY_LABELS[cat]}
                      </div>
                      <div className="text-xl font-bold text-gray-200">
                        {pct(acc)}
                      </div>
                      {gt !== undefined && (
                        <div className="text-xs text-slate-500 mt-0.5">
                          GT: {pct(gt)}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

          </div>
        )}

        {/* ── Idle hint ─────────────────────────────────────────────────── */}
        {simStatus === 'idle' && (
          <div className="text-center py-4 text-slate-500 text-sm italic">
            Select N and speed, then click <strong className="text-slate-400">Run Simulation</strong> to watch GAE learn in real time.
            The weight matrix resets to expert priors before each run.
          </div>
        )}

      </div>
    </div>
  )
}
