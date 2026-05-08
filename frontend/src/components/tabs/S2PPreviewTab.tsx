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
  lead_time: { contractual: number; actual_q4: number }
  financial_health_trend: string
}

interface Config {
  engine_version?: string
  tensor_shape?: string
  categories?: string[]
  factors?: string[]
}

interface CrossSignalEvidence {
  decision_id?: string
  category?: string
  action?: string
  outcome?: string
  days_ago?: number
  user?: string
}

interface CrossSignal {
  signal_id?: string
  source_domain?: string
  target_domain?: string
  signal_type?: string
  entity?: string
  entity_type?: string
  summary?: string
  evidence?: CrossSignalEvidence[]
  confidence?: number
  discovered_epoch?: number
  status?: string
}

interface CrossSignalsResponse {
  signals?: CrossSignal[]
  total?: number
  active?: number
  acknowledged?: number
  source_domains?: string[]
  note?: string
}

interface WarmStartLifecycleEvent {
  event_type?: string
  timestamp_offset_days?: number
  description?: string
  metadata?: Record<string, unknown>
}

interface WarmStartEvidence {
  evidence_id?: string
  source_domain?: string
  target_domain?: string
  source_rule?: string
  target_rule?: string
  source_variant_id?: string
  target_variant_id?: string
  warm_start_prior?: number
  warm_start_source?: string
  status?: string
  conservation_status?: string
  summary?: string
  lifecycle?: WarmStartLifecycleEvent[]
  impact?: {
    invoices_caught?: number
    largest_catch_usd?: number
    supplier?: string
  }
}

interface WarmStartEvidenceResponse {
  evidence?: WarmStartEvidence[]
  total?: number
  note?: string
}

interface ChainCreditDemo {
  credit_id?: string
  source_decision_id?: string
  target_decision_id?: string
  supplier?: string
  source_decision?: {
    decision_id?: string
    amount_usd?: number
    action?: string
    analyst?: string
    timestamp_offset_days?: number
    summary?: string
  }
  target_decision?: {
    decision_id?: string
    amount_usd?: number
    action?: string
    analyst?: string
    timestamp_offset_days?: number
    summary?: string
  }
  attribution?: {
    gamma?: number
    factor_overlap?: number
    chain_reward?: number
    age_days?: number
  }
  narrative?: string
}

interface ChainCreditDemoResponse {
  chain_credits?: ChainCreditDemo[]
  summary?: Record<string, unknown>
  note?: string
}

interface DomainApplicabilityRow {
  name?: string
  short?: string
  categories?: number
  actions?: number
  factors?: number
  tensor_size?: number
  penalty_ratio?: number
  engineering_days?: number | null
  status?: string
  verification?: string
}

interface DomainApplicabilityResponse {
  domains?: DomainApplicabilityRow[]
  total?: number
  live?: number
  specified?: number
  designed?: number
  engine_version?: string
  note?: string
  cross_domain_surfaces?: string
}

const UNAVAILABLE_MESSAGE = 'S2P Preview backend is not available. Start the S2P backend server and retry.'
const START_COMMAND = 'Start with: cd s2p-copilot/backend && uvicorn app.main:app'

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

async function fetchCrossSignals(): Promise<CrossSignalsResponse> {
  const response = await fetch('/api/platform/cross-signals')
  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }
  if (!response.ok) {
    throw new Error(`Cross-copilot signal request failed: ${response.status}`)
  }
  return response.json() as Promise<CrossSignalsResponse>
}

async function fetchWarmStartEvidence(): Promise<WarmStartEvidenceResponse> {
  const response = await fetch('/api/platform/warm-start-evidence')
  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }
  if (!response.ok) {
    throw new Error(`Warm-start evidence request failed: ${response.status}`)
  }
  return response.json() as Promise<WarmStartEvidenceResponse>
}

async function fetchChainCreditDemo(): Promise<ChainCreditDemoResponse> {
  const response = await fetch('/api/platform/chain-credit-demo')
  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }
  if (!response.ok) {
    throw new Error(`Chain-credit demo request failed: ${response.status}`)
  }
  return response.json() as Promise<ChainCreditDemoResponse>
}

