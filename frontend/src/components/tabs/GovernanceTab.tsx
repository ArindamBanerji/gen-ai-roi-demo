import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  Download,
  FileText,
  GitBranch,
  RefreshCw,
  Scale,
  Shield,
} from 'lucide-react'
import { ensureArray, ensureNumber, ensureString, safeKey } from '../../lib/guards'

const SOC_API = 'http://127.0.0.1:8001'

type PanelStatus = 'idle' | 'loading' | 'ready' | 'error'

interface AuditEntry {
  decision_id?: string | null
  decision_id_full?: string | null
  alert_id?: string | null
  action?: string | null
  recommendation?: string | null
  category?: string | null
  confidence?: number | null
  outcome?: string | null
  timestamp?: string | null
  hash?: string | null
}

interface EvidenceRoomData {
  generated_at?: string | null
  audit_trail?: {
    entries?: AuditEntry[] | null
    total?: number | null
  } | null
  conservation?: {
    status?: string | null
    product?: number | null
    threshold?: number | null
    verified_decisions?: number | null
    frozen?: boolean | null
    q?: number | null
    alpha?: number | null
    V?: number | null
    theta_min?: number | null
    signal?: number | null
  } | null
  hash_chain?: {
    verified?: boolean | null
    entries?: number | null
    status?: string | null
    valid_entries?: number | null
    total_entries?: number | null
  } | null
}

interface GovernanceSection {
  article?: string | null
  title?: string | null
  status?: string | null
  evidence_count?: number | null
  legal_disclaimer?: string | null
}

interface GovernanceSummary {
  title?: string | null
  generated_at?: string | null
  overall_assessment?: string | null
  legal_disclaimer?: string | null
  sections?: GovernanceSection[] | null
}

interface EuAiActArticle {
  status?: 'COMPLIANT' | 'INVESTIGATION' | string | null
  title?: string | null
  description?: string | null
}

interface EuAiActCompliance {
  article_9?: EuAiActArticle | null
  article_15?: EuAiActArticle | null
}

interface SocComplianceResponse {
  eu_ai_act?: EuAiActCompliance | null
}

interface EvolutionEvent {
  id?: string | null
  event_type?: string | null
  variant_id?: string | null
  artifact_type?: string | null
  description?: string | null
  graph_context?: Record<string, unknown> | null
  metadata?: Record<string, unknown> | null
  timestamp?: string | null
  timestamp_epoch?: number | null
}

interface EvolutionEventsResponse {
  events?: EvolutionEvent[] | null
  count?: number | null
  limit?: number | null
}

interface RLRewardEntry {
  decision_id?: string | null
  alert_id?: string | null
  category?: string | null
  action?: string | null
  severity?: number | null
  outcome?: string | null
  base_reward?: number | null
  reward_weight?: number | null
  graded_reward?: number | null
  eta_applied?: number | null
  explanation?: string | null
}

interface RLRewardDemoResponse {
  reward_breakdown?: RLRewardEntry[] | null
  summary?: {
    total_decisions?: number | null
    correct?: number | null
    incorrect?: number | null
    mean_severity?: number | null
    mean_reward_weight?: number | null
  } | null
  note?: string | null
}

interface RLExplorationEntry {
  epoch?: number | null
  decisions_in_epoch?: number | null
  conservation_margin?: number | null
  exploration_rate?: number | null
  status?: string | null
  proposals_generated?: number | null
  proposals_accepted?: number | null
  note?: string | null
}

