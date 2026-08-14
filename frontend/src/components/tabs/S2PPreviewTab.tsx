import { useEffect, useMemo, useState } from 'react'
import CompliancePanel from '../CompliancePanel'
import DisruptionSimPanel from '../DisruptionSimPanel'
import FinancialImpactPanel from '../FinancialImpactPanel'
import NoveltyPanel from '../NoveltyPanel'
import ProcessFusionPanel from '../ProcessFusionPanel'
import TrendCorrelationPanel from '../TrendCorrelationPanel'
import WorkingCapitalPanel from '../WorkingCapitalPanel'
import DomainApplicabilityPanel from '../DomainApplicabilityPanel'

// S2P Preview provenance declaration (v1.2 section 7):
// - Panels show SUMMARY context from S2P backend APIs
// - Default: "context" (most panels compute from real decisions)
// - Exception: TrendCorrelation defaults to "sample" (fixture data)
// - ProcessFusion uses API-provided provenance (cross-graph endpoint)
// - No "sample" headline without sample badge (F-25 compliance)

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
// Use the Vite same-origin proxy in the demo. A VITE override remains
// available for standalone deployments.
const S2P_API = env?.VITE_S2P_API_URL || ''

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
  risk_level?: string
  intelligence?: SupplierIntelligence
  lead_time?: { contractual?: number; actual_q4?: number }
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
  profile?: SupplierProfile | null
}

interface ProvenancedMetric {
  value?: unknown
  source?: string
  provenance_tier?: string
  provenance_label?: string
  measured?: boolean
  verified?: boolean
  source_count?: number
  label?: string
  warning?: string
}

interface SupplierIntelligenceDepth {
  headline_tier?: string
  label?: string
  metrics_past_threshold?: number
  metrics_total?: number
  per_metric?: Record<string, { tier?: string; count?: number; source_count?: number }>
  trajectory?: Record<string, unknown>
}

interface SupplierIntelligenceRisk {
  tier?: string
  basis?: string
  basis_detail?: string
  source_count?: number
  reason?: string
  warnings?: string[]
  contributing_metrics?: Array<Record<string, unknown>>
}

interface SupplierIntelligenceCaught {
  count?: number
  flagged_invoice_value?: number
  currency?: string
  source?: string
  label?: string
  caveat?: string
  warnings?: string[]
}

interface EconomicExposure {
  amount?: number
  currency?: string
  computation?: string
  source_breakdown?: Record<string, unknown>
  caveat?: string
  warnings?: string[]
}

interface BehavioralMetrics {
  learned?: Record<string, ProvenancedMetric>
  context?: Record<string, ProvenancedMetric>
  unavailable?: string[] | Record<string, unknown>
  warnings?: string[]
}

