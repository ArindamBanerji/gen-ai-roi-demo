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

import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  getCompoundingMetrics, resetAllDemoData, resetAlerts, reseedDemoData,
  getAuditDecisions, verifyAuditChain, getGAEConvergence,
  getGAEWeightEvolution, getGAEConfidenceTrajectory, getGAETrustCurve, getGAEBeforeAfter,
} from '../../lib/api'
import { domainConfig } from '../../lib/domain'
import {
  TrendingUp, Database, Activity, RefreshCw, Clock, DollarSign,
  TrendingDown, CheckCircle, Calculator, Shield, Download,
} from 'lucide-react'
import ROICalculatorModal from '../ROICalculator'

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
interface CompoundingData {
  period: { start: string; end: string }
  headline: {
    nodes_start: number; nodes_end: number
    auto_close_start: number; auto_close_end: number
    mttr_start: number; mttr_end: number
    fp_investigations_start: number; fp_investigations_end: number
  }
  weekly_trend: WeeklyMetric[]
  evolution_events: EvolutionEvent[]
  business_impact?: BusinessImpact
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

// ============================================================================
// Interfaces — GAE real data
// ============================================================================

interface GAEWeightEvolutionEntry {
  decision_number: number; action: string; outcome: number
  delta_norm: number; W_norm_after: number
}
interface GAEWeightEvolution {
  evolution: GAEWeightEvolutionEntry[]
  message: string | null
}

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

// fallback palette for unknown keys
const FALLBACK_COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']
function pickColor(key: string, idx: number): string {
  return ACTION_COLORS[key] ?? SITUATION_COLORS[key] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length]
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
  const [gaeWeightEvo, setGaeWeightEvo] = useState<GAEWeightEvolution | null>(null)
  const [gaeConfTraj, setGaeConfTraj] = useState<GAEConfidenceTrajectory | null>(null)
  const [gaeTrustCurve, setGaeTrustCurve] = useState<GAETrustCurve | null>(null)
  const [gaeBeforeAfter, setGaeBeforeAfter] = useState<GAEBeforeAfter | null>(null)
  const [gaeChartsLoading, setGaeChartsLoading] = useState(false)

  // — convergence —
  const [convergenceData, setConvergenceData] = useState<ConvergenceData | null>(null)
  const [convergenceLoading, setConvergenceLoading] = useState(false)

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

  const loadData = async () => {
    setLoading(true)
    try { setData(await getCompoundingMetrics(4) as CompoundingData) }
    catch (e) { console.error('Failed to load compounding metrics:', e) }
    finally { setLoading(false) }
  }
  useEffect(() => { loadData() }, [])

