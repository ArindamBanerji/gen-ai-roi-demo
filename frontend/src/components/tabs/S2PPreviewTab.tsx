import { useEffect, useMemo, useState } from 'react'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://localhost:8002'

interface QueueException {
  invoice_id?: string
  supplier?: string
  supplier_name?: string
  amount?: number
  category?: string
  scored_action?: string
  recommended_action?: string
  confidence?: number
  factors?: Record<string, number>
}

interface QueueResponse {
  engine_version?: string
  exceptions?: QueueException[]
  total?: number
  auto_approve_rate?: number
  confidence_avg?: number
}

interface ConservationResponse {
  engine_version?: string
  source?: string
  status?: string
  auto_approve_rate?: number
  auto_approve_pct?: number
  accuracy?: number
  verified_decisions?: number
  penalty_ratio?: number
  passed?: boolean
}

interface SupplierProfile {
  supplier_id?: string
  name?: string
  supplier_name?: string
  category?: string
  exception_rate?: number | { baseline?: number; current?: number }
  otif_score?: number
  otif?: { q1_q2?: number; q3?: number }
  avg_invoice_amount?: number
  recent_trend?: string
}

interface SuppliersResponse {
  engine_version?: string
  suppliers?: SupplierProfile[]
  total?: number
}

interface PreviewData {
  queue: QueueResponse
  conservation: ConservationResponse
  suppliers: SuppliersResponse
}

const curve = [
  { x: 0, y: 0.5, label: '50%' },
  { x: 250, y: 0.72, label: '72%' },
  { x: 500, y: 0.78, label: '78%' },
  { x: 1000, y: 0.84, label: '84%' },
]

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function formatLabel(value: unknown, fallback = 'Unknown'): string {
  if (typeof value !== 'string' || value.length === 0) return fallback
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatCurrency(value: unknown): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(toNumber(value))
}

function formatPct(value: unknown, digits = 0): string {
  const numeric = toNumber(value)
  const pct = numeric <= 1 ? numeric * 100 : numeric
  return `${pct.toFixed(digits)}%`
}

function supplierName(supplier: SupplierProfile): string {
  return supplier.name || supplier.supplier_name || supplier.supplier_id || 'Unknown supplier'
}

function supplierExceptionRate(supplier: SupplierProfile): number {
  const rate = supplier.exception_rate
  if (typeof rate === 'number') return rate
  return toNumber(rate?.current ?? rate?.baseline)
}

function supplierOtif(supplier: SupplierProfile): number {
  return toNumber(supplier.otif_score ?? supplier.otif?.q3 ?? supplier.otif?.q1_q2)
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${S2P_API}${path}`)
  if (!response.ok) throw new Error(`S2P preview request failed: ${response.status}`)
  return response.json() as Promise<T>
}

function CurveChart() {
  const points = curve.map((point) => {
    const x = 28 + (point.x / 1000) * 424
    const y = 172 - ((point.y - 0.5) / 0.38) * 132
    return { ...point, xPos: x, yPos: y }
  })
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.xPos} ${point.yPos}`).join(' ')

  return (
    <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-100">Compounding Curve</h3>
        <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-300">
          projected
        </span>
      </div>
      <svg viewBox="0 0 480 210" className="h-56 w-full" role="img" aria-label="Projected S2P compounding curve">
        <line x1="28" y1="172" x2="452" y2="172" stroke="#374151" />
        <line x1="28" y1="40" x2="28" y2="172" stroke="#374151" />
        <path d={path} fill="none" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((point) => (
          <g key={point.x}>
            <circle cx={point.xPos} cy={point.yPos} r="4" fill="#93c5fd" />
            <text x={point.xPos - 14} y={point.yPos - 12} fill="#d1d5db" fontSize="12">{point.label}</text>
            <text x={point.xPos - 18} y="194" fill="#6b7280" fontSize="11">{point.x}</text>
          </g>
        ))}
      </svg>
      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="rounded border border-gray-800 bg-slate-900 p-3">
          <div className="text-gray-500">Warm start</div>
          <div className="mt-1 font-mono text-gray-100">72%</div>
        </div>
        <div className="rounded border border-gray-800 bg-slate-900 p-3">
          <div className="text-gray-500">Shadow result</div>
          <div className="mt-1 font-mono text-gray-100">78%</div>
        </div>
        <div className="rounded border border-gray-800 bg-slate-900 p-3">
          <div className="text-gray-500">Projected</div>
          <div className="mt-1 font-mono text-green-300">84%</div>
        </div>
      </div>
    </div>
  )
}