interface SupplierIntelligence {
  depth?: SupplierIntelligenceDepth
  risk?: SupplierIntelligenceRisk
  caught?: SupplierIntelligenceCaught
  behavioral_metrics?: BehavioralMetrics
  economic_exposure?: EconomicExposure | { last_quarter?: EconomicExposure } | null
  new_manager_summary?: string
  warnings?: string[]
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

function formatMetricValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Unavailable'
  if (typeof value === 'number') {
    if (Math.abs(value) <= 1) return formatPct(value, 1)
    return value.toLocaleString()
  }
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
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

function metricRows(metrics?: Record<string, ProvenancedMetric>): Array<[string, ProvenancedMetric]> {
  return Object.entries(metrics || {}).sort(([left], [right]) => left.localeCompare(right))
}

function exposureBlock(intelligence?: SupplierIntelligence): EconomicExposure | null {
  const exposure = intelligence?.economic_exposure
  if (!exposure) return null
  if ('last_quarter' in exposure) return exposure.last_quarter || null
  return exposure as EconomicExposure
}

function safeCaveat(text?: string): string {
  if (!text) return 'Exposure is a mixed-source estimate, not confirmed savings.'
  return text
    .replace(/\bROI\b/gi, 'return claim')
    .replace(/recovered dollars/gi, 'recovery claim')
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${S2P_API}${path}`)
  if (!response.ok) throw new Error(`S2P preview request failed: ${response.status}`)
  return response.json() as Promise<T>
}

async function fetchOptionalJson<T>(path: string, fallback: T, timeoutMs = 3000): Promise<T> {
  const request = fetchJson<T>(path).catch(() => fallback)
  return Promise.race([
    request,
    new Promise<T>((resolve) => setTimeout(() => resolve(fallback), timeoutMs)),
  ])
}

function Badge({ children, tone = 'gray' }: { children: string; tone?: 'blue' | 'green' | 'yellow' | 'gray' | 'red' }) {
  const classes = {
    blue: 'border-blue-500/40 bg-blue-500/10 text-blue-200',
    green: 'border-green-500/40 bg-green-500/10 text-green-200',
    yellow: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200',
    gray: 'border-gray-700 bg-slate-900 text-gray-300',
    red: 'border-red-500/40 bg-red-500/10 text-red-200',
  }[tone]
  return <span className={`rounded border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${classes}`}>{children}</span>
}

function MetricCard({ name, metric, kind }: { name: string; metric: ProvenancedMetric; kind: 'learned' | 'context' }) {
  const learned = kind === 'learned'
  return (
    <div className="rounded border border-gray-800 bg-slate-950/60 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold text-gray-100">{formatLabel(name)}</div>
          <div className="mt-1 font-mono text-sm text-gray-200">{formatMetricValue(metric.value)}</div>
        </div>
        <Badge tone={learned ? 'green' : 'yellow'}>{learned ? 'learned' : 'context'}</Badge>
      </div>
      <div className="mt-2 space-y-1 text-[11px] leading-4 text-gray-500">
        <div>
          {metric.source || (learned ? 'verified_outcomes' : 'context')} · {metric.provenance_tier || (learned ? 'learned' : 'context')}
        </div>
        <div>measured {metric.measured ? 'yes' : 'no'} · verified {metric.verified ? 'yes' : 'no'}</div>
        {metric.source_count !== undefined && <div>{metric.source_count.toLocaleString()} source rows</div>}
        {(metric.provenance_label || metric.label || metric.warning) && (
          <div className="text-gray-400">{metric.provenance_label || metric.label || metric.warning}</div>
        )}
      </div>
    </div>
  )
}

function SupplierIntelligenceProfilePanel({
  profile,
  supplier,
}: { profile?: SupplierProfile | null; supplier?: SupplierProfile }) {
  const intelligence = profile?.intelligence
  const depth = intelligence?.depth
  const risk = intelligence?.risk
  const caught = intelligence?.caught
  const learnedRows = metricRows(intelligence?.behavioral_metrics?.learned)
  const contextRows = metricRows(intelligence?.behavioral_metrics?.context)
  const unavailable = intelligence?.behavioral_metrics?.unavailable
  const exposure = exposureBlock(intelligence)
  const canonicalRisk = risk?.tier || 'integration_pending'
  const sourceCount = risk?.source_count ?? learnedRows.find(([, metric]) => metric.source_count !== undefined)?.[1].source_count

  if (!profile || !intelligence) {
    return (
      <div className="rounded-lg border border-gray-800 bg-soc-card p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-gray-100">Supplier Intelligence Profile</h3>
          <Badge tone="gray">integration pending</Badge>
        </div>
        <p className="mt-3 text-sm leading-6 text-gray-400">
          Supplier intelligence is not available yet. Process verified decisions to build learned supplier evidence.
        </p>
        {supplier?.lead_time && (
          <div className="mt-4 rounded border border-gray-800 bg-slate-950/60 p-3">
            <div className="text-xs font-semibold text-gray-100">Lead time</div>
            <div className="mt-1 font-mono text-sm text-gray-200">
              {supplier.lead_time.contractual ?? 0} contractual days · {supplier.lead_time.actual_q4 ?? 0} actual Q4 days
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <section className="rounded-lg border border-emerald-500/20 bg-soc-card" aria-label="Supplier Intelligence Profile">
      <div className="border-b border-gray-800 px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-gray-100">Supplier Intelligence Profile</h3>
            <p className="mt-1 text-xs text-gray-500">{supplierName(profile)} · compiled from verified outcomes and context sources</p>
          </div>
          <Badge tone="green">buyer visible</Badge>
        </div>
        {intelligence.new_manager_summary && (
          <p className="mt-4 rounded border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm leading-6 text-emerald-100">
            {intelligence.new_manager_summary}
          </p>
        )}
        {supplier?.lead_time && (
          <div className="mt-4 rounded border border-gray-800 bg-slate-950/60 p-3">
            <div className="text-xs font-semibold text-gray-100">Lead time</div>
            <div className="mt-1 font-mono text-sm text-gray-200">
              {supplier.lead_time.contractual ?? 0} contractual days · {supplier.lead_time.actual_q4 ?? 0} actual Q4 days
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-5 p-5 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-5">
          <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-gray-100">Intelligence Depth</h4>
              <Badge tone="blue">{formatLabel(depth?.headline_tier, 'none')}</Badge>
            </div>
            <p className="mt-2 text-sm text-gray-300">{depth?.label || '0 of 0 metrics past threshold'}</p>
            <div className="mt-3 h-2 overflow-hidden rounded bg-slate-800">
              <div
                className="h-full rounded bg-emerald-400"
                style={{
                  width: `${Math.min(100, Math.round((toNumber(depth?.metrics_past_threshold) / Math.max(1, toNumber(depth?.metrics_total, 1))) * 100))}%`,
                }}
              />
            </div>
            <div className="mt-4 space-y-2">
              {Object.entries(depth?.per_metric || {}).map(([name, metric]) => (
                <div key={name} className="flex items-center justify-between rounded border border-gray-800 bg-slate-900 px-3 py-2 text-xs">
                  <span className="text-gray-300">{formatLabel(name)}</span>
                  <span className="font-mono text-gray-400">
                    {formatLabel(metric.tier)} · {toNumber(metric.count ?? metric.source_count).toLocaleString()} verified decisions
                  </span>
                </div>
              ))}
              {Object.keys(depth?.per_metric || {}).length === 0 && (
                <div className="rounded border border-gray-800 bg-slate-900 px-3 py-2 text-xs text-gray-500">
                  No verified metric depth yet.
                </div>
              )}
            </div>
            {depth?.trajectory && Object.keys(depth.trajectory).length > 0 && (
              <div className="mt-4 rounded border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-100">
                Projection: {JSON.stringify(depth.trajectory)}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-gray-100">Risk with Basis</h4>
              <Badge tone={canonicalRisk === 'high' ? 'red' : canonicalRisk === 'low' ? 'green' : 'yellow'}>
                {formatLabel(canonicalRisk)}
              </Badge>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded border border-gray-800 bg-slate-900 p-3">
                <div className="text-gray-500">Basis</div>
                <div className="mt-1 text-gray-100">{formatLabel(risk?.basis, 'integration pending')}</div>
              </div>
              <div className="rounded border border-gray-800 bg-slate-900 p-3">
                <div className="text-gray-500">Source count</div>
                <div className="mt-1 font-mono text-gray-100">{sourceCount !== undefined ? sourceCount.toLocaleString() : '0'}</div>
              </div>
            </div>
            {(risk?.reason || risk?.basis_detail) && <p className="mt-3 text-xs leading-5 text-gray-400">{risk.reason || risk.basis_detail}</p>}
            {profile.risk_level && (
              <p className="mt-3 text-xs leading-5 text-gray-500">
                Legacy context risk level: {profile.risk_level}. Supplier intelligence risk above is canonical.
              </p>
            )}
            {(risk?.warnings || intelligence.warnings || []).map((warning) => (
              <p key={warning} className="mt-2 text-xs text-yellow-200">{formatLabel(warning)}</p>
            ))}
          </div>

          <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
            <h4 className="text-sm font-semibold text-gray-100">What the System Caught</h4>
            <div className="mt-3 flex items-end justify-between gap-3">
              <div>
                <div className="font-mono text-2xl text-gray-100">{toNumber(caught?.count).toLocaleString()}</div>
                <div className="text-xs text-gray-500">verified caught discrepancies</div>
              </div>
              {caught?.flagged_invoice_value !== undefined && (
                <div className="text-right">
                  <div className="font-mono text-lg text-yellow-200">{formatCurrency(caught.flagged_invoice_value)}</div>
                  <div className="text-xs text-gray-500">{caught.currency || 'USD'} flagged invoice value</div>
                </div>
              )}
            </div>
            <p className="mt-3 text-xs leading-5 text-gray-400">
              {toNumber(caught?.count) > 0
                ? caught?.label || 'Confirmed discrepancies from verified outcomes.'
                : 'No verified caught discrepancies yet. This does not mean there are no supplier issues.'}
            </p>
          </div>
        </div>

        <div className="space-y-5">
          <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-gray-100">Learned / Verified Metrics</h4>
              <Badge tone="green">learned</Badge>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {learnedRows.map(([name, metric]) => <MetricCard key={name} name={name} metric={metric} kind="learned" />)}
              {learnedRows.length === 0 && (
                <div className="rounded border border-gray-800 bg-slate-900 p-3 text-xs text-gray-500">
                  No learned verified metrics yet.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-gray-100">Context / Fixture Metrics</h4>
              <Badge tone="yellow">integration pending</Badge>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {contextRows.map(([name, metric]) => <MetricCard key={name} name={name} metric={metric} kind="context" />)}
              {contextRows.length === 0 && (
                <div className="rounded border border-gray-800 bg-slate-900 p-3 text-xs text-gray-500">
                  No context metrics returned.
                </div>
              )}
            </div>
            {Array.isArray(unavailable) && unavailable.length > 0 && (
              <div className="mt-3 rounded border border-gray-800 bg-slate-900 p-3 text-xs text-gray-500">
                Unavailable: {unavailable.map((item) => formatLabel(item)).join(', ')}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-800 bg-slate-950/60 p-4">
            <h4 className="text-sm font-semibold text-gray-100">Economic Exposure</h4>
            {exposure ? (
              <>
                <div className="mt-3 font-mono text-2xl text-gray-100">{formatCurrency(exposure.amount)}</div>
                {exposure.computation && <p className="mt-2 text-xs text-gray-400">{exposure.computation}</p>}
                <p className="mt-3 rounded border border-yellow-500/20 bg-yellow-500/10 p-3 text-xs leading-5 text-yellow-100">
                  {safeCaveat(exposure.caveat)}
                </p>
                {exposure.source_breakdown && (
                  <div className="mt-3 grid gap-2 text-xs">
                    {Object.entries(exposure.source_breakdown).map(([name, value]) => (
                      <div key={name} className="rounded border border-gray-800 bg-slate-900 px-3 py-2 text-gray-400">
                        {formatLabel(name)}: {formatMetricValue(value)}
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="mt-3 text-sm text-gray-400">Economic exposure unavailable. Connect verified amount sources before using exposure for escalation.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  )
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
          fetchOptionalJson<QueueResponse>('/api/s2p/preview/queue', {}, 2500),
          fetchJson<ConservationResponse>('/api/s2p/preview/conservation'),
          fetchJson<SuppliersResponse>('/api/s2p/preview/suppliers'),
        ])
        const supplierRows = suppliers.suppliers || []
        const chenLin = supplierRows.find((supplier) => /chen-lin/i.test(supplierName(supplier)))
        const selectedSupplier = chenLin || supplierRows[0]
        let profile: SupplierProfile | null = null
        if (selectedSupplier?.supplier_id) {
          profile = await fetchOptionalJson<SupplierProfile | null>(
            `/api/s2p/suppliers/${encodeURIComponent(selectedSupplier.supplier_id)}/profile`,
            null,
            3000,
          )
        }
        if (!cancelled) setData({ queue, conservation, suppliers, profile })
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
  const intelligenceProfile = data?.profile
  const preferredSuppliers = useMemo(() => {
    const chenLin = suppliers.find((supplier) => /chen-lin/i.test(supplierName(supplier)))
    return chenLin ? [chenLin, ...suppliers.filter((supplier) => supplier !== chenLin)] : suppliers
  }, [suppliers])

  if (loading) {
    return <div className="rounded-lg border border-gray-800 bg-soc-card p-6 text-sm text-gray-400">Loading S2P Preview...</div>
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div className="rounded-lg border border-gray-800 bg-soc-card p-6">
          <h2 className="text-lg font-semibold text-gray-100">S2P Preview</h2>
          <p className="mt-2 text-sm text-gray-400">S2P Preview backend is not available. Preview data will appear when the S2P service is reachable.</p>
          <p className="mt-3 font-mono text-xs text-gray-500">{error}</p>
        </div>
        <DomainApplicabilityPanel />
      </div>
    )
  }

  const conservation = data.conservation

  return (
    <div className="space-y-6">
      <DomainApplicabilityPanel />
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

        <div data-testid="supplier-profile" className="rounded-lg border border-gray-800 bg-soc-card">
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
                {supplier.lead_time && (
                  <div className="mt-3 rounded border border-gray-800 bg-slate-900 p-3 text-xs">
                    <div className="text-gray-500">Lead time</div>
                    <div className="mt-1 font-mono text-gray-200">
                      {supplier.lead_time.contractual ?? 0} contractual days · {supplier.lead_time.actual_q4 ?? 0} actual Q4 days
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <SupplierIntelligenceProfilePanel profile={intelligenceProfile} supplier={preferredSuppliers[0]} />

      <div className="grid gap-6 xl:grid-cols-2">
        <FinancialImpactPanel />
        <WorkingCapitalPanel />
        <DisruptionSimPanel />
        <CompliancePanel />
        <ProcessFusionPanel />
        <NoveltyPanel />
      </div>

      <TrendCorrelationPanel />

      <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-5 text-center text-sm text-blue-100">
        The engine is domain-agnostic. The intelligence is firm-specific.
      </div>
    </div>
  )
}
