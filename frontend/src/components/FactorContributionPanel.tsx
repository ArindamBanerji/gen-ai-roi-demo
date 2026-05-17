import { useEffect, useState } from 'react'

interface FactorContribution {
  name: string
  index: number
  contribution_pct: number
  signal_strength: 'high' | 'medium' | 'low' | 'unknown'
  rank: number
}

interface FactorContributionResponse {
  factors: FactorContribution[]
  method: 'dk_weights' | 'uniform'
  top_factor: string | null
  weakest_factor: string | null
}

function formatFactorName(name: string) {
  return name
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function strengthClasses(strength: FactorContribution['signal_strength']) {
  if (strength === 'high') {
    return {
      bar: 'bg-green-500',
      label: 'text-green-300 border-green-500/30 bg-green-500/10',
    }
  }
  if (strength === 'medium') {
    return {
      bar: 'bg-amber-500',
      label: 'text-amber-300 border-amber-500/30 bg-amber-500/10',
    }
  }
  if (strength === 'low') {
    return {
      bar: 'bg-red-500',
      label: 'text-red-300 border-red-500/30 bg-red-500/10',
    }
  }
  return {
    bar: 'bg-gray-500',
    label: 'text-gray-300 border-gray-600 bg-gray-800',
  }
}

function normalizePayload(value: unknown): FactorContributionResponse | null {
  if (!value || typeof value !== 'object') return null
  const payload = value as Partial<FactorContributionResponse>
  if (!Array.isArray(payload.factors) || payload.factors.length === 0) return null
  if (payload.method !== 'dk_weights' && payload.method !== 'uniform') return null

  const factors = payload.factors
    .filter((factor): factor is FactorContribution => {
      return Boolean(factor)
        && typeof factor.name === 'string'
        && typeof factor.index === 'number'
        && typeof factor.contribution_pct === 'number'
        && typeof factor.rank === 'number'
        && ['high', 'medium', 'low', 'unknown'].includes(String(factor.signal_strength))
    })
    .sort((a, b) => a.rank - b.rank)

  if (factors.length === 0) return null

  return {
    factors,
    method: payload.method,
    top_factor: typeof payload.top_factor === 'string' ? payload.top_factor : null,
    weakest_factor: typeof payload.weakest_factor === 'string' ? payload.weakest_factor : null,
  }
}

export default function FactorContributionPanel() {
  const [data, setData] = useState<FactorContributionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadFactorContributions() {
      setLoading(true)
      setFailed(false)
      try {
        const response = await fetch('/api/soc/factor-contribution')
        if (!response.ok) {
          if (!cancelled) setFailed(true)
          return
        }
        const payload = normalizePayload(await response.json())
        if (!cancelled) {
          setData(payload)
          setFailed(payload === null)
        }
      } catch {
        if (!cancelled) setFailed(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadFactorContributions()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="pt-3 border-t border-gray-800">
        <p className="text-xs text-gray-500 italic">Factor contributions loading&hellip;</p>
      </div>
    )
  }

  if (failed || !data) return null

  return (
    <div data-testid="factor-contribution-panel" className="pt-3 border-t border-gray-800 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide">
            Factor Contributions ({data.method})
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Top: <span className="text-gray-300">{data.top_factor ? formatFactorName(data.top_factor) : 'None'}</span>
            {' '}| Weakest:{' '}
            <span className="text-gray-300">{data.weakest_factor ? formatFactorName(data.weakest_factor) : 'None'}</span>
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {data.factors.map((factor) => {
          const pct = Math.max(0, Math.min(100, factor.contribution_pct))
          const styles = strengthClasses(factor.signal_strength)
          return (
            <div
              key={`${factor.index}-${factor.name}`}
              data-testid={`factor-bar-${factor.index}`}
              className="space-y-1"
            >
              <div className="flex items-center justify-between gap-3 text-xs">
                <div className="min-w-0">
                  <span className="text-gray-400 font-mono mr-2">#{factor.rank}</span>
                  <span className="text-gray-300 font-medium">{formatFactorName(factor.name)}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold uppercase ${styles.label}`}>
                    {factor.signal_strength}
                  </span>
                  <span className="w-14 text-right text-gray-300 font-mono">
                    {pct.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${styles.bar}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