export default function S2PPreviewTab() {
  const [data, setData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [queue, conservation, suppliers] = await Promise.all([
          fetchJson<QueueResponse>('/api/s2p/preview/queue'),
          fetchJson<ConservationResponse>('/api/s2p/preview/conservation'),
          fetchJson<SuppliersResponse>('/api/s2p/preview/suppliers'),
        ])
        if (!cancelled) setData({ queue, conservation, suppliers })
      } catch (err) {
        if (!cancelled) {
          setData(null)
          setError(err instanceof Error ? err.message : 'S2P preview backend is not available.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const version = data?.queue.engine_version || data?.conservation.engine_version || data?.suppliers.engine_version || 'v0.7.23'
  const exceptions = data?.queue.exceptions || []
  const suppliers = useMemo(() => data?.suppliers.suppliers || [], [data?.suppliers.suppliers])
  const preferredSuppliers = useMemo(() => {
    const chenLin = suppliers.find((supplier) => /chen-lin/i.test(supplierName(supplier)))
    return chenLin ? [chenLin, ...suppliers.filter((supplier) => supplier !== chenLin)] : suppliers
  }, [suppliers])

  if (loading) {
    return <div className="rounded-lg border border-gray-800 bg-soc-card p-6 text-sm text-gray-400">Loading S2P Preview...</div>
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-soc-card p-6">
        <h2 className="text-lg font-semibold text-red-300">S2P Preview unavailable</h2>
        <p className="mt-2 text-sm text-gray-400">Start the S2P backend on port 8002, then retry this tab.</p>
        <p className="mt-3 font-mono text-xs text-gray-500">{error}</p>
      </div>
    )
  }

  const conservation = data.conservation

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-blue-500/30 bg-slate-900 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-100">S2P Preview</h2>
            <p className="mt-2 text-sm text-gray-400">Powered by Graph Attention Engine {version}</p>
          </div>
          <div className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs text-blue-300">
            Invoice exception management
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="rounded-lg border border-gray-800 bg-soc-card">
          <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
            <h3 className="text-sm font-semibold text-gray-100">Exception Queue</h3>
            <span className="text-xs text-gray-400">
              {data.queue.total || exceptions.length} total · {formatPct(data.queue.auto_approve_rate)} auto approve · {formatPct(data.queue.confidence_avg)} avg confidence
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b border-gray-800 text-left uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Invoice</th>
                  <th className="px-4 py-2 font-medium">Supplier</th>
                  <th className="px-4 py-2 font-medium">Amount</th>
                  <th className="px-4 py-2 font-medium">Category</th>
                  <th className="px-4 py-2 font-medium">Scored action</th>
                  <th className="px-4 py-2 text-right font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {exceptions.map((invoice, index) => (
                  <tr key={invoice.invoice_id || index} className="border-b border-gray-800/60 last:border-0">
                    <td className="px-4 py-3 font-mono text-blue-300">{invoice.invoice_id || `INV-${index + 1}`}</td>
                    <td className="px-4 py-3 text-gray-200">{invoice.supplier || invoice.supplier_name || 'Unknown supplier'}</td>
                    <td className="px-4 py-3 font-mono text-gray-200">{formatCurrency(invoice.amount)}</td>
                    <td className="px-4 py-3 text-gray-300">{formatLabel(invoice.category)}</td>
                    <td className="px-4 py-3">
                      <span className="rounded border border-gray-700 bg-slate-900 px-2 py-1 text-gray-200">
                        {formatLabel(invoice.scored_action || invoice.recommended_action)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-green-300">{formatPct(invoice.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg border border-green-500/30 bg-soc-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-100">Conservation</h3>
            <span className="rounded-full border border-green-500/40 bg-green-500/15 px-3 py-1 text-xs font-semibold text-green-300">
              {conservation.status || 'GREEN'}
            </span>
          </div>
          <div className="space-y-3 text-sm">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-3">
              <div className="text-xs text-gray-500">Source</div>
              <div className="mt-1 text-gray-100">{conservation.source || 'illustration'} · projected</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded border border-gray-800 bg-slate-950/60 p-3">
                <div className="text-xs text-gray-500">Auto approve</div>
                <div className="mt-1 font-mono text-gray-100">{formatPct(conservation.auto_approve_rate ?? conservation.auto_approve_pct)}</div>
              </div>
              <div className="rounded border border-gray-800 bg-slate-950/60 p-3">
                <div className="text-xs text-gray-500">Accuracy</div>
                <div className="mt-1 font-mono text-gray-100">{formatPct(conservation.accuracy)}</div>
              </div>
              <div className="rounded border border-gray-800 bg-slate-950/60 p-3">
                <div className="text-xs text-gray-500">Verified decisions</div>
                <div className="mt-1 font-mono text-gray-100">{toNumber(conservation.verified_decisions).toLocaleString()}</div>
              </div>
              <div className="rounded border border-gray-800 bg-slate-950/60 p-3">
                <div className="text-xs text-gray-500">Penalty ratio</div>
                <div className="mt-1 font-mono text-gray-100">{toNumber(conservation.penalty_ratio, 5)}:1</div>
              </div>
            </div>
            <p className="text-xs leading-5 text-gray-400">This is an illustration/projection, not a live conservation state.</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <CurveChart />

        <div className="rounded-lg border border-gray-800 bg-soc-card">
          <div className="flex items-center justify-between border-b border-gray-800 px-5 py-3">
            <h3 className="text-sm font-semibold text-gray-100">Supplier Profile</h3>
            <span className="text-xs text-gray-400">{data.suppliers.total || suppliers.length} suppliers</span>
          </div>
          <div className="grid gap-3 p-5">
            {preferredSuppliers.slice(0, 4).map((supplier, index) => (
              <div key={supplier.supplier_id || index} className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-100">{supplierName(supplier)}</h4>
                    <p className="mt-1 text-xs text-gray-500">{formatLabel(supplier.category)} · {supplier.recent_trend || 'stable'}</p>
                  </div>
                  <span className="rounded border border-gray-700 bg-slate-900 px-2 py-1 text-xs text-gray-300">
                    {formatCurrency(supplier.avg_invoice_amount)} avg
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded border border-gray-800 bg-slate-900 p-3">
                    <div className="text-gray-500">Exception rate</div>
                    <div className="mt-1 font-mono text-yellow-300">{formatPct(supplierExceptionRate(supplier), 1)}</div>
                  </div>
                  <div className="rounded border border-gray-800 bg-slate-900 p-3">
                    <div className="text-gray-500">OTIF score</div>
                    <div className="mt-1 font-mono text-green-300">{formatPct(supplierOtif(supplier), 1)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-5 text-center text-sm text-blue-100">
        The engine is domain-agnostic. The intelligence is firm-specific.
      </div>
    </div>
  )
}
