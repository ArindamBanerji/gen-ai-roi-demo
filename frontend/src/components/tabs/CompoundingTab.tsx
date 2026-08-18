/**
 * Tab 4: Compounding Dashboard
 * Purpose: Prove the compounding effect - "Watch the Moat Grow"
 * Energy: 15%
 *
 * Section order:
 *   1. Business Impact Banner (projected, labeled)
 *   2. Week 1→4 Headline (projected, labeled)
 *   3. GAE Compounding Evidence panel — REAL live data (4 sections)
 *      A. Weight Evolution   B. Confidence Trajectory
 *      C. Before / After     D. Trust Curve
 *   4. GAE Weight Convergence (already wired)
 *   5. Evidence Ledger (real)
 *   6. Weekly Trend + Three-Loop Architecture
 *   7. Evolution Events (sample, labeled)
 *   8. The Moat Message
 */

import { useEffect, useState, type ChangeEvent } from 'react'
import {
  LineChart, Line, Bar, ComposedChart, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  getCompoundingMetrics, resetAllDemoData, resetAlerts, reseedDemoData,
  fetchAutoApproveStats, fetchLearningBalanceSheet,
  getAuditDecisions, verifyAuditChain, getGAEConvergence,
  getGAEConfidenceTrajectory, getGAETrustCurve, getGAEBeforeAfter,
  getEvolutionEvents, getCentroidEvolution, getProfileState,
  uploadEvalCSV, fetchEvalTemplates, fetchLearningHealth,
  fetchInterventionHistory, simulateFailedGate,
} from '../../lib/api'
import { domainConfig } from '../../lib/domain'
import { ensureArray } from '../../lib/guards'
import { LearningControlRoom } from '../LearningControlRoom'
import {
  TrendingUp, Database, Activity, RefreshCw, Clock, DollarSign,
  TrendingDown, CheckCircle, Calculator, Shield, Download,
  ChevronDown, ChevronRight,
} from 'lucide-react'
import ROICalculatorModal from '../ROICalculator'
import SimulationPanel from '../SimulationPanel'
import ThreeChannelPanel from '../ThreeChannelPanel'
import CohortStatusPanel from '../CohortStatusPanel'
import ProvenanceBadge from '../ProvenanceBadge'

const SOC_API = 'http://127.0.0.1:8001'

// ============================================================================
// Custom Hook: Counter Animation
// ============================================================================

function useCountUp(
  start: number,
  end: number,
  duration: number = 1500,
  decimals: number = 0,
  shouldAnimate: boolean = true
): number {
  const [count, setCount] = useState(start)

  useEffect(() => {
    if (!shouldAnimate) { setCount(end); return }
    setCount(start)
    let startTime: number | null = null
    let animationFrame: number
    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      const easeOut = 1 - Math.pow(1 - progress, 3)
      setCount(start + (end - start) * easeOut)
      if (progress < 1) animationFrame = requestAnimationFrame(animate)
    }
    animationFrame = requestAnimationFrame(animate)
    return () => { if (animationFrame) cancelAnimationFrame(animationFrame) }
  }, [start, end, duration, shouldAnimate])

  return decimals > 0 ? parseFloat(count.toFixed(decimals)) : Math.round(count)
}

// ============================================================================
// Interfaces — seeded/demo data
// ============================================================================

interface WeeklyMetric {
  week: number; auto_close_rate: number; mttr_minutes: number
  fp_rate: number; pattern_count: number
}
interface EvolutionEvent {
  id: string; event_type: string; description: string
  timestamp: string; triggered_by: string
}
interface BusinessImpact {
  analyst_hours_saved_monthly: number; cost_avoided_quarterly: number
  mttr_reduction_pct: number; alert_backlog_eliminated_monthly: number
}
interface AutoApproveStats {
  total_decisions: number
  auto_approved: number
  coverage_pct: number
  by_category: Record<string, {
    total: number
    auto_approved: number
    coverage_pct: number
  }>
}
type LearningBalanceStatus = 'at_ceiling' | 'converging' | 'early' | 'insufficient_data'
interface LearningBalanceCategory {
  category: string
  epistemic_band: string
  verified_count?: number | null
  accuracy?: number | null
  centroid_drift?: number | null
  auto_approve_rate?: number | null
  iks_contribution?: number | null
  ceiling_estimate?: number | null
  status: LearningBalanceStatus
}
interface LearningBalanceSheet {
  generated_at?: string | null
  overall_iks?: number | null
  overall_ceiling?: number | null
  total_verified?: number | null
  categories?: LearningBalanceCategory[] | null
  summary?: {
    recommendation?: string | null
    [key: string]: unknown
  } | null
}
interface CompoundingData {
  period: { start: string; end: string }
  headline: {
    nodes_start: number; nodes_end: number
    auto_close_start: number; auto_close_end: number
    mttr_start: number; mttr_end: number
    fp_investigations_start: number; fp_investigations_end: number
  }
  weekly_trend: WeeklyMetric[]
  weekly_trend_estimated?: boolean
  weekly_trend_note?: string
  evolution_events: EvolutionEvent[]
  business_impact?: BusinessImpact
}

interface DecisionEconomics {
  decisions_made: number
  correct_rate: number
  false_positive_rate: number
  time_saved_hours: number
  time_saved_estimated: boolean
  note: string
  switching_cost_trajectory?: SwitchingCostTrajectory | null
}

interface SwitchingCostPoint {
  month: number
  decisions: number
  iks: number
  analyst_days: number
  cost_usd: number
  label: string
  point_type: 'actual' | 'projected'
}

interface SwitchingCostTrajectory {
  points?: SwitchingCostPoint[] | null
  current?: SwitchingCostPoint | null
  projection_12m: number
  projection_24m: number
  rebuild_rate: number
  cost_per_day: number
  note: string
}

interface OperationalMetrics {
  mttd: { value_minutes: number | null; estimated: boolean; note?: string }
  mttr: { value_minutes: number | null; estimated: boolean; note?: string }
  fp_rate: { rate: number | null; estimated: boolean }
  source: string
}

interface EconomicsData {
  decisions: {
    total: number; correct: number; correct_rate: number;
    by_action: Record<string, number>;
  };
  population: {
    total_users: number; privileged_users: number; elevated_users: number;
  };
  economics: {
    analyst_hourly_rate: number;
    time_saved_hours: number;
    cost_saved_usd: number;
    risk_reduction_usd: number;
    total_value_usd: number;
    estimated: boolean;
    note: string;
  };
  source: string;
}

interface EvolutionEventsState {
  events: EvolutionEvent[]
  note: string | null
  estimated: boolean
}
interface AuditDecision {
  id: string; alert_id: string; timestamp: string; situation_type: string
  action_taken: string; factors: string[]; confidence: number
  outcome: string | null; analyst_confirmed: boolean; hash: string
}
interface AuditVerification {
  chain_length: number; verified: boolean
  first_record: string | null; last_record: string | null
  broken_at_index?: number
}

interface InterventionHistoryResponse {
  interventions?: Array<Record<string, unknown>>
  count?: number
}

interface EvidenceRoomEntry {
  decision_id: string
  decision_id_full?: string
  action: string
  category: string
  confidence: number
  outcome: string | null
  timestamp?: string | null
  hash?: string | null
}
interface EvidenceRoomData {
  generated_at: string
  audit_trail: {
    entries: EvidenceRoomEntry[]
    total: number
  }
  conservation: {
    status: 'GREEN' | 'AMBER' | 'RED' | 'CALIBRATING' | 'UNKNOWN'
    product: number
    threshold: number
    verified_decisions?: number
    frozen?: boolean
  }
  override_analysis: {
    total: number
    overrides: number
    confirmations: number
    override_rate: number
    per_category?: Record<string, unknown>
  }
  hash_chain: {
    verified: boolean
    entries: number
    status: 'VERIFIED' | 'BROKEN'
  }
}

interface LearningHealthData {
  status?: string
  signal?: number
  theta_min?: number
  components?: {
    override_rate?: number | null
    alpha?: number | null
    q?: number | null
    V?: number | null
    n?: number | null
  }
  auto_pause_active?: boolean
}

// ============================================================================
// Interfaces — GAE real data
// ============================================================================

// VIS-2: centroid evolution entry from /api/soc/centroid-evolution
interface CentroidEvolutionEntry {
  decision_number: number
  centroid_delta_norm: number
  correct: boolean
  category: string
  action: string
}
// CentroidEvolutionData removed — backend returns flat array, not {evolution:[]} wrapper

interface GAEConfidencePoint {
  decision_number: number; confidence: number
  action: string; outcome: number; timestamp: string
}
interface GAEConfidenceTrajectory {
  trajectories: Record<string, GAEConfidencePoint[]>
  message: string | null
}

interface GAETrustPoint {
  decision_number: number; trust_level: number
  outcome: number; below_threshold: boolean; timestamp: string
}
interface GAETrustCurve {
  curves: Record<string, GAETrustPoint[]>
  review_threshold: number
  message: string | null
}

interface GAEBeforeAfterDecision {
  decision_number: number; confidence: number
  action: string; timestamp: string
}
interface GAEBeforeAfter {
  ready: boolean
  first_decision?: GAEBeforeAfterDecision
  latest_decision?: GAEBeforeAfterDecision
  improvement_pp?: number
  total_decisions?: number
  situation_types_seen?: string[]
  message?: string | null
}

interface ConvergenceData {
  decisions: number; weight_norm: number; stability: number
  accuracy: number; converged: boolean; provisional_dimensions: number
  pending_autonomous: number; weight_snapshots: number[]
  message: string | null
}

interface EvalTemplateInfo {
  format: string
  download_url: string
}

interface EvalUploadResult {
  total_rows: number
  evaluated_rows: number
  invalid_rows: number
  accuracy: number
  accuracy_trajectory: Array<{
    decision_number: number
    accuracy: number
    correct_total: number
  }>
  confidence_trajectory: Array<{
    decision_number: number
    confidence: number
    mean_confidence: number
  }>
  convergence_trajectory: Array<{
    decision_number: number
    drift_from_mu_zero: number
  }>
  per_decision_log: Array<{
    decision_number: number
    row_number: number
    row_id: string
    category: string
    predicted_action: string
    ground_truth_action: string
    correct: boolean
    confidence: number
    probabilities?: number[]
    ambiguous?: boolean
    ambiguity_note?: string
  }>
  per_category_results?: Array<{
    category: string
    verified_count: number
    accuracy: number
    convergence_pct?: number
    decisions_to_90pct?: number
  }>
  category_accuracy: Record<string, number>
  category_counts?: Record<string, number>
  duration_seconds: number
  warnings?: string[]
  row_errors?: Array<{ row_number: number; errors: string[] }>
  confidence_note?: string | null
  learning_direction?: 'correct' | 'wrong' | 'insufficient_data'
  distance_change_pct?: number
  convergence_summary?: {
    average_convergence_pct?: number
    total_verified?: number
    note?: string | null
  } | null
  calibration_warning?: boolean
  calibration_status?: 'calibrated' | 'uncalibrated' | 'unknown'
  calibration_note?: string
  ambiguity_summary?: {
    ambiguous_decisions: number
    ambiguous_pct: number
    note?: string | null
  } | null
  majority_baseline?: {
    accuracy: number
    per_category: Record<string, { majority_action: string; accuracy: number }>
  }
  learning_advantage_over_majority?: number
  ceiling_estimate?: {
    overall?: number
    per_category?: Record<string, number>
    note?: string
  } | null
}

// ============================================================================
// Color palettes
// ============================================================================

const ACTION_COLORS: Record<string, string> = {
  escalate:    '#ef4444',
  investigate: '#3b82f6',
  suppress:    '#10b981',
  monitor:     '#f59e0b',
}

const SITUATION_COLORS: Record<string, string> = {
  travel_login_anomaly:       '#8b5cf6',
  known_phishing_campaign:    '#3b82f6',
  critical_asset_malware:     '#ef4444',
  data_exfiltration_detected: '#f59e0b',
  unknown_login_pattern:      '#6b7280',
  routine_malware_scan:       '#10b981',
}

const EVAL_SOC_CATEGORIES = [
  'credential_access',
  'malware_execution',
  'lateral_movement',
  'data_exfiltration',
  'insider_threat',
  'cloud_infrastructure',
]

// fallback palette for unknown keys
const FALLBACK_COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']
function pickColor(key: string, idx: number): string {
  return ACTION_COLORS[key] ?? SITUATION_COLORS[key] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length]
}

// ============================================================================
// formatUSD — compact dollar formatter
// ============================================================================

