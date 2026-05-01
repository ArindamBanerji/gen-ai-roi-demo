import { useState, useEffect } from 'react'
import { ensureArray, safeKey } from '../../lib/guards'

interface ScoredInvoice {
  invoice_id: string
  supplier_name: string
  category: string
  amount: number
  variance_pct: number
  recommended_action: string
  confidence: number
  factors: Record<string, number>
  factor_vector: number[]
  ground_truth_action: string
}

interface ConservationStatus {
  status: 'GREEN' | 'AMBER' | 'RED'
  auto_approve_pct: number
  verified_decisions: number
  engine_version: string
  conservation_product?: number
  conservation_threshold?: number
}

interface TrajectoryPoint {
  decisions: number
  accuracy: number
  batch: number
}

interface Supplier {
  supplier_name: string
  region: string
  otif: { q1_q2: number; q3: number }
  exception_rate: { baseline: number; current: number }
  lead_time: { contractual_days: number; actual_q4_days: number }
  financial_health_trend: string
}

interface Config {
  engine_version?: string
  tensor_shape?: string
  categories?: string[]
  factors?: string[]
}

const UNAVAILABLE_MESSAGE = 'S2P Preview unavailable — ensure S2P backend is running on port 8002'
const START_COMMAND = 'Start with: cd s2p-copilot/backend && uvicorn app.main:app --port 8002'

function formatCategory(cat: unknown, fallback = 'Unknown'): string {
  if (typeof cat !== 'string') return fallback
  const label = cat
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
  return label || fallback
}

function formatAction(action: unknown): string {
  return formatCategory(action, 'Review')
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(toNumber(amount))
}

function formatPct(value: number, fractionDigits = 1): string {
  const numeric = toNumber(value)
  const pct = numeric <= 1 ? numeric * 100 : numeric
  return `${pct.toFixed(fractionDigits)}%`
}

