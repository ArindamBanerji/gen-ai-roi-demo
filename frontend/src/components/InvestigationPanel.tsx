import { useEffect, useState } from 'react'
import { CheckCircle, ChevronDown, ChevronUp, Clock, GitBranch, Play, XCircle } from 'lucide-react'
import { investigateAlert } from '../lib/api'

export interface InvestigationStep {
  step: number
  pattern: string
  alert_category?: string | null
  v_before: number[]
  v_after: number[]
  cat_distances_before: Record<string, number>
  cat_distances_after: Record<string, number>
  evidence_keys: string[]
  candidate_reads: string[]
  selected_edge: string
  propensity: number
  cost: number
  timestamp: string
  policy_version: string
  residual: number
  halt_reason?: string | null
}

export interface InvestigationResult {
  action: string
  confidence: number
  category: string
  investigated_category?: string | null
  routing_agreed: boolean
  trace: InvestigationStep[]
  v_final: number[]
  steps: number
  single_pass_action: string
  single_pass_confidence: number
  agreement: boolean
  fixture_source?: string | null
  conservation_emit_gate?: string
  halt_reason?: string
  policy?: string
}

interface InvestigationApiResponse {
  status: string
  mode: string
  alert_id: string
  single_pass: {
    action: string
    confidence: number
    category: string
  }
  vld: InvestigationResult
  investigation_trace: InvestigationStep[]
  conservation_emit_gate: string
}

interface InvestigationPanelProps {
  alertId: string
  autoRun?: boolean
  onResult?: (result: InvestigationResult) => void
}

function formatLabel(value?: string | null) {
  return value ? value.replace(/_/g, ' ') : '—'
}