function formatUSD(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${Math.round(value).toLocaleString()}`
  return `$${value.toFixed(2)}`
}

// ============================================================================
// ChartEmpty — consistent empty-state placeholder
// ============================================================================

function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="py-10 text-center text-gray-400 italic text-sm">
      {message}
    </div>
  )
}

function SwitchingCostChart({ trajectory }: { trajectory?: SwitchingCostTrajectory | null }) {
  const points = ensureArray<SwitchingCostPoint>(trajectory?.points)
    .map(point => ({
      ...point,
      month: Number(point.month ?? 0),
      decisions: Number(point.decisions ?? 0),
      iks: Number(point.iks ?? 0),
      analyst_days: Number(point.analyst_days ?? 0),
      cost_usd: Number(point.cost_usd ?? 0),
    }))
    .filter(point => point.month > 0)

  if (points.length === 0) return null

  const actualPoints = points.filter(point => point.point_type === 'actual')
  const current = trajectory?.current ?? actualPoints[actualPoints.length - 1] ?? points[points.length - 1]
  const costPerDay = Number(trajectory?.cost_per_day ?? 800)

  return (
    <div className="mt-5 rounded-lg border border-purple-200 bg-purple-50/50 p-4">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h4 className="text-sm font-bold text-gray-900">Switching Cost Trajectory</h4>
          <p className="text-xs text-gray-500 mt-1">
            Analyst-days required to rebuild accumulated judgment after switching vendors.
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase tracking-wide text-gray-500">Current</div>
          <div className="text-xl font-bold text-purple-700">{formatUSD(Number(current?.cost_usd ?? 0))}</div>
        </div>
      </div>

      <div className="h-64 bg-white rounded border border-purple-100 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ede9fe" />
            <XAxis
              dataKey="month"
              tickFormatter={(month: number) => `M${month}`}
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
            />
            <YAxis
              tickFormatter={(value: number) => formatUSD(value)}
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              width={66}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #7e22ce', borderRadius: '6px' }}
              labelStyle={{ color: '#c4b5fd', fontSize: '12px' }}
              formatter={(value: any) => [formatUSD(Number(value)), 'Switching cost']}
              labelFormatter={(_, payload) => {
                const point = payload?.[0]?.payload as SwitchingCostPoint | undefined
                if (!point) return 'Switching cost'
                return `Month ${point.month} · ${point.point_type === 'actual' ? 'Actual' : 'Projected'}`
              }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const point = payload[0].payload as SwitchingCostPoint
                return (
                  <div className="rounded-md border border-purple-500 bg-gray-950 px-3 py-2 text-xs text-gray-200 shadow-lg">
                    <div className="font-semibold text-purple-200 mb-1">
                      Month {point.month} · {point.point_type === 'actual' ? 'Actual' : 'Projected'}
                    </div>
                    <div>Cost: <span className="font-mono">{formatUSD(point.cost_usd)}</span></div>
                    <div>Decisions: <span className="font-mono">{Math.round(point.decisions).toLocaleString()}</span></div>
                    <div>IKS: <span className="font-mono">{point.iks.toFixed(1)}</span></div>
                    <div>Analyst-days: <span className="font-mono">{point.analyst_days.toFixed(1)}</span></div>
                    <div className="mt-1 text-gray-400">{point.label}</div>
                  </div>
                )
              }}
            />
            <Area
              type="monotone"
              dataKey="cost_usd"
              stroke="#7e22ce"
              strokeWidth={2}
              fill="#c084fc"
              fillOpacity={0.25}
              dot={({ cx, cy, payload }) => (
                <circle
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={(payload as SwitchingCostPoint).point_type === 'actual' ? '#7e22ce' : '#f59e0b'}
                  stroke="#ffffff"
                  strokeWidth={1.5}
                />
              )}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
        <span>Current: {formatUSD(Number(current?.cost_usd ?? 0))} ({Math.round(Number(current?.decisions ?? 0)).toLocaleString()} decisions, month {Number(current?.month ?? 0)})</span>
        <span>● Actual</span>
        <span className="text-amber-600">● Projected</span>
        <span>Uses ROI Calculator input: {formatUSD(costPerDay)}/day</span>
      </div>
    </div>
  )
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isEvidenceRoomEntry(value: unknown): value is EvidenceRoomEntry {
  const entry = value as Partial<EvidenceRoomEntry> | null
  return !!entry
    && typeof entry === 'object'
    && typeof entry.decision_id === 'string'
    && (entry.decision_id_full === undefined || typeof entry.decision_id_full === 'string')
    && typeof entry.action === 'string'
    && typeof entry.category === 'string'
    && isFiniteNumber(entry.confidence)
    && (entry.outcome === null || typeof entry.outcome === 'string')
    && (entry.timestamp === undefined || entry.timestamp === null || typeof entry.timestamp === 'string')
    && (entry.hash === undefined || entry.hash === null || typeof entry.hash === 'string')
}

function isEvidenceRoomData(value: unknown): value is EvidenceRoomData {
  const candidate = value as Partial<EvidenceRoomData> | null
  return !!candidate
    && typeof candidate === 'object'
    && !!candidate.audit_trail
    && typeof candidate.audit_trail === 'object'
    && Array.isArray(candidate.audit_trail.entries)
    && candidate.audit_trail.entries.every(isEvidenceRoomEntry)
    && isFiniteNumber(candidate.audit_trail.total)
    && !!candidate.conservation
    && typeof candidate.conservation === 'object'
    && typeof candidate.conservation.status === 'string'
    && isFiniteNumber(candidate.conservation.product)
    && isFiniteNumber(candidate.conservation.threshold)
    && (candidate.conservation.verified_decisions === undefined || isFiniteNumber(candidate.conservation.verified_decisions))
    && (candidate.conservation.frozen === undefined || typeof candidate.conservation.frozen === 'boolean')
    && !!candidate.override_analysis
    && typeof candidate.override_analysis === 'object'
    && isFiniteNumber(candidate.override_analysis.total)
    && isFiniteNumber(candidate.override_analysis.confirmations)
    && isFiniteNumber(candidate.override_analysis.overrides)
    && typeof candidate.override_analysis.override_rate === 'number'
    && Number.isFinite(candidate.override_analysis.override_rate)
    && !!candidate.hash_chain
    && typeof candidate.hash_chain === 'object'
    && typeof candidate.hash_chain.status === 'string'
    && typeof candidate.hash_chain.verified === 'boolean'
    && isFiniteNumber(candidate.hash_chain.entries)
}

// ============================================================================
// Component
// ============================================================================

export default function CompoundingTab() {
  // — seeded metrics —
  const [data, setData] = useState<CompoundingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [reseeding, setReseeding] = useState(false)
  const [reseedMessage, setReseedMessage] = useState<string | null>(null)
  const [showROI, setShowROI] = useState(false)

  // — audit —
  const [auditDecisions, setAuditDecisions] = useState<AuditDecision[]>([])
  const [auditVerification, setAuditVerification] = useState<AuditVerification | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)

  // — GAE real charts —
  const [gaeConfTraj, setGaeConfTraj] = useState<GAEConfidenceTrajectory | null>(null)
  const [gaeTrustCurve, setGaeTrustCurve] = useState<GAETrustCurve | null>(null)
  const [gaeBeforeAfter, setGaeBeforeAfter] = useState<GAEBeforeAfter | null>(null)
  const [gaeChartsLoading, setGaeChartsLoading] = useState(false)

  // — convergence —
  const [convergenceData, setConvergenceData] = useState<ConvergenceData | null>(null)
  const [convergenceLoading, setConvergenceLoading] = useState(false)

  // VIS-2: centroid evolution (replaces Chart A) + decision_count for label logic
  const [centroidEvolution, setCentroidEvolution] = useState<CentroidEvolutionEntry[]>([])
  const [vis2DecisionCount, setVis2DecisionCount] = useState(0)

  // — real Tab 4 data (H7-FIX-4) —
  const [decisionEconomics, setDecisionEconomics] = useState<DecisionEconomics | null>(null)
  const [evolutionEventsReal, setEvolutionEventsReal] = useState<EvolutionEventsState | null>(null)
  const [autoApproveStats, setAutoApproveStats] = useState<AutoApproveStats | null>(null)
  const [autoApproveLoading, setAutoApproveLoading] = useState(true)

  // — F4-OVERLAY: operational metrics —
  const [operationalMetrics, setOperationalMetrics] = useState<OperationalMetrics | null>(null)

  // — ECON-1: economics data —
  const [economicsData, setEconomicsData] = useState<EconomicsData | null>(null)
  const [headlineImpact, setHeadlineImpact] = useState<BusinessImpact | null>(null)

  // — FEATURE-01: Evaluate on Your Data —
  const [evalFile, setEvalFile] = useState<File | null>(null)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [evalResult, setEvalResult] = useState<EvalUploadResult | null>(null)
  const [evalUploading, setEvalUploading] = useState(false)
  const [evalTemplatesOpen, setEvalTemplatesOpen] = useState(false)
  const [evalTemplates, setEvalTemplates] = useState<EvalTemplateInfo[]>([])
  const [evalTemplatesLoading, setEvalTemplatesLoading] = useState(false)
  const [evalTemplatesError, setEvalTemplatesError] = useState<string | null>(null)
  const [learningBalanceExpanded, setLearningBalanceExpanded] = useState(false)
  const [learningBalanceLoading, setLearningBalanceLoading] = useState(false)
  const [learningBalanceError, setLearningBalanceError] = useState<string | null>(null)
  const [learningBalanceSheet, setLearningBalanceSheet] = useState<LearningBalanceSheet | null>(null)

  // — FEATURE-09: Evidence Room —
  const [evidenceRoom, setEvidenceRoom] = useState<EvidenceRoomData | null>(null)
  const [learningHealth, setLearningHealth] = useState<LearningHealthData | null>(null)
  const [evidenceRoomLoading, setEvidenceRoomLoading] = useState(false)
  const [evidenceRoomError, setEvidenceRoomError] = useState<string | null>(null)
  const [evidenceExporting, setEvidenceExporting] = useState(false)
  const [latestIntervention, setLatestIntervention] = useState<Record<string, unknown> | null>(null)
  const [interventionLoading, setInterventionLoading] = useState(false)
  const [failureLoading, setFailureLoading] = useState(false)
  const [failureMessage, setFailureMessage] = useState<string | null>(null)

  // ALL HOOKS MUST BE AT TOP LEVEL
  const animatedNodesEnd = useCountUp(data?.headline.nodes_start ?? 0, data?.headline.nodes_end ?? 0, 3000, 0, !!data && !loading)
  const animatedAutoCloseEnd = useCountUp(data?.headline.auto_close_start ?? 0, data?.headline.auto_close_end ?? 0, 3000, 0, !!data && !loading)
  const animatedMttrEnd = useCountUp(data?.headline.mttr_start ?? 0, data?.headline.mttr_end ?? 0, 3000, 1, !!data && !loading)
  const animatedFpEnd = useCountUp(data?.headline.fp_investigations_start ?? 0, data?.headline.fp_investigations_end ?? 0, 3000, 0, !!data && !loading)
  const animatedAnalystHours = useCountUp(0, data?.business_impact?.analyst_hours_saved_monthly ?? 0, 3000, 0, !!data?.business_impact && !loading)
  const animatedCostAvoided = useCountUp(0, data?.business_impact?.cost_avoided_quarterly ?? 0, 3000, 0, !!data?.business_impact && !loading)
  const animatedMttrReduction = useCountUp(0, data?.business_impact?.mttr_reduction_pct ?? 0, 3000, 0, !!data?.business_impact && !loading)
  const animatedBacklogEliminated = useCountUp(0, data?.business_impact?.alert_backlog_eliminated_monthly ?? 0, 3000, 0, !!data?.business_impact && !loading)

  // — load functions —

  const loadHeadlineImpact = async () => {
    try {
      const response = await fetch(`${SOC_API}/api/metrics/compounding/headline`)
      if (!response.ok) throw new Error(`Headline request failed: ${response.status}`)
      const payload = await response.json() as { business_impact?: BusinessImpact }
      if (payload.business_impact) setHeadlineImpact(payload.business_impact)
    } catch (e) {
      console.error('[CompoundingTab] Failed to load headline impact:', e)
    }
  }
  useEffect(() => { loadHeadlineImpact() }, [])

  const loadData = async () => {
    setLoading(true)
    try { setData(await getCompoundingMetrics(4) as CompoundingData) }
    catch (e) { console.error('Failed to load compounding metrics:', e) }
    finally { setLoading(false) }
  }
  useEffect(() => { loadData() }, [])

  const loadAutoApproveStats = async () => {
    setAutoApproveLoading(true)
    try {
      const stats = await fetchAutoApproveStats() as AutoApproveStats
      setAutoApproveStats(stats)
    } catch (e) {
      console.error('[CompoundingTab] Failed to load auto-approve stats:', e)
    } finally {
      setAutoApproveLoading(false)
    }
  }
  useEffect(() => { loadAutoApproveStats() }, [])

  const handleReseed = async () => {
    if (!window.confirm('Re-seed AGE? This will DELETE all current data and restore the canonical demo dataset.')) return
    setReseeding(true); setReseedMessage(null)
    try {
      const result = await reseedDemoData() as { success: boolean; alert_count?: number; error?: string }
      if (result.success) { setReseedMessage(`Re-seed complete — ${result.alert_count} alerts restored.`); await loadData() }
      else setReseedMessage(`Re-seed failed: ${result.error ?? 'unknown error'}`)
    } catch (e) {
      console.error('[CompoundingTab] Re-seed threw:', e)
      setReseedMessage('Re-seed failed — check backend logs.')
    } finally { setReseeding(false) }
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      await resetAllDemoData(); await resetAlerts(); await loadData()
      await loadGAECharts()
      await loadDecisionEconomics()
      await loadEvolutionEventsReal()
      await loadEconomicsData()
    } catch (e) { console.error('[CompoundingTab] Failed to reset demo:', e) }
    finally { setResetting(false) }
  }

  const loadAuditData = async () => {
    setAuditLoading(true)
    try {
      const [dr, vr] = await Promise.all([
        getAuditDecisions() as Promise<{ decisions: AuditDecision[]; total: number }>,
        verifyAuditChain() as Promise<AuditVerification>,
      ])
      setAuditDecisions(dr.decisions.slice(0, 5))
      setAuditVerification(vr)
    } catch (e) { console.error('[CompoundingTab] Failed to load audit data:', e) }
    finally { setAuditLoading(false) }
  }
  useEffect(() => { loadAuditData() }, [])

  const loadLatestIntervention = async () => {
    setInterventionLoading(true)
    try {
      const payload = await fetchInterventionHistory(1) as InterventionHistoryResponse
      setLatestIntervention(payload.interventions?.[0] ?? null)
    } catch (error) {
      console.error('[CompoundingTab] Failed to load interventions:', error)
      setLatestIntervention(null)
    } finally {
      setInterventionLoading(false)
    }
  }
  useEffect(() => { loadLatestIntervention() }, [])

  const handleSimulateFailure = async () => {
    setFailureLoading(true)
    setFailureMessage(null)
    try {
      const result = await simulateFailedGate() as { execution?: { status?: string; reason?: string }; eval_gate?: { overall_passed?: boolean } }
      const reason = result.execution?.reason ?? 'Conservation guard degraded to AMBER; expansion paused.'
      setFailureMessage(`AMBER / degraded: ${reason}`)
      await Promise.all([
        loadLatestIntervention(),
        loadEvidenceRoom(),
        loadData(),
      ])
    } catch (error) {
      console.error('[CompoundingTab] Simulate failure failed:', error)
      setFailureMessage('Simulate Failure unavailable')
    } finally {
      setFailureLoading(false)
    }
  }

  const loadEvidenceRoom = async () => {
    setEvidenceRoomLoading(true)
    setEvidenceRoomError(null)
    try {
      const resp = await fetch(`${SOC_API}/api/soc/evidence-room`)
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        throw new Error(`Evidence Room request failed: ${resp.status}`)
      }
      const payload = await resp.json()
      if (!isEvidenceRoomData(payload)) {
        throw new Error('Evidence Room response shape is invalid')
      }
      setEvidenceRoom(payload)
      try {
        const health = await fetchLearningHealth() as LearningHealthData
        setLearningHealth(health)
      } catch (healthError) {
        console.debug('[CompoundingTab] Learning health unavailable for override rate:', healthError)
        setLearningHealth(null)
      }
    } catch (error) {
      console.error('[CompoundingTab] Failed to load Evidence Room:', error)
      setEvidenceRoom(null)
      setLearningHealth(null)
      setEvidenceRoomError('Evidence Room unavailable')
    } finally {
      setEvidenceRoomLoading(false)
    }
  }
  useEffect(() => { loadEvidenceRoom() }, [])

  const handleEvidenceExport = async () => {
    setEvidenceExporting(true)
    try {
      const resp = await fetch(`${SOC_API}/api/soc/evidence-room/export`)
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        throw new Error(`Evidence export failed: ${resp.status}`)
      }
      const payload = await resp.json()
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      a.href = url
      a.download = `evidence_pack_${timestamp}.json`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('[CompoundingTab] Evidence export failed:', error)
      setEvidenceRoomError('Evidence Room unavailable')
    } finally {
      setEvidenceExporting(false)
    }
  }

  const loadGAECharts = async () => {
    setGaeChartsLoading(true)
    try {
      const [ct, tc, ba] = await Promise.all([
        getGAEConfidenceTrajectory()  as Promise<GAEConfidenceTrajectory>,
        getGAETrustCurve()            as Promise<GAETrustCurve>,
        getGAEBeforeAfter()           as Promise<GAEBeforeAfter>,
      ])
      console.log('[GAE] confidence-trajectory:', Object.keys(ct?.trajectories || {}), 'message:', ct?.message)
      console.log('[GAE] trust-curve:', Object.keys(tc?.curves || {}), 'message:', tc?.message)
      console.log('[GAE] before-after: ready=', ba?.ready, 'improvement_pp=', ba?.improvement_pp, 'message:', ba?.message)
      setGaeConfTraj(ct); setGaeTrustCurve(tc); setGaeBeforeAfter(ba)
    } catch (e) { console.error('[CompoundingTab] Failed to load GAE charts:', e) }
    finally { setGaeChartsLoading(false) }
  }
  useEffect(() => { loadGAECharts() }, [])

  const loadConvergenceData = async () => {
    setConvergenceLoading(true)
    try { setConvergenceData(await getGAEConvergence() as ConvergenceData) }
    catch (e) { console.error('[CompoundingTab] Failed to load convergence data:', e) }
    finally { setConvergenceLoading(false) }
  }
  useEffect(() => { loadConvergenceData() }, [])

  // H7-FIX-4: load real decision economics from AGE
  const loadDecisionEconomics = async () => {
    try {
      const resp = await fetch(`${SOC_API}/api/metrics/decision-economics`)
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        return
      }
      const d = await resp.json()
      setDecisionEconomics(d as DecisionEconomics)
    } catch (e) { console.error('[CompoundingTab] Failed to load decision economics:', e) }
  }
  useEffect(() => { loadDecisionEconomics() }, [])

  // F4-OVERLAY: load operational metrics
  const loadOperationalMetrics = async () => {
    try {
      const resp = await fetch(`${SOC_API}/api/soc/operational-metrics`)
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        return
      }
      const d = await resp.json()
      setOperationalMetrics(d as OperationalMetrics)
    } catch (e) { console.error('[CompoundingTab] Failed to load operational metrics:', e) }
  }
  useEffect(() => { loadOperationalMetrics() }, [])

  // F4-OVERLAY: board export download
  const handleBoardExport = async () => {
    try {
      const resp = await fetch(`${SOC_API}/api/soc/board-export`)
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        return
      }
      const d = await resp.json()
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const date = new Date().toISOString().split('T')[0]
      a.href = url
      a.download = `ci-platform-board-report-${date}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) { console.error('[CompoundingTab] Board export failed:', e) }
  }

  // ECON-1: load economics data
  const loadEconomicsData = async () => {
    try {
      const resp = await fetch(`${SOC_API}/api/soc/economics`)
      if (!resp.ok) {
        if (resp.status === 401) window.location.href = '/saml/login'
        return
      }
      const d = await resp.json()
      setEconomicsData(d as EconomicsData)
    } catch (e) { console.error('[CompoundingTab] Failed to load economics data:', e) }
  }
  useEffect(() => { loadEconomicsData() }, [])

  // H7-FIX-4: load real evolution events from dedicated endpoint
  const loadEvolutionEventsReal = async () => {
    try {
      const d = await getEvolutionEvents(20) as EvolutionEventsState
      setEvolutionEventsReal(d)
    } catch (e) { console.error('[CompoundingTab] Failed to load evolution events:', e) }
  }
  useEffect(() => { loadEvolutionEventsReal() }, [])

  // VIS-2: load centroid evolution (Chart A replacement).
  // On fetch error: renders ChartEmpty — no fabricated series (SOC-4 fix).
  const loadCentroidEvolution = async () => {
    try {
      const d = await getCentroidEvolution(200) as CentroidEvolutionEntry[]
      setCentroidEvolution(d)
    } catch {
      // Endpoint unavailable — show empty state instead of random illustrative data.
      setCentroidEvolution([])
    }
  }
  useEffect(() => { loadCentroidEvolution() }, [])

  // VIS-2: load decision_count for label qualification
  const loadVis2DecisionCount = async () => {
    try {
      const d = await getProfileState() as { iks?: { decision_count: number }; decision_count?: number }
      setVis2DecisionCount(d?.iks?.decision_count ?? d?.decision_count ?? 0)
    } catch { /* non-critical */ }
  }
  useEffect(() => { loadVis2DecisionCount() }, [])

  const loadLearningBalanceSheet = async () => {
    setLearningBalanceLoading(true)
    setLearningBalanceError(null)
    try {
      const sheet = await fetchLearningBalanceSheet() as LearningBalanceSheet
      setLearningBalanceSheet(sheet)
    } catch (e) {
      console.error('[CompoundingTab] Failed to load learning balance sheet:', e)
      setLearningBalanceError(e instanceof Error ? e.message : 'Unable to load learning balance sheet.')
    } finally {
      setLearningBalanceLoading(false)
    }
  }
  useEffect(() => {
    if (learningBalanceExpanded && !learningBalanceSheet && !learningBalanceLoading && !learningBalanceError) {
      void loadLearningBalanceSheet()
    }
  }, [learningBalanceExpanded, learningBalanceSheet, learningBalanceLoading, learningBalanceError])

  const loadEvalTemplates = async () => {
    if (evalTemplates.length > 0 || evalTemplatesLoading) return
    setEvalTemplatesLoading(true)
    setEvalTemplatesError(null)
    try {
      const response = await fetchEvalTemplates() as { formats?: EvalTemplateInfo[] }
      setEvalTemplates(response.formats ?? [])
    } catch (error) {
      console.error('[CompoundingTab] Failed to load eval templates:', error)
      setEvalTemplatesError('templates unavailable')
    } finally {
      setEvalTemplatesLoading(false)
    }
  }

  const handleTemplateToggle = async () => {
    const nextOpen = !evalTemplatesOpen
    setEvalTemplatesOpen(nextOpen)
    if (nextOpen && evalTemplates.length === 0 && !evalTemplatesError) {
      await loadEvalTemplates()
    }
  }

  const handleEvalFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null
    setEvalError(null)

    if (!nextFile) {
      setEvalFile(null)
      return
    }
    if (nextFile.size > 10 * 1024 * 1024) {
      setEvalFile(null)
      setEvalError('CSV must be 10MB or smaller.')
      event.target.value = ''
      return
    }

    setEvalFile(nextFile)
  }

  const handleEvalUpload = async () => {
    if (!evalFile) return
    setEvalUploading(true)
    setEvalError(null)
    try {
      const result = await uploadEvalCSV(evalFile) as EvalUploadResult
      setEvalResult(result)
    } catch (error) {
      console.error('[CompoundingTab] Eval upload failed:', error)
      setEvalResult(null)
      setEvalError(error instanceof Error ? error.message : 'Evaluation failed')
    } finally {
      setEvalUploading(false)
    }
  }

  // The panel requests above are intentionally independent. Keep the Tab 4
  // shell (and ROI calculator) interactive while the primary metrics request
  // is still loading instead of hiding every panel behind one gate.
  if (loading || !data) {
    return (
      <div className="space-y-6">
        <LearningControlRoom />
        <SimulationPanel onSimulationComplete={loadGAECharts} />
        <ThreeChannelPanel />
        <div className="rounded-lg border border-purple-200 bg-white p-6 shadow">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Decision Economics</h2>
              <p className="mt-1 text-sm text-gray-600">
                {loading ? 'Loading live compounding metrics…' : 'Live compounding metrics are temporarily unavailable.'}
              </p>
            </div>
            <button
              type="button"
              onMouseDown={() => setShowROI(true)}
              onClick={() => setShowROI(true)}
              className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-white shadow-md transition hover:bg-purple-700"
            >
              <Calculator className="h-4 w-4" />
              <span className="text-sm font-semibold">Calculate ROI</span>
            </button>
          </div>
          {headlineImpact && (
            <div className="mt-4 rounded border border-green-200 bg-green-50 p-4 text-center">
              <div className="text-xs font-medium text-gray-500">Projected quarterly value avoided</div>
              <div className="text-2xl font-bold text-green-700">
                {formatUSD(headlineImpact.cost_avoided_quarterly)}
              </div>
            </div>
          )}
        </div>
        <div className="flex h-48 items-center justify-center rounded-lg border border-gray-200 bg-white">
          <div className="text-center">
            <Activity className="mx-auto mb-3 h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-600">Loading compounding metrics…</p>
          </div>
        </div>
        <ROICalculatorModal isOpen={showROI} onClose={() => setShowROI(false)} />
      </div>
    )
  }

  const evalAccuracyChartData = ensureArray<EvalUploadResult['accuracy_trajectory'][number]>(evalResult?.accuracy_trajectory)
    .map(point => ({
      decision: point.decision_number,
      accuracyPct: point.accuracy * 100,
    }))
  const evalConvergenceChartData = ensureArray<EvalUploadResult['convergence_trajectory'][number]>(evalResult?.convergence_trajectory)
    .map(point => ({
      decision: point.decision_number,
      drift: point.drift_from_mu_zero,
    }))
  const evalDecisionsProcessed =
    evalResult?.evaluated_rows
    ?? ensureArray<EvalUploadResult['per_decision_log'][number]>(evalResult?.per_decision_log).length
    ?? 0
  const latestConvergence =
    evalConvergenceChartData.length > 0
      ? evalConvergenceChartData[evalConvergenceChartData.length - 1].drift
      : null
  const evalCategoryRows = EVAL_SOC_CATEGORIES.map((category: string) => ({
    category,
    accuracy: evalResult?.category_accuracy?.[category] ?? null,
    count: evalResult?.category_counts?.[category] ?? null,
    ceiling: evalResult?.ceiling_estimate?.per_category?.[category] ?? null,
    convergencePct: evalResult?.per_category_results?.find(row => row.category === category)?.convergence_pct ?? null,
    decisionsTo90Pct: evalResult?.per_category_results?.find(row => row.category === category)?.decisions_to_90pct ?? null,
    majorityAccuracy: evalResult?.majority_baseline?.per_category?.[category]?.accuracy ?? null,
    majorityAction: evalResult?.majority_baseline?.per_category?.[category]?.majority_action ?? null,
  }))
  const evalCeilingRows = evalCategoryRows.filter(row => row.accuracy !== null && row.ceiling !== null)
    .map(row => ({
      ...row,
      accuracyPct: (row.accuracy ?? 0) * 100,
      ceilingPct: row.ceiling ?? 0,
      roomToGrowPct: Math.max(0, (row.ceiling ?? 0) - ((row.accuracy ?? 0) * 100)),
    }))
  const hasEvalCeiling = evalCeilingRows.length > 0
  const hasEvalNearCeiling = evalCeilingRows.some(row => row.accuracyPct >= row.ceilingPct)
  const lowestCeilingCategory = evalCeilingRows.length > 0
    ? evalCeilingRows.reduce((min, row) => row.ceilingPct < min.ceilingPct ? row : min, evalCeilingRows[0]).category
    : null
  const evalDecisionRows = ensureArray<EvalUploadResult['per_decision_log'][number]>(evalResult?.per_decision_log)
  const evalAmbiguityNote = evalResult?.ambiguity_summary?.note ?? null

  const { headline, weekly_trend, evolution_events } = data
  const autoCloseChange = animatedAutoCloseEnd - headline.auto_close_start
  const mttrChangePercent = (headline.mttr_start - animatedMttrEnd) / headline.mttr_start * 100
  const fpChangePercent = (headline.fp_investigations_start - animatedFpEnd) / headline.fp_investigations_start * 100

  // — derived chart data (GAE) —

  // Confidence trajectory: merge all action series by decision_number
  const gaeConfChartData: Record<string, number>[] = (() => {
    const trj = gaeConfTraj?.trajectories
    if (!trj || Object.keys(trj).length === 0) return []
    const merged = new Map<number, Record<string, number>>()
    for (const [action, pts] of Object.entries(trj)) {
      for (const pt of pts) {
        if (!merged.has(pt.decision_number)) merged.set(pt.decision_number, { decision: pt.decision_number })
        merged.get(pt.decision_number)![action] = pt.confidence
      }
    }
    return [...merged.entries()].sort(([a], [b]) => a - b).map(([, v]) => v)
  })()
  const gaeConfActions = Object.keys(gaeConfTraj?.trajectories ?? {})

  // Trust curve: merge all action series by decision_number
  const gaeTrustChartData: Record<string, number>[] = (() => {
    const crv = gaeTrustCurve?.curves
    if (!crv || Object.keys(crv).length === 0) return []
    const merged = new Map<number, Record<string, number>>()
    for (const [action, pts] of Object.entries(crv)) {
      for (const pt of pts) {
        if (!merged.has(pt.decision_number)) merged.set(pt.decision_number, { decision: pt.decision_number })
        merged.get(pt.decision_number)![action] = pt.trust_level
      }
    }
    return [...merged.entries()].sort(([a], [b]) => a - b).map(([, v]) => v)
  })()
  const gaeTrustActions = Object.keys(gaeTrustCurve?.curves ?? {})

  // Latest trust per action → status badges
  const gaeTrustStatus: Record<string, { trust: number; humanReview: boolean }> = {}
  if (gaeTrustCurve?.curves) {
    for (const [action, pts] of Object.entries(gaeTrustCurve.curves)) {
      if (pts.length > 0) {
        const last = pts[pts.length - 1]
        gaeTrustStatus[action] = { trust: last.trust_level, humanReview: last.below_threshold }
      }
    }
  }

  const learningBalanceCategories = ensureArray<LearningBalanceCategory>(learningBalanceSheet?.categories)
  const learningBalanceTotalVerified = learningBalanceSheet?.total_verified
    ?? learningBalanceCategories.reduce((sum, item) => sum + (item.verified_count ?? 0), 0)
  const learningBalanceExpertCount = learningBalanceCategories.filter(item => item.epistemic_band === 'expert').length
  const learningBalanceRecommendation = learningBalanceSheet?.summary?.recommendation ?? 'Recommendation unavailable.'
  const showLearningBalanceCeiling = learningBalanceCategories.some(item => item.ceiling_estimate != null)
  const evidenceEntries = ensureArray<EvidenceRoomEntry>(evidenceRoom?.audit_trail.entries).slice(0, 20)
  const evidenceStatus = evidenceRoom?.conservation.status ?? 'UNKNOWN'
  const evidenceProduct = evidenceRoom?.conservation.product ?? 0
  const evidenceThreshold = evidenceRoom?.conservation.threshold ?? 0
  const evidenceConservationVerified = evidenceProduct >= evidenceThreshold && evidenceStatus !== 'RED' && evidenceRoom?.hash_chain.status !== 'BROKEN'
  const evidenceTotal = evidenceRoom?.override_analysis.total ?? 0
  const evidenceConfirmations = evidenceRoom?.override_analysis.confirmations ?? 0
  const evidenceOverrides = evidenceRoom?.override_analysis.overrides ?? 0
  const evidenceConfirmationPct = evidenceTotal > 0 ? Math.max(0, Math.min(100, (evidenceConfirmations / evidenceTotal) * 100)) : 0
  const evidenceOverridePct = evidenceTotal > 0 ? Math.max(0, Math.min(100, (evidenceOverrides / evidenceTotal) * 100)) : 0
  const liveOverrideRateRaw = learningHealth?.components?.override_rate
  const liveOverrideRate = typeof liveOverrideRateRaw === 'number' && Number.isFinite(liveOverrideRateRaw)
    ? Math.max(0, Math.min(1, liveOverrideRateRaw > 1 ? liveOverrideRateRaw / 100 : liveOverrideRateRaw))
    : (evidenceRoom?.override_analysis.override_rate ?? 0)
  const liveOverrideRatePct = Math.round(liveOverrideRate * 100)

  const bandBadgeClass = (band: string) => {
    switch (band) {
      case 'expert':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'calibrating':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'learning':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'novice':
      default:
        return 'bg-red-100 text-red-800 border-red-200'
    }
  }

  const statusBadgeClass = (status: LearningBalanceStatus) => {
    switch (status) {
      case 'at_ceiling':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'converging':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'early':
        return 'bg-gray-100 text-gray-700 border-gray-200'
      case 'insufficient_data':
      default:
        return 'bg-red-100 text-red-800 border-red-200'
    }
  }

  const conservationBadgeClass = (status: EvidenceRoomData['conservation']['status']) => {
    switch (status) {
      case 'GREEN':
        return 'bg-green-500/20 text-green-300 border-green-500/50'
      case 'AMBER':
      case 'CALIBRATING':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/50'
      case 'RED':
        return 'bg-red-500/20 text-red-300 border-red-500/50'
      case 'UNKNOWN':
      default:
        return 'bg-slate-700 text-gray-300 border-slate-600'
    }
  }

  const formatDecimal = (value: number | null | undefined) => (value ?? 0).toFixed(3)
  const formatPercent = (value: number | null | undefined) => `${Math.round((value ?? 0) * 100)}%`

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-6">
      <LearningControlRoom />

      {/* ── Simulation Panel ────────────────────────────────────────────────── */}
      <SimulationPanel onSimulationComplete={loadGAECharts} />

      <section className="rounded-lg border border-amber-300 bg-amber-50 p-5 shadow-sm" data-testid="staged-trust-panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Staged trust</p>
            <h3 className="mt-1 text-lg font-bold text-slate-950">The system said no</h3>
            <p className="mt-2 max-w-3xl text-sm text-slate-700">
              Conservation refused auto-expansion when measured accuracy moved below the threshold.
            </p>
          </div>
          <button
            type="button"
            onClick={handleSimulateFailure}
            disabled={failureLoading}
            className="inline-flex items-center gap-2 rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            <Shield className="h-4 w-4" />
            {failureLoading ? 'Simulating...' : 'Simulate Failure'}
          </button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-md border border-amber-200 bg-white p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Latest intervention</span>
              <ProvenanceBadge source="real_measured" />
            </div>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {interventionLoading
                ? 'Loading intervention history...'
                : latestIntervention
                  ? String(latestIntervention.action ?? latestIntervention.type ?? latestIntervention.reason ?? 'learning paused')
                  : 'No intervention recorded yet'}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {latestIntervention
                ? String(latestIntervention.reason ?? latestIntervention.message ?? 'Automatic expansion paused by conservation gate.')
                : 'Refusal events appear here after the conservation gate pauses learning or expansion.'}
            </p>
          </div>
          <div className="rounded-md border border-amber-200 bg-white p-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Red-team result</span>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {failureMessage ?? 'Click Simulate Failure to force the AMBER / degraded path.'}
            </p>
            <p className="mt-1 text-xs text-slate-600">The presenter-visible action is blocked, not silently accepted.</p>
          </div>
        </div>
      </section>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {domainConfig.displayName} Compounding — "Watch the Moat Grow"
            </h2>
            <p className="text-gray-600">
              Same model. Same rules. More intelligence. When competitors deploy, they start at zero. We start at {animatedNodesEnd} patterns.
            </p>
          </div>
          <button
            type="button"
            onMouseDown={() => setShowROI(true)}
            onClick={() => setShowROI(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-all hover:scale-105 shadow-md"
          >
            <Calculator className="w-4 h-4" />
            <span className="text-sm font-semibold">Calculate ROI</span>
          </button>
        </div>
      </div>

      <CohortStatusPanel />

      {/* ── 1. Business Impact Banner — PROJECTED ──────────────────────────── */}
      {data.business_impact && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border-2 border-green-400 shadow-lg p-6">
          {/* Projection badge */}
          <div className="flex items-center justify-center gap-2 mb-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-300">
              📊 Projected at Scale
            </span>
          </div>
          <div className="text-center mb-4">
            <h3 className="text-xl font-bold text-gray-900">Business Impact Summary</h3>
            <p className="text-sm text-gray-500 mt-1">Based on 200 alerts/day processing rate</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-lg border-2 border-green-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <Clock className="w-5 h-5 text-green-600 mx-auto mb-2" />
              <div className="text-4xl font-bold text-green-600 mb-1">{animatedAnalystHours.toLocaleString()}</div>
              <div className="text-xs text-gray-600 font-medium">{domainConfig.impactLabels.hrsSaved}</div>
            </div>
            <div className="bg-white rounded-lg border-2 border-blue-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <DollarSign className="w-5 h-5 text-blue-600 mx-auto mb-2" />
              <div className="text-4xl font-bold text-blue-600 mb-1">${(animatedCostAvoided / 1000).toFixed(0)}K</div>
              <div className="text-xs text-gray-600 font-medium">Cost Avoided / Quarter</div>
            </div>
            <div className="bg-white rounded-lg border-2 border-purple-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <TrendingDown className="w-5 h-5 text-purple-600 mx-auto mb-2" />
              <div className="text-4xl font-bold text-purple-600 mb-1">{animatedMttrReduction}%</div>
              <div className="text-xs text-gray-600 font-medium">MTTR Reduction</div>
            </div>
            <div className="bg-white rounded-lg border-2 border-emerald-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <CheckCircle className="w-5 h-5 text-emerald-600 mx-auto mb-2" />
              <div className="text-4xl font-bold text-emerald-600 mb-1">{animatedBacklogEliminated.toLocaleString()}</div>
              <div className="text-xs text-gray-600 font-medium">{domainConfig.impactLabels.backlog}</div>
            </div>
            <div className="bg-white rounded-lg border-2 border-sky-300 shadow p-5 hover:shadow-xl transition-shadow">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-5 h-5 text-sky-600" />
                <div>
                  <div className="text-sm font-bold text-slate-900">Automation Rate</div>
                  <div className="text-xs text-gray-500">Auto-approve snapshot</div>
                </div>
              </div>

              {autoApproveLoading && !autoApproveStats ? (
                <div className="text-sm text-gray-500 italic">Loading automation stats&hellip;</div>
              ) : autoApproveStats ? (
                <>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg bg-sky-50 border border-sky-200 p-2">
                      <div className="text-[10px] uppercase tracking-wide text-sky-700 font-semibold">Auto-approve</div>
                      <div className="text-2xl font-bold text-sky-700">{autoApproveStats.coverage_pct.toFixed(1)}%</div>
                    </div>
                    <div className="rounded-lg bg-sky-50 border border-sky-200 p-2">
                      <div className="text-[10px] uppercase tracking-wide text-sky-700 font-semibold">Precision / accuracy</div>
                      <div className="text-2xl font-bold text-sky-700">{autoApproveStats.coverage_pct.toFixed(1)}%</div>
                    </div>
                    <div className="rounded-lg bg-sky-50 border border-sky-200 p-2">
                      <div className="text-[10px] uppercase tracking-wide text-sky-700 font-semibold">Threshold</div>
                      <div className="text-2xl font-bold text-sky-700">90%</div>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-gray-600 leading-relaxed">
                    {autoApproveStats.coverage_pct.toFixed(1)}% of alerts auto-resolved at 90% precision gate.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(autoApproveStats.by_category).slice(0, 6).map(([category, stats]) => (
                      <span
                        key={category}
                        className="inline-flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50 px-2 py-1 text-[11px] text-sky-700"
                      >
                        <span className="font-semibold">{category.replace(/_/g, ' ')}</span>
                        <span>{stats.coverage_pct.toFixed(0)}%</span>
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-500 italic">Automation stats unavailable.</div>
              )}
            </div>
          </div>

          <div className="mt-4 text-center">
            <p className="text-sm italic text-gray-700">
              💼 Present these numbers to your CFO — this is the business case for AI-augmented {domainConfig.operationsLabel}.
            </p>
          </div>
          <div className="mt-6">
            <button
              onClick={() => setShowROI(true)}
              className="w-full bg-gradient-to-r from-purple-600 via-blue-600 to-purple-600 hover:from-purple-700 hover:via-blue-700 hover:to-purple-700 text-white font-bold py-4 px-6 rounded-lg shadow-xl transition-all hover:scale-[1.02] hover:shadow-2xl flex items-center justify-center gap-3 group"
            >
              <Calculator className="w-6 h-6 group-hover:rotate-12 transition-transform" />
              <span className="text-lg">Calculate Your ROI — Input Your {domainConfig.displayName} Numbers</span>
              <div className="ml-2 px-3 py-1 bg-white/20 rounded-full text-xs font-semibold">Interactive</div>
            </button>
          </div>
        </div>
      )}

      {/* ── 2. THE HEADLINE — PROJECTED ────────────────────────────────────── */}
      <div className="bg-white rounded-lg border-2 border-purple-200 shadow-lg p-8">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xl font-bold text-gray-900">THE HEADLINE</h3>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            📈 Projected Growth Trajectory
          </span>
        </div>
        <p className="text-xs text-gray-400 text-center italic mb-6">Live compounding data shown in charts below</p>

        <div className="grid md:grid-cols-2 gap-8 mb-8">
          <div className="text-center">
            <div className="text-sm font-semibold text-gray-600 mb-3">WEEK 1</div>
            <div className="bg-gray-50 rounded-lg p-6 border-2 border-gray-300">
              <div className="flex justify-center items-center mb-4">
                <div className="grid grid-cols-3 gap-2">
                  {[...Array(9)].map((_, i) => <div key={i} className="w-6 h-6 bg-blue-300 rounded-full opacity-50" />)}
                </div>
              </div>
              <div className="text-3xl font-bold text-gray-700">{headline.nodes_start} nodes</div>
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm font-semibold text-gray-600 mb-3">WEEK 4</div>
            <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg p-6 border-2 border-purple-400">
              <div className="flex justify-center items-center mb-4">
                <div className="grid grid-cols-5 gap-1">
                  {[...Array(25)].map((_, i) => <div key={i} className="w-4 h-4 bg-purple-500 rounded-full" />)}
                </div>
              </div>
              <div className="text-3xl font-bold text-purple-700">{animatedNodesEnd} nodes</div>
            </div>
          </div>
        </div>

        <div className="space-y-3 border-t pt-6">
          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">Auto-Close Rate:</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">{headline.auto_close_start}% → {animatedAutoCloseEnd}%</span>
              <span className="text-green-600 font-semibold">(+{autoCloseChange.toFixed(0)} pts)</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">MTTR:</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">{headline.mttr_start} min → {animatedMttrEnd.toFixed(1)} min</span>
              <span className="text-green-600 font-semibold">(-{mttrChangePercent.toFixed(0)}%)</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">FP Investigations:</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">{headline.fp_investigations_start.toLocaleString()}/wk → {animatedFpEnd.toLocaleString()}/wk</span>
              <span className="text-green-600 font-semibold">(-{fpChangePercent.toFixed(0)}%)</span>
            </div>
          </div>
        </div>
      <div className="mt-6 text-center">
        <p className="text-lg font-medium text-gray-700 italic">Same model. Same rules. More intelligence.</p>
      </div>
    </div>

      {/* ── 2b. Evaluate on Your Data — FEATURE-01 ─────────────────────────── */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-gray-900">Evaluate on Your Data</h3>
            <p className="text-sm text-gray-600 max-w-3xl">
              Upload a CSV with pre-computed SOC factors to score against the live ProfileScorer without touching production state.
            </p>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Bootstrap σ with honest framing: static <span className="font-mono">_FACTOR_SIGMA</span>, replaced after 200+ decisions.
            </div>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600 lg:w-[26rem]">
            <div className="font-semibold text-gray-900">Accepted CSV schema</div>
            <div className="mt-1">Required: category, ground_truth_action, and the SOC factor columns.</div>
            <button
              onClick={handleTemplateToggle}
              className="mt-3 inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100"
            >
              {evalTemplatesOpen ? 'Hide templates' : 'Show templates'}
            </button>
            {evalTemplatesOpen && (
              <div className="mt-3 space-y-2">
                {evalTemplatesLoading && (
                  <div className="text-xs italic text-gray-500">Loading templates…</div>
                )}
                {evalTemplatesError && (
                  <div className="text-xs italic text-red-600">{evalTemplatesError}</div>
                )}
                {!evalTemplatesLoading && evalTemplates.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {evalTemplates.map(template => (
                      <a
                        key={template.format}
                        href={`/api/eval/templates/${template.format}.csv`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100"
                      >
                        <Download className="h-4 w-4" />
                        {template.format}
                      </a>
                    ))}
                  </div>
                )}
                {!evalTemplatesLoading && evalTemplates.length === 0 && !evalTemplatesError && (
                  <div className="text-xs italic text-gray-500">No template metadata returned.</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <label className="mb-2 block text-sm font-semibold text-gray-900" htmlFor="eval-upload-input">
              CSV file
            </label>
            <input
              id="eval-upload-input"
              type="file"
              accept=".csv,text/csv"
              onChange={handleEvalFileChange}
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-gray-100 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-gray-700 hover:file:bg-gray-200"
            />
            <div className="mt-2 text-xs text-gray-500">
              {evalFile ? `Selected: ${evalFile.name}` : 'No file selected yet.'}
            </div>
          </div>
          <button
            onClick={handleEvalUpload}
            disabled={!evalFile || evalUploading}
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {evalUploading ? 'Evaluating…' : 'Upload CSV'}
          </button>
        </div>

        {evalError && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {evalError}
          </div>
        )}

        {evalResult && (
          <div className="mt-6 space-y-6">
            {ensureArray<string>(evalResult.warnings).length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {ensureArray<string>(evalResult.warnings).join(' ')}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
                <div className="text-xs font-medium text-gray-500">Overall Accuracy</div>
                <div className="mt-1 text-2xl font-bold text-blue-700">
                  {(evalResult.accuracy * 100).toFixed(1)}%
                </div>
              </div>
              {evalResult.majority_baseline != null && (
                <div className={`rounded-lg border p-4 text-center ${
                  typeof evalResult.learning_advantage_over_majority === 'number' && evalResult.learning_advantage_over_majority >= 0
                    ? 'border-green-200 bg-green-50'
                    : 'border-amber-200 bg-amber-50'
                }`}>
                  <div className="text-xs font-medium text-gray-500">Majority Baseline</div>
                  <div className={`mt-1 text-2xl font-bold ${
                    typeof evalResult.learning_advantage_over_majority === 'number' && evalResult.learning_advantage_over_majority >= 0
                      ? 'text-green-700' : 'text-amber-700'
                  }`}>
                    {(evalResult.majority_baseline.accuracy * 100).toFixed(1)}%
                  </div>
                  {typeof evalResult.learning_advantage_over_majority === 'number' && (
                    <div className="mt-1 text-xs text-gray-600">
                      {evalResult.learning_advantage_over_majority >= 0 ? '+' : ''}
                      {(evalResult.learning_advantage_over_majority * 100).toFixed(1)}pp advantage
                    </div>
                  )}
                </div>
              )}
              <div className="rounded-lg border border-purple-200 bg-purple-50 p-4 text-center">
                <div className="text-xs font-medium text-gray-500">Convergence</div>
                <div className="mt-1 text-2xl font-bold text-purple-700">
                  {latestConvergence !== null ? latestConvergence.toFixed(3) : 'N/A'}
                </div>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
                <div className="text-xs font-medium text-gray-500">Decisions Processed</div>
                <div className="mt-1 text-2xl font-bold text-gray-700">{evalDecisionsProcessed}</div>
              </div>
            </div>

            {evalAmbiguityNote && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {evalAmbiguityNote}
              </div>
            )}

            {evalResult.learning_direction === 'correct' && (
              <div className="rounded-lg border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800">
                <div className="font-semibold">
                  &#10003; Centroids converging toward ground truth
                  {typeof evalResult.distance_change_pct === 'number' && (
                    <span className="font-mono text-green-700"> (drift: {evalResult.distance_change_pct.toFixed(1)}%)</span>
                  )}
                </div>
                <div className="mt-1 text-green-700">
                  Learning is active and moving in the correct direction. Accuracy will continue to improve with more verified decisions.
                </div>
              </div>
            )}
            {evalResult.learning_direction === 'wrong' && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm">
                <div className="font-semibold text-amber-900">&#9888; Centroids moving away from ground truth.</div>
                <div className="mt-2 text-amber-900">
                  This typically occurs when:
                </div>
                <div className="mt-1 space-y-0.5 text-amber-800">
                  <div>&bull; Baseline centroids are not calibrated to your environment</div>
                  <div>&bull; The uploaded data has very different characteristics from the training set</div>
                </div>
                <div className="mt-2 text-amber-900">
                  Recommended: Run calibration with your institution&apos;s historical alert data before evaluating. Contact support for calibration assistance.
                </div>
              </div>
            )}
            {evalResult.learning_direction === 'insufficient_data' && (
              <p className="text-sm text-gray-500">Not enough decisions to determine direction (need &#8805;5)</p>
            )}

            {evalResult.calibration_status === 'uncalibrated' && (
              <div className="rounded-lg border border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <span className="font-semibold">&#9888; Uncalibrated centroids detected.</span>{' '}
                {evalResult.calibration_note || 'All centroid values cluster near 0.5 — consider running calibration before deployment.'}
              </div>
            )}

            {typeof evalResult.learning_advantage_over_majority === 'number' &&
              evalResult.majority_baseline != null && (
              <div className={`rounded-lg border px-4 py-3 text-sm ${
                evalResult.learning_advantage_over_majority >= 0
                  ? 'border-green-300 bg-green-50 text-green-800'
                  : 'border-amber-300 bg-amber-50 text-amber-800'
              }`}>
                <span className="font-semibold">
                  {evalResult.learning_advantage_over_majority >= 0 ? '&#10003;' : '&#9888;'}{' '}
                  Learning advantage over majority baseline:{' '}
                  {evalResult.learning_advantage_over_majority >= 0 ? '+' : ''}
                  {(evalResult.learning_advantage_over_majority * 100).toFixed(1)}pp
                </span>
                <span className="ml-2 text-xs opacity-75">
                  (majority baseline accuracy: {(evalResult.majority_baseline.accuracy * 100).toFixed(1)}%)
                </span>
              </div>
            )}

            {hasEvalCeiling && (
              <div className="rounded-lg border border-cyan-200 bg-cyan-50 p-4">
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-cyan-900">Structural Ceiling Estimate (approximate)</h4>
                    <p className="mt-1 text-xs text-cyan-800">
                      {evalResult.ceiling_estimate?.note ?? 'Approximate structural estimate for relative comparison; not predicted accuracy.'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {hasEvalNearCeiling && (
                      <span className="inline-flex rounded-full border border-amber-300 bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
                        Near ceiling
                      </span>
                    )}
                    {/* OBS-FIX-21: Investigate factors link to Factor Analysis */}
                    <button
                      type="button"
                      onClick={() => window.dispatchEvent(new CustomEvent('vis2:navigate', { detail: { tab: 'evolution' } }))}
                      className="inline-flex items-center gap-1 rounded-lg border border-cyan-400 bg-cyan-100 px-2.5 py-1 text-xs font-semibold text-cyan-800 transition-colors hover:bg-cyan-200"
                    >
                      Investigate factors →
                    </button>
                  </div>
                </div>
                {hasEvalNearCeiling && (
                  <p className="mt-3 text-xs text-amber-800">
                    One or more categories are near ceiling relative to this approximate structural estimate.
                  </p>
                )}
                {lowestCeilingCategory && (
                  <p className="mt-2 text-xs text-cyan-700">
                    Bottleneck: <span className="font-semibold">{lowestCeilingCategory}</span> has the lowest structural ceiling.
                  </p>
                )}
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-cyan-100 text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wide text-cyan-700">
                        <th className="pb-2 pr-4 font-semibold">Category</th>
                        <th className="pb-2 pr-4 font-semibold">Accuracy</th>
                        <th className="pb-2 pr-4 font-semibold">Ceiling</th>
                        <th className="pb-2 font-semibold">Room to grow</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-cyan-100">
                      {evalCeilingRows.map(row => (
                        <tr key={row.category} className={row.category === lowestCeilingCategory ? 'bg-amber-50/50' : undefined}>
                          <td className="py-2 pr-4 font-medium text-cyan-950">
                            {row.category}
                            {row.category === lowestCeilingCategory && (
                              <span className="ml-2 rounded-full border border-amber-300 bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">bottleneck</span>
                            )}
                          </td>
                          <td className="py-2 pr-4 text-cyan-900">{row.accuracyPct.toFixed(1)}%</td>
                          <td className="py-2 pr-4 text-cyan-900">
                            <span>{row.ceilingPct.toFixed(1)}%</span>
                          </td>
                          <td className="py-2 text-cyan-900">{row.roomToGrowPct.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="grid gap-6 xl:grid-cols-2">
              <div className="rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-900">Accuracy Trajectory</h4>
                {evalAccuracyChartData.length > 0 ? (
                  <div className="mt-4">
                    <ResponsiveContainer width="100%" height={260}>
                      <AreaChart data={evalAccuracyChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="decision" />
                        <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
                        <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                        <Area type="monotone" dataKey="accuracyPct" stroke="#2563eb" fill="#93c5fd" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <ChartEmpty message="Accuracy trajectory will appear after a successful upload." />
                )}
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-900">Convergence Curve</h4>
                {evalConvergenceChartData.length > 0 ? (
                  <div className="mt-4">
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={evalConvergenceChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="decision" />
                        <YAxis />
                        <Tooltip formatter={(value: number) => value.toFixed(4)} />
                        <Line type="monotone" dataKey="drift" stroke="#7c3aed" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <ChartEmpty message="Convergence data will appear after a successful upload." />
                )}
                {evalResult.confidence_note && (
                  <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-xs leading-5 text-gray-600">
                    {evalResult.confidence_note}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 p-4">
              <h4 className="text-sm font-semibold text-gray-900">Category Breakdown</h4>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                      <th className="pb-2 pr-4 font-semibold">Category</th>
                      <th className="pb-2 pr-4 font-semibold">Accuracy</th>
                      <th className="pb-2 pr-4 font-semibold">Majority baseline</th>
                      <th className="pb-2 pr-4 font-semibold">Count</th>
                      <th className="pb-2 pr-4 font-semibold">Convergence</th>
                      <th className="pb-2 font-semibold">Remaining</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {evalCategoryRows.map((row) => {
                      const beatsBaseline = row.accuracy !== null && row.majorityAccuracy !== null && row.accuracy > row.majorityAccuracy
                      return (
                        <tr key={row.category}>
                          <td className="py-2 pr-4 font-medium text-gray-900">{row.category}</td>
                          <td className="py-2 pr-4 text-gray-700">
                            {row.accuracy !== null ? `${(row.accuracy * 100).toFixed(1)}%` : '—'}
                          </td>
                          <td className="py-2 pr-4">
                            {row.majorityAccuracy !== null ? (
                              <span className={beatsBaseline ? 'text-green-700 font-medium' : 'text-amber-700 font-medium'}>
                                {(row.majorityAccuracy * 100).toFixed(1)}%
                                {row.majorityAction && <span className="ml-1 text-xs text-gray-500">({row.majorityAction})</span>}
                              </span>
                            ) : '—'}
                          </td>
                          <td className="py-2 pr-4 text-gray-700">{row.count ?? '—'}</td>
                          <td className="py-2 pr-4 text-gray-700">
                            {row.convergencePct !== null ? `${row.convergencePct.toFixed(0)}%` : '—'}
                          </td>
                          <td className="py-2 text-gray-700">
                            {row.decisionsTo90Pct !== null ? `~${row.decisionsTo90Pct} decisions` : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 p-4">
              <h4 className="text-sm font-semibold text-gray-900">Per-Decision Results</h4>
              {evalDecisionRows.length > 0 ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                        <th className="pb-2 pr-3 font-semibold"></th>
                        <th className="pb-2 pr-4 font-semibold">Decision</th>
                        <th className="pb-2 pr-4 font-semibold">Category</th>
                        <th className="pb-2 pr-4 font-semibold">Predicted</th>
                        <th className="pb-2 pr-4 font-semibold">Ground Truth</th>
                        <th className="pb-2 pr-4 font-semibold">Confidence</th>
                        <th className="pb-2 font-semibold">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {evalDecisionRows.map((decision) => (
                        <tr
                          key={`${decision.decision_number}-${decision.row_id}`}
                          className={decision.ambiguous ? 'bg-amber-50/70' : undefined}
                        >
                          <td className="py-2 pr-3 text-amber-700">
                            {decision.ambiguous ? (
                              <span title={decision.ambiguity_note ?? undefined} className="font-semibold">
                                &#8776;
                              </span>
                            ) : null}
                          </td>
                          <td className="py-2 pr-4 text-gray-700">#{decision.decision_number}</td>
                          <td className="py-2 pr-4 text-gray-700">
                            <div>{decision.category}</div>
                            {decision.ambiguous && decision.ambiguity_note && (
                              <div className="mt-0.5 text-xs text-amber-700">{decision.ambiguity_note}</div>
                            )}
                          </td>
                          <td className="py-2 pr-4 text-gray-700">{decision.predicted_action}</td>
                          <td className="py-2 pr-4 text-gray-700">{decision.ground_truth_action}</td>
                          <td className="py-2 pr-4 text-gray-700">{(decision.confidence * 100).toFixed(1)}%</td>
                          <td className={`py-2 font-medium ${decision.correct ? 'text-green-700' : 'text-red-600'}`}>
                            {decision.correct ? 'Correct' : 'Mismatch'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <ChartEmpty message="Per-decision results will appear after a successful upload." />
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 2c. Learning Balance Sheet — FEATURE-10 ─────────────────────────── */}
      <div className="bg-white rounded-lg border shadow">
        <button
          type="button"
          onClick={() => setLearningBalanceExpanded(current => !current)}
          className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
        >
          <div>
            <h3 className="text-xl font-bold text-gray-900">Learning Balance Sheet</h3>
            <p className="mt-1 text-sm text-gray-600">
              Verified learning depth, centroid drift, automation coverage, and category readiness in one view.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-600">
            <span>{learningBalanceExpanded ? 'Collapse' : 'Expand'}</span>
            {learningBalanceExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </div>
        </button>

        {learningBalanceExpanded && (
          <div className="border-t border-gray-200 px-6 py-6">
            {learningBalanceLoading && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-600">
                Loading learning balance sheet…
              </div>
            )}

            {!learningBalanceLoading && learningBalanceError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-4">
                <div className="text-sm text-red-700">{learningBalanceError}</div>
                <button
                  type="button"
                  onClick={() => { void loadLearningBalanceSheet() }}
                  className="mt-3 inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100"
                >
                  <RefreshCw className="h-4 w-4" />
                  Retry
                </button>
              </div>
            )}

            {!learningBalanceLoading && !learningBalanceError && (
              <div className="space-y-6">
                {showLearningBalanceCeiling && (
                  <div className="rounded-lg border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
                    Ceiling values are approximate structural estimates for relative comparison.
                  </div>
                )}
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                    <div className="text-xs font-medium uppercase tracking-wide text-blue-700">Overall IKS</div>
                    <div className="mt-2 text-3xl font-bold text-blue-900">{(learningBalanceSheet?.overall_iks ?? 0).toFixed(1)}</div>
                  </div>
                  <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
                    <div className="text-xs font-medium uppercase tracking-wide text-purple-700">Total Verified</div>
                    <div className="mt-2 text-3xl font-bold text-purple-900">{learningBalanceTotalVerified.toLocaleString()}</div>
                  </div>
                  <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                    <div className="text-xs font-medium uppercase tracking-wide text-green-700">Categories At Expert</div>
                    <div className="mt-2 text-3xl font-bold text-green-900">{learningBalanceExpertCount} of 6</div>
                  </div>
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                    <div className="text-xs font-medium uppercase tracking-wide text-amber-700">Recommendation</div>
                    <div className="mt-2 text-sm font-medium leading-6 text-amber-900">{learningBalanceRecommendation}</div>
                  </div>
                </div>

                {learningBalanceCategories.length === 0 ? (
                  <ChartEmpty message="No learning balance data returned yet." />
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-gray-200">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-50">
                        <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                          <th className="px-4 py-3 font-semibold">Category</th>
                          <th className="px-4 py-3 font-semibold">Band</th>
                          <th className="px-4 py-3 font-semibold">Verified</th>
                          <th className="px-4 py-3 font-semibold">Drift</th>
                          <th className="px-4 py-3 font-semibold">Auto-approve</th>
                          {showLearningBalanceCeiling && (
                            <th className="px-4 py-3 font-semibold">Ceiling</th>
                          )}
                          <th className="px-4 py-3 font-semibold">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 bg-white">
                        {learningBalanceCategories.map((item) => (
                          <tr key={item.category} data-testid="learning-balance-category-row">
                            <td className="px-4 py-3 font-medium text-gray-900">{item.category}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${bandBadgeClass(item.epistemic_band)}`}>
                                {item.epistemic_band}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-700">{Math.round(item.verified_count ?? 0)}</td>
                            <td className="px-4 py-3 text-gray-700">{formatDecimal(item.centroid_drift)}</td>
                            <td className="px-4 py-3 text-gray-700">{formatPercent(item.auto_approve_rate)}</td>
                            {showLearningBalanceCeiling && (
                              <td className="px-4 py-3 text-gray-700">{formatPercent(item.ceiling_estimate)}</td>
                            )}
                            <td className="px-4 py-3">
                              <div className="flex flex-col gap-1">
                                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${statusBadgeClass(item.status)}`}>
                                  {item.status}
                                </span>
                                {item.status === 'at_ceiling' && (
                                  <button
                                    type="button"
                                    onClick={() => window.dispatchEvent(new CustomEvent('vis2:navigate', { detail: { tab: 'evolution' } }))}
                                    className="inline-flex items-center gap-1 rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-100"
                                    style={{ fontSize: '0.72rem' }}
                                  >
                                    Improve →
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 3. GAE Compounding Evidence — REAL DATA ────────────────────────── */}
      <div className="bg-slate-900 rounded-lg border border-purple-500 shadow-2xl p-6">

        {/* Panel header + single Refresh button */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              The Compounding Curve
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-500/20 text-green-400 border border-green-500/40">
                ● LIVE
              </span>
            </h3>
            <p className="text-sm text-gray-400 mt-0.5">Real data from GAE weight matrix — process alerts in Tab 3 to populate</p>
          </div>
          <button
            onClick={loadGAECharts}
            disabled={gaeChartsLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-purple-900/50 hover:bg-purple-800/60 text-purple-300 rounded-lg text-sm font-medium transition-colors border border-purple-600 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${gaeChartsLoading ? 'animate-spin' : ''}`} />
            {gaeChartsLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {/* ── Section A: Centroid Learning Magnitude ───────────────────────── */}
        <div className="mb-6">
          <p className="text-xs font-semibold text-purple-300 uppercase tracking-wide mb-1">A · Centroid Learning Magnitude</p>
          <p className="text-xs text-gray-500 mb-3">
            How far the ProfileScorer centroid moved per verified decision \u2014 green = reinforced, orange = corrected. Rolling 5-decision average shown as line.
          </p>
          <div className="bg-white rounded-md p-3">
            {centroidEvolution.length === 0 ? (
              <ChartEmpty message="Process alerts and provide outcome feedback to see centroid learning magnitude" />
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <ComposedChart
                  data={(() => {
                    const evol = centroidEvolution
                    const win = 5
                    return evol.map((e, i) => {
                      const slice = evol.slice(Math.max(0, i - win + 1), i + 1)
                      const avg = slice.reduce((s, x) => s + x.centroid_delta_norm, 0) / slice.length
                      return {
                        decision: e.decision_number,
                        drift_reinforced: e.correct ? e.centroid_delta_norm : undefined,
                        drift_corrected: !e.correct ? e.centroid_delta_norm : undefined,
                        rolling_avg: avg,
                      }
                    })
                  })()}
                  margin={{ top: 5, right: 10, left: -10, bottom: 18 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="decision" tick={{ fontSize: 10 }} label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => v.toFixed(3)} />
                  <Tooltip
                    formatter={(v: any, name: string) => [
                      Number(v).toFixed(5),
                      name === 'drift_reinforced' ? '\u2016\u0394\u03bc\u2016 reinforced' : name === 'drift_corrected' ? '\u2016\u0394\u03bc\u2016 corrected' : 'rolling avg',
                    ]}
                    labelFormatter={(label) => `Decision #${label}`}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 10 }}
                    formatter={(v: string) =>
                      v === 'drift_reinforced' ? '\u2016\u0394\u03bc\u2016 reinforced'
                      : v === 'drift_corrected' ? '\u2016\u0394\u03bc\u2016 corrected'
                      : 'rolling avg (5)'
                    }
                  />
                  <Bar dataKey="drift_reinforced" fill="#10b981" name="drift_reinforced" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="drift_corrected"  fill="#f97316" name="drift_corrected"  radius={[2, 2, 0, 0]} />
                  <Line type="monotone" dataKey="rolling_avg" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="rolling_avg" />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ── Section B: Confidence Trajectory ───────────────────────────── */}
        <div className="mb-6">
          <p className="text-xs font-semibold text-blue-300 uppercase tracking-wide mb-1">B · Confidence Trajectory</p>
          <p className="text-xs text-gray-500 mb-3">
            Agent confidence per recommended action over time — ascending trend = the W matrix is compounding
          </p>
          <div className="bg-white rounded-md p-3">
            {gaeConfChartData.length === 0 ? (
              <ChartEmpty message={gaeConfTraj?.message ?? 'Process alerts and provide feedback to see confidence trajectory'} />
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={gaeConfChartData} margin={{ top: 5, right: 10, left: -10, bottom: 18 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="decision" tick={{ fontSize: 10 }} label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }} />
                  <YAxis domain={[0, 1.0]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {gaeConfActions.map((action, idx) => (
                    <Line key={action} type="monotone" dataKey={action} stroke={pickColor(action, idx)} strokeWidth={2} dot={{ r: 3 }} name={action.replace(/_/g, ' ')} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ── Section C: Before / After ───────────────────────────────────── */}
        <div className="mb-6">
          <p className="text-xs font-semibold text-green-300 uppercase tracking-wide mb-1">C · Before / After</p>
          <p className="text-xs text-gray-500 mb-3">First vs. latest decision confidence from the live W matrix</p>

          {!gaeBeforeAfter || !gaeBeforeAfter.ready ? (
            <div className="bg-slate-800 rounded-md p-4 text-center text-gray-400 italic text-sm">
              {gaeBeforeAfter?.message ?? 'Need at least 2 decisions for before/after comparison'}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="bg-slate-800 rounded-lg border border-gray-600 p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">First Decision</div>
                  <div className="text-3xl font-bold text-gray-300 mb-1">
                    {Math.round((gaeBeforeAfter.first_decision!.confidence) * 100)}%
                  </div>
                  <div className="text-xs text-gray-500">Confidence</div>
                  <div className="mt-2 text-xs text-gray-400">Decision #{gaeBeforeAfter.first_decision!.decision_number}</div>
                  <div className="mt-1 text-xs text-gray-500 italic">{gaeBeforeAfter.first_decision!.action.replace(/_/g, ' ')}</div>
                </div>
                <div className="bg-slate-800 rounded-lg border border-green-500 p-4">
                  <div className="text-xs text-green-400 uppercase tracking-wide mb-2">Latest Decision</div>
                  <div className="text-3xl font-bold text-green-300 mb-1">
                    {Math.round((gaeBeforeAfter.latest_decision!.confidence) * 100)}%
                  </div>
                  <div className="text-xs text-gray-500">Confidence</div>
                  <div className="mt-2 text-xs text-gray-400">Decision #{gaeBeforeAfter.latest_decision!.decision_number}</div>
                  <div className="mt-1 text-xs text-gray-500 italic">{gaeBeforeAfter.latest_decision!.action.replace(/_/g, ' ')}</div>
                </div>
              </div>
              <div className={`rounded-lg px-4 py-3 text-center border ${(gaeBeforeAfter.improvement_pp ?? 0) >= 0 ? 'bg-green-900/30 border-green-500/50' : 'bg-red-900/30 border-red-500/50'}`}>
                <span className={`font-bold text-lg ${(gaeBeforeAfter.improvement_pp ?? 0) >= 0 ? 'text-green-300' : 'text-red-300'}`}>
                  {(gaeBeforeAfter.improvement_pp ?? 0) >= 0 ? '+' : ''}{gaeBeforeAfter.improvement_pp} pp
                </span>
                <span className="text-gray-400 text-sm ml-2">
                  Confidence {(gaeBeforeAfter.improvement_pp ?? 0) >= 0 ? 'improved' : 'changed'} {Math.abs(gaeBeforeAfter.improvement_pp ?? 0)} percentage points across {gaeBeforeAfter.total_decisions} decisions
                </span>
              </div>
            </>
          )}
        </div>

        {/* ── Section D: Trust Curve ──────────────────────────────────────── */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold text-red-300 uppercase tracking-wide">D · Trust Curve</p>
            <span className="text-xs text-gray-500">earns slowly (+3% correct) · loses fast (−60% incorrect) · 20:1</span>
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Simulated trust per action from live outcome history — below 30% triggers human review
          </p>

          <div className="bg-white rounded-md p-3 mb-3">
            {gaeTrustChartData.length === 0 ? (
              <ChartEmpty message={gaeTrustCurve?.message ?? 'Process alerts and provide feedback to see trust curve'} />
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={gaeTrustChartData} margin={{ top: 5, right: 10, left: -10, bottom: 18 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="decision" tick={{ fontSize: 10 }} label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }} />
                  <YAxis domain={[0, 1.0]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v: any) => `${(Number(v) * 100).toFixed(0)}%`} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  <ReferenceLine
                    y={gaeTrustCurve?.review_threshold ?? 0.3}
                    stroke="#ef4444" strokeDasharray="4 4"
                    label={{ value: 'Review threshold (30%)', fill: '#ef4444', fontSize: 9, position: 'insideTopRight' }}
                  />
                  {gaeTrustActions.map((action, idx) => (
                    <Line key={action} type="monotone" dataKey={action} stroke={pickColor(action, idx)} strokeWidth={2} dot={{ r: 3 }} name={action.replace(/_/g, ' ')} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Trust status badges */}
          {Object.keys(gaeTrustStatus).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Current Trust Status</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(gaeTrustStatus).map(([action, s]) => (
                  <div key={action} className={`rounded-lg border p-3 flex items-center justify-between ${s.humanReview ? 'bg-red-900/20 border-red-500/50' : 'bg-green-900/20 border-green-500/50'}`}>
                    <div>
                      <div className="text-xs text-gray-400 italic mb-0.5">{action.replace(/_/g, ' ')}</div>
                      <div className={`text-2xl font-bold ${s.humanReview ? 'text-red-300' : 'text-green-300'}`}>
                        {Math.round(s.trust * 100)}%
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-1 rounded ${s.humanReview ? 'bg-amber-600 text-white' : 'bg-green-500 text-white'}`}>
                      {s.humanReview ? `Learning \u2014 ${vis2DecisionCount} decisions recorded` : 'TRUSTED'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Three-Channel Error Budget (FW-10) ──────────────────────────── */}
      <ThreeChannelPanel />

      {/* ── 4. GAE Weight Convergence ───────────────────────────────────────── */}
      <div className="bg-slate-900 rounded-lg border border-blue-500/50 shadow-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span className="text-blue-400 text-lg">⚡</span>
              GAE Weight Convergence
            </h3>
            <p className="text-sm text-blue-300 font-medium mt-0.5">Hebbian learning — W updated via Eq. 4b with 20:1 asymmetry</p>
            <p className="text-xs text-gray-400 mt-0.5">stability = std(‖W‖_F last 10 updates) · accuracy = correct% last 20</p>
          </div>
          <button
            onClick={loadConvergenceData}
            disabled={convergenceLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-blue-900/30 hover:bg-blue-800/40 text-blue-300 rounded-lg text-sm font-medium transition-colors border border-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${convergenceLoading ? 'animate-spin' : ''}`} />
            {convergenceLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {convergenceData?.message ? (
          <div className="py-6 text-center text-gray-400 italic text-sm">{convergenceData.message}</div>
        ) : convergenceData ? (
          <>
            <div className="flex items-center gap-3 mb-5">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold ${convergenceData.converged ? 'bg-green-500/20 text-green-300 border border-green-500/50' : 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/50'}`}>
                {convergenceData.converged ? '✓ CONVERGED' : '⟳ LEARNING'}
              </span>
              <span className="text-xs text-gray-400">
                {convergenceData.decisions} weight update{convergenceData.decisions !== 1 ? 's' : ''} completed
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              {[
                { label: 'Weight Norm', value: convergenceData.weight_norm.toFixed(2), sub: '‖W‖_F', color: 'text-blue-300' },
                { label: 'Stability', value: convergenceData.stability.toFixed(4), sub: 'threshold < 0.05', color: convergenceData.stability < 0.05 ? 'text-green-300' : 'text-yellow-300' },
                { label: 'Accuracy', value: `${Math.round(convergenceData.accuracy * 100)}%`, sub: 'last 20 decisions', color: convergenceData.accuracy > 0.80 ? 'text-green-300' : 'text-red-300' },
                { label: 'Decisions', value: String(convergenceData.decisions), sub: 'total updates', color: 'text-purple-300' },
              ].map(({ label, value, sub, color }) => (
                <div key={label} className="bg-slate-800 rounded-lg p-3 text-center border border-slate-700">
                  <div className="text-xs text-gray-400 mb-1 uppercase tracking-wide">{label}</div>
                  <div className={`text-2xl font-bold ${color}`}>{value}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{sub}</div>
                </div>
              ))}
            </div>

            {/* Weight snapshots sparkline */}
            {ensureArray<number>(convergenceData.weight_snapshots).length > 1 && (
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-2">‖W‖_F last {ensureArray<number>(convergenceData.weight_snapshots).length} updates</p>
                <ResponsiveContainer width="100%" height={60}>
                  <LineChart data={ensureArray<number>(convergenceData.weight_snapshots).map((v, i) => ({ i: i + 1, norm: v }))} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
                    <Line type="monotone" dataKey="norm" stroke="#60a5fa" strokeWidth={1.5} dot={false} />
                    <Tooltip formatter={(v: any) => Number(v).toFixed(4)} labelFormatter={(l) => `Update ${l}`} />
                    <YAxis domain={['dataMin - 0.05', 'dataMax + 0.05']} hide />
                    <XAxis dataKey="i" hide />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="bg-slate-800/50 rounded-lg px-4 py-3 text-xs text-gray-400 border border-slate-700">
              <span className="text-gray-300 font-medium">Convergence criterion: </span>
              stability &lt; 0.05 AND accuracy &gt; 80% →{' '}
              {convergenceData.converged
                ? <span className="text-green-300 font-medium">both met — W has stabilised</span>
                : <span className="text-yellow-300 font-medium">not yet met — continue processing alerts</span>
              }
            </div>
          </>
        ) : (
          <div className="py-6 text-center text-gray-500 text-sm">Loading convergence metrics...</div>
        )}
      </div>

      {/* ── 5. Evidence Ledger ──────────────────────────────────────────────── */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div>
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600" />
              Evidence Ledger
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">Tamper-evident decision audit trail</p>
          </div>
          <div className="flex items-center gap-3 flex-wrap justify-end">
            {auditVerification && (
              auditVerification.verified
                ? <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-green-100 text-green-700 border border-green-300"><CheckCircle className="w-4 h-4" />Chain verified ✓</span>
                : <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-red-100 text-red-700 border border-red-300">Chain broken ✗{auditVerification.broken_at_index !== undefined && <span className="font-normal">(at #{auditVerification.broken_at_index})</span>}</span>
            )}
            <a href="/api/audit/decisions?format=csv" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-semibold transition-colors border border-gray-200">
              <Download className="w-4 h-4" />Download CSV
            </a>
            <button onClick={loadAuditData} disabled={auditLoading} className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm font-semibold transition-colors border border-blue-200 disabled:opacity-50">
              <RefreshCw className={`w-4 h-4 ${auditLoading ? 'animate-spin' : ''}`} />
              {auditLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {auditDecisions.length === 0 ? (
          <div className="py-8 text-center text-gray-400 italic text-sm">No decisions recorded yet — run a triage in Tab 3 to populate.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  {['Timestamp', 'Alert', 'Action', 'Outcome', 'Hash'].map(h => (
                    <th key={h} className="pb-2 text-left font-semibold text-gray-600 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditDecisions.map(d => (
                  <tr key={d.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-2.5 pr-4 text-gray-500 text-xs tabular-nums">{d.timestamp.split('T')[1]?.slice(0, 8) ?? d.timestamp}</td>
                    <td className="py-2.5 pr-4"><span className="font-mono text-xs text-blue-700 font-semibold">{d.alert_id}</span></td>
                    <td className="py-2.5 pr-4"><span className="text-xs text-gray-700">{d.action_taken.replace(/_/g, ' ')}</span></td>
                    <td className="py-2.5 pr-4">
                      {d.outcome
                        ? <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${d.outcome === 'correct' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{d.outcome}</span>
                        : <span className="text-xs text-gray-400 italic">pending</span>}
                    </td>
                    <td className="py-2.5"><span className="font-mono text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{d.hash ? `${d.hash.slice(0, 8)}...` : '—'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {auditVerification && auditVerification.chain_length > 0 && (
              <div className="mt-3 text-xs text-gray-400 text-right">
                {auditVerification.chain_length} record{auditVerification.chain_length !== 1 ? 's' : ''} in chain
                {auditVerification.first_record && <span> · from {auditVerification.first_record.split('T')[1]?.slice(0, 8)}</span>}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 5b. Evidence Room — FEATURE-09 ─────────────────────────────────── */}
      <div className="bg-slate-900 rounded-lg border border-cyan-500/50 shadow-2xl p-6">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-cyan-300" />
              Evidence Room
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                product evidence
              </span>
            </h3>
            <p className="text-sm text-gray-400 mt-0.5">Audit, conservation, override, and hash-chain evidence for governance review.</p>
          </div>
          <button
            onClick={loadEvidenceRoom}
            disabled={evidenceRoomLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-cyan-900/40 hover:bg-cyan-800/50 text-cyan-300 rounded-lg text-sm font-medium transition-colors border border-cyan-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${evidenceRoomLoading ? 'animate-spin' : ''}`} />
            {evidenceRoomLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {evidenceRoomError ? (
          <div className="rounded-lg border border-red-500/50 bg-red-900/20 px-4 py-6 text-center text-sm font-semibold text-red-200">
            Evidence Room unavailable
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-bold text-white">Decision Audit Trail</h4>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{evidenceRoom?.audit_trail.total ?? 0} total</span>
                  <ProvenanceBadge source="real_measured" />
                </div>
              </div>
              {evidenceEntries.length === 0 ? (
                <div className="py-8 text-center text-gray-400 italic text-sm">No decisions recorded yet</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wide text-gray-400">
                        {['ID', 'Action', 'Category', 'Confidence', 'Outcome'].map(header => (
                          <th key={header} className="pb-2 pr-3 font-semibold">{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700">
                      {evidenceEntries.map((entry, idx) => (
                        <tr key={entry.decision_id_full ?? `${entry.decision_id}-${idx}`} className="text-gray-300">
                          <td className="py-2.5 pr-3 font-mono text-xs text-cyan-300">{(entry.decision_id || '').slice(0, 12)}</td>
                          <td className="py-2.5 pr-3 text-xs">{entry.action.replace(/_/g, ' ') || 'unknown'}</td>
                          <td className="py-2.5 pr-3 text-xs">{entry.category.replace(/_/g, ' ') || 'unknown'}</td>
                          <td className="py-2.5 pr-3 text-xs">{Math.round((entry.confidence ?? 0) * 100)}%</td>
                          <td className="py-2.5 pr-3">
                            <span className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${entry.outcome === 'correct' ? 'bg-green-500/20 text-green-300' : entry.outcome ? 'bg-red-500/20 text-red-300' : 'bg-slate-700 text-gray-300'}`}>
                              {entry.outcome ?? 'pending'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-bold text-white">Conservation Compliance</h4>
                <div className="flex items-center gap-2">
                  <ProvenanceBadge source="real_measured" />
                  <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${conservationBadgeClass(evidenceStatus)}`}>
                    {evidenceStatus}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-3">
                  <div className="text-xs text-gray-400">α·q·V</div>
                  <div className="mt-1 text-2xl font-bold text-cyan-300">{evidenceProduct.toFixed(4)}</div>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-3">
                  <div className="text-xs text-gray-400">θ_min</div>
                  <div className="mt-1 text-2xl font-bold text-purple-300">{evidenceThreshold.toFixed(4)}</div>
                </div>
              </div>
              <div className={`rounded-lg border px-4 py-3 text-sm font-semibold ${evidenceConservationVerified ? 'border-green-500/50 bg-green-900/20 text-green-300' : 'border-amber-500/50 bg-amber-900/20 text-amber-300'}`}>
                {evidenceConservationVerified ? 'Conservation law verified' : 'Learning paused — below threshold'}
              </div>
              {evidenceRoom?.conservation.frozen && (
                <span className="mt-3 inline-flex rounded-full border border-red-500/50 bg-red-500/20 px-2.5 py-1 text-xs font-bold text-red-300">
                  frozen
                </span>
              )}
            </div>

            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <h4 className="text-sm font-bold text-white mb-3">Override Analysis</h4>
              <div className="grid grid-cols-3 gap-3 mb-4">
                {[
                  { label: 'Total Decisions', value: evidenceTotal },
                  { label: 'Confirmations', value: evidenceConfirmations },
                  { label: 'Overrides', value: evidenceOverrides },
                ].map(item => (
                  <div key={item.label} className="rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-center">
                    <div className="text-2xl font-bold text-white">{item.value}</div>
                    <div className="mt-1 text-xs text-gray-400">{item.label}</div>
                  </div>
                ))}
              </div>
              <div className="mb-2 flex items-center justify-between text-xs text-gray-400">
                <span>Confirmation vs override ratio</span>
                <span>{liveOverrideRatePct}% override rate</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-700">
                <div className="flex h-full">
                  <div className="bg-green-400" style={{ width: `${evidenceConfirmationPct}%` }} />
                  <div className="bg-amber-400" style={{ width: `${evidenceOverridePct}%` }} />
                </div>
              </div>
            </div>

            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-bold text-white">Evidence Export Pack</h4>
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${evidenceRoom?.hash_chain.status === 'VERIFIED' ? 'border-green-500/50 bg-green-500/20 text-green-300' : 'border-red-500/50 bg-red-500/20 text-red-300'}`}>
                  {evidenceRoom?.hash_chain.status === 'VERIFIED' ? 'Hash chain: VERIFIED ✓' : 'Hash chain: NEEDS REVIEW ⚠'}
                </span>
              </div>
              <p className="mb-4 text-sm text-gray-400">
                Export the full JSON evidence pack for product governance review, including full decision IDs and chain indexes.
              </p>
              <button
                onClick={handleEvidenceExport}
                disabled={evidenceExporting}
                className="inline-flex items-center gap-2 rounded-lg border border-cyan-600 bg-cyan-900/40 px-4 py-2 text-sm font-semibold text-cyan-200 transition-colors hover:bg-cyan-800/50 disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                {evidenceExporting ? 'Preparing...' : 'Download Evidence Pack'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── 5c. Decision Economics (Live) — H7-FIX-4 ───────────────────────── */}
      {decisionEconomics && (
        <div className="bg-white rounded-lg border shadow p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Calculator className="w-5 h-5 text-purple-600" />
            Decision Economics
            <span className="text-xs font-normal text-gray-500 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">live</span>
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded border border-gray-200 p-4 text-center">
              <div className="text-2xl font-bold text-gray-900">{decisionEconomics.decisions_made}</div>
              <div className="text-xs text-gray-500 mt-1">decisions made</div>
            </div>
            <div className="bg-green-50 rounded border border-green-200 p-4 text-center">
              <div className="text-2xl font-bold text-green-700">{(decisionEconomics.correct_rate * 100).toFixed(1)}%</div>
              <div className="text-xs text-gray-500 mt-1">correct rate</div>
            </div>
            <div className="bg-red-50 rounded border border-red-200 p-4 text-center">
              <div className="text-2xl font-bold text-red-600">{(decisionEconomics.false_positive_rate * 100).toFixed(1)}%</div>
              <div className="text-xs text-gray-500 mt-1">false positive rate</div>
            </div>
            <div className="bg-blue-50 rounded border border-blue-200 p-4 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {decisionEconomics.time_saved_hours.toFixed(1)}h
                {decisionEconomics.time_saved_estimated && (
                  <span className="text-xs font-normal text-gray-500 ml-1">(estimated)</span>
                )}
              </div>
              <div className="text-xs text-gray-500 mt-1">time saved</div>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-3 italic">{decisionEconomics.note}</p>
          <SwitchingCostChart trajectory={decisionEconomics.switching_cost_trajectory} />
        </div>
      )}

      {/* ── 5c. Operational Metrics + Board Export — F4-OVERLAY ─────────────── */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-600" />
            Operational Metrics
            <span className="text-xs font-normal text-gray-500 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">live</span>
          </h3>
          <button
            onClick={handleBoardExport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export for Board
          </button>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {/* MTTD */}
          <div className="bg-blue-50 rounded border border-blue-200 p-4 text-center">
            <div className="text-xs text-gray-500 mb-1 font-medium">MTTD</div>
            <div className="text-2xl font-bold text-blue-700">
              {operationalMetrics?.mttd.value_minutes !== null && operationalMetrics?.mttd.value_minutes !== undefined
                ? `${operationalMetrics.mttd.value_minutes}min`
                : '—'}
            </div>
            <div className="text-xs text-gray-400 mt-1">Mean Time to Detect</div>
            {operationalMetrics?.mttd.estimated && (
              <span className="inline-block mt-1.5 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs border border-yellow-200">
                estimated
              </span>
            )}
          </div>
          {/* MTTR */}
          <div className="bg-purple-50 rounded border border-purple-200 p-4 text-center">
            <div className="text-xs text-gray-500 mb-1 font-medium">MTTR</div>
            <div className="text-2xl font-bold text-purple-700">
              {operationalMetrics?.mttr.value_minutes !== null && operationalMetrics?.mttr.value_minutes !== undefined
                ? `${operationalMetrics.mttr.value_minutes}min`
                : '—'}
            </div>
            <div className="text-xs text-gray-400 mt-1">Mean Time to Respond</div>
            {operationalMetrics?.mttr.estimated && (
              <span className="inline-block mt-1.5 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs border border-yellow-200">
                estimated
              </span>
            )}
          </div>
          {/* FP Rate */}
          <div className="bg-red-50 rounded border border-red-200 p-4 text-center">
            <div className="text-xs text-gray-500 mb-1 font-medium">FP Rate</div>
            <div className="text-2xl font-bold text-red-600">
              {operationalMetrics?.fp_rate.rate !== null && operationalMetrics?.fp_rate.rate !== undefined
                ? `${(operationalMetrics.fp_rate.rate * 100).toFixed(1)}%`
                : '—'}
            </div>
            <div className="text-xs text-gray-400 mt-1">False Positive Rate</div>
            {operationalMetrics?.fp_rate.estimated && (
              <span className="inline-block mt-1.5 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs border border-yellow-200">
                estimated
              </span>
            )}
          </div>
        </div>
        {!operationalMetrics && (
          <p className="text-xs text-gray-400 mt-3 italic text-center">Loading operational metrics…</p>
        )}
      </div>

      {/* ── 5d. Economics Summary — ECON-1 ──────────────────────────────────── */}
      <div className="bg-white rounded-lg border shadow p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-green-600" />
          Economics Summary
          {economicsData && (
            <span className="text-xs font-normal text-gray-500 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">
              {economicsData.source === 'graph' ? 'live data' : economicsData.source}
            </span>
          )}
        </h3>

        {economicsData && economicsData.decisions.total === 0 ? (
          <p className="text-sm text-gray-500 italic text-center py-4">
            No decisions recorded yet. Process alerts in Tab 3 to generate economics data.
          </p>
        ) : economicsData ? (
          <>
            {/* ROW 1 — three headline numbers */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="bg-green-50 rounded border border-green-200 p-4 text-center">
                <div className="text-xs text-gray-500 mb-1 font-medium">Total Value Generated</div>
                <div className="text-2xl font-bold text-green-700">
                  {formatUSD(economicsData.economics.total_value_usd)}
                </div>
                {economicsData.economics.estimated && (
                  <span className="text-xs text-gray-400">(estimated)</span>
                )}
              </div>
              <div className="bg-blue-50 rounded border border-blue-200 p-4 text-center">
                <div className="text-xs text-gray-500 mb-1 font-medium">Analyst Time Saved</div>
                <div className="text-2xl font-bold text-blue-700">
                  {economicsData.economics.time_saved_hours.toFixed(1)} hrs
                </div>
                {economicsData.economics.estimated && (
                  <span className="text-xs text-gray-400">(estimated)</span>
                )}
              </div>
              <div className="bg-purple-50 rounded border border-purple-200 p-4 text-center">
                <div className="text-xs text-gray-500 mb-1 font-medium">Risk Reduction</div>
                <div className="text-2xl font-bold text-purple-700">
                  {formatUSD(economicsData.economics.risk_reduction_usd)}
                </div>
                {economicsData.economics.estimated && (
                  <span className="text-xs text-gray-400">(estimated)</span>
                )}
              </div>
            </div>

            {/* ROW 2 — decision breakdown */}
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-4">
              <div className="bg-gray-50 rounded border border-gray-200 p-3 text-center">
                <div className="text-xl font-bold text-gray-900">{economicsData.decisions.total}</div>
                <div className="text-xs text-gray-500 mt-0.5">Total</div>
              </div>
              <div className="bg-green-50 rounded border border-green-200 p-3 text-center">
                <div className="text-xl font-bold text-green-700">
                  {(economicsData.decisions.correct_rate * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Correct</div>
              </div>
              <div className="bg-red-50 rounded border border-red-200 p-3 text-center">
                <div className="text-xl font-bold text-red-600">
                  {economicsData.decisions.by_action['escalate'] ?? 0}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Escalate</div>
              </div>
              <div className="bg-emerald-50 rounded border border-emerald-200 p-3 text-center">
                <div className="text-xl font-bold text-emerald-700">
                  {economicsData.decisions.by_action['suppress'] ?? 0}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Suppress</div>
              </div>
              <div className="bg-blue-50 rounded border border-blue-200 p-3 text-center">
                <div className="text-xl font-bold text-blue-700">
                  {economicsData.decisions.by_action['investigate'] ?? 0}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Investigate</div>
              </div>
              <div className="bg-yellow-50 rounded border border-yellow-200 p-3 text-center">
                <div className="text-xl font-bold text-yellow-700">
                  {economicsData.decisions.by_action['monitor'] ?? 0}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Monitor</div>
              </div>
            </div>

            {/* ROW 3 — population context */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <div className="bg-gray-50 rounded border border-gray-200 p-3 text-center">
                <div className="text-xl font-bold text-gray-900">{economicsData.population.total_users}</div>
                <div className="text-xs text-gray-500 mt-0.5">Total Users</div>
              </div>
              <div className="bg-orange-50 rounded border border-orange-200 p-3 text-center">
                <div className="text-xl font-bold text-orange-700">{economicsData.population.privileged_users}</div>
                <div className="text-xs text-gray-500 mt-0.5">Privileged Users</div>
              </div>
              <div className="bg-yellow-50 rounded border border-yellow-200 p-3 text-center">
                <div className="text-xl font-bold text-yellow-700">{economicsData.population.elevated_users}</div>
                <div className="text-xs text-gray-500 mt-0.5">Elevated Users</div>
              </div>
            </div>

            <p className="text-xs text-gray-400 italic">{economicsData.economics.note}</p>
          </>
        ) : (
          <p className="text-xs text-gray-400 italic text-center py-4">Loading economics data…</p>
        )}
      </div>

      {/* ── 6. Weekly Trend + Three-Loop Architecture ───────────────────────── */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border shadow p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Weekly Trend</h3>
          {ensureArray<WeeklyMetric>(weekly_trend).length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={ensureArray<WeeklyMetric>(weekly_trend)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" label={{ value: 'Week', position: 'insideBottom', offset: -5 }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="auto_close_rate" stroke="#8b5cf6" strokeWidth={2} name="Auto-Close %" />
                  <Line type="monotone" dataKey="mttr_minutes"    stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" name="MTTR (min)" />
                  <Line type="monotone" dataKey="fp_rate"         stroke="#ef4444" strokeWidth={2} strokeDasharray="3 3" name="FP Rate %" />
                </LineChart>
              </ResponsiveContainer>
              <div className="mt-4 grid grid-cols-4 gap-2 text-center text-sm">
                {ensureArray<WeeklyMetric>(weekly_trend).map(w => (
                  <div key={w.week} className="bg-gray-50 rounded p-2">
                    <div className="font-semibold text-gray-900">Week {w.week}</div>
                    <div className="text-xs text-gray-600">{w.pattern_count} patterns</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="py-10 text-center">
              <p className="text-sm text-amber-600 italic">
                {data.weekly_trend_note ?? 'Trend data will appear as decisions are recorded'}
              </p>
            </div>
          )}
        </div>

        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-lg border-2 border-purple-500 shadow-2xl p-5">
          <h3 className="text-xl font-bold text-white mb-1 text-center">Three-Loop Architecture</h3>
          <p className="text-xs text-gray-400 text-center mb-4">Three cross-layer loops. One living graph. Intelligence that compounds automatically.</p>

          <div className="flex items-stretch gap-1.5 mb-1">
            <div className="flex-1 bg-blue-900/40 rounded border-2 border-blue-500 p-2.5">
              <div className="text-xs font-bold text-blue-300 uppercase tracking-wide mb-0.5">Loop 1</div>
              <div className="text-sm font-semibold text-blue-200 mb-0.5">Situation Analyzer</div>
              <div className="text-xs text-blue-300/60 italic mb-1.5">Smarter within each decision</div>
              {['Classifies situations', 'Evaluates options', 'Reasons over context'].map(t => (
                <div key={t} className="flex items-start gap-1 mb-0.5"><div className="w-1 h-1 bg-blue-400 rounded-full mt-1.5 shrink-0" /><span className="text-xs text-gray-300">{t}</span></div>
              ))}
              <div className="mt-1.5 pt-1.5 border-t border-blue-800 text-xs text-blue-400">Demo: Tab 3 →</div>
            </div>
            <div className="flex items-center text-gray-500 text-sm font-bold shrink-0">→</div>
            <div className="flex items-center justify-center w-28 shrink-0">
              <div className="bg-gradient-to-br from-purple-700 to-blue-700 rounded-lg p-3 border-2 border-yellow-400 shadow-xl animate-pulse text-center w-full">
                <Database className="w-5 h-5 text-white mx-auto mb-1" />
                <div className="text-xs font-bold text-white leading-tight">Living Context</div>
                <div className="text-xs font-bold text-white leading-tight">Graph</div>
                <div className="text-xs text-gray-300 mt-1">(AGE)</div>
              </div>
            </div>
            <div className="flex items-center text-gray-500 text-sm font-bold shrink-0">←</div>
            <div className="flex-1 bg-purple-900/40 rounded border-2 border-purple-500 p-2.5">
              <div className="text-xs font-bold text-purple-300 uppercase tracking-wide mb-0.5">Loop 2</div>
              <div className="text-sm font-semibold text-purple-200 mb-0.5">ProfileScorer + AgentEvolver</div>
              <div className="text-xs text-purple-300/60 italic mb-1.5">Smarter across decisions</div>
              {['ProfileScorer: centroid drift tracks category mastery', 'AgentEvolver: promotes high-performing variants'].map(t => (
                <div key={t} className="flex items-start gap-1 mb-0.5"><div className="w-1 h-1 bg-purple-400 rounded-full mt-1.5 shrink-0" /><span className="text-xs text-gray-300">{t}</span></div>
              ))}
              <div className="mt-1.5 pt-1.5 border-t border-purple-800 text-xs text-purple-400">Demo: Tab 2 →</div>
            </div>
          </div>

          <div className="flex justify-center"><div className="text-amber-500/50 text-sm leading-none">↑</div></div>
          <div className="flex justify-center mb-3">
            <div className="bg-amber-900/40 rounded border-2 border-amber-500 p-2.5 w-3/5 text-center">
              <div className="text-xs font-bold text-amber-300 uppercase tracking-wide mb-0.5">Loop 3</div>
              <div className="text-sm font-semibold text-amber-200 mb-0.5">RL Reward / Penalty</div>
              <div className="text-xs text-amber-300/60 italic mb-1.5">Governs both loops</div>
              <div className="flex justify-center gap-2 flex-wrap">
                {['+0.3 reward', '−6.0 penalty', '20:1 ratio'].map((t, i) => (
                  <span key={i} className="text-xs text-gray-300">{t}</span>
                ))}
              </div>
              <div className="mt-1.5 pt-1.5 border-t border-amber-800 text-xs text-amber-400">Demo: Tab 2 →</div>
            </div>
          </div>

          <div className="text-center mb-4">
            <div className="inline-block bg-gradient-to-r from-blue-700 via-purple-700 to-amber-700 rounded-lg px-4 py-2 border border-yellow-400/60">
              <div className="text-xs font-bold text-white">ALL THREE WRITE BACK → TRIGGERED_EVOLUTION</div>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-700">
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Situation Types', val: '2 → 6', color: 'border-blue-500/30 text-blue-400' },
                { label: 'Prompt Variants Evolved', val: '0 → 4', color: 'border-purple-500/30 text-purple-400' },
                { label: 'Cross-Alert Patterns', val: 'Travel: 47 | Phish: 31', color: 'border-green-500/30 text-green-400 text-sm' },
                { label: 'Asymmetric Ratio', val: '20:1 penalty', color: 'border-amber-500/30 text-amber-400' },
              ].map(({ label, val, color }) => (
                <div key={label} className={`bg-slate-800/50 rounded p-2 border text-center ${color}`}>
                  <div className="text-xs text-gray-400 mb-0.5">{label}</div>
                  <div className={`font-bold ${color.includes('text-sm') ? 'text-sm' : 'text-base'}`}>{val}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 text-center">
            <p className="text-xs italic text-gray-400">
              💡 "SIEMs get better rules. Our copilot <span className="text-purple-400 font-semibold">becomes</span> a better copilot."
            </p>
          </div>
        </div>
      </div>

      {/* ── 7. Evolution Events — REAL from AGE (H7-FIX-4) ───────────────── */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-600" />
              Recent Evolution Events
            </h3>
            {evolutionEventsReal && ensureArray<EvolutionEvent>(evolutionEventsReal.events).length > 0 ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 border border-green-200">
                live
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
                awaiting decisions
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReseed}
              disabled={reseeding || resetting}
              className="flex items-center gap-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors disabled:opacity-50 font-semibold"
              title="Delete all AGE data and restore the canonical demo dataset"
            >
              <Database className={`w-4 h-4 ${reseeding ? 'animate-pulse' : ''}`} />
              {reseeding ? 'Re-seeding...' : 'Re-seed Data'}
            </button>
            <button
              onClick={handleReset}
              disabled={resetting || reseeding}
              className="flex items-center gap-2 px-4 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors disabled:opacity-50 font-semibold"
              title="Reset all demo data: alerts, patterns, decisions, and evolution events"
            >
              <RefreshCw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} />
              {resetting ? 'Resetting All...' : 'Reset All Demo Data'}
            </button>
          </div>
        </div>

        {reseedMessage && (
          <div className={`mb-3 px-3 py-2 rounded text-xs font-medium ${reseedMessage.startsWith('Re-seed complete') ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
            {reseedMessage}
          </div>
        )}

        {/* Use real events from dedicated endpoint (H7-FIX-4); fall back to compounding data */}
        {(() => {
          const displayEvents = (ensureArray<EvolutionEvent>(evolutionEventsReal?.events).length) > 0
            ? ensureArray<EvolutionEvent>(evolutionEventsReal!.events)
            : ensureArray<EvolutionEvent>(evolution_events)
          const emptyNote = evolutionEventsReal?.note ?? 'No decisions recorded yet — process alerts in Tab 3'
          return displayEvents.length > 0 ? (
            <div className="space-y-2">
              {displayEvents.map((event, idx) => (
                <div key={event.id || `event-${idx}`} className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200 hover:bg-purple-100 transition-colors">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="text-sm font-mono text-purple-700 font-semibold">{event.id}</div>
                    <div className="text-sm text-gray-600">{formatEventType(event.event_type)}</div>
                    <div className="text-sm font-semibold text-gray-900">{event.description}</div>
                  </div>
                  <div className="text-xs text-gray-500">{formatTimeAgo(event.timestamp)}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic py-4 text-center">{emptyNote}</p>
          )
        })()}
      </div>

      {/* ── 8. The Moat Message ─────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg p-8 text-center">
        <p className="text-2xl font-bold text-white leading-relaxed">
          "When a competitor deploys at a new customer, they start at zero.
          <br />
          We start at <span className="text-yellow-300">{animatedNodesEnd} patterns</span>. That's the moat."
        </p>
      </div>

      {/* ROI Calculator Modal */}
      <ROICalculatorModal isOpen={showROI} onClose={() => setShowROI(false)} />
    </div>
  )
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)
  if (diffHours < 1) return 'Just now'
  if (diffHours === 1) return '1h ago'
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return '1d ago'
  return `${diffDays}d ago`
}

function formatEventType(eventType: string): string {
  return eventType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
