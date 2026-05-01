import { useState, useEffect, useRef } from 'react'
import {
  Zap,
  Sparkles,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  Activity,
  AlertTriangle,
  TrendingUp,
  Lightbulb,
  DollarSign,
  BarChart2,
  Database,
  ArrowUp,
  ArrowDown,
  Minus,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import {
  ComposedChart, Bar, Line,
  AreaChart, Area, ReferenceLine,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import * as api from '@/lib/api'
import { domainConfig } from '@/lib/domain'
import { ensureArray, ensureObject } from '@/lib/guards'

// ── suppress unused-import lint warnings for icons used only via JSX ──
void BarChart2; void Database; void ArrowUp; void ArrowDown; void Minus

interface Deployment {
  agent_name: string
  version: string
  status: 'active' | 'canary' | 'inactive'
  traffic_pct: number
  auto_close_rate_7d: number
  sample_count_7d: number
  config_preview: string
  pattern_count: number
}

interface EvalCheck {
  name: string
  score: number
  threshold: number
  passed: boolean
  message: string
}

interface ProcessResult {
  alert_id: string
  routed_to: string
  eval_gate: {
    checks: EvalCheck[]
    overall_passed: boolean
    overall_score: number
  }
  execution: {
    status: 'executed' | 'blocked'
    reason?: string
  }
  blocked_reason?: string
  decision_trace: {
    id: string
    type: string
    reasoning: string
    confidence: number
    action_taken: string
    nodes_consulted: number
    pattern_id?: string
    playbook_id?: string
  }
  triggered_evolution: {
    occurred: boolean
    event_id?: string
    event_type?: string
    description?: string
    changes?: Array<{
      type: string
      before: any
      after: any
    }>
  }
  execution_time_ms: number
  context_preview: {
    user_name: string
    asset_hostname: string
    travel_destination?: string
    pattern_count: number
  }
  prompt_evolution?: {
    current_variant: string
    current_success_rate: number
    previous_variant?: string | null
    previous_success_rate?: number | null
    promotion_occurred: boolean
    promotion_reason?: string | null
    what_changed_narrative?: string
    operational_impact?: {
      fewer_false_escalations_pct: number
      fewer_false_escalations_monthly: number
      analyst_hours_recovered: number
      estimated_monthly_savings: number
      missed_threats: number
    }
  }
  gae_scoring?: {
    decision_id: string
    factor_vector: number[]
    factor_names: string[]
    action_probabilities: Record<string, number>
    softmax_sum: number
    temperature: number
    low_confidence: boolean
    ambiguous: boolean
    decision_method: string
  }
  gae_summary?: {
    decision_count: number
    w_norms: Record<string, number>
    factor_names: string[]
    has_real_data: boolean
  }
}

interface ModelSwapAlertRow {
  alert_id: string
  category: string
  action_name: string
  confidence: number
  probabilities: number[]
  factor_vector: number[]
}

interface ModelSwapTrialResult {
  ok: boolean
  status: string
  n_alerts_requested: number
  n_alerts_processed: number
  llm_calls_made: number
  llm_dependency: boolean
  narrative_affects_scoring: boolean
  narrative_llm_used: string
  scoring_method: string
  summary: string
  reproducibility_check: {
    passed: boolean
    reason?: string
    first_run?: ModelSwapAlertRow
    second_run?: ModelSwapAlertRow
  }
  alerts: ModelSwapAlertRow[]
  errors: string[]
}

interface RewardSummary {
  total_decisions: number
  correct: number
  incorrect: number
  asymmetric_ratio: number
  cumulative_r_t: number
  loop3_status: 'active' | 'insufficient_data'
  governs: string[]
}

interface ProfileState {
  categories: string[]
  actions: string[]
  centroids: number[][][]   // shape (C, A, d) where d = number of factors
  counts: number[][]        // shape (6, 4)
  decision_count: number
}

interface GraphStats {
  nodes_traversed: number
  relationships_analyzed: number
  historical_decisions: number
  source: 'neo4j' | 'unavailable'
}

interface IksState {
  current: number | null
  delta_7d: number | null
  interpretation: string
  decision_count: number
  estimated: boolean
  trend: number[]
}

interface ProfileStateWithIks extends ProfileState {
  iks?: IksState
}

interface CentroidEvolutionEntry {
  id: string
  decision_number: number
  centroid_delta_norm: number
  correct: boolean
  category: string
  action: string
  verified_at?: string
}

// CentroidEvolutionData removed — backend returns flat array, not {evolution:[]} wrapper

interface CentroidExportResponse {
  exported_at?: number
  generated_at_epoch?: number
  tensor_shape?: number[]
  sha256?: string
  decision_count?: number
}

interface WhatIfPreset {
  name: string
  description: string
  alpha: number
  V: number
  q_initial: number
  q_target: number
  q_ramp_days?: number
  horizon_days: number
  disruption_day?: number | null
  disruption_delta?: number
  eta: number
  n_half: number
  t_max_days: number
}

interface WhatIfDay {
  day: number
  q: number
  signal: number
  status: 'GREEN' | 'AMBER' | 'RED'
  passed: boolean
  headroom: number
  iks_estimate: number
}

interface WhatIfResult {
  scenario?: {
    q_initial?: number
    alpha?: number
    V?: number
  }
  daily_trajectory: WhatIfDay[]
  summary: {
    days_green: number
    days_amber: number
    days_red: number
    first_amber_day: number | null
    first_red_day: number | null
    auto_pause_triggered: boolean
    final_status: 'GREEN' | 'AMBER' | 'RED'
    final_iks: number
  }
  conservation_law: {
    theta_min: number
    formula: string
    explanation: string
    q_threshold: number | null
  }
  iks_estimate: number
  ceiling_estimate?: number | null
  ceiling_note?: string
  warnings: string[]
}

interface TimeMachineSnapshotMeta {
  snapshot_id: string
  timestamp?: number
  timestamp_epoch?: number
  decision_count?: number
  sha256?: string
  file_path?: string
}

interface TimeMachineSnapshotDetail extends TimeMachineSnapshotMeta {
  shape?: number[]
  centroids?: number[][][]
  drift_from_bootstrap?: number | null
  drift_from_current?: number | null
}

interface TimeMachineComparison {
  overall_frobenius_distance?: number
  per_category_distances?: Record<string, number>
  top_movers?: Array<{
    category: string
    action: string
    distance: number
  }>
  movement_direction?: string
  timeline?: {
    timestamps?: number[]
    decision_counts?: number[]
  }
}

interface TimeMachineTimelinePoint {
  snapshot_id: string
  timestamp?: number
  timestamp_epoch?: number
  decision_count?: number
  sha256?: string
  drift_from_bootstrap?: number | null
  iks_estimate?: number | null
  ceiling_estimate?: number | null
}

interface TimeMachineTimelineResponse {
  timeline?: TimeMachineTimelinePoint[]
  ceiling_estimate?: number | null
  ceiling_note?: string | null
}

const DEFAULT_ALERT_ID = domainConfig.defaultAlertId

function formatRelativeTime(timestamp?: number | null) {
  if (!timestamp) return 'unknown'
  const diffMs = Date.now() - timestamp
  const diffMinutes = Math.max(0, Math.floor(diffMs / 60000))
  if (diffMinutes < 1) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}


// ============================================================================
// AccuracyTrajectoryPanel — two-plateau visualization (C2)
// ============================================================================

function AccuracyTrajectoryPanel() {
  const [data, setData]         = useState<any>(null)
  const [loading, setLoading]   = useState(true)
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    api.getAccuracyTrajectory()
      .then((d: any) => {
        setData(d)
        if (d.categories?.length > 0) {
          setSelected(d.categories[0].category)
        }
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="p-4 text-gray-400 text-sm">
      Loading accuracy trajectory...
    </div>
  )
  if (!data) return (
    <div className="p-4 text-gray-400 text-sm">
      Accuracy trajectory unavailable.
    </div>
  )

  const categoryNames: string[] = (data.categories ?? []).map((c: any) => c.category)
  const cat = (data.categories ?? []).find((c: any) => c.category === selected)
  if (!cat) return null

  const chartData = (cat.trajectory_points ?? []).map((pt: any) => ({
    decisions:    pt.decisions,
    cold_start:   Math.round(pt.accuracy * 1000) / 10,
    enriched:     Math.round(cat.enriched_plateau * 1000) / 10,
    cold_plateau: Math.round(cat.cold_start_plateau * 1000) / 10,
  }))

  const gapPP     = cat.permanent_gap_pp?.toFixed(1) ?? '—'
  const nHalfNote = cat.n_half_applicable
    ? 'Convergence to plateau within one quarter.'
    : `Cold-start plateau ${(cat.cold_start_plateau * 100).toFixed(1)}% — permanent gap.`

  return (
    <div className="bg-gray-900 rounded-xl p-5 mt-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-400" />
          <h3 className="text-white font-semibold">Accuracy Trajectory</h3>
          <span className="text-xs text-gray-400 ml-2">
            σ-band: {cat.sigma_band ?? 'medium'}
          </span>
        </div>
        <select
          value={selected}
          onChange={e => setSelected(e.target.value)}
          className="bg-gray-800 text-gray-300 text-xs rounded px-2 py-1
                     border border-gray-700 focus:outline-none"
        >
          {categoryNames.map(c => (
            <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData}
          margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="decisions"
            tick={{ fill: '#9CA3AF', fontSize: 11 }}
            label={{ value: 'Decisions', position: 'insideBottom',
                     offset: -2, fill: '#6B7280', fontSize: 11 }} />
          <YAxis domain={[20, 100]}
            tick={{ fill: '#9CA3AF', fontSize: 11 }}
            tickFormatter={(v: number) => `${v}%`} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1F2937',
                            border: '1px solid #374151' }}
            formatter={(v: any, name: string) => [
              `${v}%`,
              name === 'cold_start' ? 'Cold-start (no enrichment)' :
              name === 'enriched'   ? 'Enriched (your deployment)' : name
            ]}
            labelFormatter={(v: any) => `${v} decisions`} />

          <Area type="monotone" dataKey="enriched"
            stroke="#22C55E" strokeWidth={2} strokeDasharray="6 3"
            fill="#22C55E" fillOpacity={0.10} name="enriched" dot={false} />

          <Line type="monotone" dataKey="cold_start"
            stroke="#F59E0B" strokeWidth={2}
            name="cold_start" dot={false} />

          <ReferenceLine
            y={Math.round(cat.cold_start_plateau * 1000) / 10}
            stroke="#F59E0B" strokeDasharray="4 4" strokeOpacity={0.5} />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-3 space-y-1">
        <div className="flex items-start gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-300">
            Your deployment: enriched plateau
            {' '}{(cat.enriched_plateau * 100).toFixed(1)}% from Day 1.
          </p>
        </div>
        <div className="flex items-start gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-300">
            Without enrichment: cold-start levels off at
            {' '}{(cat.cold_start_plateau * 100).toFixed(1)}%.{' '}
            <span className="text-amber-400 font-medium">
              Permanent gap: {gapPP}pp.
            </span>
          </p>
        </div>
        <p className="text-xs text-gray-500 mt-1">{nHalfNote}</p>
      </div>
    </div>
  )
}


export default function RuntimeEvolutionTab() {
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<ProcessResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [visibleChecks, setVisibleChecks] = useState<number[]>([])
  const [rewardSummary, setRewardSummary] = useState<RewardSummary | null>(null)
  const [profileState, setProfileState] = useState<ProfileState | null>(null)
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null)

  // VIS-2 new state
  const [profileStateFull, setProfileStateFull] = useState<ProfileStateWithIks | null>(null)
  const [centroidEvolution, setCentroidEvolution] = useState<CentroidEvolutionEntry[]>([])
  const [centroidEvoLoading, setCentroidEvoLoading] = useState(false)
  const [centroidEvoError, setCentroidEvoError] = useState(false)
  const [profileError, setProfileError] = useState(false)
  const [learningStateData, setLearningStateData] = useState<{ iks_v2: number } | null>(null)
  const [activeSection, setActiveSection] = useState<'a' | 'b' | 'c' | 'd'>('a')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [pendingDecisionId, setPendingDecisionId] = useState<string | null>(null)
  const [heatmapData, setHeatmapData] = useState<{
    factors: string[]
    kernel_label?: string
    noise_fingerprint: Record<string, { sigma: number; kernel_weight: number; label: string }>
  } | null>(null)
  const [enrichmentStatus, setEnrichmentStatus] = useState<{
    sources: Array<{
      source_name: string
      record_count: number
      trust_level: string
      status: 'active' | 'stale' | 'unavailable'
      affects_factor: string
      staleness_hours?: number
      last_refreshed_human?: string
    }>
    enrichment_health: string
    health_reason: string
    total_enrichment_nodes: number
  } | null>(null)
  const [centroidSupport, setCentroidSupport] = useState<{
    overall_health: string
    warning_count: number
    interpretation: string
    note?: string
  } | null>(null)
  const [centroidExportBusy, setCentroidExportBusy] = useState(false)
  const [centroidExportMessage, setCentroidExportMessage] = useState<string | null>(null)

  // WIRE-03/04: Learning Health + IKS Trend — lazy-loaded when section D activates
  const [healthData, setHealthData] = useState<any>(null)
  const [iksTrend, setIksTrend] = useState<any>(null)
  const [healthDataLoading, setHealthDataLoading] = useState(false)
  const [iksTrendLoading, setIksTrendLoading] = useState(false)

  // WIRE-05: Shadow Mode
  const [shadowEnabled, setShadowEnabled] = useState(false)
  const [shadowReport, setShadowReport] = useState<any>(null)
  const [shadowToggleBusy, setShadowToggleBusy] = useState(false)

  // WIRE-06: Checkpoints
  const [checkpoints, setCheckpoints] = useState<any[]>([])
  const [checkpointBusy, setCheckpointBusy] = useState(false)
  const [checkpointMsg, setCheckpointMsg] = useState<string | null>(null)
  const [rollbackBusy, setRollbackBusy] = useState<string | null>(null)

  // FEATURE-03: What-If Simulator
  const [whatIfExpanded, setWhatIfExpanded] = useState(false)
  const [whatIfPresets, setWhatIfPresets] = useState<Record<string, WhatIfPreset>>({})
  const [whatIfPresetsLoading, setWhatIfPresetsLoading] = useState(false)
  const [whatIfPresetsLoaded, setWhatIfPresetsLoaded] = useState(false)
  const [whatIfRunning, setWhatIfRunning] = useState(false)
  const [whatIfError, setWhatIfError] = useState<string | null>(null)
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null)
  const [qStart, setQStart] = useState(0.85)
  const [qEnd, setQEnd] = useState(0.85)
  const [rampDays, setRampDays] = useState(30)
  const [alphaProjection, setAlphaProjection] = useState(0.05)
  const [volumeProjection, setVolumeProjection] = useState(200)
  const [whatIfHorizon, setWhatIfHorizon] = useState(90)
  const [disruptionEnabled, setDisruptionEnabled] = useState(false)
  const [disruptionDay, setDisruptionDay] = useState(14)
  const [disruptionDrop, setDisruptionDrop] = useState(0.25)

  // FEATURE-04: Centroid Time Machine
  const [timeMachineExpanded, setTimeMachineExpanded] = useState(false)
  const [timeMachineLoaded, setTimeMachineLoaded] = useState(false)
  const [timeMachineLoading, setTimeMachineLoading] = useState(false)
  const [timeMachineError, setTimeMachineError] = useState<string | null>(null)
  const [timeMachineTimeline, setTimeMachineTimeline] = useState<TimeMachineTimelinePoint[]>([])
  const [timeMachineSnapshots, setTimeMachineSnapshots] = useState<TimeMachineSnapshotMeta[]>([])
  const [selectedSnapshotIds, setSelectedSnapshotIds] = useState<string[]>([])
  const [timeMachineComparison, setTimeMachineComparison] = useState<TimeMachineComparison | null>(null)
  const [timeMachineComparisonLoading, setTimeMachineComparisonLoading] = useState(false)
  const [timeMachineComparisonError, setTimeMachineComparisonError] = useState<string | null>(null)
  const [timeMachineSnapshotDetail, setTimeMachineSnapshotDetail] = useState<TimeMachineSnapshotDetail | null>(null)
  const [timeMachineSnapshotDetailLoading, setTimeMachineSnapshotDetailLoading] = useState(false)
  const [timeMachineSnapshotDetailError, setTimeMachineSnapshotDetailError] = useState<string | null>(null)

  const [factorAnalysisExpanded, setFactorAnalysisExpanded] = useState(false)
  const [factorAnalysisSummaryLoaded, setFactorAnalysisSummaryLoaded] = useState(false)
  const [factorAnalysisSummaryLoading, setFactorAnalysisSummaryLoading] = useState(false)
  const [factorAnalysisSummaryError, setFactorAnalysisSummaryError] = useState<string | null>(null)
  const [factorAnalysisSummary, setFactorAnalysisSummary] = useState<any>(null)
  const [factorAnalysisReportLoading, setFactorAnalysisReportLoading] = useState(false)
  const [factorAnalysisReportError, setFactorAnalysisReportError] = useState<string | null>(null)
  const [factorAnalysisReport, setFactorAnalysisReport] = useState<any>(null)
  const [modelSwapTrialN, setModelSwapTrialN] = useState(20)
  const [modelSwapTrialLoading, setModelSwapTrialLoading] = useState(false)
  const [modelSwapTrialError, setModelSwapTrialError] = useState<string | null>(null)
  const [modelSwapTrialResult, setModelSwapTrialResult] = useState<ModelSwapTrialResult | null>(null)

  // Section refs for IntersectionObserver
  const sectionARef = useRef<HTMLDivElement>(null)
  const sectionBRef = useRef<HTMLDivElement>(null)
  const sectionCRef = useRef<HTMLDivElement>(null)
  const sectionDRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadDeployments()
  }, [])

  useEffect(() => {
    loadRewardSummary()
  }, [])

  useEffect(() => {
    loadProfileState()
  }, [])

  useEffect(() => {
    loadGraphStats()
  }, [])

  useEffect(() => {
    loadCentroidEvolution()
  }, [])

  useEffect(() => {
    loadLearningState()
  }, [])

  useEffect(() => {
    loadHeatmap()
  }, [])

  useEffect(() => {
    loadEnrichmentStatus()
  }, [])

  useEffect(() => {
    loadCentroidSupport()
  }, [])

  useEffect(() => {
    if (result) {
      loadRewardSummary()
    }
  }, [result])

  useEffect(() => {
    if (result) {
      setVisibleChecks([])
      ensureArray<EvalCheck>(result.eval_gate.checks).forEach((_, index) => {
        setTimeout(() => {
          setVisibleChecks(prev => [...prev, index])
        }, index * 800)
      })
    }
  }, [result])

  // On-mount: read sessionStorage / URL param for pending decision
  useEffect(() => {
    const stored = sessionStorage.getItem('vis2_pending_decision')
    if (stored) {
      setPendingDecisionId(stored)
      sessionStorage.removeItem('vis2_pending_decision')
    }
    const params = new URLSearchParams(window.location.search)
    const decParam = params.get('decision')
    if (decParam) setPendingDecisionId(decParam)
  }, [])

  // IntersectionObserver for active section highlight
  useEffect(() => {
    const refs = [
      { ref: sectionARef, id: 'a' as const },
      { ref: sectionBRef, id: 'b' as const },
      { ref: sectionCRef, id: 'c' as const },
      { ref: sectionDRef, id: 'd' as const },
    ]
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting)
        if (visible.length > 0) {
          const topEntry = visible.sort((a, b) =>
            a.boundingClientRect.top - b.boundingClientRect.top
          )[0]
          const id = topEntry.target.getAttribute('data-section') as 'a' | 'b' | 'c' | 'd'
          if (id) setActiveSection(id)
        }
      },
      { threshold: 0.15, rootMargin: '-80px 0px -40% 0px' }
    )
    refs.forEach(({ ref }) => { if (ref.current) observer.observe(ref.current) })
    return () => observer.disconnect()
  }, [])

  // Lazy-load WIRE-03/04/05/06 data only when System Health section is active
  useEffect(() => {
    if (activeSection !== 'd') return
    setHealthDataLoading(true)
    api.fetchLearningHealth()
      .then((d: any) => setHealthData(d))
      .catch(() => {})
      .finally(() => setHealthDataLoading(false))
    setIksTrendLoading(true)
    api.fetchIksTrend()
      .then((d: any) => setIksTrend(d))
      .catch(() => {})
      .finally(() => setIksTrendLoading(false))
    api.fetchShadowReport()
      .then((d: any) => setShadowReport(d))
      .catch(() => {})
    api.fetchCheckpoints()
      .then((d: any) => setCheckpoints(ensureArray((d as any)?.checkpoints)))
      .catch(() => {})
  }, [activeSection])

  useEffect(() => {
    if (!whatIfExpanded || whatIfPresetsLoaded || whatIfPresetsLoading) return
    setWhatIfPresetsLoading(true)
    api.fetchWhatIfPresets()
      .then((d: any) => {
        setWhatIfPresets(ensureObject<Record<string, WhatIfPreset>>((d as any)?.presets))
        setWhatIfPresetsLoaded(true)
      })
      .catch(() => {
        setWhatIfError('Failed to load simulator presets')
      })
      .finally(() => setWhatIfPresetsLoading(false))
  }, [whatIfExpanded, whatIfPresetsLoaded, whatIfPresetsLoading])

  useEffect(() => {
    if (!timeMachineExpanded || timeMachineLoaded || timeMachineLoading) return
    setTimeMachineLoading(true)
    setTimeMachineError(null)
    Promise.allSettled([
      api.fetchTimeMachineTimeline(),
      api.fetchTimeMachineSnapshots(),
    ])
      .then(([timelineResult, snapshotResult]) => {
        if (timelineResult.status === 'fulfilled') {
          const timelineData = timelineResult.value as TimeMachineTimelineResponse
          setTimeMachineTimeline(ensureArray<TimeMachineTimelinePoint>((timelineData as any)?.timeline))
        } else {
          setTimeMachineError('Timeline unavailable.')
        }

        if (snapshotResult.status === 'fulfilled') {
          const snapshotsData = snapshotResult.value as { snapshots?: TimeMachineSnapshotMeta[] }
          setTimeMachineSnapshots(ensureArray<TimeMachineSnapshotMeta>((snapshotsData as any)?.snapshots))
        } else {
          setTimeMachineError(prev => prev ? `${prev} Snapshot list unavailable.` : 'Snapshot list unavailable.')
        }

        setTimeMachineLoaded(true)
      })
      .catch(() => {
        setTimeMachineError('Centroid Time Machine unavailable.')
      })
      .finally(() => setTimeMachineLoading(false))
  }, [timeMachineExpanded, timeMachineLoaded, timeMachineLoading])

  useEffect(() => {
    if (!factorAnalysisExpanded || factorAnalysisSummaryLoaded || factorAnalysisSummaryLoading) return
    setFactorAnalysisSummaryLoading(true)
    setFactorAnalysisSummaryError(null)
    api.fetchFactorAnalysisSummary()
      .then((data: any) => {
        setFactorAnalysisSummary(data)
        setFactorAnalysisSummaryLoaded(true)
      })
      .catch(() => {
        setFactorAnalysisSummaryError('Factor Analysis summary unavailable.')
      })
      .finally(() => setFactorAnalysisSummaryLoading(false))
  }, [factorAnalysisExpanded, factorAnalysisSummaryLoaded, factorAnalysisSummaryLoading])

  const loadDeployments = async () => {
    try {
      const data = await api.getDeployments() as { deployments: Deployment[] }
      setDeployments(data.deployments)
    } catch (error) {
      console.error('Failed to load deployments:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadRewardSummary = async () => {
    try {
      const data = await api.getRewardSummary()
      setRewardSummary(data as RewardSummary)
    } catch (error) {
      console.error('Failed to load reward summary:', error)
    }
  }

  const loadProfileState = async () => {
    try {
      // Use api.getProfileState() which calls fetchJSON and throws on !response.ok.
      // The previous raw fetch().then(r => r.json()) had no .ok check — a 500 body
      // would be stored as profileState causing silent rendering bugs downstream.
      const data = await api.getProfileState()
      setProfileStateFull(data as ProfileStateWithIks)
      setProfileState(data as ProfileState)
    } catch (error) {
      console.error('Failed to load profile state:', error)
      setProfileError(true)
    }
  }

  const loadGraphStats = async () => {
    try {
      const resp = await fetch('/api/soc/graph-stats')
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        return
      }
      const data = await resp.json()
      setGraphStats(data as GraphStats)
    } catch (error) {
      console.error('Failed to load graph stats:', error)
    }
  }

  const loadCentroidEvolution = async () => {
    setCentroidEvoLoading(true)
    setCentroidEvoError(false)
    try {
      const data = await fetch('/api/soc/centroid-evolution?n=200').then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      setCentroidEvolution(data as CentroidEvolutionEntry[])
    } catch {
      setCentroidEvoError(true)
    } finally {
      setCentroidEvoLoading(false)
    }
  }

  const loadLearningState = async () => {
    try {
      const data = await fetch('/api/soc/learning-state').then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      setLearningStateData(data)
    } catch {
      // Non-critical — IKS v2 display falls back to v1
    }
  }

  const loadHeatmap = async () => {
    try {
      const data = await fetch('/api/soc/centroid-heatmap').then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      if (data.status !== 'cold_start') setHeatmapData(data)
    } catch {
      // Non-critical — table hidden when null
    }
  }

  const loadFactorAnalysisReport = async () => {
    setFactorAnalysisReportLoading(true)
    setFactorAnalysisReportError(null)
    try {
      const data = await api.fetchFactorAnalysis()
      setFactorAnalysisReport(data)
    } catch {
      setFactorAnalysisReportError('Full factor analysis unavailable.')
    } finally {
      setFactorAnalysisReportLoading(false)
    }
  }

  const runModelSwapTrial = async () => {
    setModelSwapTrialLoading(true)
    setModelSwapTrialError(null)
    try {
      const data = await api.fetchModelSwapTrial(modelSwapTrialN)
      setModelSwapTrialResult(data as ModelSwapTrialResult)
    } catch {
      setModelSwapTrialError('Model swap trial unavailable.')
    } finally {
      setModelSwapTrialLoading(false)
    }
  }

  const snrToneClass = (snr: number | null | undefined) => {
    if ((snr ?? 0) < 1.5) return 'text-red-400'
    if ((snr ?? 0) <= 2.5) return 'text-amber-400'
    return 'text-emerald-400'
  }

  const statusToneClass = (status: string | null | undefined) => {
    if (status === 'at_ceiling') return 'text-red-400'
    if (status === 'near_ceiling') return 'text-amber-400'
    return 'text-emerald-400'
  }

  const loadEnrichmentStatus = async () => {
    try {
      const data = await fetch('/api/soc/enrichment-status').then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      setEnrichmentStatus(data)
    } catch {
      // Non-critical — section hidden when null
    }
  }

  const loadCentroidSupport = async () => {
    try {
      const data = await fetch('/api/soc/centroid-support').then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      setCentroidSupport(data)
    } catch {
      // Non-critical — indicator hidden when null
    }
  }

  const handleExportCentroids = async () => {
    setCentroidExportBusy(true)
    setCentroidExportMessage(null)

    try {
      const data = await api.fetchCentroidExport() as CentroidExportResponse
      const payload = JSON.stringify(data, null, 2)
      const blob = new Blob([payload], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const timestamp = data.exported_at ?? data.generated_at_epoch ?? Date.now()
      const stamp = new Date(timestamp).toISOString().replace(/[:.]/g, '-')
      const link = document.createElement('a')
      link.href = url
      link.download = `centroid_export_${stamp}.json`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)

      const tensorShape = Array.isArray(data.tensor_shape) ? data.tensor_shape.join('x') : 'unknown'
      const sha256 = data.sha256 ?? 'unknown'
      const decisionCount = data.decision_count ?? 0
      setCentroidExportMessage(
        `Exported ${tensorShape} tensor, ${decisionCount} decisions, SHA-256 ${sha256}, ${new Date(timestamp).toLocaleString()}.`
      )
    } catch (error) {
      console.error('[RuntimeEvolutionTab] Failed to export centroids:', error)
      setCentroidExportMessage('Centroid export failed.')
    } finally {
      setCentroidExportBusy(false)
    }
  }

  const handleShadowToggle = async () => {
    const newState = !shadowEnabled
    if (newState && !window.confirm('Enable shadow mode? The system will observe but not act on recommendations.')) return
    setShadowToggleBusy(true)
    try {
      const result: any = await api.toggleShadowMode(newState)
      setShadowEnabled(result.shadow_mode)
      if (result.shadow_mode) {
        const report: any = await api.fetchShadowReport()
        setShadowReport(report)
      }
    } catch {
      // non-critical
    } finally {
      setShadowToggleBusy(false)
    }
  }

  const handleCreateCheckpoint = async () => {
    setCheckpointBusy(true)
    setCheckpointMsg(null)
    try {
      const result: any = await api.createCheckpoint()
      setCheckpointMsg(`Checkpoint created: ${String(result.checkpoint_id).slice(0, 8)}… (${result.reason})`)
      const list: any = await api.fetchCheckpoints()
      setCheckpoints(ensureArray((list as any)?.checkpoints))
    } catch {
      setCheckpointMsg('Failed to create checkpoint')
    } finally {
      setCheckpointBusy(false)
    }
  }

  const handleRollback = async (checkpointId: string) => {
    const cp = checkpoints.find((c: any) => c.id === checkpointId)
    const dcLabel = cp ? `${cp.decision_count} decisions` : '?'
    if (!window.confirm(`Roll back to checkpoint ${checkpointId.slice(0, 8)}…?\nThis will restore centroids to their state at ${dcLabel}.\nThis action cannot be undone.`)) return
    setRollbackBusy(checkpointId)
    setCheckpointMsg(null)
    try {
      const result: any = await api.rollbackCheckpoint(checkpointId)
      setCheckpointMsg(`Restored to checkpoint (${result.restored_decision_count} decisions). Scorer is now frozen.`)
      const list: any = await api.fetchCheckpoints()
      setCheckpoints(ensureArray((list as any)?.checkpoints))
    } catch {
      setCheckpointMsg('Rollback failed. Check backend connection.')
    } finally {
      setRollbackBusy(null)
    }
  }

  const handleSelectTimeMachineSnapshot = async (snapshotId: string) => {
    setSelectedSnapshotIds(prev => {
      if (prev.includes(snapshotId)) return prev.filter(id => id !== snapshotId)
      if (prev.length === 2) return [prev[1], snapshotId]
      return [...prev, snapshotId]
    })

    setTimeMachineSnapshotDetailLoading(true)
    setTimeMachineSnapshotDetailError(null)
    try {
      const detail = await api.fetchTimeMachineSnapshot(snapshotId) as TimeMachineSnapshotDetail
      setTimeMachineSnapshotDetail(detail)
    } catch {
      setTimeMachineSnapshotDetailError('Snapshot detail unavailable.')
    } finally {
      setTimeMachineSnapshotDetailLoading(false)
    }
  }

  const handleRunTimeMachineCompare = async (idA: string, idB: string) => {
    setTimeMachineComparisonLoading(true)
    setTimeMachineComparisonError(null)
    try {
      const result = await api.fetchTimeMachineCompare(idA, idB) as TimeMachineComparison
      setTimeMachineComparison(result)
    } catch {
      setTimeMachineComparisonError('Snapshot comparison unavailable.')
    } finally {
      setTimeMachineComparisonLoading(false)
    }
  }

  const handleCompareCurrentVsBootstrap = async () => {
    const latestSnapshotId = timeMachineSnapshots[timeMachineSnapshots.length - 1]?.snapshot_id
    if (!latestSnapshotId) return
    setTimeMachineComparisonLoading(true)
    setTimeMachineComparisonError(null)
    setTimeMachineComparison(null)
    try {
      const result = await api.fetchTimeMachineCompareBootstrap(latestSnapshotId) as TimeMachineComparison
      setTimeMachineComparison(result)
      setSelectedSnapshotIds([latestSnapshotId])
    } catch {
      setTimeMachineComparisonError('Bootstrap comparison unavailable.')
    } finally {
      setTimeMachineComparisonLoading(false)
    }
  }

  const applyWhatIfPreset = (preset: WhatIfPreset) => {
    setQStart(preset.q_initial ?? 0.85)
    setQEnd(preset.q_target ?? preset.q_initial ?? 0.85)
    setRampDays(preset.q_ramp_days ?? 0)
    setAlphaProjection(preset.alpha ?? 0.05)
    setVolumeProjection(preset.V ?? 200)
    setWhatIfHorizon(preset.horizon_days ?? 90)
    setDisruptionEnabled((preset.disruption_day ?? null) !== null && (preset.disruption_delta ?? 0) !== 0)
    setDisruptionDay(preset.disruption_day ?? 14)
    setDisruptionDrop(Math.abs(preset.disruption_delta ?? 0.25))
    setWhatIfError(null)
  }

  const handleRunWhatIf = async (overrides?: Partial<{
    q_initial: number; q_target: number; q_ramp_days: number
    alpha: number; V: number; horizon_days: number
    disruption_day: number | null; disruption_delta: number
    name: string; description: string
  }>) => {
    setWhatIfRunning(true)
    setWhatIfError(null)
    try {
      // FIX-13: send q_ramp_days to backend; backend is sole source of truth for trajectory.
      const result = await api.runWhatIfProjection({
        name: overrides?.name ?? 'custom_projection',
        description: overrides?.description ?? 'Frontend what-if projection',
        alpha: overrides?.alpha ?? alphaProjection,
        V: overrides?.V ?? volumeProjection,
        q_initial: overrides?.q_initial ?? qStart,
        q_target: overrides?.q_target ?? qEnd,
        q_ramp_days: overrides?.q_ramp_days ?? rampDays,
        horizon_days: overrides?.horizon_days ?? whatIfHorizon,
        disruption_day: overrides !== undefined && 'disruption_day' in overrides
          ? overrides.disruption_day
          : disruptionEnabled ? disruptionDay : null,
        disruption_delta: overrides !== undefined && 'disruption_delta' in overrides
          ? overrides.disruption_delta
          : disruptionEnabled ? -Math.abs(disruptionDrop) : 0,
      }) as WhatIfResult
      setWhatIfResult(result)
    } catch {
      setWhatIfError('Projection failed. Check backend availability.')
    } finally {
      setWhatIfRunning(false)
    }
  }

  const processAlert = async (alertId: string = DEFAULT_ALERT_ID) => {
    setProcessing(true)
    setResult(null)
    setVisibleChecks([])
    try {
      const data = await api.processAlert(alertId, false)
      setResult(data as ProcessResult)
    } catch (error) {
      console.error('Failed to process alert:', error)
    } finally {
      setProcessing(false)
    }
  }

  const simulateFailedGate = async () => {
    setProcessing(true)
    setResult(null)
    setVisibleChecks([])
    try {
      const data = await api.processAlertBlocked(DEFAULT_ALERT_ID)
      setResult(data as ProcessResult)
    } catch (error) {
      console.error('Failed to simulate failure:', error)
    } finally {
      setProcessing(false)
    }
  }

  // ── Derived values ────────────────────────────────────────────────────

  const iks = profileStateFull?.iks ?? null
  // IKS v1 (centroid-drift) is 0 until centroids drift from bootstrap.
  // Prefer IKS v2 (Neo4j composite) which reflects actual decision volume.
  const iksCurrentDisplay: number | null = learningStateData?.iks_v2 ?? iks?.current ?? null
  const decisionCount = iks?.decision_count ?? profileState?.decision_count ?? 0

  // WIRE-04: IKS trend derived values
  const iksTrendPoints: { decisions: number; iks_v2: number; timestamp: string }[] =
    iksTrend ? ensureArray(iksTrend.trend) : []
  const iksTrendDir =
    iksTrendPoints.length >= 2
      ? iksTrendPoints[iksTrendPoints.length - 1].iks_v2 - iksTrendPoints[0].iks_v2
      : 0
  const whatIfChartData = whatIfResult?.daily_trajectory ?? []
  const whatIfCeiling = whatIfResult?.ceiling_estimate ?? null
  const whatIfStartsAboveCeiling = whatIfResult != null && whatIfCeiling != null && (whatIfResult.scenario?.q_initial ?? 0) > (whatIfCeiling / 100)
  const whatIfPresetButtons = [
    ['Healthy', 'healthy_deployment'],
    ['Gradual Decline', 'gradual_degradation'],
    ['Sudden Disruption', 'sudden_disruption'],
    ['High Auto', 'high_automation_good_quality'],
    ['Low Volume', 'low_volume_stress'],
  ] as const
  const timeMachineTimelineChartData = timeMachineTimeline.map(point => ({
    snapshot_id: point.snapshot_id,
    decision_count: point.decision_count ?? 0,
    timestamp_epoch: point.timestamp_epoch ?? point.timestamp ?? 0,
    drift_from_bootstrap: point.drift_from_bootstrap ?? null,
    ceiling_estimate: point.ceiling_estimate ?? null,
  }))
  const hasTimeMachineCeiling = timeMachineTimelineChartData.some(point => point.ceiling_estimate != null)
  const latestSnapshot = timeMachineSnapshots[timeMachineSnapshots.length - 1] ?? null
  const timeMachineComparisonBars = Object.entries(timeMachineComparison?.per_category_distances ?? {}).map(([category, distance]) => ({
    category: category.replace(/_/g, ' '),
    distance,
  }))
  const selectedSnapshotSet = new Set(selectedSnapshotIds)

  useEffect(() => {
    if (selectedSnapshotIds.length !== 2) {
      setTimeMachineComparison(null)
      setTimeMachineComparisonError(null)
      return
    }
    handleRunTimeMachineCompare(selectedSnapshotIds[0], selectedSnapshotIds[1])
  }, [selectedSnapshotIds])

  const categoryStats = (() => {
    if (centroidEvolution.length === 0) return null
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    centroidEvolution.forEach(e => {
      if (!grouped[e.category]) grouped[e.category] = []
      grouped[e.category].push(e)
    })
    let converging = 0, adapting = 0, cold = 0
    const totalCats = profileState?.categories.length ?? 6
    const seenCats = Object.keys(grouped)
    cold = totalCats - seenCats.length
    seenCats.forEach(cat => {
      const entries = grouped[cat]
      const last10 = entries.slice(-10)
      const pctCorrect = last10.filter(e => e.correct).length / last10.length
      if (pctCorrect >= 0.7) converging++
      else adapting++
    })
    return { converging, adapting, cold }
  })()

  const filteredEvolution = (() => {
    if (categoryFilter === 'all') return centroidEvolution
    return centroidEvolution.filter(e => e.category === categoryFilter)
  })()

  const centroidChartData = filteredEvolution.map((e, i) => {
    const win = 20
    const slice = filteredEvolution.slice(Math.max(0, i - win + 1), i + 1)
    const avg = slice.reduce((s, x) => s + x.centroid_delta_norm, 0) / slice.length
    return {
      idx: i + 1,
      reinforced: e.correct ? e.centroid_delta_norm : undefined,
      corrected: !e.correct ? e.centroid_delta_norm : undefined,
      rolling_avg: avg,
    }
  })

  const availableCategories = (() => {
    // Always include all SOC categories from profileState, supplemented by
    // any additional categories that appear in centroidEvolution data.
    const base = profileState?.categories ?? []
    const fromEvolution = centroidEvolution.map(e => e.category)
    return [...new Set([...base, ...fromEvolution])]
  })()

  const categoryConvergenceRows = (() => {
    const cats = profileState?.categories ?? []
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    centroidEvolution.forEach(e => {
      if (!grouped[e.category]) grouped[e.category] = []
      grouped[e.category].push(e)
    })
    return cats.map(cat => {
      const entries = grouped[cat] ?? []
      const last = entries[entries.length - 1]
      const last10 = entries.slice(-10)
      const pctCorrect = last10.length > 0 ? last10.filter(e => e.correct).length / last10.length : 0
      const status = entries.length === 0 ? 'cold' : pctCorrect >= 0.7 ? 'converging' : 'adapting'
      return {
        category: cat,
        status,
        decisions: entries.length,
        lastDelta: last?.centroid_delta_norm ?? null,
      }
    })
  })()

  const categoryNarratives = (() => {
    const cats = profileState?.categories ?? []
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    centroidEvolution.forEach(e => {
      if (!grouped[e.category]) grouped[e.category] = []
      grouped[e.category].push(e)
    })
    return cats.map(cat => {
      const entries = grouped[cat] ?? []
      if (entries.length < 5) return null
      const pct = Math.round(entries.filter(e => e.correct).length / entries.length * 100)
      return `${cat.replace(/_/g, ' ')}: your system resolves ${pct}% of decisions correctly after ${entries.length} verified decisions.`
    }).filter(Boolean) as string[]
  })()

  const driftAlerts = (() => {
    const D_MAX = 0.30
    if (centroidEvolution.length < 50) return null
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    centroidEvolution.forEach(e => {
      if (!grouped[e.category]) grouped[e.category] = []
      grouped[e.category].push(e)
    })
    const alerts: Array<{ category: string; drift: number }> = []
    Object.entries(grouped).forEach(([cat, entries]) => {
      const last50 = entries.slice(-50)
      const drift = last50.reduce((s, e) => s + e.centroid_delta_norm, 0)
      if (drift > D_MAX) alerts.push({ category: cat, drift })
    })
    return alerts
  })()

  // Section A: find matching centroid-evolution entry for the pending decision (Option A)
  const pendingEntry = pendingDecisionId
    ? centroidEvolution.find(e => e.id === pendingDecisionId) ?? null
    : null

  const iksArrow = iks?.delta_7d !== null && iks?.delta_7d !== undefined
    ? (iks.delta_7d > 0 ? '\u2191' : iks.delta_7d < 0 ? '\u2193' : '\u2192')
    : '\u2192'
  const iksDeltaLabel = iks?.delta_7d !== null && iks?.delta_7d !== undefined
    ? `${iks.delta_7d > 0 ? '+' : ''}${iks.delta_7d.toFixed(1)} this week`
    : 'no trend data yet'

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading deployments...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ── Summary Panel ────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 rounded-lg border border-purple-500/40 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-5 h-5 text-soc-secondary" />
          <h2 className="text-base font-bold text-white">Institutional Intelligence Summary — How the system's judgment has evolved</h2>
          <span className="ml-2 px-2 py-0.5 bg-soc-secondary/30 text-soc-secondary text-xs font-bold rounded-full">THE DIFFERENTIATOR</span>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          {/* Left: ProfileScorer */}
          <div className="bg-blue-900/20 rounded border border-blue-500/30 p-4">
            <div className="text-xs font-semibold text-blue-300 uppercase tracking-wide mb-3">Situational Understanding (ProfileScorer)</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Categories converging</span>
                <span className="font-bold text-green-400">{categoryStats?.converging ?? 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Categories adapting</span>
                <span className="font-bold text-amber-400">{categoryStats?.adapting ?? 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Categories cold</span>
                <span className="font-bold text-gray-500">{categoryStats?.cold ?? (profileState?.categories.length ?? 6)}</span>
              </div>
              {!categoryStats && decisionCount === 0 && (
                <p className="text-xs text-gray-500 italic mt-1">(cold-start &mdash; {decisionCount} decisions recorded)</p>
              )}
            </div>
          </div>

          {/* Right: AgentEvolver */}
          <div className="bg-purple-900/20 rounded border border-purple-500/30 p-4">
            <div className="text-xs font-semibold text-purple-300 uppercase tracking-wide mb-3">Deployment Adaptation (AgentEvolver)</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Active variant</span>
                <span className="font-mono text-purple-300 text-xs">{result?.prompt_evolution?.current_variant ?? '\u2014'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Promotions (session)</span>
                <span className="font-bold text-purple-300">{result?.prompt_evolution?.promotion_occurred ? 1 : 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">False escalation &Delta;</span>
                <span className="font-bold text-green-400">
                  {result?.prompt_evolution?.operational_impact
                    ? `${result.prompt_evolution.operational_impact.fewer_false_escalations_pct}%`
                    : '\u2014'}
                  {result?.prompt_evolution?.operational_impact && decisionCount < 50 && (
                    <span className="text-xs text-gray-500 font-normal ml-1">(projected)</span>
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer row */}
        <div className="flex items-center justify-between border-t border-gray-700/50 pt-3">
          <span className="text-sm text-gray-400">
            <span className="font-semibold text-white">{decisionCount}</span> verified decisions &middot; Both mechanisms active
          </span>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">IKS:</span>
            {iksCurrentDisplay === null ? (
              <span className="text-gray-500 italic">&mdash; (baseline not established)</span>
            ) : (
              <>
                <span className="font-bold text-soc-secondary">{iksCurrentDisplay.toFixed(1)}</span>
                <span className="text-gray-400">{iksArrow}</span>
                <span className={`text-xs ${iks?.delta_7d !== null && iks?.delta_7d !== undefined && iks?.delta_7d > 0 ? 'text-green-400' : 'text-gray-500'}`}>
                  {iksDeltaLabel}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Mobile horizontal tab bar ─────────────────────────────────── */}
      <div className="md:hidden flex gap-1 bg-soc-card rounded-lg border border-gray-800 p-1">
        {(['a', 'b', 'c', 'd'] as const).map((id, i) => {
          const labels = ['A \u00b7 This Decision', 'B \u00b7 Situational', 'C \u00b7 Adaptation', 'D \u00b7 Health']
          return (
            <button
              key={id}
              onClick={() => {
                document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth' })
                setActiveSection(id)
              }}
              className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${activeSection === id ? 'bg-soc-secondary/20 text-soc-secondary' : 'text-gray-500 hover:text-gray-300'}`}
            >
              {labels[i]}
            </button>
          )
        })}
      </div>

      {/* ── Left-rail + Sections ──────────────────────────────────────── */}
      <div className="flex gap-6 items-start">

        {/* Left-rail navigator — sticky desktop */}
        <nav className="hidden md:block w-44 flex-shrink-0 sticky top-4 self-start">
          <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-800">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sections</span>
            </div>
            <div className="p-2 space-y-1">
              {[
                { id: 'a', label: 'This Decision', sub: 'Eval \u00b7 GAE \u00b7 Trace' },
                { id: 'b', label: 'Situational', sub: 'Centroids \u00b7 Chart' },
                { id: 'c', label: 'Adaptation', sub: 'AgentEvolver' },
                { id: 'd', label: 'System Health', sub: 'IKS \u00b7 Loop 3 \u00b7 Graph' },
              ].map(({ id, label, sub }) => (
                <button
                  key={id}
                  onClick={() => {
                    document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                    setActiveSection(id as 'a' | 'b' | 'c' | 'd')
                  }}
                  className={`w-full text-left px-2.5 py-2 rounded transition-colors ${activeSection === id ? 'bg-soc-secondary/15 border-l-2 border-soc-secondary' : 'hover:bg-gray-800/50 border-l-2 border-transparent'}`}
                >
                  <div className={`text-xs font-bold uppercase tracking-wide ${activeSection === id ? 'text-soc-secondary' : 'text-gray-400'}`}>
                    [{id.toUpperCase()}] {label}
                  </div>
                  <div className="text-xs text-gray-600 mt-0.5">{sub}</div>
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* Main sections content */}
        <div className="flex-1 min-w-0 space-y-12">

          {/* ── SECTION A: This Decision ─────────────────────────────── */}
          <div id="section-a" data-section="a" ref={sectionARef} className="scroll-mt-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-soc-secondary/20 border border-soc-secondary/50 flex items-center justify-center text-xs font-bold text-soc-secondary">A</div>
              <h3 className="font-bold text-white text-base">This Decision</h3>
              {pendingDecisionId && (
                <span className="text-xs text-purple-300 bg-purple-900/30 border border-purple-500/30 px-2 py-0.5 rounded">
                  &larr; Decision {pendingDecisionId}
                </span>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex gap-3 mb-6">
              <button
                onClick={() => processAlert()}
                disabled={processing}
                className="flex items-center gap-2 px-5 py-2.5 bg-soc-primary hover:bg-soc-primary/80 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors text-sm"
              >
                {processing ? (
                  <><Clock className="w-4 h-4 animate-spin" />Processing...</>
                ) : (
                  <><Activity className="w-4 h-4" />Process {domainConfig.triggerEntity} ({DEFAULT_ALERT_ID})</>
                )}
              </button>
              <button
                onClick={simulateFailedGate}
                disabled={processing}
                className="flex items-center gap-2 px-5 py-2.5 bg-soc-danger/20 hover:bg-soc-danger/30 disabled:bg-gray-700 disabled:cursor-not-allowed border border-soc-danger/50 rounded-lg font-semibold transition-colors text-sm"
              >
                <AlertTriangle className="w-4 h-4" />Simulate Failed Gate
              </button>
            </div>

            {!result ? (
              pendingEntry ? (
                <div className="bg-purple-900/10 border border-purple-500/30 rounded-lg p-5 space-y-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-purple-400" />
                    <span className="text-sm font-semibold text-purple-300">
                      Decision recorded — centroid updated
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <div className="text-gray-500">Category</div>
                      <div className="text-gray-200 font-mono mt-0.5">{pendingEntry.category}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Action</div>
                      <div className="text-gray-200 font-mono mt-0.5">{pendingEntry.action}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Centroid ‖Δμ‖</div>
                      <div className="text-gray-200 font-mono mt-0.5">{pendingEntry.centroid_delta_norm.toFixed(4)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Outcome</div>
                      <div className={`font-semibold mt-0.5 ${pendingEntry.correct ? 'text-green-400' : 'text-amber-400'}`}>
                        {pendingEntry.correct ? 'Correct ✓' : 'Incorrect — corrected'}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500">
                    Process a new alert above to see the live eval gate and GAE scoring for comparison.
                  </p>
                </div>
              ) : (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-8 text-center">
                  <Activity className="w-8 h-8 mx-auto mb-3 text-gray-600" />
                  <p className="text-gray-500 text-sm">
                    {pendingDecisionId
                      ? `Decision ${pendingDecisionId} was recorded \u2014 process a new alert to see live decision trace.`
                      : `No verified decisions yet \u2014 click \u201cProcess Alert\u201d above to begin.`}
                  </p>
                </div>
              )
            ) : (
              <div className="space-y-5">

                {/* Eval Gate */}
                <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-800">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold flex items-center gap-2 text-sm">
                        <Shield className="w-4 h-4" />
                        Eval Gate &mdash; {result.alert_id}
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-500 text-white">CONSUME &#10003;</span>
                      </h4>
                      {result.eval_gate.overall_passed
                        ? <span className="flex items-center gap-1 text-soc-success text-sm font-semibold"><CheckCircle className="w-4 h-4" />PASS</span>
                        : <span className="flex items-center gap-1 text-soc-danger text-sm font-semibold"><XCircle className="w-4 h-4" />BLOCKED</span>}
                    </div>
                  </div>
                  <div className="p-5 space-y-3">
                    {ensureArray<EvalCheck>(result.eval_gate.checks).map((check, index) => {
                      const isVisible = visibleChecks.includes(index)
                      return (
                        <div
                          key={check.name}
                          className={`flex items-center justify-between p-3 rounded border transition-all duration-500 ${isVisible ? 'opacity-100' : 'opacity-30'} ${isVisible && !check.passed ? 'bg-soc-danger/10 border-soc-danger/50' : 'bg-soc-bg border-gray-800'}`}
                        >
                          {isVisible ? (
                            <>
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-0.5">
                                  <span className="font-semibold text-sm">{check.name}</span>
                                  {check.passed ? <CheckCircle className="w-3.5 h-3.5 text-soc-success" /> : <XCircle className="w-3.5 h-3.5 text-soc-danger" />}
                                </div>
                                <p className={`text-xs ${check.passed ? 'text-gray-400' : 'text-soc-danger'}`}>{check.message}</p>
                              </div>
                              <div className="text-right ml-4">
                                <div className={`font-mono font-bold ${check.passed ? '' : 'text-soc-danger'}`}>{check.score.toFixed(2)}</div>
                                <div className="text-xs text-gray-500">&gt; {check.threshold.toFixed(2)}</div>
                              </div>
                            </>
                          ) : (
                            <div className="flex items-center gap-2">
                              <Clock className="w-4 h-4 animate-spin text-gray-400" />
                              <span className="font-semibold text-gray-400 text-sm">{check.name}</span>
                              <span className="text-xs text-gray-500">Checking...</span>
                            </div>
                          )}
                        </div>
                      )
                    })}
                    <div className="p-3 bg-soc-bg/50 rounded border border-gray-700">
                      <span className="text-xs text-gray-400">Overall Score: </span>
                      <span className="font-bold font-mono">{result.eval_gate.overall_score.toFixed(3)}</span>
                    </div>
                  </div>
                </div>

                {/* BLOCKED banner */}
                {!result.eval_gate.overall_passed && (
                  <div className="bg-gradient-to-r from-soc-danger/30 to-amber-900/30 rounded-lg border-2 border-soc-danger p-5">
                    <div className="flex items-start gap-3">
                      <Shield className="w-5 h-5 text-soc-danger mt-0.5 flex-shrink-0" />
                      <div>
                        <h4 className="font-bold text-soc-danger mb-1">&#128737; BLOCKED BY EVAL GATE</h4>
                        <p className="text-sm text-gray-300">{result.blocked_reason || result.execution.reason || 'Action blocked by evaluation gate.'}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* GAE Scoring */}
                {result.gae_scoring && (
                  <div className="bg-soc-card rounded-lg border border-soc-secondary/30 overflow-hidden">
                    <div className="px-5 py-3 border-b border-soc-secondary/20 bg-soc-secondary/5">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-soc-secondary">GAE Scoring</span>
                        <span className="px-1.5 py-0.5 bg-soc-secondary/20 text-soc-secondary text-xs rounded font-mono">
                          softmax(&minus;&#8214;f&minus;&mu;&#8214;&sup2; / &tau;={result.gae_scoring.temperature})
                        </span>
                        <span className="text-xs text-gray-500">Why this action was recommended</span>
                      </div>
                    </div>
                    <div className="p-5">
                      <div className="space-y-1.5 mb-4">
                        {ensureArray<string>(result.gae_scoring.factor_names).map((name, i) => (
                          <div key={name} className="flex items-center gap-2 text-xs">
                            <div className="w-32 text-gray-400 truncate capitalize">{name.replace(/_/g, ' ')}</div>
                            <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                              <div className="bg-soc-secondary h-1.5 rounded-full transition-all" style={{ width: `${(result.gae_scoring!.factor_vector[i] * 100).toFixed(0)}%` }} />
                            </div>
                            <div className="w-10 text-right text-gray-400 font-mono">{result.gae_scoring!.factor_vector[i].toFixed(2)}</div>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-2 flex-wrap">
                        {Object.entries(ensureObject<Record<string, number>>(result.gae_scoring.action_probabilities)).sort(([, a], [, b]) => b - a).map(([action, prob]) => (
                          <span
                            key={action}
                            className={`px-2 py-0.5 rounded text-xs font-mono ${action === result.decision_trace.action_taken ? 'bg-soc-secondary/30 text-soc-secondary font-bold ring-1 ring-soc-secondary/50' : 'bg-gray-800 text-gray-400'}`}
                          >
                            {action}: {(prob * 100).toFixed(1)}%
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Centroid delta from most recent entry */}
                {centroidEvolution.length > 0 && (() => {
                  const last = centroidEvolution[centroidEvolution.length - 1]
                  if (last.centroid_delta_norm <= 0) return null
                  return (
                    <div className="bg-soc-card rounded-lg border border-gray-700 p-4">
                      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Last Centroid Update</div>
                      <div className="flex items-center gap-3 text-sm">
                        <span className="font-mono text-gray-300">&#8214;&Delta;&mu;&#8214; = {last.centroid_delta_norm.toFixed(4)}</span>
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${last.correct ? 'bg-green-900/30 text-green-400 border border-green-600/40' : 'bg-orange-900/30 text-orange-400 border border-orange-600/40'}`}>
                          {last.correct ? '\u2191 Reinforced' : '\u2193 Corrected'}
                        </span>
                        <span className="text-gray-500 text-xs">
                          {last.category.replace(/_/g, ' ')}: This decision {last.correct ? 'reinforced' : 'corrected'} the {last.action} centroid.
                        </span>
                      </div>
                    </div>
                  )
                })()}

                {/* Decision Trace */}
                <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                  <div className="px-5 py-3 border-b border-gray-800">
                    <h4 className="font-semibold flex items-center gap-2 text-sm">
                      <Activity className="w-4 h-4" />
                      Decision Trace &mdash; {result.decision_trace.id}
                    </h4>
                  </div>
                  <div className="p-5 space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-gray-500 mb-1 text-xs">Input</div>
                        <div className="font-semibold">{result.alert_id}</div>
                        <div className="text-xs text-gray-400">{result.context_preview.user_name} on {result.context_preview.asset_hostname}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 mb-1 text-xs">Context</div>
                        <div className="font-semibold">{result.decision_trace.nodes_consulted} graph nodes</div>
                        <div className="text-xs text-gray-400">{result.context_preview.pattern_count} patterns matched</div>
                      </div>
                      <div>
                        <div className="text-gray-500 mb-1 text-xs">Decision</div>
                        <div className="font-semibold">{result.decision_trace.action_taken.replace(/_/g, ' ')}</div>
                        <div className="text-xs text-gray-400">{(result.decision_trace.confidence * 100).toFixed(0)}% confidence</div>
                      </div>
                      <div>
                        <div className="text-gray-500 mb-1 text-xs">Execution</div>
                        <div className="flex items-center gap-1 text-soc-success">
                          <CheckCircle className="w-4 h-4" />
                          <span className="font-semibold">{result.execution.status}</span>
                        </div>
                      </div>
                    </div>
                    <div className="p-3 bg-soc-bg rounded border border-gray-800">
                      <div className="text-xs text-gray-500 mb-1">Reasoning</div>
                      <p className="text-sm leading-relaxed">{result.decision_trace.reasoning}</p>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-soc-bg rounded border border-gray-800 p-3 text-center">
                        <div className="text-xs text-gray-500 mb-1">Execution Time</div>
                        <div className="font-bold font-mono">{result.execution_time_ms.toFixed(0)}ms</div>
                      </div>
                      <div className="bg-soc-bg rounded border border-gray-800 p-3 text-center">
                        <div className="text-xs text-gray-500 mb-1">Routed To</div>
                        <div className="font-bold font-mono text-sm">{result.routed_to}</div>
                      </div>
                      <div className="bg-soc-bg rounded border border-gray-800 p-3 text-center">
                        <div className="text-xs text-gray-500 mb-1">Event ID</div>
                        <div className="font-bold font-mono text-sm text-soc-secondary">{result.triggered_evolution.event_id || 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* TRIGGERED_EVOLUTION */}
                {result.triggered_evolution.occurred && (
                  <div className="bg-gradient-to-r from-soc-secondary/30 to-purple-900/30 rounded-lg border-2 border-soc-secondary p-5">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-soc-secondary/20 rounded-lg">
                        <TrendingUp className="w-5 h-5 text-soc-secondary" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-bold text-soc-secondary">&#128279; TRIGGERED_EVOLUTION</h4>
                          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-600 text-white">MUTATE &#10003;</span>
                          <span className="px-2 py-0.5 bg-soc-secondary/20 text-soc-secondary text-xs font-bold rounded">What SIEMs don&apos;t have</span>
                        </div>
                        <p className="text-sm text-gray-300 mb-3">This decision trace triggered agent evolution:</p>
                        {result.triggered_evolution.changes?.map((change, idx) => (
                          <div key={idx} className="bg-soc-bg/50 rounded p-3 mb-2 border border-soc-secondary/30">
                            <div className="font-semibold mb-1 text-sm">{result.triggered_evolution.description}</div>
                            <div className="flex items-center gap-4 text-sm">
                              <div><span className="text-gray-500">Before:</span><span className="ml-2 font-mono">{change.before.confidence}%</span></div>
                              <div className="text-gray-500">&rarr;</div>
                              <div><span className="text-gray-500">After:</span><span className="ml-2 font-mono font-bold text-soc-success">{change.after.confidence}%</span></div>
                              <div className="ml-auto text-soc-success font-semibold">+{change.after.confidence - change.before.confidence} pts</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* No evolution when blocked */}
                {!result.triggered_evolution.occurred && !result.eval_gate.overall_passed && (
                  <div className="bg-gray-800/50 rounded-lg border-2 border-gray-700 p-5">
                    <div className="flex items-start gap-3">
                      <XCircle className="w-5 h-5 text-gray-400 mt-0.5" />
                      <div>
                        <h4 className="font-bold text-gray-400 mb-1">No Evolution Triggered</h4>
                        <p className="text-sm text-gray-400 mb-2">Agent evolution did not occur because the action was blocked by the eval gate.</p>
                        <p className="text-sm text-gray-400"><strong>Safety First:</strong> Only successful, verified actions contribute to agent learning.</p>
                      </div>
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>

          {/* ── SECTION B: Situational Understanding ─────────────────── */}
          <div id="section-b" data-section="b" ref={sectionBRef} className="scroll-mt-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-blue-500/20 border border-blue-500/50 flex items-center justify-center text-xs font-bold text-blue-400">B</div>
              <h3 className="font-bold text-white text-base">Situational Understanding</h3>
              <span className="text-xs text-gray-500">What your environment&apos;s patterns have taught the system</span>
            </div>

            <div className="space-y-5">

              {/* D1. Centroid Evolution Chart */}
              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-200">Centroid learning magnitude per verified decision</h4>
                    <p className="text-xs text-gray-500 mt-0.5">Green = reinforced, orange = corrected &middot; Purple line = 20-decision rolling average</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {availableCategories.length > 0 && (
                      <select
                        value={categoryFilter}
                        onChange={e => setCategoryFilter(e.target.value)}
                        className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300"
                      >
                        <option value="all">All categories</option>
                        {availableCategories.map(cat => (
                          <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>
                <div className="p-4">
                  {centroidEvoLoading ? (
                    <div className="py-10 text-center text-gray-500 text-sm">Loading centroid evolution data...</div>
                  ) : centroidEvoError ? (
                    <div className="py-10 text-center text-gray-500 text-sm italic">
                      Centroid evolution data not yet available.
                    </div>
                  ) : centroidChartData.length === 0 ? (
                    <div className="py-10 text-center text-gray-500 text-sm italic">
                      No verified decisions recorded yet. This chart will populate as analysts verify triage outcomes.
                    </div>
                  ) : (
                    <div className="bg-white rounded p-3">
                      <ResponsiveContainer width="100%" height={200}>
                        <ComposedChart
                          data={centroidChartData}
                          margin={{ top: 5, right: 10, left: -10, bottom: 18 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                          <XAxis
                            dataKey="idx"
                            tick={{ fontSize: 10 }}
                            label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }}
                          />
                          <YAxis
                            tick={{ fontSize: 10 }}
                            tickFormatter={(v: number) => v.toFixed(3)}
                            label={{ value: '\u2016\u0394\u03bc\u2016', angle: -90, position: 'insideLeft', fontSize: 10 }}
                          />
                          <Tooltip
                            formatter={(v: unknown, name: string) => [
                              Number(v).toFixed(5),
                              name === 'reinforced' ? '\u2016\u0394\u03bc\u2016 reinforced' : name === 'corrected' ? '\u2016\u0394\u03bc\u2016 corrected' : 'rolling avg (20)',
                            ]}
                            labelFormatter={(l) => `Decision #${l}`}
                          />
                          <Legend
                            wrapperStyle={{ fontSize: 10 }}
                            formatter={(v: string) => v === 'reinforced' ? '\u2016\u0394\u03bc\u2016 reinforced' : v === 'corrected' ? '\u2016\u0394\u03bc\u2016 corrected' : 'rolling avg (20)'}
                          />
                          <Bar dataKey="reinforced" fill="#10b981" name="reinforced" radius={[2, 2, 0, 0]} />
                          <Bar dataKey="corrected" fill="#f97316" name="corrected" radius={[2, 2, 0, 0]} />
                          <Line type="monotone" dataKey="rolling_avg" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="rolling_avg" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </div>

              {/* D2. Per-Category Convergence Table */}
              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-800">
                  <h4 className="text-sm font-semibold text-gray-200">Per-Category Convergence Status</h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-soc-bg/50">
                      <tr className="text-left text-xs text-gray-400">
                        <th className="px-4 py-2">Category</th>
                        <th className="px-4 py-2">Status</th>
                        <th className="px-4 py-2">Decisions</th>
                        <th className="px-4 py-2">Last &#8214;&Delta;&mu;&#8214;</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {categoryConvergenceRows.map(row => (
                        <tr key={row.category} className="text-sm">
                          <td className="px-4 py-2 capitalize">{row.category.replace(/_/g, ' ')}</td>
                          <td className="px-4 py-2">
                            {row.status === 'converging' && <span className="px-1.5 py-0.5 bg-green-900/30 text-green-400 text-xs rounded border border-green-700/40 font-semibold">Converging</span>}
                            {row.status === 'adapting' && <span className="px-1.5 py-0.5 bg-amber-900/30 text-amber-400 text-xs rounded border border-amber-700/40 font-semibold">Adapting</span>}
                            {row.status === 'cold' && <span className="px-1.5 py-0.5 bg-gray-800 text-gray-500 text-xs rounded border border-gray-700 font-semibold">Cold start</span>}
                          </td>
                          <td className="px-4 py-2 font-mono text-gray-300">{row.decisions}</td>
                          <td className="px-4 py-2 font-mono text-gray-400">{row.lastDelta !== null ? row.lastDelta.toFixed(4) : '\u2014'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* D3. Profile Centroids Heatmap */}
              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-200">Profile Centroids &mdash; Current State</h4>
                    <p className="text-xs text-gray-500 mt-0.5">Mean factor value per (category, action) &mdash; higher = stronger signal</p>
                  </div>
                  {profileStateFull && (
                    <span className="text-xs text-gray-500 font-mono">{decisionCount} decisions recorded</span>
                  )}
                </div>
                <div className="p-4 overflow-x-auto">
                  {!profileState ? (
                    <div className="text-sm text-gray-500 py-4 text-center">Loading centroid data&hellip;</div>
                  ) : (
                    <>
                      <table style={{ borderCollapse: 'collapse', minWidth: '100%' }}>
                        <thead>
                          <tr>
                            <th style={{ width: 160, textAlign: 'left', padding: '4px 8px', fontSize: 11, color: '#9ca3af', fontWeight: 500 }}>Category</th>
                            {ensureArray<string>(profileState.actions).map(action => (
                              <th key={action} style={{ width: 80, textAlign: 'center', padding: '4px 8px', fontSize: 11, color: '#9ca3af', fontWeight: 500, textTransform: 'capitalize' }}>{action}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {ensureArray<string>(profileState.categories).map((cat, cIdx) => (
                            <tr key={cat}>
                              <td style={{ padding: '4px 8px', fontSize: 11, color: '#d1d5db', whiteSpace: 'nowrap' }}>{cat.replace(/_/g, ' ')}</td>
                              {ensureArray<string>(profileState.actions).map((_, aIdx) => {
                                const factors = profileState.centroids[cIdx][aIdx]
                                const meanVal = factors.reduce((s, v) => s + v, 0) / factors.length
                                const count = profileState.counts[cIdx][aIdx]
                                const bg = `rgba(59, 130, 246, ${meanVal.toFixed(2)})`
                                const textColor = meanVal > 0.6 ? '#ffffff' : '#d1d5db'
                                return (
                                  <td key={aIdx} style={{ width: 80, padding: '4px 8px', textAlign: 'center', backgroundColor: bg, color: textColor, borderRadius: 4 }}>
                                    {count === 0 ? (
                                      <div style={{ fontSize: 10, color: '#6b7280', fontStyle: 'italic' }}>cold start</div>
                                    ) : (
                                      <>
                                        <div style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace' }}>{meanVal.toFixed(2)}</div>
                                        <div style={{ fontSize: 10, opacity: 0.75 }}>n={count}</div>
                                      </>
                                    )}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p style={{ fontSize: 10, color: '#6b7280', marginTop: 8 }}>0.0 = no signal &nbsp;&middot;&nbsp; 1.0 = strong signal &nbsp;&middot;&nbsp; color intensity &prop; mean centroid value</p>
                    </>
                  )}
                </div>
              </div>

              {/* D4. Natural Language Narrative */}
              {categoryNarratives.length > 0 && (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Category Learning Narrative</h4>
                  <ul className="space-y-1.5">
                    {categoryNarratives.map((n, i) => (
                      <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                        <span className="text-blue-400 mt-0.5">&bull;</span>
                        <span>{n}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            </div>
          </div>

          {/* ── SECTION C: Deployment Adaptation ────────────────────── */}
          <div id="section-c" data-section="c" ref={sectionCRef} className="scroll-mt-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-purple-500/20 border border-purple-500/50 flex items-center justify-center text-xs font-bold text-purple-400">C</div>
              <h3 className="font-bold text-white text-base">Deployment Adaptation</h3>
              <span className="text-xs text-gray-500">How the system has learned to operate in your environment</span>
            </div>

            {/* Deployment Registry */}
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden mb-5">
              <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
                <h4 className="text-sm font-semibold flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  Deployment Registry
                </h4>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-soc-bg/50">
                    <tr className="text-left text-xs text-gray-400">
                      <th className="px-5 py-3">Agent</th>
                      <th className="px-5 py-3">Version</th>
                      <th className="px-5 py-3">Traffic</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Auto-Close Rate (7d)</th>
                      <th className="px-5 py-3">Patterns</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {deployments.map((deployment) => (
                      <tr key={deployment.version} className="text-sm">
                        <td className="px-5 py-3">{deployment.agent_name}</td>
                        <td className="px-5 py-3 font-mono font-semibold">{deployment.version}</td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                              <div className="h-full bg-soc-primary" style={{ width: `${deployment.traffic_pct}%` }} />
                            </div>
                            <span className="text-gray-400 text-xs">{deployment.traffic_pct}%</span>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${deployment.status === 'active' ? 'bg-soc-success/20 text-soc-success' : 'bg-soc-warning/20 text-soc-warning'}`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${deployment.status === 'active' ? 'bg-soc-success' : 'bg-soc-warning'}`} />
                            {deployment.status}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <span className="font-semibold">{deployment.auto_close_rate_7d}%</span>
                          <span className="text-gray-500 text-xs ml-2">(n={deployment.sample_count_7d.toLocaleString()})</span>
                        </td>
                        <td className="px-5 py-3">
                          <span className="font-semibold text-soc-secondary">{deployment.pattern_count}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Agent Evolution Panel */}
            {result?.prompt_evolution && (
              <div className="bg-purple-900/20 rounded-lg border-2 border-purple-500/40 p-5">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 bg-purple-500/20 rounded-lg">
                    <Sparkles className="w-5 h-5 text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h4 className="font-bold text-purple-300">&#129166; Agent Evolution</h4>
                      <span className="px-2 py-0.5 bg-purple-500/30 text-purple-300 text-xs font-semibold rounded border border-purple-400/50">MUTATE</span>
                    </div>
                    <p className="text-sm text-gray-300 mb-3">Loop 2: Prompt variants track performance across decisions. Better variants get promoted automatically.</p>

                    {/* GAE Learning State strip */}
                    {result.gae_summary && (
                      <div className="mb-4 p-3 bg-purple-950/30 rounded border border-purple-500/20 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-sm min-w-0">
                          <Activity className="w-4 h-4 text-purple-400 flex-shrink-0" />
                          {result.gae_summary.decision_count === 0 ? (
                            <span className="text-gray-500 text-xs">W matrix at initialization &mdash; submit outcomes in Tab 3 to evolve weights</span>
                          ) : (
                            <span className="text-xs">
                              <span className="font-bold text-purple-300">{result.gae_summary.decision_count}</span>
                              <span className="text-gray-400"> GAE weight update{result.gae_summary.decision_count !== 1 ? 's' : ''} applied</span>
                            </span>
                          )}
                        </div>
                        {result.gae_summary.has_real_data && (
                          <div className="flex gap-3 flex-shrink-0">
                            {Object.entries(ensureObject<Record<string, number>>(result.gae_summary.w_norms)).map(([action, norm]) => (
                              <div key={action} className="text-center">
                                <div className="text-xs font-mono text-purple-300">{norm.toFixed(2)}</div>
                                <div className="text-xs text-gray-600 capitalize">{action.slice(0, 3)}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Variant performance */}
                    <div className="space-y-3 mb-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-500 uppercase tracking-wide">Variant performance</span>
                      </div>
                      {result.prompt_evolution.previous_variant && (
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-gray-400 font-mono">{result.prompt_evolution.previous_variant}</span>
                            <span className="text-xs text-gray-400">
                              {(result.prompt_evolution.previous_success_rate! * 100).toFixed(1)}%{' '}
                              <span className="text-gray-600 font-normal">(Historical baseline &mdash; 15 decisions)</span>
                            </span>
                          </div>
                          <div className="w-full bg-gray-700/50 rounded-full h-2">
                            <div
                              className="bg-gray-500 h-2 rounded-full transition-all duration-1000"
                              style={{ width: `${result.prompt_evolution.previous_success_rate! * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-purple-300 font-mono font-semibold">{result.prompt_evolution.current_variant}</span>
                          <span className="text-sm text-purple-300 font-semibold">
                            {(result.prompt_evolution.current_success_rate * 100).toFixed(1)}%{' '}
                            <span className="text-gray-500 text-xs font-normal">(This session)</span>
                          </span>
                        </div>
                        <div className="w-full bg-gray-700/50 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full transition-all duration-1000"
                            style={{ width: `${result.prompt_evolution.current_success_rate * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Promotion Status */}
                    <div className="p-3 bg-purple-950/40 rounded border border-purple-500/30 mb-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-purple-200">Status:</span>
                        {result.prompt_evolution.promotion_occurred
                          ? <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs font-semibold rounded border border-green-400/50">Promoted &#10003;</span>
                          : <span className="text-sm text-gray-400">Active (monitoring)</span>}
                      </div>
                      {result.prompt_evolution.promotion_reason && (
                        <p className="text-sm text-gray-300 mt-1">{result.prompt_evolution.promotion_reason}</p>
                      )}
                    </div>

                    {/* What Changed Narrative */}
                    {result.prompt_evolution.what_changed_narrative && (
                      <div className="p-4 bg-purple-950/20 rounded border border-purple-500/30 mb-3">
                        <div className="flex items-start gap-2">
                          <Lightbulb className="w-4 h-4 text-purple-300 mt-0.5 flex-shrink-0" />
                          <div>
                            {decisionCount < 20 ? (
                              <p className="text-sm text-gray-500 italic">Insufficient session decisions to characterize operational change &mdash; available after 20 decisions.</p>
                            ) : (
                              <>
                                <div className="text-xs font-semibold text-purple-300 uppercase tracking-wide mb-1">What Changed</div>
                                <p className="text-sm text-gray-300 italic">{result.prompt_evolution.what_changed_narrative}</p>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Operational Impact */}
                    {result.prompt_evolution.operational_impact && (
                      <div className="mb-3">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="text-xs font-semibold text-purple-300 uppercase tracking-wide">Operational Impact</div>
                          {decisionCount < 50 && (
                            <span className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 text-xs border border-gray-700">
                              projected &mdash; based on {decisionCount} decisions
                            </span>
                          )}
                        </div>
                        <div className="flex gap-3 flex-wrap">
                          <div className="flex-1 min-w-[100px] bg-purple-950/30 rounded border border-purple-500/20 p-3">
                            <div className="text-xl font-bold text-green-400">{result.prompt_evolution.operational_impact.fewer_false_escalations_pct}%</div>
                            <div className="text-xs text-gray-400 mt-1">fewer false escalations</div>
                          </div>
                          <div className="flex-1 min-w-[100px] bg-purple-950/30 rounded border border-purple-500/20 p-3">
                            <div className="text-xl font-bold text-green-400">{result.prompt_evolution.operational_impact.fewer_false_escalations_monthly}</div>
                            <div className="text-xs text-gray-400 mt-1">fewer Tier 2 reviews/mo</div>
                          </div>
                          <div className="flex-1 min-w-[100px] bg-purple-950/30 rounded border border-purple-500/20 p-3">
                            <div className="text-xl font-bold text-green-400">{result.prompt_evolution.operational_impact.analyst_hours_recovered}</div>
                            <div className="text-xs text-gray-400 mt-1">hrs recovered/mo</div>
                          </div>
                          <div className="flex-1 min-w-[100px] bg-purple-950/30 rounded border border-purple-500/20 p-3">
                            <div className="flex items-center gap-1">
                              <DollarSign className="w-4 h-4 text-green-400" />
                              <div className="text-xl font-bold text-green-400">{result.prompt_evolution.operational_impact.estimated_monthly_savings.toLocaleString()}</div>
                            </div>
                            <div className="text-xs text-gray-400 mt-1">saved/mo</div>
                          </div>
                          <div className="flex-1 min-w-[100px] bg-purple-950/30 rounded border border-purple-500/20 p-3">
                            <div className="flex items-center gap-1">
                              <Shield className="w-4 h-4 text-blue-400" />
                              <div className="text-xl font-bold text-blue-400">{result.prompt_evolution.operational_impact.missed_threats}</div>
                            </div>
                            <div className="text-xs text-gray-400 mt-1">missed threats</div>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="p-3 bg-purple-950/30 rounded border border-purple-500/30">
                      <p className="text-sm italic text-purple-300">&#128161; Loop 2 makes the agent smarter ACROSS decisions by learning which prompts work best.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!result?.prompt_evolution && (
              <div className="bg-soc-card rounded-lg border border-gray-800 p-8 text-center">
                <Sparkles className="w-8 h-8 mx-auto mb-3 text-gray-600" />
                <p className="text-sm text-gray-500">Process an alert in Section A to see agent evolution data.</p>
              </div>
            )}
          </div>

          {/* ── SECTION D: System Health ─────────────────────────────── */}
          <div id="section-d" data-section="d" ref={sectionDRef} className="scroll-mt-4">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center text-xs font-bold text-emerald-400">D</div>
              <h3 className="font-bold text-white text-base">System Health</h3>
            </div>

            <div className="space-y-5">

              {profileError && (
                <div className="text-sm text-red-400 py-2 px-3 bg-red-900/20 rounded border border-red-800/50">
                  Unable to load profile data — check backend connection
                </div>
              )}

              {/* F1. IKS Block */}
              <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                <h4 className="text-sm font-semibold text-gray-200 mb-3">Institutional Knowledge Score (IKS)</h4>
                {!iks && !learningStateData ? (
                  <div className="text-sm text-gray-500 py-2">Loading IKS&hellip;</div>
                ) : iksCurrentDisplay === null ? (
                  <div className="text-sm text-gray-400 italic">IKS: &mdash; (baseline not established)</div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="text-3xl font-bold font-mono text-soc-secondary">{iksCurrentDisplay.toFixed(1)}</div>
                        <div className="text-xs text-gray-500">/ 100</div>
                      </div>
                      <div>
                        <div className={`text-lg font-semibold ${iks?.delta_7d !== null && iks?.delta_7d !== undefined && iks.delta_7d > 0 ? 'text-green-400' : iks?.delta_7d !== null && iks?.delta_7d !== undefined && iks.delta_7d < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                          {iksArrow} {iksDeltaLabel}
                        </div>
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded border border-gray-700 p-3">
                      <p className="text-sm text-gray-300 italic">{iks?.interpretation}</p>
                    </div>
                    {iks?.estimated && (!iks?.trend || iks.trend.length === 0) && (
                      <p className="text-xs text-gray-500 italic">(Drift trend available after first 50 verified decisions)</p>
                    )}

                    {/* WIRE-04: IKS Trajectory sparkline */}
                    {iksTrendLoading && !iksTrend && (
                      <p className="text-xs text-gray-600">Loading IKS trend…</p>
                    )}
                    {iksTrendPoints.length > 0 && (
                      <div className="mt-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-gray-500">IKS Trajectory</span>
                          <span className={`text-xs font-semibold ${iksTrendDir > 0.5 ? 'text-green-400' : iksTrendDir < -0.5 ? 'text-red-400' : 'text-gray-400'}`}>
                            {iksTrendDir > 0.5 ? '↑ improving' : iksTrendDir < -0.5 ? '↓ degrading' : '→ stable'}
                          </span>
                        </div>
                        <ResponsiveContainer width="100%" height={72}>
                          <AreaChart data={iksTrendPoints} margin={{ top: 2, right: 2, left: 0, bottom: 0 }}>
                            <defs>
                              <linearGradient id="iksGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <XAxis dataKey="decisions" hide />
                            <YAxis domain={[0, 100]} hide />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #374151', borderRadius: '6px', fontSize: '11px' }}
                              formatter={(v: number) => [v.toFixed(1), 'IKS']}
                              labelFormatter={(l: number) => `${l} decisions`}
                            />
                            <Area
                              type="monotone"
                              dataKey="iks_v2"
                              stroke="#10b981"
                              fill="url(#iksGrad)"
                              strokeWidth={1.5}
                              dot={iksTrendPoints.length === 1 ? { r: 3, fill: '#10b981' } : false}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                        <p className="text-xs text-gray-600 mt-0.5">
                          Based on {iksTrendPoints.length} data point{iksTrendPoints.length !== 1 ? 's' : ''}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* F1a. Conservation Law Status (WIRE-03) */}
              {healthDataLoading && !healthData && (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                  <div className="text-sm text-gray-500">Loading conservation status…</div>
                </div>
              )}
              {healthData && (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-gray-200">Conservation Law</h4>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      healthData.status === 'GREEN'
                        ? 'bg-green-900/40 text-green-400 border border-green-500/30'
                        : healthData.status === 'AMBER'
                        ? 'bg-amber-900/40 text-amber-400 border border-amber-500/30'
                        : healthData.status === 'RED'
                        ? 'bg-red-900/40 text-red-400 border border-red-500/30'
                        : 'bg-gray-700/40 text-gray-400 border border-gray-600/30'
                    }`}>{healthData.status}</span>
                  </div>

                  {healthData.auto_pause_active ? (
                    <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-red-900/30 border border-red-500/40 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                      <span className="text-xs font-semibold text-red-300">Learning paused — conservation threshold breached</span>
                    </div>
                  ) : (
                    <div className="mb-3 flex items-center gap-1.5">
                      <div className="w-2 h-2 bg-green-400 rounded-full" />
                      <span className="text-xs text-green-400 font-semibold">Learning active</span>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="bg-soc-bg rounded p-2 border border-gray-700">
                      <div className="text-gray-500 mb-0.5">α · learning rate</div>
                      <div className="font-mono font-semibold text-gray-200">
                        {((healthData.components?.alpha) ?? 0).toFixed(4)}
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded p-2 border border-gray-700">
                      <div className="text-gray-500 mb-0.5">q · accuracy</div>
                      <div className="font-mono font-semibold text-gray-200">
                        {(((healthData.components?.q) ?? 0) * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded p-2 border border-gray-700">
                      <div className="text-gray-500 mb-0.5">V · verified</div>
                      <div className="font-mono font-semibold text-gray-200">
                        {(healthData.components?.V) ?? 0}
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded p-2 border border-gray-700">
                      <div className="text-gray-500 mb-0.5">θ_min · floor</div>
                      <div className="font-mono font-semibold text-gray-200">
                        {((healthData.theta_min) ?? 0).toFixed(3)}
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded p-2 border border-gray-700">
                      <div className="text-gray-500 mb-0.5">α·q·V · signal</div>
                      <div className={`font-mono font-semibold ${healthData.conservation?.passed ? 'text-green-400' : 'text-red-400'}`}>
                        {((healthData.signal) ?? 0).toFixed(2)}
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded p-2 border border-gray-700">
                      <div className="text-gray-500 mb-0.5">headroom</div>
                      <div className={`font-mono font-semibold ${((healthData.conservation?.headroom) ?? 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {((healthData.conservation?.headroom) ?? 0) > 0 ? '+' : ''}
                        {((healthData.conservation?.headroom) ?? 0).toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {healthData.interpretation && (
                    <p className="mt-3 text-xs text-gray-400 italic leading-relaxed">{healthData.interpretation}</p>
                  )}
                </div>
              )}

              {/* ── Operator Controls (WIRE-05 + WIRE-06) ─────────────── */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <div className="h-px flex-1 bg-gray-800" />
                  <span className="text-xs text-gray-500 uppercase tracking-widest">Operator Controls</span>
                  <div className="h-px flex-1 bg-gray-800" />
                </div>

                {/* WIRE-05: Shadow Mode */}
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5 mb-4">
                  {shadowEnabled && (
                    <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-amber-900/30 border border-amber-500/40 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                      <span className="text-xs font-semibold text-amber-300">Shadow mode active — system is observing, not acting</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-gray-400" />
                      <h4 className="text-sm font-semibold text-gray-200">Shadow Mode</h4>
                    </div>
                    <button
                      onClick={handleShadowToggle}
                      disabled={shadowToggleBusy}
                      aria-label={shadowEnabled ? 'Disable shadow mode' : 'Enable shadow mode'}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-50 ${shadowEnabled ? 'bg-amber-500' : 'bg-gray-600'}`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${shadowEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">
                    {shadowEnabled
                      ? 'System observes but does not act. Analyst actions are recorded for agreement tracking.'
                      : 'Enable to observe system decisions without acting on them.'}
                  </p>
                  {shadowReport && (shadowReport.total_shadow_decisions ?? 0) > 0 && (
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-soc-bg rounded p-2 border border-gray-700">
                        <div className="text-gray-500 mb-0.5">Shadow decisions</div>
                        <div className="font-mono font-semibold text-gray-200">{shadowReport.total_shadow_decisions}</div>
                      </div>
                      <div className="bg-soc-bg rounded p-2 border border-gray-700">
                        <div className="text-gray-500 mb-0.5">Agreement rate</div>
                        <div className="font-mono font-semibold text-green-400">{((shadowReport.overall_agreement ?? 0) * 100).toFixed(1)}%</div>
                      </div>
                      <div className="bg-soc-bg rounded p-2 border border-gray-700">
                        <div className="text-gray-500 mb-0.5">Recommendation</div>
                        <div className={`font-semibold ${shadowReport.recommendation === 'Ready for live mode' ? 'text-green-400' : 'text-amber-400'}`}>
                          {shadowReport.recommendation}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* WIRE-06: Checkpoints */}
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-gray-400" />
                      <h4 className="text-sm font-semibold text-gray-200">Checkpoints</h4>
                    </div>
                    <button
                      onClick={handleCreateCheckpoint}
                      disabled={checkpointBusy}
                      className="inline-flex items-center gap-1.5 rounded border border-sky-500/40 bg-sky-500/10 px-3 py-1.5 text-xs font-semibold text-sky-300 hover:bg-sky-500/20 disabled:opacity-50"
                    >
                      {checkpointBusy ? 'Creating…' : '+ Create Checkpoint'}
                    </button>
                  </div>
                  {checkpointMsg && (
                    <p className={`mb-3 text-xs px-2 py-1.5 rounded border ${checkpointMsg.startsWith('Failed') || checkpointMsg.startsWith('Rollback failed') ? 'text-red-300 bg-red-900/20 border-red-500/30' : 'text-green-300 bg-green-900/20 border-green-500/30'}`}>
                      {checkpointMsg}
                    </p>
                  )}
                  {checkpoints.length === 0 ? (
                    <p className="text-xs text-gray-500 italic text-center py-3">No checkpoints yet. Create one before making significant changes.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {checkpoints.slice(0, 5).map((cp: any) => {
                        const tsMs = Number(cp.timestamp)
                        const relTime = (() => {
                          if (isNaN(tsMs)) return cp.timestamp
                          const diffMs = Date.now() - tsMs
                          const diffH = Math.floor(diffMs / 3600000)
                          const diffM = Math.floor(diffMs / 60000)
                          return diffH > 0 ? `${diffH}h ago` : diffM > 0 ? `${diffM}m ago` : 'just now'
                        })()
                        return (
                          <div key={cp.id} className="flex items-center gap-2 text-xs bg-soc-bg rounded border border-gray-700 px-3 py-2">
                            <span className="font-mono text-gray-400 flex-1">{String(cp.id ?? '').slice(0, 8)}…</span>
                            <span className="text-gray-500">{relTime}</span>
                            <span className="text-gray-600">·</span>
                            <span className="text-gray-400">{cp.decision_count} decisions</span>
                            <button
                              onClick={() => handleRollback(cp.id)}
                              disabled={rollbackBusy === cp.id}
                              className="ml-auto inline-flex items-center gap-1 rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-amber-300 hover:bg-amber-500/20 disabled:opacity-50"
                            >
                              {rollbackBusy === cp.id ? 'Rolling back…' : 'Rollback'}
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setWhatIfExpanded(prev => !prev)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left hover:bg-gray-900/40"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-cyan-400" />
                      <h4 className="text-sm font-semibold text-gray-200">What-If Simulator</h4>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Parameter projection only. No scorer calls, no production-state changes.
                    </p>
                  </div>
                  {whatIfExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                </button>

                {whatIfExpanded && (
                  <div className="border-t border-gray-800 px-5 py-5 space-y-5">
                    <div className="flex flex-wrap gap-2">
                      {whatIfPresetButtons.map(([label, key]) => (
                        <button
                          key={key}
                          type="button"
                          onClick={async () => {
                            const preset = whatIfPresets[key]
                            if (!preset) return
                            applyWhatIfPreset(preset)
                            await handleRunWhatIf({
                              name: preset.name,
                              alpha: preset.alpha,
                              V: preset.V,
                              q_initial: preset.q_initial,
                              q_target: preset.q_target,
                              q_ramp_days: preset.q_ramp_days ?? 0,
                              horizon_days: preset.horizon_days,
                              disruption_day: preset.disruption_day ?? null,
                              disruption_delta: preset.disruption_delta ?? 0,
                            })
                          }}
                          disabled={!whatIfPresets[key] || whatIfPresetsLoading}
                          className="rounded border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 disabled:opacity-50"
                        >
                          {label}
                        </button>
                      ))}
                      {whatIfPresetsLoading && (
                        <span className="self-center text-xs text-gray-500">Loading presets...</span>
                      )}
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="rounded-lg border border-gray-800 bg-soc-bg p-4 space-y-4">
                        <div>
                          <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
                            <span className="flex items-center gap-1">
                              Starting q
                              <span
                                title="Wrong-direction updates are attenuated at 1/5 strength. At 15% analyst error rate, accuracy drops by less than 0.5pp (validated across 15 experimental conditions, 5 seeds)."
                                className="cursor-help text-gray-500 select-none"
                              >ⓘ</span>
                            </span>
                            <span className="font-mono text-gray-200">{qStart.toFixed(2)}</span>
                          </div>
                          <input type="range" min="0" max="1" step="0.01" value={qStart} onChange={(e) => setQStart(Number(e.target.value))} className="w-full accent-cyan-400" />
                        </div>
                        <div>
                          <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
                            <span>Ending q</span>
                            <span className="font-mono text-gray-200">{qEnd.toFixed(2)}</span>
                          </div>
                          <input type="range" min="0" max="1" step="0.01" value={qEnd} onChange={(e) => setQEnd(Number(e.target.value))} className="w-full accent-cyan-400" />
                        </div>
                        <div>
                          <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
                            <span>Ramp days</span>
                            <span className="font-mono text-gray-200">{rampDays}</span>
                          </div>
                          <input type="range" min="1" max={whatIfHorizon} step="1" value={Math.min(rampDays, whatIfHorizon)} onChange={(e) => setRampDays(Number(e.target.value))} className="w-full accent-cyan-400" />
                        </div>
                        <div>
                          <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
                            <span>Alpha</span>
                            <span className="font-mono text-gray-200">{alphaProjection.toFixed(2)}</span>
                          </div>
                          <input type="range" min="0.01" max="0.5" step="0.01" value={alphaProjection} onChange={(e) => setAlphaProjection(Number(e.target.value))} className="w-full accent-emerald-400" />
                        </div>
                      </div>

                      <div className="rounded-lg border border-gray-800 bg-soc-bg p-4 space-y-4">
                        <label className="block text-xs text-gray-400">
                          Volume per day
                          <input
                            type="number"
                            min={10}
                            max={1000}
                            value={volumeProjection}
                            onChange={(e) => setVolumeProjection(Number(e.target.value))}
                            className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200"
                          />
                        </label>
                        <label className="block text-xs text-gray-400">
                          Horizon
                          <select
                            value={whatIfHorizon}
                            onChange={(e) => {
                              const next = Number(e.target.value)
                              setWhatIfHorizon(next)
                              setRampDays(prev => Math.min(prev, next))
                            }}
                            className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200"
                          >
                            {[30, 60, 90, 180].map(days => <option key={days} value={days}>{days} days</option>)}
                          </select>
                        </label>
                        <label className="flex items-center gap-2 text-sm text-gray-300">
                          <input type="checkbox" checked={disruptionEnabled} onChange={(e) => setDisruptionEnabled(e.target.checked)} className="accent-amber-400" />
                          Enable disruption
                        </label>
                        {disruptionEnabled && (
                          <div className="grid gap-3 sm:grid-cols-2">
                            <label className="block text-xs text-gray-400">
                              Disruption day
                              <input
                                type="number"
                                min={0}
                                max={Math.max(0, whatIfHorizon - 1)}
                                value={disruptionDay}
                                onChange={(e) => setDisruptionDay(Number(e.target.value))}
                                className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200"
                              />
                            </label>
                            <label className="block text-xs text-gray-400">
                              Drop magnitude
                              <input
                                type="number"
                                min={0}
                                max={1}
                                step={0.01}
                                value={disruptionDrop}
                                onChange={(e) => setDisruptionDrop(Number(e.target.value))}
                                className="mt-1 w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200"
                              />
                            </label>
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={() => handleRunWhatIf()}
                          disabled={whatIfRunning}
                          className="inline-flex items-center gap-2 rounded border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
                        >
                          <Zap className="w-4 h-4" />
                          {whatIfRunning ? 'Running Projection...' : 'Run Projection'}
                        </button>
                      </div>
                    </div>

                    {whatIfError && (
                      <div className="rounded border border-red-800/60 bg-red-900/20 px-3 py-2 text-sm text-red-300">
                        {whatIfError}
                      </div>
                    )}

                    {whatIfResult && (
                      <div className="space-y-4">
                        <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                          <div className="mb-3 flex items-center justify-between">
                            <h5 className="text-sm font-semibold text-gray-200">Projected Signal vs. Theta Floor</h5>
                            <span className="text-xs text-gray-500">Run on button click only</span>
                          </div>
                          <ResponsiveContainer width="100%" height={260}>
                            <AreaChart data={whatIfChartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                              <XAxis dataKey="day" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                              <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                                formatter={(value: any, name: string) => [
                                  typeof value === 'number' ? value.toFixed(3) : value,
                                  name === 'structural_ceiling' ? 'Structural ceiling (approx.)' : name,
                                ]}
                                labelFormatter={(value: any) => `Day ${value}`}
                              />
                              <Area type="monotone" dataKey="signal" stroke="#22c55e" fill="#22c55e" fillOpacity={0.14} strokeWidth={2} />
                              <ReferenceLine y={whatIfResult.conservation_law.theta_min} stroke="#f59e0b" strokeDasharray="6 4" label={{ value: 'theta_min', fill: '#f59e0b', fontSize: 11 }} />
                              {whatIfCeiling != null && (
                                <ReferenceLine
                                  y={whatIfCeiling}
                                  stroke="#67e8f9"
                                  strokeDasharray="6 4"
                                  label={{ value: 'Structural ceiling (approx.)', fill: '#67e8f9', fontSize: 11 }}
                                />
                              )}
                            </AreaChart>
                          </ResponsiveContainer>
                          {whatIfResult.ceiling_estimate != null && (
                            <p className="mt-3 text-xs text-cyan-300">
                              {whatIfResult.ceiling_note ?? 'Approximate structural estimate for relative comparison only; not predicted accuracy.'}
                            </p>
                          )}
                          {whatIfStartsAboveCeiling && (
                            <p className="mt-2 text-xs text-amber-300">
                              Note: starting q exceeds the estimated structural ceiling (approx.).
                            </p>
                          )}
                        </div>

                        <div className="grid gap-3 md:grid-cols-4">
                          <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                            <div className="text-xs uppercase tracking-wide text-gray-500">Days by Status</div>
                            <div className="mt-2 text-sm text-gray-300">
                              G {whatIfResult.summary.days_green} / A {whatIfResult.summary.days_amber} / R {whatIfResult.summary.days_red}
                            </div>
                          </div>
                          <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                            <div className="text-xs uppercase tracking-wide text-gray-500">Auto-Pause</div>
                            <div className={`mt-2 text-sm font-semibold ${whatIfResult.summary.auto_pause_triggered ? 'text-red-400' : 'text-green-400'}`}>
                              {whatIfResult.summary.auto_pause_triggered ? 'Triggered' : 'Not triggered'}
                            </div>
                          </div>
                          <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                            <div className="text-xs uppercase tracking-wide text-gray-500">Final Status</div>
                            <div className={`mt-2 text-sm font-semibold ${
                              whatIfResult.summary.final_status === 'GREEN'
                                ? 'text-green-400'
                                : whatIfResult.summary.final_status === 'AMBER'
                                  ? 'text-amber-400'
                                  : 'text-red-400'
                            }`}>
                              {whatIfResult.summary.final_status}
                            </div>
                          </div>
                          <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                            <div className="text-xs uppercase tracking-wide text-gray-500">Final IKS</div>
                            <div className="mt-2 text-sm font-semibold text-cyan-300">{whatIfResult.summary.final_iks.toFixed(1)}</div>
                          </div>
                        </div>

                        <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                          <h5 className="text-sm font-semibold text-gray-200">Conservation Formula</h5>
                          <p className="mt-2 text-xs text-gray-400">{whatIfResult.conservation_law.formula}</p>
                          <p className="mt-2 text-sm text-gray-300">
                            Required q threshold:{' '}
                            <span className="font-mono text-amber-300">
                              {whatIfResult.conservation_law.q_threshold != null
                                ? whatIfResult.conservation_law.q_threshold.toFixed(4)
                                : 'inf'}
                            </span>
                          </p>
                          <p className="mt-2 text-xs text-gray-500 leading-relaxed">{whatIfResult.conservation_law.explanation}</p>
                          {whatIfResult.warnings.length > 0 && (
                            <div className="mt-3 rounded border border-amber-800/50 bg-amber-900/10 px-3 py-2 text-xs text-amber-300">
                              {whatIfResult.warnings.join(' ')}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setTimeMachineExpanded(prev => !prev)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left hover:bg-gray-800/30"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-cyan-300" />
                      <h4 className="text-sm font-semibold text-gray-200">Centroid Time Machine</h4>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Inspect centroid drift over time, browse snapshots, and compare movement by category.
                    </p>
                  </div>
                  {timeMachineExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-500" />
                  )}
                </button>

                {timeMachineExpanded && (
                  <div className="border-t border-gray-800 px-5 py-5 space-y-5">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-500">Snapshot Drift Explorer</div>
                        <div className="mt-1 text-sm text-gray-300">
                          Select one snapshot for detail or two snapshots for direct comparison.
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleCompareCurrentVsBootstrap()}
                        disabled={timeMachineSnapshots.length === 0 || timeMachineSnapshotDetailLoading}
                        className="inline-flex items-center gap-2 rounded border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 disabled:opacity-50"
                      >
                        <Activity className="h-3.5 w-3.5" />
                        Current vs Bootstrap
                      </button>
                    </div>

                    {timeMachineLoading && (
                      <div className="rounded border border-gray-800 bg-soc-bg px-4 py-3 text-sm text-gray-500">
                        Loading centroid history…
                      </div>
                    )}

                    {timeMachineError && (
                      <div className="rounded border border-red-800/60 bg-red-900/20 px-4 py-3 text-sm text-red-300">
                        {timeMachineError}
                      </div>
                    )}

                    {!timeMachineLoading && timeMachineTimelineChartData.length === 0 && !timeMachineError && (
                      <div className="rounded border border-gray-800 bg-soc-bg px-4 py-3 text-sm text-gray-500">
                        No centroid snapshots yet. Timeline activates after the first backup is written.
                      </div>
                    )}

                    {timeMachineTimelineChartData.length > 0 && (
                      <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                        <div className="mb-3 flex items-center justify-between">
                          <div>
                            <h5 className="text-sm font-semibold text-gray-200">Evolution Timeline</h5>
                            <p className="text-xs text-gray-500">Drift from bootstrap across verified decision count.</p>
                          </div>
                          <div className="text-xs text-gray-500">
                            {selectedSnapshotIds.length === 0
                              ? 'Select timeline points or rows below'
                              : selectedSnapshotIds.length === 1
                                ? '1 snapshot selected'
                                : '2 snapshots selected'}
                          </div>
                        </div>

                        <ResponsiveContainer width="100%" height={260}>
                          <ComposedChart data={timeMachineTimelineChartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis
                              dataKey="decision_count"
                              tick={{ fill: '#9CA3AF', fontSize: 11 }}
                              label={{ value: 'verified decisions', position: 'insideBottom', offset: -2, fill: '#6B7280', fontSize: 11 }}
                            />
                            <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                              formatter={(value: any, name: string) => [
                                typeof value === 'number' ? value.toFixed(3) : 'n/a',
                                name === 'drift_from_bootstrap' ? 'drift from bootstrap' : 'Ceiling (approx. structural estimate)',
                              ]}
                              labelFormatter={(_, payload) => {
                                const row = payload?.[0]?.payload as { decision_count?: number; snapshot_id?: string } | undefined
                                return row ? `${row.decision_count ?? 0} decisions · ${String(row.snapshot_id ?? '').slice(0, 12)}…` : ''
                              }}
                            />
                            <Legend wrapperStyle={{ fontSize: '12px' }} />
                            <Line
                              type="monotone"
                              dataKey="drift_from_bootstrap"
                              stroke="#38bdf8"
                              strokeWidth={2}
                              name="drift_from_bootstrap"
                              dot={(props: any) => {
                                const point = props?.payload as { snapshot_id?: string } | undefined
                                const snapshotId = point?.snapshot_id ?? ''
                                const selected = selectedSnapshotSet.has(snapshotId)
                                return (
                                  <circle
                                    key={snapshotId || String(props?.cx)}
                                    cx={props.cx}
                                    cy={props.cy}
                                    r={selected ? 6 : 4}
                                    fill={selected ? '#f59e0b' : '#38bdf8'}
                                    stroke="#0f172a"
                                    strokeWidth={1.5}
                                    className="cursor-pointer"
                                    onClick={() => { if (snapshotId) void handleSelectTimeMachineSnapshot(snapshotId) }}
                                  />
                                )
                              }}
                            />
                            {hasTimeMachineCeiling && (
                              <Line
                                type="monotone"
                                dataKey="ceiling_estimate"
                                stroke="#f59e0b"
                                strokeWidth={1.5}
                                strokeDasharray="6 4"
                                dot={false}
                                connectNulls={false}
                                name="Ceiling (approx. structural estimate)"
                              />
                            )}
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
                      <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                        <div className="mb-3 flex items-center justify-between">
                          <h5 className="text-sm font-semibold text-gray-200">Snapshot Browser</h5>
                          <span className="text-xs text-gray-500">{timeMachineSnapshots.length} snapshots</span>
                        </div>

                        {timeMachineSnapshots.length === 0 ? (
                          <p className="text-sm text-gray-500">No snapshots available.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="border-b border-gray-800 text-left uppercase tracking-wide text-gray-500">
                                  <th className="py-2 pr-3">Select</th>
                                  <th className="py-2 pr-3">Timestamp</th>
                                  <th className="py-2 pr-3">Decisions</th>
                                  <th className="py-2 pr-3">SHA-256</th>
                                </tr>
                              </thead>
                              <tbody>
                                {timeMachineSnapshots.map(snapshot => {
                                  const timestamp = snapshot.timestamp_epoch ?? snapshot.timestamp
                                  const selected = selectedSnapshotSet.has(snapshot.snapshot_id)
                                  return (
                                    <tr
                                      key={snapshot.snapshot_id}
                                      className={`border-b border-gray-800/60 last:border-0 ${selected ? 'bg-amber-500/10' : ''}`}
                                    >
                                      <td className="py-2 pr-3">
                                        <button
                                          type="button"
                                          onClick={() => void handleSelectTimeMachineSnapshot(snapshot.snapshot_id)}
                                          className={`rounded border px-2 py-1 font-medium ${selected ? 'border-amber-400 bg-amber-500/10 text-amber-300' : 'border-gray-700 text-gray-300 hover:border-gray-500'}`}
                                        >
                                          {selected ? 'Selected' : 'Select'}
                                        </button>
                                      </td>
                                      <td className="py-2 pr-3 text-gray-300">
                                        <div>{formatRelativeTime(timestamp)}</div>
                                        <div className="text-[11px] text-gray-500">{timestamp ? new Date(timestamp).toLocaleString() : 'n/a'}</div>
                                      </td>
                                      <td className="py-2 pr-3 text-gray-300">{snapshot.decision_count ?? 0}</td>
                                      <td className="py-2 pr-3 font-mono text-gray-400">{String(snapshot.sha256 ?? '').slice(0, 12)}…</td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>

                      <div className="space-y-4">
                        <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                          <h5 className="text-sm font-semibold text-gray-200">Snapshot Detail</h5>
                          {timeMachineSnapshotDetailLoading && (
                            <p className="mt-3 text-sm text-gray-500">Loading snapshot detail…</p>
                          )}
                          {timeMachineSnapshotDetailError && (
                            <p className="mt-3 text-sm text-red-300">{timeMachineSnapshotDetailError}</p>
                          )}
                          {!timeMachineSnapshotDetailLoading && !timeMachineSnapshotDetailError && timeMachineSnapshotDetail && (
                            <div className="mt-3 space-y-3 text-xs">
                              <div className="grid grid-cols-2 gap-2">
                                <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
                                  <div className="text-gray-500">Selected Snapshot</div>
                                  <div className="mt-1 font-mono text-gray-200">{timeMachineSnapshotDetail.snapshot_id.slice(0, 16)}…</div>
                                </div>
                                <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
                                  <div className="text-gray-500">Tensor Shape</div>
                                  <div className="mt-1 font-mono text-gray-200">{Array.isArray(timeMachineSnapshotDetail.shape) ? timeMachineSnapshotDetail.shape.join('x') : 'n/a'}</div>
                                </div>
                                <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
                                  <div className="text-gray-500">Drift from Bootstrap</div>
                                  <div className="mt-1 font-mono text-cyan-300">
                                    {timeMachineSnapshotDetail.drift_from_bootstrap == null ? 'n/a' : timeMachineSnapshotDetail.drift_from_bootstrap.toFixed(3)}
                                  </div>
                                </div>
                                <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
                                  <div className="text-gray-500">Drift from Current</div>
                                  <div className="mt-1 font-mono text-amber-300">
                                    {timeMachineSnapshotDetail.drift_from_current == null ? 'n/a' : timeMachineSnapshotDetail.drift_from_current.toFixed(3)}
                                  </div>
                                </div>
                              </div>
                              {selectedSnapshotIds.length < 2 && latestSnapshot?.snapshot_id === timeMachineSnapshotDetail.snapshot_id && (
                                <p className="text-xs text-gray-500">
                                  Current vs Bootstrap shows the latest snapshot’s current drift to bootstrap and current live centroids without forcing a second snapshot selection.
                                </p>
                              )}
                            </div>
                          )}
                          {!timeMachineSnapshotDetailLoading && !timeMachineSnapshotDetailError && !timeMachineSnapshotDetail && (
                            <p className="mt-3 text-sm text-gray-500">Choose a snapshot to inspect its drift and tensor metadata.</p>
                          )}
                        </div>

                        <div className="rounded-lg border border-gray-800 bg-soc-bg p-4">
                          <div className="mb-3 flex items-center justify-between">
                            <h5 className="text-sm font-semibold text-gray-200">Comparison View</h5>
                            <span className="text-xs text-gray-500">
                              {selectedSnapshotIds.length === 2 ? 'two snapshots selected' : 'select two snapshots'}
                            </span>
                          </div>

                          {timeMachineComparisonLoading && (
                            <p className="text-sm text-gray-500">Computing comparison…</p>
                          )}
                          {timeMachineComparisonError && (
                            <p className="text-sm text-red-300">{timeMachineComparisonError}</p>
                          )}
                          {!timeMachineComparisonLoading && !timeMachineComparisonError && timeMachineComparison && (
                            <div className="space-y-4">
                              <div className="grid gap-3 md:grid-cols-2">
                                <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
                                  <div className="text-xs uppercase tracking-wide text-gray-500">Overall Distance</div>
                                  <div className="mt-1 text-lg font-semibold text-cyan-300">
                                    {(timeMachineComparison.overall_frobenius_distance ?? 0).toFixed(3)}
                                  </div>
                                </div>
                                <div className="rounded border border-gray-800 bg-gray-900/60 p-3">
                                  <div className="text-xs uppercase tracking-wide text-gray-500">Direction</div>
                                  <div className={`mt-1 text-sm font-semibold ${
                                    timeMachineComparison.movement_direction === 'toward_bootstrap'
                                      ? 'text-green-400'
                                      : timeMachineComparison.movement_direction === 'away_from_bootstrap'
                                        ? 'text-amber-400'
                                        : 'text-gray-300'
                                  }`}>
                                    {String(timeMachineComparison.movement_direction ?? 'unknown').replace(/_/g, ' ')}
                                  </div>
                                </div>
                              </div>

                              {timeMachineComparisonBars.length > 0 && (
                                <ResponsiveContainer width="100%" height={220}>
                                  <ComposedChart data={timeMachineComparisonBars} margin={{ top: 8, right: 12, left: 0, bottom: 18 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="category" tick={{ fill: '#9CA3AF', fontSize: 10 }} angle={-18} textAnchor="end" interval={0} height={60} />
                                    <YAxis tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                                    <Tooltip
                                      contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                                      formatter={(value: number) => [value.toFixed(3), 'distance']}
                                    />
                                    <Bar dataKey="distance" fill="#22c55e" radius={[4, 4, 0, 0]} />
                                  </ComposedChart>
                                </ResponsiveContainer>
                              )}

                              <div>
                                <div className="mb-2 text-xs uppercase tracking-wide text-gray-500">Top 5 Movers</div>
                                {ensureArray(timeMachineComparison.top_movers).length === 0 ? (
                                  <p className="text-sm text-gray-500">No movers returned.</p>
                                ) : (
                                  <div className="space-y-2">
                                    {ensureArray(timeMachineComparison.top_movers).map((mover: any, index) => (
                                      <div key={`${mover.category}-${mover.action}`} className="flex items-center justify-between rounded border border-gray-800 bg-gray-900/60 px-3 py-2 text-xs">
                                        <div className="text-gray-300">
                                          <span className="mr-2 text-gray-500">#{index + 1}</span>
                                          {String(mover.category).replace(/_/g, ' ')} / {String(mover.action).replace(/_/g, ' ')}
                                        </div>
                                        <div className="font-mono text-cyan-300">{Number(mover.distance ?? 0).toFixed(3)}</div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                          {!timeMachineComparisonLoading && !timeMachineComparisonError && !timeMachineComparison && (
                            <p className="text-sm text-gray-500">Comparison appears here after two snapshots are selected.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <button
                  onClick={() => setFactorAnalysisExpanded(v => !v)}
                  className="w-full px-5 py-4 flex items-start justify-between text-left hover:bg-gray-900/40 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <BarChart2 className="h-4 w-4 text-cyan-400" />
                      <h4 className="text-sm font-semibold text-gray-200">Factor Analysis (SNR)</h4>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      Review signal-to-noise by category and inspect which factors are carrying the current separation.
                    </p>
                  </div>
                  {factorAnalysisExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-500" />
                  )}
                </button>

              {factorAnalysisExpanded && (
                  <div className="border-t border-gray-800 px-5 py-5 space-y-5">
                    {factorAnalysisSummaryLoading ? (
                      <div className="text-sm text-gray-400">Loading SNR summary...</div>
                    ) : factorAnalysisSummaryError ? (
                      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                        {factorAnalysisSummaryError}
                      </div>
                    ) : factorAnalysisSummary ? (
                      <>
                        <div className="grid gap-3 md:grid-cols-3">
                          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Overall SNR</div>
                            <div className={`mt-2 text-2xl font-semibold ${snrToneClass(factorAnalysisSummary.overall_snr)}`}>
                              {Number(factorAnalysisSummary.overall_snr ?? 0).toFixed(2)}
                            </div>
                          </div>
                          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Overall Ceiling</div>
                            <div className="mt-2 text-2xl font-semibold text-gray-100">
                              {Number(factorAnalysisSummary.overall_ceiling ?? 0).toFixed(1)}%
                            </div>
                          </div>
                          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Weakest Category</div>
                            <div className="mt-2 text-base font-semibold text-gray-100">
                              {factorAnalysisSummary.weakest_category || 'Unavailable'}
                            </div>
                            <div className="mt-1 text-sm text-gray-400">
                              Ceiling {Number(factorAnalysisSummary.weakest_category_ceiling ?? factorAnalysisSummary.overall_ceiling ?? 0).toFixed(1)}%
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                          <p className="text-sm text-gray-400">
                            {factorAnalysisSummary.recommendation || 'Load the full report to inspect per-category action separation and factor weighting.'}
                          </p>
                          <button
                            onClick={loadFactorAnalysisReport}
                            disabled={factorAnalysisReportLoading}
                            className="inline-flex items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {factorAnalysisReportLoading ? 'Loading...' : 'Load Full Report'}
                          </button>
                        </div>
                      </>
                    ) : null}

                    {factorAnalysisReportError && (
                      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                        {factorAnalysisReportError}
                      </div>
                    )}

                    {factorAnalysisReport?.current && (
                      <>
                        {factorAnalysisReport.current.proposed_improvement?.recommendation && (
                          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-amber-300/80">Proposed Improvement</div>
                            <p className="mt-2 text-sm text-amber-100">
                              {factorAnalysisReport.current.proposed_improvement.recommendation}
                            </p>
                          </div>
                        )}

                        <div className="overflow-x-auto rounded-lg border border-gray-800">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-900/70 text-gray-400">
                              <tr>
                                <th className="px-4 py-3 text-left font-medium">Category</th>
                                <th className="px-4 py-3 text-left font-medium">SNR</th>
                                <th className="px-4 py-3 text-left font-medium">Ceiling</th>
                                <th className="px-4 py-3 text-left font-medium">Status</th>
                                <th className="px-4 py-3 text-left font-medium">Weakest Pair</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(factorAnalysisReport.current.categories || []).map((row: any) => (
                                <tr key={row.category} className="border-t border-gray-800 text-gray-300">
                                  <td className="px-4 py-3 font-medium text-gray-200">{row.category}</td>
                                  <td className={`px-4 py-3 ${snrToneClass(row.snr_effective)}`}>
                                    {Number(row.snr_effective ?? 0).toFixed(2)}
                                  </td>
                                  <td className="px-4 py-3">{Number(row.ceiling_estimate ?? 0).toFixed(1)}%</td>
                                  <td className={`px-4 py-3 capitalize ${statusToneClass(row.status)}`}>
                                    {String(row.status || 'healthy').replace('_', ' ')}
                                  </td>
                                  <td className="px-4 py-3 text-gray-400">
                                    {Array.isArray(row.weakest_pair_names) ? row.weakest_pair_names.join(' vs ') : 'Unavailable'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="mb-4 flex items-center justify-between">
                            <div>
                              <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Factor Importance</div>
                              <div className="mt-1 text-sm text-gray-300">Dominant-axis contribution by factor</div>
                            </div>
                          </div>
                          <div className="space-y-3">
                            {Object.entries(factorAnalysisReport.current.factor_importance || {}).map(([name, value]) => {
                              const width = Math.max(4, Math.min(100, Number(value ?? 0) * 100))
                              return (
                                <div key={name} className="space-y-1">
                                  <div className="flex items-center justify-between text-sm">
                                    <span className="text-gray-300">{name}</span>
                                    <span className="text-gray-500">{(Number(value ?? 0) * 100).toFixed(1)}%</span>
                                  </div>
                                  <div className="h-2 overflow-hidden rounded-full bg-gray-800">
                                    <div
                                      className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-emerald-400"
                                      style={{ width: `${width}%` }}
                                    />
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-800 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-emerald-400" />
                      <h4 className="text-sm font-semibold text-gray-200">Model Swap Trial (LLM Independence Proof)</h4>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      On-demand proof that swapping the narrative layer does not affect deterministic scoring.
                    </p>
                  </div>
                  <button
                    onClick={runModelSwapTrial}
                    disabled={modelSwapTrialLoading}
                    className="inline-flex items-center justify-center rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-200 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {modelSwapTrialLoading ? 'Running…' : 'Run Model Swap Trial'}
                  </button>
                </div>

                <div className="px-5 py-5 space-y-5">
                  <div className="flex items-center gap-3">
                    <label className="text-xs uppercase tracking-[0.18em] text-gray-500" htmlFor="model-swap-n-alerts">
                      N Alerts
                    </label>
                    <input
                      id="model-swap-n-alerts"
                      type="number"
                      min={1}
                      max={100}
                      value={modelSwapTrialN}
                      onChange={(e) => setModelSwapTrialN(Math.max(1, Number(e.target.value) || 1))}
                      className="w-24 rounded border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-200 outline-none focus:border-emerald-500"
                    />
                    <span className="text-xs text-gray-500">Demo alerts processed on demand only</span>
                  </div>

                  {modelSwapTrialError && (
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                      {modelSwapTrialError}
                    </div>
                  )}

                  {!modelSwapTrialResult ? (
                    <div className="rounded-lg border border-dashed border-gray-700 bg-gray-950/50 px-4 py-5 text-sm text-gray-500">
                      Run the trial to prove the scoring path stays deterministic and LLM-independent.
                    </div>
                  ) : (
                    <>
                      <div className="grid gap-3 md:grid-cols-4">
                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">LLM Calls</div>
                          <div className="mt-2 text-2xl font-semibold text-green-400">{modelSwapTrialResult.llm_calls_made}</div>
                          <div className="mt-1 text-xs text-green-300/80">Zero by construction</div>
                        </div>
                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Scoring Method</div>
                          <div className="mt-2 text-sm font-semibold text-gray-100">centroid_tensor_softmax</div>
                          <div className="mt-1 text-xs text-gray-400">{modelSwapTrialResult.scoring_method}</div>
                        </div>
                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">Deterministic</div>
                          <div className={`mt-2 text-2xl font-semibold ${modelSwapTrialResult.reproducibility_check?.passed ? 'text-green-400' : 'text-red-400'}`}>
                            {modelSwapTrialResult.reproducibility_check?.passed ? 'PASS' : 'FAIL'}
                          </div>
                          <div className="mt-1 text-xs text-gray-400">Same alert scored twice</div>
                        </div>
                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500">LLM Dependency</div>
                          <div className="mt-2 text-2xl font-semibold text-gray-100">None</div>
                          <div className="mt-1 text-xs text-gray-400">Narrative is isolated from scoring</div>
                        </div>
                      </div>

                      <div className="rounded-lg border border-gray-800 bg-gray-950/50 p-4 text-sm text-gray-300 space-y-2">
                        <p>
                          Narrative uses <span className="font-mono text-emerald-300">{modelSwapTrialResult.narrative_llm_used || 'UNKNOWN'}</span>.
                        </p>
                        <p>
                          Scoring uses centroid tensor math. Swapping or removing the narrative LLM changes text only.
                        </p>
                        <p>
                          {modelSwapTrialResult.summary}
                        </p>
                      </div>

                      <div className="overflow-x-auto rounded-lg border border-gray-800">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-900/70 text-gray-400">
                            <tr>
                              <th className="px-4 py-3 text-left font-medium">Alert ID</th>
                              <th className="px-4 py-3 text-left font-medium">Category</th>
                              <th className="px-4 py-3 text-left font-medium">Action</th>
                              <th className="px-4 py-3 text-left font-medium">Confidence</th>
                              <th className="px-4 py-3 text-left font-medium">LLM Used?</th>
                            </tr>
                          </thead>
                          <tbody>
                            {modelSwapTrialResult.alerts.map((row) => (
                              <tr key={row.alert_id} className="border-t border-gray-800 text-gray-300">
                                <td className="px-4 py-3 font-mono text-gray-200">{row.alert_id}</td>
                                <td className="px-4 py-3">{row.category}</td>
                                <td className="px-4 py-3">{row.action_name}</td>
                                <td className="px-4 py-3 font-mono">{Number(row.confidence).toFixed(4)}</td>
                                <td className="px-4 py-3 text-green-400 font-semibold">No</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="text-xs uppercase tracking-[0.18em] text-gray-500">Repro Proof</div>
                          {modelSwapTrialResult.reproducibility_check?.passed ? (
                            <div className="mt-2 space-y-1 text-sm text-green-300">
                              <p>same_action: yes</p>
                              <p>same_confidence: yes</p>
                              <p>same_probabilities: yes</p>
                            </div>
                          ) : (
                            <div className="mt-2 text-sm text-red-300">
                              {modelSwapTrialResult.reproducibility_check?.reason || 'Reproducibility check failed.'}
                            </div>
                          )}
                        </div>
                        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
                          <div className="text-xs uppercase tracking-[0.18em] text-gray-500">Evidence</div>
                          <div className="mt-2 text-sm text-gray-300">
                            LLM calls remain at zero, narrative generation is isolated, and the scoring path stays on the centroid tensor + softmax pipeline.
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* F1b. Noise Fingerprint — Block 2.4 */}
              {heatmapData && (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                  <h4 className="text-sm font-semibold text-gray-200 mb-1">Noise Fingerprint — Factor Trust Levels</h4>
                  <p className="text-xs text-gray-500 mb-3">
                    {heatmapData.kernel_label ?? 'DiagonalKernel'} automatically weights each factor by its historical reliability (1/σ²). Lower σ = more trust.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-500 uppercase tracking-wide border-b border-gray-700">
                          <th className="text-left py-1 pr-3 font-medium">Factor</th>
                          <th className="text-right py-1 pr-3 font-medium">σ</th>
                          <th className="text-right py-1 pr-3 font-medium">Kernel Weight</th>
                          <th className="text-left py-1 font-medium">Trust Level</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(heatmapData.factors ?? []).map(f => {
                          const fp = heatmapData.noise_fingerprint?.[f]
                          if (!fp) return null
                          const kwPct = (fp.kernel_weight * 100).toFixed(1) + '%'
                          const isLow = fp.kernel_weight < 0.15
                          return (
                            <tr key={f} className="border-b border-gray-800/50 last:border-0">
                              <td className="py-1.5 pr-3 text-gray-300 font-mono">{f.replace(/_/g, ' ')}</td>
                              <td className="py-1.5 pr-3 text-right text-gray-400">{fp.sigma.toFixed(2)}</td>
                              <td className={`py-1.5 pr-3 text-right font-semibold ${isLow ? 'text-amber-400' : 'text-gray-200'}`}>{kwPct}</td>
                              <td className={`py-1.5 text-xs ${fp.label.startsWith('High') ? 'text-green-400' : fp.label.startsWith('Auto') ? 'text-amber-400' : 'text-gray-400'}`}>{fp.label}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* F1c. Enrichment Sources — Block 5.2 */}
              {enrichmentStatus && (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="text-sm font-semibold text-gray-200">Enrichment Sources</h4>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      enrichmentStatus.enrichment_health === 'GREEN' ? 'bg-green-900/40 text-green-400 border border-green-500/30' :
                      enrichmentStatus.enrichment_health === 'AMBER' ? 'bg-amber-900/40 text-amber-400 border border-amber-500/30' :
                      'bg-red-900/40 text-red-400 border border-red-500/30'
                    }`}>{enrichmentStatus.enrichment_health}</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">External threat intelligence feeding the knowledge graph</p>
                  <div className="space-y-2">
                    {ensureArray<{ source_name: string; record_count: number; trust_level: string; status: 'active' | 'stale' | 'unavailable'; affects_factor: string; staleness_hours?: number; last_refreshed_human?: string }>(enrichmentStatus.sources).map(src => {
                      const dot = src.status === 'active' ? '🟢' : src.status === 'stale' ? '🟡' : '🔴'
                      const staleLabel = src.staleness_hours != null
                        ? `last updated ${src.staleness_hours < 1 ? '<1h' : Math.round(src.staleness_hours) + 'h'} ago`
                        : src.last_refreshed_human ?? 'never refreshed'
                      return (
                        <div key={src.source_name} className="flex items-center gap-2 text-xs">
                          <span>{dot}</span>
                          <span className="text-gray-200 font-medium w-36 flex-shrink-0">{src.source_name}</span>
                          <span className="text-gray-500">{src.record_count.toLocaleString()} records</span>
                          <span className="text-gray-600">—</span>
                          <span className="text-gray-400">{staleLabel}</span>
                          <span className="text-gray-600">—</span>
                          <span className={`uppercase font-semibold ${src.trust_level === 'high' ? 'text-green-400' : 'text-gray-400'}`}>
                            {src.trust_level} trust
                          </span>
                        </div>
                      )
                    })}
                  </div>
                  <p className="text-xs text-gray-600 mt-3 italic">{enrichmentStatus.health_reason}</p>
                </div>
              )}

              {/* F1d. Centroid Support — Block 3.6 */}
              {centroidSupport && (
                <div className="bg-soc-card rounded-lg border border-gray-800 p-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">
                      {centroidSupport.overall_health === 'GREEN' ? '🟢' :
                       centroidSupport.overall_health === 'AMBER' ? '🟡' : '🔴'}
                    </span>
                    <span className="text-sm font-semibold text-gray-200">Centroid Support</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      centroidSupport.overall_health === 'GREEN' ? 'bg-green-900/40 text-green-400 border border-green-500/30' :
                      centroidSupport.overall_health === 'AMBER' ? 'bg-amber-900/40 text-amber-400 border border-amber-500/30' :
                      'bg-red-900/40 text-red-400 border border-red-500/30'
                    }`}>{centroidSupport.overall_health}</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1 ml-6">{centroidSupport.interpretation}</p>
                </div>
              )}

              <div className="bg-soc-card rounded-lg border border-gray-800 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-200">Institutional Knowledge Export</h4>
                    <p className="text-xs text-gray-500 mt-1">Download the current centroid tensor as JSON.</p>
                  </div>
                  <button
                    onClick={handleExportCentroids}
                    disabled={centroidExportBusy}
                    className="inline-flex items-center gap-2 rounded border border-sky-500/40 bg-sky-500/10 px-3 py-1.5 text-xs font-semibold text-sky-300 hover:bg-sky-500/20 disabled:opacity-50"
                  >
                    <Database className="w-3.5 h-3.5" />
                    {centroidExportBusy ? 'Exporting...' : 'Export Centroids'}
                  </button>
                </div>
                {centroidExportMessage && (
                  <p className="mt-2 text-xs text-green-400">{centroidExportMessage}</p>
                )}
              </div>

              {/* F2. Drift Alerts */}
              <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                <h4 className="text-sm font-semibold text-gray-200 mb-3">Drift Alerts</h4>
                {driftAlerts === null ? (
                  <p className="text-sm text-gray-500 italic">Drift monitoring active after 50 verified decisions.</p>
                ) : driftAlerts.length === 0 ? (
                  <p className="text-sm text-green-400">&#10003; No drift alerts &mdash; all categories within bounds (threshold: 0.30).</p>
                ) : (
                  <div className="space-y-2">
                    {driftAlerts.map(alert => (
                      <div key={alert.category} className="flex items-start gap-2 p-3 bg-amber-900/20 border border-amber-500/40 rounded">
                        <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-amber-200">
                          <strong>{alert.category.replace(/_/g, ' ')}</strong>: centroid moved {alert.drift.toFixed(3)} in last 50 decisions (threshold: 0.30)
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* F3. Learning State */}
              <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                <h4 className="text-sm font-semibold text-gray-200 mb-2">Learning State</h4>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full" />
                  <span className="text-sm text-green-400 font-semibold">Learning active</span>
                  <span className="text-xs text-gray-500">&mdash; {decisionCount} decisions recorded</span>
                </div>
              </div>

              {/* F4. Loop 3: RL Reward / Penalty */}
              <div className="bg-soc-card rounded-lg border border-gray-700 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-700">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h4 className="font-semibold flex items-center gap-2 text-sm">
                        <Activity className="w-4 h-4 text-emerald-400" />
                        Loop 3: RL Reward / Penalty
                      </h4>
                      <p className="text-xs text-gray-400 mt-1">Governs Loops 1 and 2 &mdash; continuous reinforcement signal</p>
                    </div>
                    <span className="flex-shrink-0 px-3 py-1 bg-emerald-900/40 text-emerald-400 text-xs font-bold rounded-full border border-emerald-500/30">
                      {domainConfig.loop3BadgeLabel}
                    </span>
                  </div>
                </div>
                <div className="p-5">
                  {!rewardSummary ? (
                    <div className="text-center py-6 text-gray-600 text-sm">Loading reward signal...</div>
                  ) : rewardSummary.loop3_status === 'insufficient_data' ? (
                    <div className="text-center py-8 text-gray-500">
                      <Activity className="w-8 h-8 mx-auto mb-3 opacity-25" />
                      <p className="text-sm">Awaiting first verified outcome...</p>
                      <p className="text-xs mt-1 text-gray-600">
                        Process an {domainConfig.triggerEntity.toLowerCase()} in Tab 3 and mark the outcome correct or incorrect to activate Loop 3.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-soc-bg rounded border border-gray-800 p-4">
                          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Cumulative r(t)</div>
                          <div className={`text-2xl font-bold font-mono ${rewardSummary.cumulative_r_t >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {rewardSummary.cumulative_r_t >= 0 ? '+' : ''}{rewardSummary.cumulative_r_t.toFixed(1)}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">running total</div>
                        </div>
                        <div className="bg-soc-bg rounded border border-gray-800 p-4">
                          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Asymmetric Ratio</div>
                          <div className="text-2xl font-bold font-mono text-amber-400">{rewardSummary.asymmetric_ratio.toFixed(0)}:1</div>
                          <div className="text-xs text-gray-600 mt-1">penalty : reward</div>
                        </div>
                        <div className="bg-soc-bg rounded border border-gray-800 p-4">
                          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Decisions Governed</div>
                          <div className="text-2xl font-bold font-mono text-gray-200">{rewardSummary.total_decisions}</div>
                          <div className="text-xs text-gray-600 mt-1">
                            <span className="text-emerald-500">{rewardSummary.correct}&#10003;</span>
                            {' / '}
                            <span className="text-red-500">{rewardSummary.incorrect}&#10007;</span>
                          </div>
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Reward Signal Scale</div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-gray-400 w-24 text-right font-mono shrink-0">+0.3 reward</span>
                            <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden">
                              <div className="h-full bg-emerald-500 rounded" style={{ width: '5%' }} />
                            </div>
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-gray-400 w-24 text-right font-mono shrink-0">&minus;6.0 penalty</span>
                            <div className="flex-1 h-4 bg-gray-800 rounded overflow-hidden">
                              <div className="h-full bg-red-500 rounded" style={{ width: '100%' }} />
                            </div>
                            <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                          </div>
                        </div>
                        <p className="text-xs text-gray-600 mt-2">
                          Incorrect decisions are penalized 20&times; harder to preserve {domainConfig.guaranteesLabel}.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* F5. Knowledge Graph State */}
              <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
                  <h4 className="text-sm font-semibold flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-400" />
                    Knowledge Graph State
                  </h4>
                  {graphStats && (
                    <span className={`text-xs font-mono px-2 py-0.5 rounded ${graphStats.source === 'neo4j' ? 'bg-green-900/30 text-green-400 border border-green-700/40' : 'bg-gray-800 text-gray-500'}`}>
                      {graphStats.source}
                    </span>
                  )}
                </div>
                <div className="p-4">
                  {!graphStats ? (
                    <div className="text-sm text-gray-500 py-2 text-center">Loading graph stats&hellip;</div>
                  ) : (
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-soc-bg rounded border border-gray-800 p-4 text-center">
                        <div className="text-2xl font-bold font-mono text-blue-400">{graphStats.nodes_traversed.toLocaleString()}</div>
                        <div className="text-xs text-gray-500 mt-1">nodes in graph</div>
                      </div>
                      <div className="bg-soc-bg rounded border border-gray-800 p-4 text-center">
                        <div className="text-2xl font-bold font-mono text-blue-400">{graphStats.relationships_analyzed.toLocaleString()}</div>
                        <div className="text-xs text-gray-500 mt-1">relationships</div>
                      </div>
                      <div className="bg-soc-bg rounded border border-gray-800 p-4 text-center">
                        <div className="text-2xl font-bold font-mono text-purple-400">{graphStats.historical_decisions.toLocaleString()}</div>
                        <div className="text-xs text-gray-500 mt-1">historical decisions</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* C2. Accuracy Trajectory */}
              <AccuracyTrajectoryPanel />

            </div>
          </div>

        </div>{/* end main sections */}
      </div>{/* end left-rail + sections flex */}

    </div>
  )
}