interface RLExplorationDemoResponse {
  exploration_log?: RLExplorationEntry[] | null
  summary?: {
    current_status?: string | null
    current_margin?: number | null
    current_rate?: number | null
    total_proposals?: number | null
    total_accepted?: number | null
  } | null
  note?: string | null
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

function formatTimestamp(value: string | number | null | undefined): string {
  if (value == null || value === '') return 'time unknown'
  if (typeof value === 'number') {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatPercent(value: unknown): string {
  const numeric = ensureNumber(value, NaN)
  if (!Number.isFinite(numeric)) return 'not reported'
  return `${Math.round(numeric * 1000) / 10}%`
}

function formatMetric(value: unknown, decimals = 4): string {
  const numeric = ensureNumber(value, NaN)
  if (!Number.isFinite(numeric)) return 'not reported'
  return numeric.toFixed(decimals)
}

function formatSignedMetric(value: unknown, decimals = 3): string {
  const numeric = ensureNumber(value, NaN)
  if (!Number.isFinite(numeric)) return 'not reported'
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${numeric.toFixed(decimals)}`
}

function statusBadgeClass(status: string | null | undefined): string {
  switch ((status ?? '').toUpperCase()) {
    case 'GREEN':
    case 'READY':
    case 'VERIFIED':
    case 'COMPLIANT':
      return 'border-green-500/40 bg-green-500/15 text-green-300'
    case 'AMBER':
    case 'ATTENTION':
    case 'PAUSED':
    case 'CALIBRATING':
    case 'INVESTIGATION':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-300'
    case 'RED':
    case 'BROKEN':
      return 'border-red-500/40 bg-red-500/15 text-red-300'
    default:
      return 'border-slate-600 bg-slate-800 text-slate-300'
  }
}

function eventVisual(eventType: string | null | undefined) {
  switch (eventType) {
    case 'variant_created':
      return { label: 'Generated', dot: 'bg-blue-400', text: 'text-blue-200' }
    case 'shadow_started':
      return { label: 'Shadow Testing', dot: 'bg-purple-400', text: 'text-purple-200' }
    case 'shadow_result':
      return { label: 'Shadow Result', dot: 'bg-orange-400', text: 'text-orange-200' }
    case 'promotion_approved':
      return { label: 'Promoted ✅', dot: 'bg-green-400', text: 'text-green-200' }
    case 'promotion_rejected':
      return { label: 'Rejected ✗', dot: 'bg-red-400', text: 'text-red-200' }
    case 'rollback':
      return { label: 'Rolled Back ⚠️', dot: 'bg-red-500', text: 'text-red-200' }
    default:
      return { label: ensureString(eventType, 'Event'), dot: 'bg-slate-400', text: 'text-slate-200' }
  }
}

function graphContextSummary(context: Record<string, unknown> | null | undefined): string[] {
  if (!context) return []
  const parts: string[] = []
  const campaignId = ensureString(context.campaign_id, '')
  if (campaignId) parts.push(`campaign ${campaignId}`)

  const affectedCategories = ensureArray<string>(context.affected_categories)
  if (affectedCategories.length > 0) parts.push(`categories ${affectedCategories.join(', ')}`)

  const nodesInvolved = context.nodes_involved
  if (Array.isArray(nodesInvolved)) parts.push(`${nodesInvolved.length} nodes`)
  else if (typeof nodesInvolved === 'number') parts.push(`${nodesInvolved} nodes`)

  const evidenceType = ensureString(context.evidence_type, '')
  if (evidenceType) parts.push(evidenceType.replace(/_/g, ' '))

  const driftFactor = ensureString(context.factor, '') || ensureString(context.drift_factor, '')
  if (driftFactor) parts.push(`factor ${driftFactor}`)

  const driftCategory = ensureString(context.category, '') || ensureString(context.drift_category, '')
  if (driftCategory) parts.push(`category ${driftCategory.replace(/_/g, ' ')}`)

  const sampleSize = ensureNumber(context.sample_size, NaN)
  if (Number.isFinite(sampleSize) && sampleSize > 0) parts.push(`sample ${sampleSize}`)

  const winRate = ensureNumber(context.win_rate, NaN)
  if (Number.isFinite(winRate)) parts.push(`win rate ${formatPercent(winRate)}`)

  const superiority = ensureNumber(context.superiority_pp, NaN)
  if (Number.isFinite(superiority)) parts.push(`superiority ${superiority.toFixed(1)}pp`)

  const conservationStatus = ensureString(context.conservation_status, '')
  if (conservationStatus) parts.push(`conservation ${conservationStatus}`)

  return parts
}

function shadowWinsText(event: EvolutionEvent): string | null {
  const metadata = event.metadata ?? {}
  const context = event.graph_context ?? {}
  const wins = ensureNumber(metadata.wins ?? context.wins, NaN)
  const total = ensureNumber(metadata.total ?? context.total ?? context.sample_size, NaN)
  if (!Number.isFinite(wins) || !Number.isFinite(total) || total <= 0) return null
  return `${wins}/${total} wins`
}

function compactStatusClass(status: string | null | undefined): string {
  switch ((status ?? '').toLowerCase()) {
    case 'active':
      return 'border-green-500/40 bg-green-500/15 text-green-300'
    case 'reduced':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-300'
    case 'paused':
      return 'border-red-500/40 bg-red-500/15 text-red-300'
    default:
      return 'border-slate-600 bg-slate-800 text-slate-300'
  }
}

function PanelShell({
  title,
  icon,
  status,
  error,
  children,
}: {
  title: string
  icon: ReactNode
  status: PanelStatus
  error: string | null
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-5 shadow">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-base font-bold text-white">
          {icon}
          {title}
        </h3>
        {status === 'loading' && <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />}
      </div>
      {error ? (
        <div className="rounded-md border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
          {error}
        </div>
      ) : (
        children
      )}
    </section>
  )
}

function RLRewardBreakdownPanel({ data }: { data: RLRewardDemoResponse | null }) {
  const rows = ensureArray<RLRewardEntry>(data?.reward_breakdown)
  if (rows.length === 0) return null

  return (
    <PanelShell
      title="RL Reward Breakdown"
      icon={<Scale className="h-5 w-5 text-cyan-300" />}
      status="ready"
      error={null}
    >
      <div className="space-y-3">
        {rows.map((row, index) => (
          <div key={safeKey(row.decision_id ?? row.alert_id, index)} className="rounded-md border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold text-cyan-300">{ensureString(row.alert_id, `ALERT-${index + 1}`)}</span>
                  <span className="text-xs text-slate-500">·</span>
                  <span className="text-sm text-slate-300">{ensureString(row.category, 'unknown').replace(/_/g, ' ')}</span>
                  <span className="text-xs text-slate-500">·</span>
                  <span className="text-sm text-slate-300">{ensureString(row.action, 'review').replace(/_/g, ' ')}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-400">{row.explanation ?? 'No explanation recorded.'}</p>
              </div>
              <div className="grid min-w-[260px] grid-cols-3 gap-2 text-xs">
                <div className="rounded border border-slate-800 bg-slate-900 p-2">
                  <div className="text-slate-500">Severity</div>
                  <div className="mt-1 font-mono text-slate-100">{formatMetric(row.severity, 2)}</div>
                </div>
                <div className="rounded border border-slate-800 bg-slate-900 p-2">
                  <div className="text-slate-500">eta</div>
                  <div className="mt-1 font-mono text-cyan-200">{formatMetric(row.eta_applied, 3)}</div>
                </div>
                <div className="rounded border border-slate-800 bg-slate-900 p-2">
                  <div className="text-slate-500">Reward</div>
                  <div className={`mt-1 font-mono ${ensureNumber(row.graded_reward, 0) < 0 ? 'text-red-300' : 'text-green-300'}`}>
                    {formatSignedMetric(row.graded_reward, 3)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-cyan-500/30 bg-cyan-950/20 px-3 py-2 text-xs text-cyan-100">
          <span>Mean severity {formatMetric(data?.summary?.mean_severity, 3)}</span>
          <span className="text-cyan-500">·</span>
          <span>Mean weight {formatMetric(data?.summary?.mean_reward_weight, 3)}</span>
          {data?.note && <span className="basis-full text-cyan-100/75">{data.note}</span>}
        </div>
      </div>
    </PanelShell>
  )
}

function RLExplorationAutoPausePanel({ data }: { data: RLExplorationDemoResponse | null }) {
  const rows = ensureArray<RLExplorationEntry>(data?.exploration_log)
  if (rows.length === 0) return null

  return (
    <PanelShell
      title="Exploration Auto-Pause"
      icon={<AlertTriangle className="h-5 w-5 text-amber-300" />}
      status="ready"
      error={null}
    >
      <div className="space-y-3">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {rows.map((row, index) => {
            const status = ensureString(row.status, 'unknown')
            return (
              <div key={safeKey(`epoch-${row.epoch ?? index + 1}`, index)} className="rounded-md border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-500">Epoch {ensureNumber(row.epoch, index + 1)}</p>
                    <p className="mt-1 text-sm font-semibold text-white">{ensureNumber(row.decisions_in_epoch, 0)} decisions</p>
                  </div>
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] font-bold uppercase ${compactStatusClass(status)}`}>
                    {status}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded border border-slate-800 bg-slate-900 p-2">
                    <div className="text-slate-500">Margin</div>
                    <div className="mt-1 font-mono text-slate-100">{formatMetric(row.conservation_margin, 2)}</div>
                  </div>
                  <div className="rounded border border-slate-800 bg-slate-900 p-2">
                    <div className="text-slate-500">Rate</div>
                    <div className="mt-1 font-mono text-amber-200">{formatPercent(row.exploration_rate)}</div>
                  </div>
                  <div className="col-span-2 rounded border border-slate-800 bg-slate-900 p-2">
                    <div className="text-slate-500">Proposals</div>
                    <div className="mt-1 font-mono text-slate-100">
                      {ensureNumber(row.proposals_generated, 0)} generated · {ensureNumber(row.proposals_accepted, 0)} accepted
                    </div>
                  </div>
                </div>
                <p className="mt-3 text-xs leading-5 text-slate-400">{row.note ?? 'No note recorded.'}</p>
              </div>
            )
          })}
        </div>
        <div className="rounded-md border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-100">
          <span>Current margin {formatMetric(data?.summary?.current_margin, 2)}</span>
          <span className="mx-2 text-amber-500">·</span>
          <span>Current rate {formatPercent(data?.summary?.current_rate)}</span>
          <span className="mx-2 text-amber-500">·</span>
          <span>{ensureNumber(data?.summary?.total_proposals, 0)} proposals / {ensureNumber(data?.summary?.total_accepted, 0)} accepted</span>
          {data?.note && <p className="mt-1 text-amber-100/75">{data.note}</p>}
        </div>
      </div>
    </PanelShell>
  )
}