function getConfidenceColor(conf: number): string {
  const pct = toNumber(conf) <= 1 ? toNumber(conf) * 100 : toNumber(conf)
  if (pct > 80) return 'text-green-400'
  if (pct >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

function getStatusColor(status: string): string {
  if (status === 'GREEN') return 'bg-green-500/20 text-green-300 border-green-500/40'
  if (status === 'AMBER') return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
  if (status === 'RED') return 'bg-red-500/20 text-red-300 border-red-500/40'
  return 'bg-gray-500/20 text-gray-300 border-gray-500/40'
}

function getFactorEntries(factors: unknown, factorVector?: unknown, labels: string[] = []): [string, number][] {
  if (factors && typeof factors === 'object' && !Array.isArray(factors)) {
    const entries = Object.entries(factors as Record<string, unknown>).map(([key, value]) => [key, toNumber(value)] as [string, number])
    if (entries.length > 0) return entries
  }
  return ensureArray<unknown>(factorVector).map((value, index) => [
    labels[index] || `factor_${index + 1}`,
    toNumber(value),
  ])
}

function normalizeArrayPayload<T>(payload: unknown, keys: string[]): T[] {
  const direct = ensureArray<T>(payload)
  if (direct.length > 0 || Array.isArray(payload)) return direct
  if (!payload || typeof payload !== 'object') return []

  const record = payload as Record<string, unknown>
  for (const key of keys) {
    const rows = ensureArray<T>(record[key])
    if (rows.length > 0 || Array.isArray(record[key])) return rows
  }
  return []
}

function normalizeTrajectory(payload: unknown): TrajectoryPoint[] {
  return normalizeArrayPayload<unknown>(payload, ['trajectory', 'points', 'accuracy_trajectory', 'data'])
    .map((point, index): TrajectoryPoint | null => {
      if (!point || typeof point !== 'object' || Array.isArray(point)) return null
      const record = point as Record<string, unknown>
      const decisions = toNumber(record.decisions, NaN)
      const accuracy = toNumber(record.accuracy, NaN)
      if (!Number.isFinite(decisions) || !Number.isFinite(accuracy)) return null
      return {
        decisions,
        accuracy,
        batch: toNumber(record.batch, index + 1),
      }
    })
    .filter((point): point is TrajectoryPoint => point !== null)
}

function buildChartPath(points: TrajectoryPoint[]): string {
  if (points.length === 0) return ''
  const width = 520
  const height = 170
  const xMin = 0
  const xMax = 1000
  const yMin = 70
  const yMax = 95

  return ensureArray<TrajectoryPoint>(points).map((point, index) => {
    if (!point || typeof point !== 'object') return ''
    const xRaw = toNumber(point.decisions)
    const yRaw = toNumber(point.accuracy)
    const accuracy = yRaw <= 1 ? yRaw * 100 : yRaw
    const x = Math.max(0, Math.min(width, ((xRaw - xMin) / (xMax - xMin)) * width))
    const y = Math.max(0, Math.min(height, height - ((accuracy - yMin) / (yMax - yMin)) * height))
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  }).filter(Boolean).join(' ')
}

async function fetchPreview<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }
  if (!response.ok) {
    throw new Error(`S2P preview request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export default function S2PPreviewTab() {
  const [queue, setQueue] = useState<ScoredInvoice[]>([])
  const [conservation, setConservation] = useState<ConservationStatus | null>(null)
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadPreviewData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [queuePayload, conservationPayload, compoundingPayload, suppliersPayload, configPayload] = await Promise.all([
        fetchPreview<unknown>('/api/s2p/preview/queue?limit=5'),
        fetchPreview<unknown>('/api/s2p/preview/conservation'),
        fetchPreview<unknown>('/api/s2p/preview/compounding'),
        fetchPreview<unknown>('/api/s2p/preview/suppliers?limit=2'),
        fetchPreview<unknown>('/api/s2p/preview/config'),
      ])

      setQueue(normalizeArrayPayload<ScoredInvoice>(queuePayload, ['queue', 'invoices', 'items']))
      setConservation((conservationPayload && typeof conservationPayload === 'object' ? conservationPayload : null) as ConservationStatus | null)
      setTrajectory(normalizeTrajectory(compoundingPayload))
      setSuppliers(normalizeArrayPayload<Supplier>(suppliersPayload, ['suppliers', 'items']))
      setConfig((configPayload && typeof configPayload === 'object' ? configPayload : null) as Config | null)
    } catch (err) {
      console.error('[S2PPreviewTab] Failed to load preview data:', err)
      setQueue([])
      setConservation(null)
      setTrajectory([])
      setSuppliers([])
      setConfig(null)
      setError(UNAVAILABLE_MESSAGE)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPreviewData()
  }, [])

  const version = config?.engine_version || conservation?.engine_version || '0.7.23'
  const tensorShape = config?.tensor_shape || '(5,5,7)'
  const categoryCount = ensureArray<string>(config?.categories).length || 5
  const factorLabels = ensureArray<string>(config?.factors)
  const factorCount = factorLabels.length || 7
  const status = conservation?.status || 'AMBER'
  const product = toNumber(conservation?.conservation_product)
  const threshold = toNumber(conservation?.conservation_threshold)
  const initialAccuracy = trajectory.length > 0 ? toNumber(trajectory[0].accuracy) : 0
  const currentAccuracy = trajectory.length > 0 ? toNumber(trajectory[trajectory.length - 1].accuracy) : 0
  const initialPct = initialAccuracy <= 1 ? initialAccuracy * 100 : initialAccuracy
  const currentPct = currentAccuracy <= 1 ? currentAccuracy * 100 : currentAccuracy
  const deltaPct = currentPct - initialPct
  const chartPath = buildChartPath(trajectory)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="bg-soc-card rounded-lg border border-gray-800 p-5 text-sm text-gray-500">
          Loading S2P preview...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="max-w-2xl text-center bg-soc-card rounded-lg border border-red-500/30 p-6">
          <p className="text-base font-semibold text-red-300">{UNAVAILABLE_MESSAGE}</p>
          <p className="mt-3 text-xs text-gray-500 font-mono">{START_COMMAND}</p>
          <button
            onClick={loadPreviewData}
            className="mt-5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 rounded-lg p-6 border border-gray-800 border-l-4 border-l-blue-500">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-100">S2P Invoice Exception Copilot — Preview</h2>
            <p className="mt-2 text-sm text-gray-400">Same engine. Different domain. Both compounding.</p>
          </div>
          <span className="shrink-0 text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1 rounded-full">
            GAE {version} · Tensor {tensorShape} · {categoryCount} categories · {factorCount} factors
          </span>
        </div>
      </div>

      <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-2">
          <span className="text-sm font-semibold">Invoice Exception Queue</span>
          <span className="ml-auto text-xs bg-soc-primary/20 text-soc-primary px-2 py-0.5 rounded">
            {queue.length} invoices scored
          </span>
        </div>
        {queue.length === 0 ? (
          <div className="p-5 text-sm text-gray-500">No invoices available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-800 text-gray-500 uppercase tracking-wide">
                  <th className="text-left py-2 px-4 font-medium">Invoice ID</th>
                  <th className="text-left py-2 px-4 font-medium">Supplier</th>
                  <th className="text-left py-2 px-4 font-medium">Category</th>
                  <th className="text-right py-2 px-4 font-medium">Amount</th>
                  <th className="text-left py-2 px-4 font-medium">Action</th>
                  <th className="text-right py-2 px-4 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {ensureArray<ScoredInvoice>(queue).map((invoice, index) => {
                  const factors = getFactorEntries(invoice?.factors, invoice?.factor_vector, factorLabels)
                  return (
                    <tr key={safeKey(invoice?.invoice_id, index)} className="border-b border-gray-800/60 last:border-0">
                      <td className="py-3 px-4 align-top font-mono text-blue-300">{invoice?.invoice_id || `INV-${index + 1}`}</td>
                      <td className="py-3 px-4 align-top text-gray-200">{invoice?.supplier_name || 'Unknown supplier'}</td>
                      <td className="py-3 px-4 align-top text-gray-300">{formatCategory(invoice?.category || 'unknown')}</td>
                      <td className="py-3 px-4 align-top text-right font-mono text-gray-200">{formatCurrency(toNumber(invoice?.amount))}</td>
                      <td className="py-3 px-4 align-top">
                        <span className="inline-flex px-2 py-0.5 rounded bg-slate-800 text-gray-200 border border-gray-700">
                          {formatAction(invoice?.recommended_action || 'review')}
                        </span>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {factors.length > 0 ? factors.map(([factor, value], factorIndex) => (
                            <span
                              key={safeKey(factor, factorIndex)}
                              className="inline-flex items-center gap-1 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-gray-400"
                            >
                              {formatCategory(factor)} <span className="text-gray-200">{toNumber(value).toFixed(2)}</span>
                            </span>
                          )) : (
                            <span className="text-[10px] text-gray-600">No factor details</span>
                          )}
                        </div>
                      </td>
                      <td className={`py-3 px-4 align-top text-right font-mono font-semibold ${getConfidenceColor(toNumber(invoice?.confidence))}`}>
                        {formatPct(toNumber(invoice?.confidence))}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="bg-slate-800 rounded-lg border border-gray-800 p-5">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-gray-100">Conservation Law</h3>
            <span className={`inline-flex px-3 py-1 rounded-full border text-xs font-bold ${getStatusColor(status)}`}>
              {status}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-soc-bg rounded border border-gray-700 p-4">
              <div className="text-xs text-gray-500 mb-1">Auto-approve rate</div>
              <div className="text-2xl font-bold text-gray-100">{formatPct(toNumber(conservation?.auto_approve_pct))}</div>
            </div>
            <div className="bg-soc-bg rounded border border-gray-700 p-4">
              <div className="text-xs text-gray-500 mb-1">Verified decisions</div>
              <div className="text-2xl font-bold text-gray-100">{toNumber(conservation?.verified_decisions).toLocaleString()}</div>
            </div>
          </div>
          <div className="mt-4 rounded border border-gray-700 bg-soc-bg p-4 text-sm text-gray-300">
            Conservation: α·q·V = <span className="font-mono text-blue-300">{product.toFixed(1)}</span>
            {' '}&gt; θ_min = <span className="font-mono text-blue-300">{threshold.toFixed(2)}</span>
          </div>
        </div>

        <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-gray-100">Accuracy Trajectory</h3>
            <span className="text-xs text-gray-600">0 to 1000 decisions</span>
          </div>
          {trajectory.length === 0 ? (
            <div className="h-56 flex items-center justify-center text-sm text-gray-500">No trajectory data available</div>
          ) : (
            <>
              <div className="h-56">
                <svg viewBox="0 0 580 220" className="h-full w-full" role="img" aria-label="Accuracy trajectory">
                  <line x1="40" y1="20" x2="40" y2="190" stroke="#374151" strokeWidth="1" />
                  <line x1="40" y1="190" x2="560" y2="190" stroke="#374151" strokeWidth="1" />
                  <text x="8" y="25" fill="#6b7280" fontSize="11">95%</text>
                  <text x="8" y="194" fill="#6b7280" fontSize="11">70%</text>
                  <text x="40" y="210" fill="#6b7280" fontSize="11">0</text>
                  <text x="532" y="210" fill="#6b7280" fontSize="11">1000</text>
                  <path d={`M 40 190 h 520 M 40 122 h 520 M 40 54 h 520`} stroke="#1f2937" strokeWidth="1" fill="none" />
                  <g transform="translate(40 20)">
                    <path d={chartPath} fill="none" stroke="#3b82f6" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                  </g>
                </svg>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="bg-soc-bg rounded border border-gray-700 p-3">
                  <div className="text-gray-500">Initial</div>
                  <div className="font-mono text-gray-200">{formatPct(initialPct)}</div>
                </div>
                <div className="bg-soc-bg rounded border border-gray-700 p-3">
                  <div className="text-gray-500">Current</div>
                  <div className="font-mono text-gray-200">{formatPct(currentPct)}</div>
                </div>
                <div className="bg-soc-bg rounded border border-gray-700 p-3">
                  <div className="text-gray-500">Improvement</div>
                  <div className="font-mono text-green-400">+{deltaPct.toFixed(1)} pp</div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-2">
          <span className="text-sm font-semibold">Supplier Intelligence</span>
          <span className="ml-auto text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded">LIVE from fixture</span>
        </div>
        {suppliers.length === 0 ? (
          <div className="p-5 text-sm text-gray-500">No supplier intelligence available</div>
        ) : (
          <div className="p-5 grid gap-4 md:grid-cols-2">
            {ensureArray<Supplier>(suppliers).slice(0, 2).map((supplier, index) => {
              const q1q2 = toNumber(supplier?.otif?.q1_q2)
              const q3 = toNumber(supplier?.otif?.q3)
              const baseline = toNumber(supplier?.exception_rate?.baseline)
              const current = toNumber(supplier?.exception_rate?.current)
              const exceptionSpike = baseline > 0 && current > baseline * 2
              return (
                <div key={safeKey(supplier?.supplier_name, index)} className="rounded-lg border border-gray-800 bg-slate-800 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-100">{supplier?.supplier_name || 'Unknown supplier'}</h3>
                      <p className="text-xs text-gray-500">{supplier?.region || 'Unknown region'}</p>
                    </div>
                    <span className="text-xs rounded bg-soc-bg px-2 py-0.5 text-gray-300 border border-gray-700">
                      {supplier?.financial_health_trend || 'unknown'}
                    </span>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded border border-gray-700 bg-soc-bg p-3">
                      <div className="text-gray-500 mb-1">OTIF</div>
                      <div className="font-mono text-gray-200">
                        {formatPct(q1q2)} <span className={q3 < q1q2 ? 'text-red-400' : 'text-green-400'}>→</span> {formatPct(q3)}
                      </div>
                    </div>
                    <div className="rounded border border-gray-700 bg-soc-bg p-3">
                      <div className="text-gray-500 mb-1">Exception rate</div>
                      <div className={`font-mono ${exceptionSpike ? 'text-red-400' : 'text-gray-200'}`}>
                        {formatPct(baseline)} → {formatPct(current)}
                      </div>
                    </div>
                    <div className="rounded border border-gray-700 bg-soc-bg p-3 col-span-2">
                      <div className="text-gray-500 mb-1">Lead time</div>
                      <div className="font-mono text-gray-200">
                        {toNumber(supplier?.lead_time?.contractual_days)} contractual days · {toNumber(supplier?.lead_time?.actual_q4_days)} actual Q4 days
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