function pct(value: number | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function fmt(value: number | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return value.toFixed(3)
}

function badgeClass(active: boolean) {
  return active
    ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-300'
    : 'border-amber-500/50 bg-amber-500/10 text-amber-300'
}

function categoryBadge(category?: string | null) {
  return (
    <span className="inline-flex rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-xs font-semibold text-cyan-200">
      {formatLabel(category)}
    </span>
  )
}

function renderDistances(distances: Record<string, number>) {
  const entries = Object.entries(distances ?? {}).sort((a, b) => a[1] - b[1]).slice(0, 3)
  if (!entries.length) return <span className="text-gray-500">No centroid distances returned</span>
  return entries.map(([category, distance]) => (
    <span key={category} className="rounded border border-gray-700 bg-gray-900 px-2 py-0.5 text-xs text-gray-300">
      {formatLabel(category)} d={fmt(distance)}
    </span>
  ))
}

export default function InvestigationPanel({ alertId, autoRun = false, onResult }: InvestigationPanelProps) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<InvestigationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState(false)

  const runInvestigation = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await investigateAlert(alertId) as InvestigationApiResponse
      const vld = { ...payload.vld, trace: payload.investigation_trace ?? payload.vld.trace }
      setResult(vld)
      setCollapsed(false)
      onResult?.(vld)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Investigation unavailable')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (autoRun && alertId) {
      void runInvestigation()
    }
    // autoRun is intentionally mount/alert driven; onResult is a callback sink.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alertId, autoRun])

  return (
    <section className="bg-soc-card rounded-lg border border-cyan-900/70 overflow-hidden" data-testid="investigation-panel" aria-label="Investigation Trace">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-300" />
            Investigation Trace
            <span className="inline-flex rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-xs font-semibold text-cyan-200">VLD shadow</span>
          </h3>
          <p className="text-xs text-gray-500 mt-1">Score-keyed graph routing for alert {alertId}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void runInvestigation()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded bg-cyan-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <Clock className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            {loading ? 'Investigating...' : 'Run Investigation'}
          </button>
          {result && (
            <button
              type="button"
              onClick={() => setCollapsed((value) => !value)}
              className="rounded p-1 hover:bg-gray-800"
              aria-label={collapsed ? 'Expand investigation trace' : 'Collapse investigation trace'}
            >
              {collapsed ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronUp className="h-4 w-4 text-gray-400" />}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 text-sm text-red-300 bg-red-950/30 border-b border-red-900/60" role="alert">
          Investigation error: {error}
        </div>
      )}

      {!result && !loading && !error && (
        <div className="p-5 text-sm text-gray-400">
          Run the read-only VLD investigation to see which graph branches were checked and how the final recommendation compares with single-pass scoring.
        </div>
      )}

      {result && !collapsed && (
        <div className="p-5 space-y-5">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Routed category</p>
              <div className="mt-1">{categoryBadge(result.investigated_category)}</div>
            </div>
            <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Final category</p>
              <div className="mt-1">{categoryBadge(result.category)}</div>
            </div>
            <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">VLD action</p>
              <p className="mt-1 text-sm font-semibold text-white">{formatLabel(result.action).toUpperCase()} · {pct(result.confidence)}</p>
            </div>
            <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Single-pass</p>
              <p className="mt-1 text-sm font-semibold text-white">{formatLabel(result.single_pass_action).toUpperCase()} · {pct(result.single_pass_confidence)}</p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded border border-gray-800 bg-gray-950/60 p-3 text-sm text-gray-300">
              <span className="text-gray-500">Investigation:</span> {result.steps} {result.steps === 1 ? 'step' : 'steps'}
            </div>
            <div className={`rounded border px-3 py-2 text-sm ${badgeClass(result.routing_agreed)}`}>
              {result.routing_agreed ? <CheckCircle className="mr-2 inline h-4 w-4" /> : <XCircle className="mr-2 inline h-4 w-4" />}
              Routing agreed: {result.routing_agreed ? 'yes' : 'no'}
            </div>
            <div className={`rounded border px-3 py-2 text-sm ${badgeClass(result.agreement)}`}>
              {result.agreement ? <CheckCircle className="mr-2 inline h-4 w-4" /> : <XCircle className="mr-2 inline h-4 w-4" />}
              {result.agreement ? 'Agreement: single-pass matched VLD' : 'Agreement: VLD changed the decision'}
            </div>
          </div>

          {result.trace.length === 0 ? (
            <div className="rounded border border-gray-800 bg-gray-900/60 p-4 text-sm text-gray-400">
              No investigation needed (converged immediately). Halt: {formatLabel(result.halt_reason)}
            </div>
          ) : (
            <div className="space-y-3">
              {result.trace.map((step) => (
                <div key={`${step.step}-${step.pattern}-${step.timestamp}`} className="relative rounded-lg border border-gray-800 bg-gray-950/70 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-100">
                        Step {step.step}: Routed to {formatLabel(step.pattern)} <span className="text-gray-500">(residual={fmt(step.residual)})</span>
                      </p>
                      <p className="mt-1 text-xs text-gray-500">Edge followed: {step.selected_edge || 'not reported'} · Policy {step.policy_version}</p>
                    </div>
                    {step.halt_reason && (
                      <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-200">
                        Halt: {formatLabel(step.halt_reason)}
                      </span>
                    )}
                  </div>

                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <div className="rounded border border-gray-800 bg-gray-900/70 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Evidence found</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {step.evidence_keys.length ? step.evidence_keys.map((key) => (
                          <span key={key} className="rounded border border-cyan-800/70 bg-cyan-950/40 px-2 py-0.5 text-xs text-cyan-200">
                            {formatLabel(key)}
                          </span>
                        )) : <span className="text-xs text-gray-500">No evidence keys returned</span>}
                      </div>
                    </div>
                    <div className="rounded border border-gray-800 bg-gray-900/70 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Closest categories after read</p>
                      <div className="mt-2 flex flex-wrap gap-2">{renderDistances(step.cat_distances_after)}</div>
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 text-xs text-gray-400 md:grid-cols-3">
                    <span>Candidate reads: {step.candidate_reads.length ? step.candidate_reads.map(formatLabel).join(', ') : '—'}</span>
                    <span>Propensity: {fmt(step.propensity)}</span>
                    <span>Cost: {fmt(step.cost)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="rounded border border-gray-800 bg-gray-900/60 p-3 text-xs text-gray-500">
            Conservation emit gate: {formatLabel(result.conservation_emit_gate)} · Policy: {result.policy ?? 'vld'} · Final halt: {formatLabel(result.halt_reason)}
          </div>
        </div>
      )}
    </section>
  )
}