async function fetchDomainApplicability(): Promise<DomainApplicabilityResponse> {
  const response = await fetch('/api/platform/domain-applicability')
  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }
  if (!response.ok) {
    throw new Error(`Domain applicability request failed: ${response.status}`)
  }
  return response.json() as Promise<DomainApplicabilityResponse>
}

function getSignalStatusClass(status: string): string {
  if (status === 'acknowledged') return 'bg-green-500/15 text-green-300 border-green-500/40'
  if (status === 'active') return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40'
  return 'bg-slate-700 text-gray-300 border-gray-600'
}

function domainStatusTone(status: string) {
  if (status === 'live') return 'bg-green-500/15 text-green-300 border-green-500/30'
  if (status === 'specified') return 'bg-blue-500/15 text-blue-300 border-blue-500/30'
  if (status === 'designed') return 'bg-gray-700/70 text-gray-300 border-gray-600'
  return 'bg-amber-500/15 text-amber-300 border-amber-500/30'
}

function CrossCopilotSignalPanel({ data }: { data: CrossSignalsResponse | null }) {
  const signals = ensureArray<CrossSignal>(data?.signals)
  if (signals.length === 0) return null

  const activeCount = toNumber(data?.active)

  return (
    <div className="bg-soc-card rounded-lg border border-yellow-500/30 overflow-hidden">
      <div className="px-5 py-3 border-b border-yellow-500/20 flex items-center gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-100">Cross-Copilot Signals</h3>
          <p className="mt-1 text-xs text-gray-400">Shared graph context surfaced supplier risk outside the S2P copilot's local view.</p>
        </div>
        <span className="ml-auto shrink-0 text-xs bg-yellow-500/20 text-yellow-200 border border-yellow-500/40 px-2.5 py-1 rounded-full">
          {activeCount} active
        </span>
      </div>

      <div className="grid gap-3 p-4 xl:grid-cols-3">
        {signals.map((signal, index) => {
          const status = String(signal?.status || 'active').toLowerCase()
          const evidence = ensureArray<CrossSignalEvidence>(signal?.evidence)
          const icon = status === 'acknowledged' ? '✅' : '⚠️'
          return (
            <div key={safeKey(signal?.signal_id, index)} className="rounded-lg border border-gray-800 bg-slate-900/70 p-4">
              <div className="flex items-start gap-3">
                <span className="text-lg leading-none" aria-hidden="true">{icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="text-sm font-semibold text-gray-100">{signal?.entity || 'Unknown entity'}</h4>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${getSignalStatusClass(status)}`}>
                      {status}
                    </span>
                  </div>
                  <div className="mt-1 text-[11px] uppercase tracking-wide text-gray-500">
                    {formatCategory(signal?.signal_type || 'cross_signal')} · {formatPct(toNumber(signal?.confidence))}
                  </div>
                </div>
              </div>

              <p className="mt-3 text-xs leading-5 text-gray-300">{signal?.summary || 'No summary available.'}</p>

              {evidence.length > 0 && (
                <div className="mt-3 space-y-2">
                  {evidence.map((item, evidenceIndex) => (
                    <div key={safeKey(item?.decision_id, evidenceIndex)} className="rounded border border-gray-800 bg-slate-950/60 p-2">
                      <div className="flex items-center justify-between gap-2 text-[11px]">
                        <span className="font-mono text-blue-300">{item?.decision_id || `EVIDENCE-${evidenceIndex + 1}`}</span>
                        <span className="text-gray-500">{toNumber(item?.days_ago)}d ago</span>
                      </div>
                      <div className="mt-1 text-[11px] text-gray-400">
                        {item?.user || 'unknown user'} · {formatCategory(item?.category || 'unknown')} · {formatAction(item?.action || 'review')} · {item?.outcome || 'unverified'}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-3 border-t border-gray-800 pt-2 text-[11px] text-gray-500">
                {signal?.source_domain || 'source'} → {signal?.target_domain || 'target'}
              </div>
            </div>
          )
        })}
      </div>

      <div className="border-t border-yellow-500/20 px-5 py-3 text-xs text-yellow-100/80">
        {data?.note || 'Neither copilot was programmed to detect this. The graph discovered it.'}
      </div>
    </div>
  )
}

function WarmStartEvidencePanel({ data }: { data: WarmStartEvidenceResponse | null }) {
  const item = ensureArray<WarmStartEvidence>(data?.evidence)[0]
  if (!item) return null

  const lifecycle = ensureArray<WarmStartLifecycleEvent>(item.lifecycle)
  const shadowResult = lifecycle.find((event) => event?.event_type === 'shadow_result')
  const shadowMetadata = shadowResult?.metadata || {}

  return (
    <div className="bg-soc-card rounded-lg border border-blue-500/30 overflow-hidden">
      <div className="px-5 py-3 border-b border-blue-500/20">
        <h3 className="text-sm font-semibold text-gray-100">Cross-Domain Rule Transfer</h3>
        <p className="mt-1 text-xs text-gray-400">SOC campaign learning became an S2P exception-cluster rule after shadow validation.</p>
      </div>

      <div className="grid gap-4 p-5 xl:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-lg border border-gray-800 bg-slate-900/70 p-4">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">SOC source</div>
          <div className="mt-1 font-mono text-sm text-blue-300">{item.source_rule || 'RULE-CAMPAIGN-ESCALATE'}</div>
          <div className="mt-2 text-xs text-gray-400">{item.warm_start_source || `Win rate ${formatPct(toNumber(item.warm_start_prior))}`}</div>
        </div>

        <div className="hidden items-center text-gray-500 xl:flex">-&gt; warm-started -&gt;</div>

        <div className="rounded-lg border border-gray-800 bg-slate-900/70 p-4">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">S2P target</div>
          <div className="mt-1 font-mono text-sm text-green-300">{item.target_rule || 'RULE-S2P-EXCEPTION-CLUSTER'}</div>
          <div className="mt-2 text-xs text-gray-400">Promotion {formatCategory(item.status || 'approved')} · Conservation {item.conservation_status || 'GREEN'}</div>
        </div>
      </div>

      <div className="grid gap-4 px-5 pb-5 xl:grid-cols-2">
        <div className="rounded-lg border border-gray-800 bg-slate-950/50 p-4">
          <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Lifecycle</div>
          <div className="space-y-2">
            {lifecycle.map((event, index) => (
              <div key={safeKey(event?.event_type, index)} className="flex gap-3 rounded border border-gray-800 bg-slate-900/70 p-2 text-xs">
                <span className="w-12 shrink-0 font-mono text-gray-500">{toNumber(event?.timestamp_offset_days)}d</span>
                <div>
                  <div className="font-mono text-gray-200">{event?.event_type || 'event'}</div>
                  <div className="mt-1 text-gray-400">{event?.description || 'No description available.'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-gray-800 bg-slate-950/50 p-4">
          <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Shadow result and impact</div>
          <div className="grid gap-3 text-xs sm:grid-cols-2">
            <div className="rounded border border-gray-800 bg-slate-900/70 p-3">
              <div className="text-gray-500">Shadow win rate</div>
              <div className="mt-1 font-mono text-green-300">
                {formatPct(toNumber(shadowMetadata.win_rate))} ({toNumber(shadowMetadata.wins)}/{toNumber(shadowMetadata.comparisons)})
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-900/70 p-3">
              <div className="text-gray-500">Largest catch</div>
              <div className="mt-1 font-mono text-green-300">{formatCurrency(toNumber(item.impact?.largest_catch_usd))}</div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-900/70 p-3">
              <div className="text-gray-500">Invoices caught</div>
              <div className="mt-1 font-mono text-gray-200">{toNumber(item.impact?.invoices_caught)}</div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-900/70 p-3">
              <div className="text-gray-500">Supplier</div>
              <div className="mt-1 text-gray-200">{item.impact?.supplier || 'Unknown supplier'}</div>
            </div>
          </div>
          <p className="mt-4 text-xs leading-5 text-blue-100/80">
            SOC didn't know this would help procurement. Priya's team didn't know SOC learned it.
          </p>
        </div>
      </div>
    </div>
  )
}

function ChainCreditPanel({ data }: { data: ChainCreditDemoResponse | null }) {
  const credit = ensureArray<ChainCreditDemo>(data?.chain_credits)[0]
  if (!credit) return null

  const source = credit.source_decision || {}
  const target = credit.target_decision || {}
  const attribution = credit.attribution || {}

  return (
    <div className="bg-soc-card rounded-lg border border-green-500/30 overflow-hidden">
      <div className="px-5 py-3 border-b border-green-500/20">
        <h3 className="text-sm font-semibold text-gray-100">Chain Credit Attribution</h3>
        <p className="mt-1 text-xs text-gray-400">RL attribution links Priya's earlier hold to a later automatic catch.</p>
      </div>

      <div className="grid gap-4 p-5 xl:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-lg border border-gray-800 bg-slate-900/70 p-4">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">Source decision</div>
          <div className="mt-1 text-2xl font-bold text-gray-100">{formatCurrency(toNumber(source.amount_usd))}</div>
          <div className="mt-2 text-xs text-gray-400">
            {formatAction(source.action || 'hold_payment')} · {toNumber(source.timestamp_offset_days)}d · {source.analyst || 'analyst'}
          </div>
          <p className="mt-3 text-xs leading-5 text-gray-300">{source.summary || 'No source summary available.'}</p>
        </div>

        <div className="flex flex-col items-center justify-center text-center text-xs text-green-200">
          <span className="rounded-full border border-green-500/40 bg-green-500/15 px-3 py-1 font-mono">
            gamma={toNumber(attribution.gamma).toFixed(3)}
          </span>
          <span className="mt-2 text-gray-500">factor overlap {formatPct(toNumber(attribution.factor_overlap), 0)}</span>
        </div>

        <div className="rounded-lg border border-gray-800 bg-slate-900/70 p-4">
          <div className="text-[11px] uppercase tracking-wide text-gray-500">Target decision</div>
          <div className="mt-1 text-2xl font-bold text-green-300">{formatCurrency(toNumber(target.amount_usd))}</div>
          <div className="mt-2 text-xs text-gray-400">
            {formatAction(target.action || 'auto_hold')} · {toNumber(target.timestamp_offset_days)}d · {target.analyst || 'system_auto'}
          </div>
          <p className="mt-3 text-xs leading-5 text-gray-300">{target.summary || 'No target summary available.'}</p>
        </div>
      </div>

      <div className="border-t border-green-500/20 px-5 py-3 text-xs text-green-100/80">
        {credit.narrative || "Your first hold enabled this recovery."}
      </div>
    </div>
  )
}

function DomainApplicabilityPanel({ data }: { data: DomainApplicabilityResponse | null }) {
  const domains = ensureArray<DomainApplicabilityRow>(data?.domains)
  if (domains.length === 0) return null

  return (
    <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800 flex flex-wrap items-start gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-100">Domain Applicability</h3>
          <p className="mt-1 text-xs text-gray-500">Nine domains, one engine. Domain engineering still scales with each surface.</p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-full border border-green-500/30 bg-green-500/10 px-2 py-1 text-green-300">{toNumber(data?.live)} live</span>
          <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-blue-300">{toNumber(data?.specified)} specified</span>
          <span className="rounded-full border border-gray-600 bg-gray-800 px-2 py-1 text-gray-300">{toNumber(data?.designed)} designed</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 text-left text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Domain</th>
              <th className="px-4 py-3 font-medium">Shape</th>
              <th className="px-4 py-3 font-medium">Penalty</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Est.</th>
            </tr>
          </thead>
          <tbody>
            {domains.map((domain, index) => {
              const status = String(domain?.status || 'designed').toLowerCase()
              const categories = toNumber(domain?.categories)
              const actions = toNumber(domain?.actions)
              const factors = toNumber(domain?.factors)
              const engineeringDays = domain?.engineering_days
              return (
                <tr
                  key={safeKey(domain?.short || domain?.name, index)}
                  className="border-b border-gray-800/70 last:border-0 hover:bg-gray-800/30"
                  title={domain?.verification || undefined}
                >
                  <td className="px-4 py-3">
                    <div className="font-semibold text-gray-200">{domain?.short || 'Domain'}</div>
                    <div className="mt-0.5 text-[11px] text-gray-500">{domain?.name || 'Unnamed domain'}</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-300">({categories},{actions},{factors})</td>
                  <td className="px-4 py-3 font-mono text-gray-300">{toNumber(domain?.penalty_ratio)}:1</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full border px-2 py-1 text-[11px] uppercase tracking-wide ${domainStatusTone(status)}`}>
                      {status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {typeof engineeringDays === 'number' ? `${engineeringDays}d` : '-'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="border-t border-gray-800 px-5 py-3 text-xs text-gray-400 space-y-1">
        <p>{data?.note || 'Domain expansion requires explicit engineering for each domain surface.'}</p>
        <p className="text-gray-500">{data?.cross_domain_surfaces || 'Cross-domain surfaces grow with each additional domain.'}</p>
      </div>
    </div>
  )
}

export default function S2PPreviewTab() {
  const [queue, setQueue] = useState<ScoredInvoice[]>([])
  const [conservation, setConservation] = useState<ConservationStatus | null>(null)
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [config, setConfig] = useState<Config | null>(null)
  const [crossSignals, setCrossSignals] = useState<CrossSignalsResponse | null>(null)
  const [warmStartEvidence, setWarmStartEvidence] = useState<WarmStartEvidenceResponse | null>(null)
  const [chainCreditDemo, setChainCreditDemo] = useState<ChainCreditDemoResponse | null>(null)
  const [domainApplicability, setDomainApplicability] = useState<DomainApplicabilityResponse | null>(null)
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
      console.debug('[S2PPreviewTab] Preview data unavailable:', err)
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

  const loadCrossSignals = async () => {
    try {
      const payload = await fetchCrossSignals()
      setCrossSignals(payload && typeof payload === 'object' ? payload : null)
    } catch (err) {
      console.debug('[S2PPreviewTab] Cross-copilot signals unavailable:', err)
      setCrossSignals(null)
    }
  }

  const loadWarmStartEvidence = async () => {
    try {
      const payload = await fetchWarmStartEvidence()
      setWarmStartEvidence(payload && typeof payload === 'object' ? payload : null)
    } catch (err) {
      console.debug('[S2PPreviewTab] Warm-start evidence unavailable:', err)
      setWarmStartEvidence(null)
    }
  }

  const loadChainCreditDemo = async () => {
    try {
      const payload = await fetchChainCreditDemo()
      setChainCreditDemo(payload && typeof payload === 'object' ? payload : null)
    } catch (err) {
      console.debug('[S2PPreviewTab] Chain-credit demo unavailable:', err)
      setChainCreditDemo(null)
    }
  }

  const loadDomainApplicability = async () => {
    try {
      const payload = await fetchDomainApplicability()
      setDomainApplicability(payload && typeof payload === 'object' ? payload : null)
    } catch (err) {
      console.debug('[S2PPreviewTab] Domain applicability unavailable:', err)
      setDomainApplicability(null)
    }
  }

  useEffect(() => {
    loadPreviewData()
    loadCrossSignals()
    loadWarmStartEvidence()
    loadChainCreditDemo()
    loadDomainApplicability()
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
      <div className="space-y-6">
        <CrossCopilotSignalPanel data={crossSignals} />
        <WarmStartEvidencePanel data={warmStartEvidence} />
        <ChainCreditPanel data={chainCreditDemo} />
        <DomainApplicabilityPanel data={domainApplicability} />
        <div className="flex items-center justify-center h-96">
          <div className="max-w-2xl text-center bg-soc-card rounded-lg border border-red-500/30 p-6">
            <p className="text-base font-semibold text-red-300">{UNAVAILABLE_MESSAGE}</p>
            <p className="mt-3 text-xs text-gray-500 font-mono">{START_COMMAND}</p>
            <button
              onClick={() => {
                loadPreviewData()
                loadCrossSignals()
                loadWarmStartEvidence()
                loadChainCreditDemo()
                loadDomainApplicability()
              }}
              className="mt-5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-colors"
            >
              Retry
            </button>
          </div>
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

      <CrossCopilotSignalPanel data={crossSignals} />
      <WarmStartEvidencePanel data={warmStartEvidence} />
      <ChainCreditPanel data={chainCreditDemo} />
      <DomainApplicabilityPanel data={domainApplicability} />

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
                        {toNumber(supplier?.lead_time?.contractual)} contractual days · {toNumber(supplier?.lead_time?.actual_q4)} actual Q4 days
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