  const handleReseed = async () => {
    if (!window.confirm('Re-seed Neo4j? This will DELETE all current data and restore the canonical demo dataset.')) return
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

  const loadGAECharts = async () => {
    setGaeChartsLoading(true)
    try {
      const [we, ct, tc, ba] = await Promise.all([
        getGAEWeightEvolution()       as Promise<GAEWeightEvolution>,
        getGAEConfidenceTrajectory()  as Promise<GAEConfidenceTrajectory>,
        getGAETrustCurve()            as Promise<GAETrustCurve>,
        getGAEBeforeAfter()           as Promise<GAEBeforeAfter>,
      ])
      console.log('[GAE] weight-evolution:', we?.evolution?.length ?? 0, 'entries, message:', we?.message)
      console.log('[GAE] confidence-trajectory:', Object.keys(we && ct?.trajectories || {}), 'message:', ct?.message)
      console.log('[GAE] trust-curve:', Object.keys(tc?.curves || {}), 'message:', tc?.message)
      console.log('[GAE] before-after: ready=', ba?.ready, 'improvement_pp=', ba?.improvement_pp, 'message:', ba?.message)
      setGaeWeightEvo(we); setGaeConfTraj(ct); setGaeTrustCurve(tc); setGaeBeforeAfter(ba)
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

  // — early return while seeded metrics load —
  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Loading compounding metrics...</p>
        </div>
      </div>
    )
  }

  const { headline, weekly_trend, evolution_events } = data
  const autoCloseChange = animatedAutoCloseEnd - headline.auto_close_start
  const mttrChangePercent = (headline.mttr_start - animatedMttrEnd) / headline.mttr_start * 100
  const fpChangePercent = (headline.fp_investigations_start - animatedFpEnd) / headline.fp_investigations_start * 100

  // — derived chart data (GAE) —

  // Weight Evolution: bar chart, two series for correct/incorrect
  const gaeWeightBarData = (gaeWeightEvo?.evolution ?? []).map(e => ({
    decision:        e.decision_number,
    action:          e.action,
    W_norm:          e.W_norm_after,
    delta_correct:   e.outcome === 1  ? e.delta_norm : undefined,
    delta_incorrect: e.outcome === -1 ? e.delta_norm : undefined,
  }))

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

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-6">

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
            onClick={() => setShowROI(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-all hover:scale-105 shadow-md"
          >
            <Calculator className="w-4 h-4" />
            <span className="text-sm font-semibold">Calculate ROI</span>
          </button>
        </div>
      </div>

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

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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

        {/* ── Section A: Weight Evolution ─────────────────────────────────── */}
        <div className="mb-6">
          <p className="text-xs font-semibold text-purple-300 uppercase tracking-wide mb-1">A · Weight Evolution</p>
          <p className="text-xs text-gray-500 mb-3">
            How much the W matrix shifted per decision — green = correct, red = incorrect. Tall red bar = 20:1 asymmetric penalty.
          </p>
          <div className="bg-white rounded-md p-3">
            {gaeWeightBarData.length === 0 ? (
              <ChartEmpty message={gaeWeightEvo?.message ?? 'Process alerts and provide feedback to see weight evolution'} />
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={gaeWeightBarData} margin={{ top: 5, right: 10, left: -10, bottom: 18 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis dataKey="decision" tick={{ fontSize: 10 }} label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => v.toFixed(3)} />
                  <Tooltip
                    formatter={(v: any, name: string) => [
                      Number(v).toFixed(5),
                      name === 'delta_correct' ? 'ΔW (correct)' : 'ΔW (incorrect)',
                    ]}
                    labelFormatter={(label) => {
                      const row = gaeWeightBarData.find(d => d.decision === label)
                      return `Decision #${label}  action: ${row?.action ?? '?'}  ‖W‖_F: ${row?.W_norm.toFixed(4) ?? '?'}`
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 10 }} formatter={(v: string) => v === 'delta_correct' ? 'ΔW correct' : 'ΔW incorrect'} />
                  <Bar dataKey="delta_correct"   fill="#10b981" name="delta_correct"   radius={[2, 2, 0, 0]} />
                  <Bar dataKey="delta_incorrect" fill="#ef4444" name="delta_incorrect" radius={[2, 2, 0, 0]} />
                </BarChart>
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
                    <span className={`text-xs font-bold px-2 py-1 rounded ${s.humanReview ? 'bg-red-500 text-white' : 'bg-green-500 text-white'}`}>
                      {s.humanReview ? 'HUMAN REVIEW' : 'TRUSTED'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

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
            {convergenceData.weight_snapshots.length > 1 && (
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-2">‖W‖_F last {convergenceData.weight_snapshots.length} updates</p>
                <ResponsiveContainer width="100%" height={60}>
                  <LineChart data={convergenceData.weight_snapshots.map((v, i) => ({ i: i + 1, norm: v }))} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
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

      {/* ── 6. Weekly Trend + Three-Loop Architecture ───────────────────────── */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border shadow p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Weekly Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={weekly_trend}>
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
            {weekly_trend.map(w => (
              <div key={w.week} className="bg-gray-50 rounded p-2">
                <div className="font-semibold text-gray-900">Week {w.week}</div>
                <div className="text-xs text-gray-600">{w.pattern_count} patterns</div>
              </div>
            ))}
          </div>
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
                <div className="text-xs text-gray-300 mt-1">(Neo4j)</div>
              </div>
            </div>
            <div className="flex items-center text-gray-500 text-sm font-bold shrink-0">←</div>
            <div className="flex-1 bg-purple-900/40 rounded border-2 border-purple-500 p-2.5">
              <div className="text-xs font-bold text-purple-300 uppercase tracking-wide mb-0.5">Loop 2</div>
              <div className="text-sm font-semibold text-purple-200 mb-0.5">AgentEvolver</div>
              <div className="text-xs text-purple-300/60 italic mb-1.5">Smarter across decisions</div>
              {['Tracks variants', 'Evolves behavior', 'Promotes winners'].map(t => (
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

      {/* ── 7. Evolution Events — SAMPLE EVENTS ────────────────────────────── */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-600" />
              Recent Evolution Events
            </h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
              Sample events
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReseed}
              disabled={reseeding || resetting}
              className="flex items-center gap-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors disabled:opacity-50 font-semibold"
              title="Delete all Neo4j data and restore the canonical demo dataset"
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

        <div className="space-y-2">
          {evolution_events.map(event => (
            <div key={event.id} className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200 hover:bg-purple-100 transition-colors">
              <div className="flex items-center gap-4 flex-1">
                <div className="text-sm font-mono text-purple-700 font-semibold">{event.id}</div>
                <div className="text-sm text-gray-600">{formatEventType(event.event_type)}</div>
                <div className="text-sm font-semibold text-gray-900">{event.description}</div>
              </div>
              <div className="text-xs text-gray-500">{formatTimeAgo(event.timestamp)}</div>
            </div>
          ))}
        </div>
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