export default function GovernanceTab() {
  const [evidenceRoom, setEvidenceRoom] = useState<EvidenceRoomData | null>(null)
  const [evidenceStatus, setEvidenceStatus] = useState<PanelStatus>('idle')
  const [evidenceError, setEvidenceError] = useState<string | null>(null)

  const [governanceSummary, setGovernanceSummary] = useState<GovernanceSummary | null>(null)
  const [governanceStatus, setGovernanceStatus] = useState<PanelStatus>('idle')
  const [governanceError, setGovernanceError] = useState<string | null>(null)

  const [socCompliance, setSocCompliance] = useState<SocComplianceResponse | null>(null)

  const [evolutionEvents, setEvolutionEvents] = useState<EvolutionEvent[]>([])
  const [evolutionStatus, setEvolutionStatus] = useState<PanelStatus>('idle')
  const [evolutionError, setEvolutionError] = useState<string | null>(null)

  const [rlRewardDemo, setRlRewardDemo] = useState<RLRewardDemoResponse | null>(null)
  const [rlExplorationDemo, setRlExplorationDemo] = useState<RLExplorationDemoResponse | null>(null)

  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setEvidenceStatus('loading')
    setEvidenceError(null)
    fetchJson<EvidenceRoomData>('/api/soc/evidence-room')
      .then((payload) => {
        if (!cancelled) {
          setEvidenceRoom(payload)
          setEvidenceStatus('ready')
        }
      })
      .catch((error) => {
        console.error('[GovernanceTab] Evidence Room failed:', error)
        if (!cancelled) {
          setEvidenceRoom(null)
          setEvidenceError('Evidence Room unavailable')
          setEvidenceStatus('error')
        }
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    setGovernanceStatus('loading')
    setGovernanceError(null)
    fetchJson<GovernanceSummary>('/api/governance/summary')
      .then((payload) => {
        if (!cancelled) {
          setGovernanceSummary(payload)
          setGovernanceStatus('ready')
        }
      })
      .catch((error) => {
        console.error('[GovernanceTab] Governance summary failed:', error)
        if (!cancelled) {
          setGovernanceSummary(null)
          setGovernanceError('Governance summary unavailable')
          setGovernanceStatus('error')
        }
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchJson<SocComplianceResponse>('/api/soc/compliance')
      .then((payload) => {
        if (!cancelled) setSocCompliance(payload && typeof payload === 'object' ? payload : null)
      })
      .catch((error) => {
        console.debug('[GovernanceTab] SOC compliance unavailable:', error)
        if (!cancelled) setSocCompliance(null)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    setEvolutionStatus('loading')
    setEvolutionError(null)
    fetchJson<EvolutionEventsResponse>('/api/evolution/recent-events?limit=20')
      .then((payload) => {
        if (!cancelled) {
          setEvolutionEvents(ensureArray<EvolutionEvent>(payload?.events))
          setEvolutionStatus('ready')
        }
      })
      .catch((error) => {
        console.error('[GovernanceTab] Evolution events failed:', error)
        if (!cancelled) {
          setEvolutionEvents([])
          setEvolutionError('Evolution audit unavailable')
          setEvolutionStatus('error')
        }
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchJson<RLRewardDemoResponse>('/api/platform/rl-reward-demo')
      .then((payload) => {
        if (!cancelled) setRlRewardDemo(payload && typeof payload === 'object' ? payload : null)
      })
      .catch((error) => {
        console.debug('[GovernanceTab] RL reward demo unavailable:', error)
        if (!cancelled) setRlRewardDemo(null)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchJson<RLExplorationDemoResponse>('/api/platform/rl-exploration-demo')
      .then((payload) => {
        if (!cancelled) setRlExplorationDemo(payload && typeof payload === 'object' ? payload : null)
      })
      .catch((error) => {
        console.debug('[GovernanceTab] RL exploration demo unavailable:', error)
        if (!cancelled) setRlExplorationDemo(null)
      })
    return () => { cancelled = true }
  }, [])

  const auditEntries = useMemo(
    () => ensureArray<AuditEntry>(evidenceRoom?.audit_trail?.entries).slice(0, 20),
    [evidenceRoom]
  )
  const governanceSections = useMemo(
    () => ensureArray<GovernanceSection>(governanceSummary?.sections),
    [governanceSummary]
  )
  const euAiActArticles = useMemo(
    () => [
      { key: 'article_9', article: socCompliance?.eu_ai_act?.article_9 },
      { key: 'article_15', article: socCompliance?.eu_ai_act?.article_15 },
    ].filter((item): item is { key: string; article: EuAiActArticle } => Boolean(item.article)),
    [socCompliance]
  )

  const conservation = evidenceRoom?.conservation
  const hashChain = evidenceRoom?.hash_chain
  const hashVerified = Boolean(hashChain?.verified)
  const hashEntries = ensureNumber(hashChain?.entries ?? hashChain?.total_entries, 0)
  const hashValidEntries = ensureNumber(hashChain?.valid_entries, NaN)

  const handleExport = async () => {
    setExporting(true)
    setExportError(null)
    try {
      const response = await fetch(`${SOC_API}/api/soc/evidence-room/export`)
      if (response.status === 401) {
        window.location.href = '/saml/login'
        throw new Error('Unauthorized')
      }
      if (!response.ok) throw new Error(`Export failed: ${response.status}`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'evidence-room.json'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('[GovernanceTab] Evidence export failed:', error)
      setExportError('Export failed')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-lg border border-cyan-500/40 bg-slate-950 p-6 shadow-2xl md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="flex items-center gap-3 text-2xl font-bold text-white">
            <Shield className="h-6 w-6 text-cyan-300" />
            Evidence Room
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Governance evidence, audit chain, conservation health, and evolution trail
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 md:items-end">
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="inline-flex items-center gap-2 rounded-lg border border-cyan-600 bg-cyan-900/40 px-4 py-2 text-sm font-semibold text-cyan-200 transition-colors hover:bg-cyan-800/50 disabled:opacity-50"
          >
            {exporting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            {exporting ? 'Preparing...' : 'Export JSON'}
          </button>
          {exportError && <p className="text-xs font-semibold text-red-300">{exportError}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <PanelShell
          title="Audit Trail"
          icon={<FileText className="h-5 w-5 text-cyan-300" />}
          status={evidenceStatus}
          error={evidenceError}
        >
          <div className="mb-4 flex flex-wrap items-center gap-3">
            {hashVerified ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-green-500/40 bg-green-500/15 px-3 py-1 text-xs font-bold text-green-300">
                <CheckCircle className="h-3.5 w-3.5" />
                Chain verified ✓
              </span>
            ) : Number.isFinite(hashValidEntries) && hashEntries > 0 ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/15 px-3 py-1 text-xs font-bold text-amber-300">
                Chain integrity: {hashValidEntries}/{hashEntries} entries valid
              </span>
            ) : (
              <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${statusBadgeClass(hashChain?.status)}`}>
                Chain status: {hashChain?.status ?? 'UNAVAILABLE'}
              </span>
            )}
            <span className="text-xs text-slate-400">{evidenceRoom?.audit_trail?.total ?? 0} decisions</span>
          </div>

          {evidenceStatus === 'loading' ? (
            <div className="py-8 text-center text-sm text-slate-400">Loading audit trail...</div>
          ) : auditEntries.length === 0 ? (
            <div className="py-8 text-center text-sm italic text-slate-400">No decisions recorded yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-left text-xs uppercase text-slate-500">
                    {['Decision', 'Action', 'Timestamp', 'Hash'].map((header) => (
                      <th key={header} className="pb-2 pr-3 font-semibold">{header}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {auditEntries.map((entry, index) => {
                    const id = entry.decision_id_full ?? entry.decision_id ?? entry.alert_id ?? `decision-${index + 1}`
                    const action = entry.action ?? entry.recommendation ?? 'unknown'
                    return (
                      <tr key={safeKey(id, index)} className="text-slate-300">
                        <td className="py-2.5 pr-3 font-mono text-xs text-cyan-300">{ensureString(entry.decision_id ?? entry.alert_id ?? id).slice(0, 16)}</td>
                        <td className="py-2.5 pr-3 text-xs">{action.replace(/_/g, ' ')}</td>
                        <td className="py-2.5 pr-3 text-xs text-slate-400">{formatTimestamp(entry.timestamp)}</td>
                        <td className="py-2.5 pr-3 font-mono text-xs text-slate-400">{entry.hash ? `${entry.hash.slice(0, 8)}...` : 'not reported'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </PanelShell>

        <PanelShell
          title="Conservation & Health"
          icon={<ActivityIcon />}
          status={evidenceStatus}
          error={evidenceError}
        >
          {evidenceStatus === 'loading' ? (
            <div className="py-8 text-center text-sm text-slate-400">Loading conservation status...</div>
          ) : !conservation ? (
            <div className="py-8 text-center text-sm italic text-slate-400">Conservation status: calibrating</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold ${statusBadgeClass(conservation.status)}`}>
                  {conservation.status ?? 'CALIBRATING'}
                </span>
                {conservation.frozen && (
                  <span className="inline-flex rounded-full border border-red-500/40 bg-red-500/15 px-3 py-1 text-xs font-bold text-red-300">
                    frozen
                  </span>
                )}
              </div>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
                <div>
                  <dt className="text-xs uppercase text-slate-500">q</dt>
                  <dd className="mt-1 font-mono text-slate-200">{formatMetric(conservation.q, 3)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase text-slate-500">alpha</dt>
                  <dd className="mt-1 font-mono text-slate-200">{formatMetric(conservation.alpha, 3)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase text-slate-500">V</dt>
                  <dd className="mt-1 font-mono text-slate-200">{formatMetric(conservation.V ?? conservation.verified_decisions, 0)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase text-slate-500">theta_min</dt>
                  <dd className="mt-1 font-mono text-slate-200">{formatMetric(conservation.theta_min ?? conservation.threshold, 4)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase text-slate-500">signal</dt>
                  <dd className="mt-1 font-mono text-slate-200">{formatMetric(conservation.signal ?? conservation.product, 4)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase text-slate-500">verified</dt>
                  <dd className="mt-1 font-mono text-slate-200">{formatMetric(conservation.verified_decisions, 0)}</dd>
                </div>
              </dl>
            </div>
          )}
        </PanelShell>
      </div>

      <PanelShell
        title="Compliance"
        icon={<Scale className="h-5 w-5 text-purple-300" />}
        status={governanceStatus}
        error={governanceError}
      >
        {governanceStatus === 'loading' ? (
          <div className="py-8 text-center text-sm text-slate-400">Compliance report loading...</div>
        ) : !governanceSummary ? (
          <div className="py-8 text-center text-sm text-slate-400">Compliance report loading...</div>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold text-white">{governanceSummary.title ?? 'Governance summary'}</p>
              <p className="mt-1 text-sm text-slate-400">{governanceSummary.overall_assessment ?? 'Assessment unavailable.'}</p>
            </div>
            {euAiActArticles.length > 0 && (
              <div className="rounded-md border border-purple-500/30 bg-purple-950/20 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-purple-300">EU AI Act</p>
                    <p className="mt-1 text-sm text-slate-300">Compliance evidence from the SOC control plane</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {euAiActArticles.map(({ key, article }, index) => (
                    <div key={safeKey(key, index)} className="rounded-md border border-slate-800 bg-slate-950/70 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase text-purple-300">
                            {key === 'article_9' ? 'Article 9 / Risk Management' : 'Article 15 / Accuracy & Robustness'}
                          </p>
                          <p className="mt-1 text-sm font-semibold text-white">{article.title ?? 'EU AI Act control'}</p>
                        </div>
                        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-bold ${statusBadgeClass(article.status)}`}>
                          {article.status ?? 'UNKNOWN'}
                        </span>
                      </div>
                      <p className="mt-3 text-xs leading-5 text-slate-400">
                        {article.description ?? 'Compliance evidence is not available yet.'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {governanceSections.length === 0 ? (
              <div className="rounded-md border border-slate-800 px-3 py-4 text-center text-sm text-slate-400">
                Compliance report loading...
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                {governanceSections.map((section, index) => (
                  <div key={safeKey(`${section.article}-${section.title}`, index)} className="rounded-md border border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase text-purple-300">{section.article ?? 'Control'}</p>
                        <p className="mt-1 text-sm font-semibold text-white">{section.title ?? 'Untitled control'}</p>
                      </div>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-bold ${statusBadgeClass(section.status)}`}>
                        {section.status ?? 'UNKNOWN'}
                      </span>
                    </div>
                    <p className="mt-3 text-xs text-slate-400">{section.evidence_count ?? 0} evidence items</p>
                  </div>
                ))}
              </div>
            )}
            {governanceSummary.legal_disclaimer && (
              <p className="rounded-md border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-200">
                {governanceSummary.legal_disclaimer}
              </p>
            )}
          </div>
        )}
      </PanelShell>

      <PanelShell
        title="Evolution Audit"
        icon={<GitBranch className="h-5 w-5 text-orange-300" />}
        status={evolutionStatus}
        error={evolutionError}
      >
        {evolutionStatus === 'loading' ? (
          <div className="py-8 text-center text-sm text-slate-400">Loading evolution events...</div>
        ) : evolutionEvents.length === 0 ? (
          <div className="py-8 text-center text-sm italic text-slate-400">
            No evolution events yet. The system will generate variants as graph signals accumulate.
          </div>
        ) : (
          <div className="space-y-3">
            {evolutionEvents.map((event, index) => {
              const visual = eventVisual(event.event_type)
              const contextParts = graphContextSummary(event.graph_context)
              const winsText = event.event_type === 'shadow_result' ? shadowWinsText(event) : null
              return (
                <div key={safeKey(event.id ?? event.variant_id, index)} className="rounded-md border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${visual.dot}`} />
                        <span className={`text-sm font-bold ${visual.text}`}>{visual.label}</span>
                        {event.artifact_type && (
                          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs font-semibold text-slate-300">
                            {event.artifact_type.replace(/_/g, ' ')}
                          </span>
                        )}
                        {winsText && (
                          <span className="rounded-full border border-orange-500/40 bg-orange-500/15 px-2 py-0.5 text-xs font-semibold text-orange-200">
                            {winsText}
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-sm text-slate-200">{event.description ?? 'No description recorded'}</p>
                      {event.variant_id && <p className="mt-1 font-mono text-xs text-slate-500">{event.variant_id}</p>}
                    </div>
                    <p className="shrink-0 text-xs text-slate-500">{formatTimestamp(event.timestamp ?? event.timestamp_epoch)}</p>
                  </div>
                  {contextParts.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {contextParts.map((part, partIndex) => (
                        <span key={safeKey(part, partIndex)} className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300">
                          {part}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </PanelShell>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <RLRewardBreakdownPanel data={rlRewardDemo} />
        <RLExplorationAutoPausePanel data={rlExplorationDemo} />
      </div>
    </div>
  )
}

function ActivityIcon() {
  return <AlertTriangle className="h-5 w-5 text-amber-300" />
}
