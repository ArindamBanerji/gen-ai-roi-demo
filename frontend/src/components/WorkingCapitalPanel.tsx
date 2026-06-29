import { useEffect, useState } from 'react'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'

type Payload = Record<string, unknown>

function numberValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function money(value: unknown): string {
  const numeric = numberValue(value)
  if (numeric === null) return 'Unavailable'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(numeric)
}

function percent(value: unknown): string {
  const numeric = numberValue(value)
  if (numeric === null) return 'Unavailable'
  const pct = Math.abs(numeric) <= 1 ? numeric * 100 : numeric
  return `${pct.toFixed(1)}%`
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const numeric = numberValue(value)
    if (numeric !== null) return numeric
  }
  return null
}

export default function WorkingCapitalPanel() {
  const [strategy, setStrategy] = useState<Payload | null>(null)
  const [portfolio, setPortfolio] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const [strategyResponse, portfolioResponse] = await Promise.all([
          fetch(`${S2P_API}/api/s2p/suppliers/payment-strategy`),
          fetch(`${S2P_API}/api/s2p/suppliers/payment-portfolio`),
        ])
        if (!strategyResponse.ok || !portfolioResponse.ok) throw new Error('payment endpoint unavailable')
        const [strategyPayload, portfolioPayload] = await Promise.all([
          strategyResponse.json() as Promise<Payload>,
          portfolioResponse.json() as Promise<Payload>,
        ])
        if (!cancelled) {
          setStrategy(strategyPayload)
          setPortfolio(portfolioPayload)
        }
      } catch {
        if (!cancelled) {
          setStrategy(null)
          setPortfolio(null)
          setError(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const dpo = firstNumber(strategy?.portfolio_dpo_improvement, strategy?.dpo_improvement_days, portfolio?.portfolio_dpo_improvement)
  const cash = strategy?.cash_flow_benefit ?? portfolio?.cash_flow_benefit ?? portfolio?.total_annual_benefit
  const discount = portfolio?.discount_capture_rate ?? strategy?.discount_capture_rate ?? portfolio?.discount_opportunity
  const strategies = Array.isArray(strategy?.strategies) ? strategy?.strategies : []
  const supplierCount = firstNumber(strategy?.supplier_count, portfolio?.supplier_count) ?? strategies.length

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Working Capital">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Working capital</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Payment timing strategy</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F19</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading payment timing...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && (
        <>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">DPO impact</div>
              <div className="mt-2 font-mono text-xl text-gray-100">{dpo === null ? 'Unavailable' : `${dpo.toFixed(1)} days`}</div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Early-pay discount capture</div>
              <div className="mt-2 font-mono text-xl text-gray-100">{percent(discount)}</div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Cash flow benefit</div>
              <div className="mt-2 font-mono text-xl text-green-300">{money(cash)}</div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-300">
            Optimized payment timing saved {money(cash)} across {supplierCount || 'available'} suppliers.
          </p>
          {typeof strategy?.narrative === 'string' && <p className="mt-2 text-xs leading-5 text-gray-500">{strategy.narrative}</p>}
        </>
      )}
    </section>
  )
}
