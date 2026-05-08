import { useEffect, useState } from 'react'

interface LearningStateData {
  strategy: string
  category: string
  phase: string
  alpha: number
  dk_weights: number[] | number[][] | null
  freeze_point: number | null
  decisions_in_category: number
  novelty_rate: number | null
  batch_pipeline: Record<string, unknown> | null
}

interface LearningStatePanelProps {
  category?: string
}

export default function LearningStatePanel({ category = 'credential_access' }: LearningStatePanelProps) {
  const [data, setData] = useState<LearningStateData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadLearningState() {
      setLoading(true)
      try {
        const response = await fetch(`/api/triage/learning-state?category=${encodeURIComponent(category)}`)
        if (!response.ok) {
          if (!cancelled) setData(null)
          return
        }
        const payload = await response.json() as LearningStateData
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadLearningState()
    return () => {
      cancelled = true
    }
  }, [category])

  if (loading || !data || data.strategy === 'continuous') return null

  const rawWeights = data.dk_weights
  const weights: number[] = rawWeights
    ? Array.isArray(rawWeights[0])
      ? (rawWeights as number[][])[0]
      : (rawWeights as number[])
    : []
  const alphaPct = Math.round(data.alpha * 100)
  const isVarianceLearning = data.phase === 'VARIANCE_LEARNING'

  return (
    <div className="bg-soc-card rounded-lg border border-blue-500/40 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold"> Learning State</h3>
          <p className="text-xs text-gray-500 mt-1">Two-phase scoring for {data.category}</p>
        </div>
        <span className={`text-xs font-semibold px-2 py-1 rounded border ${
          isVarianceLearning
            ? 'bg-blue-500/15 text-blue-300 border-blue-500/40'
            : 'bg-amber-500/15 text-amber-300 border-amber-500/40'
        }`}>
          {isVarianceLearning ? 'Phase 2 — DK Learning' : 'Phase 1 — Centroid Convergence'}
        </span>
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Shrinkage (α)</p>
            <p className="text-xl font-bold text-gray-100">{alphaPct}%</p>
            <p className="text-xs text-gray-500 mt-1">0% = centroid-only · 100% = full DK dimensional importance</p>
          </div>
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Decisions in category</p>
            <p className="text-xl font-bold text-gray-100">{data.decisions_in_category}</p>
          </div>
          {data.freeze_point !== null && (
            <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-3">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Freeze point</p>
              <p className="text-xl font-bold text-gray-100">{data.freeze_point}</p>
            </div>
          )}
        </div>

        {weights.length > 0 && (
          <div className="pt-3 border-t border-gray-800">
            <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-3">Dimensional importance</p>
            <div className="space-y-2">
              {weights.map((w, idx) => {
                const pct = Math.round(Math.min(w, 1.0) * 100)
                return (
                  <div key={`weight-${idx}`} className="grid grid-cols-[2rem_1fr_3rem] items-center gap-3 text-xs">
                    <span className="text-gray-400 font-mono">F{idx + 1}</span>
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${Math.max(0, pct)}%` }}
                      />
                    </div>
                    <span className="text-gray-300 text-right font-mono">{w.toFixed(2)}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
