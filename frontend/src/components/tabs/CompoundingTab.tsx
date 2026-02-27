/**
 * Tab 4: Compounding Dashboard
 * Purpose: Prove the compounding effect - "Watch the Moat Grow"
 * Energy: 15%
 */

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { getCompoundingMetrics, resetAllDemoData, resetAlerts, reseedDemoData, getAuditDecisions, verifyAuditChain, getWeightHistory, getConfidenceTrajectory, getTrustScores } from '../../lib/api'
import { domainConfig } from '../../lib/domain'
import { TrendingUp, Database, Activity, RefreshCw, Clock, DollarSign, TrendingDown, CheckCircle, Calculator, Shield, Download } from 'lucide-react'
import ROICalculatorModal from '../ROICalculator'

// ============================================================================
// Custom Hook: Counter Animation
// ============================================================================

/**
 * Animates a number from start to end over duration using requestAnimationFrame
 * with ease-out easing (fast start, slow finish)
 */
function useCountUp(
  start: number,
  end: number,
  duration: number = 1500,
  decimals: number = 0,
  shouldAnimate: boolean = true
): number {
  const [count, setCount] = useState(start)

  useEffect(() => {
    if (!shouldAnimate) {
      setCount(end)
      return
    }

    // Reset to start value
    setCount(start)

    let startTime: number | null = null
    let animationFrame: number

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Ease-out cubic: fast start, slow finish
      const easeOut = 1 - Math.pow(1 - progress, 3)

      const currentValue = start + (end - start) * easeOut
      setCount(currentValue)

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate)
      }
    }

    animationFrame = requestAnimationFrame(animate)

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame)
      }
    }
  }, [start, end, duration, shouldAnimate])

  return decimals > 0 ? parseFloat(count.toFixed(decimals)) : Math.round(count)
}

interface WeeklyMetric {
  week: number
  auto_close_rate: number
  mttr_minutes: number
  fp_rate: number
  pattern_count: number
}

interface EvolutionEvent {
  id: string
  event_type: string
  description: string
  timestamp: string
  triggered_by: string
}

interface BusinessImpact {
  analyst_hours_saved_monthly: number
  cost_avoided_quarterly: number
  mttr_reduction_pct: number
  alert_backlog_eliminated_monthly: number
}

interface CompoundingData {
  period: {
    start: string
    end: string
  }
  headline: {
    nodes_start: number
    nodes_end: number
    auto_close_start: number
    auto_close_end: number
    mttr_start: number
    mttr_end: number
    fp_investigations_start: number
    fp_investigations_end: number
  }
  weekly_trend: WeeklyMetric[]
  evolution_events: EvolutionEvent[]
  business_impact?: BusinessImpact
}

interface AuditDecision {
  id: string
  alert_id: string
  timestamp: string
  situation_type: string
  action_taken: string
  factors: string[]
  confidence: number
  outcome: string | null
  analyst_confirmed: boolean
  hash: string
}

interface AuditVerification {
  chain_length: number
  verified: boolean
  first_record: string | null
  last_record: string | null
  broken_at_index?: number
}

// F4c: Weight history
interface WeightHistoryEntry {
  decision_number: number
  timestamp: string
  alert_type: string
  weights: Record<string, number>
  trigger: string
  outcome: boolean
}

interface WeightHistoryData {
  history: WeightHistoryEntry[]
  total: number
  alert_type_filter: string | null
}

// F4c: Confidence trajectory
interface ConfidencePoint {
  decision: number
  confidence: number
}

interface ConfidenceTrajectoryData {
  trajectory: Record<string, ConfidencePoint[]>
  total_decisions: number
  situation_types: string[]
}

// F6b: Trust tracking
interface TrustScoreEntry {
  trust_score: number
  human_review_required: boolean
}

interface TrustHistoryPoint {
  decision_number: number
  timestamp: string
  situation_type: string
  trust_score: number
  delta: number
  outcome: 'correct' | 'incorrect'
}

interface TrustData {
  trust_scores: Record<string, TrustScoreEntry>
  history: TrustHistoryPoint[]
  total_updates: number
  low_trust_situations: string[]
}

// F4c: Color palettes for charts
const VARIANT_COLORS: Record<string, string> = {
  TRAVEL_CONTEXT_v1:    '#94a3b8',
  TRAVEL_CONTEXT_v2:    '#8b5cf6',
  PHISHING_RESPONSE_v1: '#3b82f6',
  PHISHING_RESPONSE_v2: '#06b6d4',
}

const SITUATION_COLORS: Record<string, string> = {
  travel_login_anomaly:       '#8b5cf6',
  known_phishing_campaign:    '#3b82f6',
  critical_asset_malware:     '#ef4444',
  data_exfiltration_detected: '#f59e0b',
  unknown_login_pattern:      '#6b7280',
  routine_malware_scan:       '#10b981',
}

export default function CompoundingTab() {
  const [data, setData] = useState<CompoundingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [reseeding, setReseeding] = useState(false)
  const [reseedMessage, setReseedMessage] = useState<string | null>(null)
  const [showROI, setShowROI] = useState(false)
  const [auditDecisions, setAuditDecisions] = useState<AuditDecision[]>([])
  const [auditVerification, setAuditVerification] = useState<AuditVerification | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)

  // F4c: Compounding Proof state
  const [weightHistory, setWeightHistory] = useState<WeightHistoryData | null>(null)
  const [confidenceTrajectory, setConfidenceTrajectory] = useState<ConfidenceTrajectoryData | null>(null)
  const [proofLoading, setProofLoading] = useState(false)

  // F6b: Trust Curve state
  const [trustData, setTrustData] = useState<TrustData | null>(null)
  const [trustLoading, setTrustLoading] = useState(false)

  // ALL HOOKS MUST BE AT TOP LEVEL - Called unconditionally with safe defaults
  // Uses optional chaining (??) to provide fallback values when data is null
  const animatedNodesEnd = useCountUp(
    data?.headline.nodes_start ?? 0,
    data?.headline.nodes_end ?? 0,
    3000,
    0,
    !!data && !loading
  )
  const animatedAutoCloseEnd = useCountUp(
    data?.headline.auto_close_start ?? 0,
    data?.headline.auto_close_end ?? 0,
    3000,
    0,
    !!data && !loading
  )
  const animatedMttrEnd = useCountUp(
    data?.headline.mttr_start ?? 0,
    data?.headline.mttr_end ?? 0,
    3000,
    1,
    !!data && !loading
  )
  const animatedFpEnd = useCountUp(
    data?.headline.fp_investigations_start ?? 0,
    data?.headline.fp_investigations_end ?? 0,
    3000,
    0,
    !!data && !loading
  )

  // Business impact counter animations
  const animatedAnalystHours = useCountUp(
    0,
    data?.business_impact?.analyst_hours_saved_monthly ?? 0,
    3000,
    0,
    !!data?.business_impact && !loading
  )
  const animatedCostAvoided = useCountUp(
    0,
    data?.business_impact?.cost_avoided_quarterly ?? 0,
    3000,
    0,
    !!data?.business_impact && !loading
  )
  const animatedMttrReduction = useCountUp(
    0,
    data?.business_impact?.mttr_reduction_pct ?? 0,
    3000,
    0,
    !!data?.business_impact && !loading
  )
  const animatedBacklogEliminated = useCountUp(
    0,
    data?.business_impact?.alert_backlog_eliminated_monthly ?? 0,
    3000,
    0,
    !!data?.business_impact && !loading
  )

  const loadData = async () => {
    setLoading(true)
    try {
      const result = await getCompoundingMetrics(4)
      setData(result)
    } catch (error) {
      console.error('Failed to load compounding metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleReseed = async () => {
    if (!window.confirm('Re-seed Neo4j? This will DELETE all current data and restore the canonical demo dataset.')) return
    setReseeding(true)
    setReseedMessage(null)
    try {
      console.log('[CompoundingTab] Re-seeding demo data...')
      const result = await reseedDemoData() as { success: boolean; alert_count?: number; error?: string }
      if (result.success) {
        setReseedMessage(`Re-seed complete — ${result.alert_count} alerts restored.`)
        await loadData()
      } else {
        setReseedMessage(`Re-seed failed: ${result.error ?? 'unknown error'}`)
      }
    } catch (error) {
      console.error('[CompoundingTab] Re-seed threw:', error)
      setReseedMessage('Re-seed failed — check backend logs.')
    } finally {
      setReseeding(false)
    }
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      console.log('[CompoundingTab] Resetting all demo data...')
      await resetAllDemoData()
      await resetAlerts()
      console.log('[CompoundingTab] Demo data reset successfully, reloading...')
      await loadData()
    } catch (error) {
      console.error('[CompoundingTab] Failed to reset demo:', error)
    } finally {
      setResetting(false)
    }
  }

  const loadAuditData = async () => {
    setAuditLoading(true)
    try {
      const [decisionsResult, verifyResult] = await Promise.all([
        getAuditDecisions() as Promise<{ decisions: AuditDecision[]; total: number }>,
        verifyAuditChain() as Promise<AuditVerification>,
      ])
      setAuditDecisions(decisionsResult.decisions.slice(0, 5))
      setAuditVerification(verifyResult)
    } catch (error) {
      console.error('[CompoundingTab] Failed to load audit data:', error)
    } finally {
      setAuditLoading(false)
    }
  }

  useEffect(() => {
    loadAuditData()
  }, [])

  // F4c: load weight history + confidence trajectory
  const loadCompoundingProof = async () => {
    setProofLoading(true)
    try {
      const [wh, ct] = await Promise.all([
        getWeightHistory() as Promise<WeightHistoryData>,
        getConfidenceTrajectory() as Promise<ConfidenceTrajectoryData>,
      ])
      setWeightHistory(wh)
      setConfidenceTrajectory(ct)
    } catch (error) {
      console.error('[CompoundingTab] Failed to load compounding proof:', error)
    } finally {
      setProofLoading(false)
    }
  }

  useEffect(() => {
    loadCompoundingProof()
  }, [])

  // F6b: load trust scores
  const loadTrustData = async () => {
    setTrustLoading(true)
    try {
      const td = await getTrustScores() as TrustData
      setTrustData(td)
    } catch (error) {
      console.error('[CompoundingTab] Failed to load trust data:', error)
    } finally {
      setTrustLoading(false)
    }
  }

  useEffect(() => {
    loadTrustData()
  }, [])

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

  // Calculate percentage changes (using animated values for live updates)
  const autoCloseChange = animatedAutoCloseEnd - headline.auto_close_start
  const mttrChangePercent = ((headline.mttr_start - animatedMttrEnd) / headline.mttr_start * 100)
  const fpInvestigationsChangePercent = ((headline.fp_investigations_start - animatedFpEnd) / headline.fp_investigations_start * 100)

  // F4c: Derived chart data (plain variables, not hooks — recomputed each render)
  const weightChartData: Record<string, number>[] = weightHistory?.history
    ? weightHistory.history.map(h => ({ decision: h.decision_number, ...h.weights }))
    : []

  const weightVariantNames: string[] = weightHistory?.history?.length
    ? Array.from(new Set(weightHistory.history.flatMap(h => Object.keys(h.weights))))
    : []

  // Merge confidence points from all situation types into one array keyed by decision #
  const confChartData: Record<string, number>[] = (() => {
    if (!confidenceTrajectory?.trajectory) return []
    const merged = new Map<number, Record<string, number>>()
    for (const [sit, pts] of Object.entries(confidenceTrajectory.trajectory)) {
      for (const { decision, confidence } of pts) {
        if (!merged.has(decision)) merged.set(decision, { decision })
        merged.get(decision)![sit] = confidence
      }
    }
    return [...merged.entries()].sort(([a], [b]) => a - b).map(([, v]) => v)
  })()

  const confSituationTypes: string[] = confidenceTrajectory?.situation_types ?? []

  // F6b: Trust curve derived data
  const trustChartData: Record<string, number>[] = (() => {
    if (!trustData?.history?.length) return []
    const merged = new Map<number, Record<string, number>>()
    for (const point of trustData.history) {
      if (!merged.has(point.decision_number)) {
        merged.set(point.decision_number, { decision: point.decision_number })
      }
      merged.get(point.decision_number)![point.situation_type] = point.trust_score
    }
    return [...merged.entries()].sort(([a], [b]) => a - b).map(([, v]) => v)
  })()

  const trustSituationTypes: string[] = Array.from(
    new Set(trustData?.history?.map(h => h.situation_type) ?? [])
  )

  // Find the worst single drop to annotate on the chart
  const worstDrop = (() => {
    if (!trustData?.history?.length) return null
    return trustData.history.reduce(
      (worst, h) => (h.delta < worst.delta ? h : worst),
      trustData.history[0]
    )
  })()

  const annotationText: string | null =
    worstDrop && worstDrop.delta < -0.1
      ? `Incorrect decision at #${worstDrop.decision_number} → trust dropped from ${Math.round((worstDrop.trust_score - worstDrop.delta) * 100)}% to ${Math.round(worstDrop.trust_score * 100)}%`
      : null

  // F4d: Before/after comparison — situation type with the most data points (≥2 required)
  const compareData = (() => {
    if (!confidenceTrajectory?.trajectory) return null
    let bestSit: string | null = null
    let bestLen = 0
    for (const [sit, pts] of Object.entries(confidenceTrajectory.trajectory)) {
      if (pts.length >= 2 && pts.length > bestLen) {
        bestLen = pts.length
        bestSit = sit
      }
    }
    if (!bestSit) return null
    const pts = confidenceTrajectory.trajectory[bestSit]
    const sorted = [...pts].sort((a, b) => a.decision - b.decision)
    const first = sorted[0]
    const latest = sorted[sorted.length - 1]
    return {
      situationType: bestSit,
      first,
      latest,
      deltaPoints: Math.round((latest.confidence - first.confidence) * 100),
    }
  })()

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Business Impact Banner - Executive Summary */}
      {data.business_impact && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border-2 border-green-400 shadow-lg p-6">
          <div className="text-center mb-4">
            <h3 className="text-xl font-bold text-gray-900">
              Business Impact Summary
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Quarterly projections for CFO reporting
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Card 1: Analyst Hours Saved */}
            <div className="bg-white rounded-lg border-2 border-green-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <div className="flex items-center justify-center mb-2">
                <Clock className="w-5 h-5 text-green-600" />
              </div>
              <div className="text-4xl font-bold text-green-600 mb-1">
                {animatedAnalystHours.toLocaleString()}
              </div>
              <div className="text-xs text-gray-600 font-medium">
                {domainConfig.impactLabels.hrsSaved}
              </div>
            </div>

            {/* Card 2: Cost Avoided */}
            <div className="bg-white rounded-lg border-2 border-blue-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <div className="flex items-center justify-center mb-2">
                <DollarSign className="w-5 h-5 text-blue-600" />
              </div>
              <div className="text-4xl font-bold text-blue-600 mb-1">
                ${(animatedCostAvoided / 1000).toFixed(0)}K
              </div>
              <div className="text-xs text-gray-600 font-medium">
                Cost Avoided / Quarter
              </div>
            </div>

            {/* Card 3: MTTR Reduction */}
            <div className="bg-white rounded-lg border-2 border-purple-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <div className="flex items-center justify-center mb-2">
                <TrendingDown className="w-5 h-5 text-purple-600" />
              </div>
              <div className="text-4xl font-bold text-purple-600 mb-1">
                {animatedMttrReduction}%
              </div>
              <div className="text-xs text-gray-600 font-medium">
                MTTR Reduction
              </div>
            </div>

            {/* Card 4: Alert Backlog Eliminated */}
            <div className="bg-white rounded-lg border-2 border-emerald-300 shadow p-5 text-center hover:shadow-xl transition-shadow">
              <div className="flex items-center justify-center mb-2">
                <CheckCircle className="w-5 h-5 text-emerald-600" />
              </div>
              <div className="text-4xl font-bold text-emerald-600 mb-1">
                {animatedBacklogEliminated.toLocaleString()}
              </div>
              <div className="text-xs text-gray-600 font-medium">
                {domainConfig.impactLabels.backlog}
              </div>
            </div>
          </div>

          {/* Executive Note */}
          <div className="mt-4 text-center">
            <p className="text-sm italic text-gray-700">
              💼 Present these numbers to your CFO — this is the business case for AI-augmented {domainConfig.operationsLabel}.
            </p>
          </div>

          {/* ROI Calculator CTA Button */}
          <div className="mt-6">
            <button
              onClick={() => setShowROI(true)}
              className="w-full bg-gradient-to-r from-purple-600 via-blue-600 to-purple-600 hover:from-purple-700 hover:via-blue-700 hover:to-purple-700 text-white font-bold py-4 px-6 rounded-lg shadow-xl transition-all hover:scale-[1.02] hover:shadow-2xl flex items-center justify-center gap-3 group"
            >
              <Calculator className="w-6 h-6 group-hover:rotate-12 transition-transform" />
              <span className="text-lg">Calculate Your ROI — Input Your {domainConfig.displayName} Numbers</span>
              <div className="ml-2 px-3 py-1 bg-white/20 rounded-full text-xs font-semibold">
                Interactive
              </div>
            </button>
          </div>
        </div>
      )}

      {/* THE HEADLINE - Week 1 vs Week 4 Comparison */}
      <div className="bg-white rounded-lg border-2 border-purple-200 shadow-lg p-8">
        <h3 className="text-xl font-bold text-gray-900 mb-6 text-center">
          THE HEADLINE
        </h3>

        {/* Graph Visualization */}
        <div className="grid md:grid-cols-2 gap-8 mb-8">
          {/* Week 1 */}
          <div className="text-center">
            <div className="text-sm font-semibold text-gray-600 mb-3">WEEK 1</div>
            <div className="bg-gray-50 rounded-lg p-6 border-2 border-gray-300">
              <div className="flex justify-center items-center mb-4">
                {/* Simple graph visualization */}
                <div className="grid grid-cols-3 gap-2">
                  {[...Array(9)].map((_, i) => (
                    <div
                      key={i}
                      className="w-6 h-6 bg-blue-300 rounded-full opacity-50"
                    />
                  ))}
                </div>
              </div>
              <div className="text-3xl font-bold text-gray-700">
                {headline.nodes_start} nodes
              </div>
            </div>
          </div>

          {/* Arrow */}
          <div className="hidden md:flex items-center justify-center absolute left-1/2 transform -translate-x-1/2">
            <TrendingUp className="w-12 h-12 text-purple-600" />
          </div>

          {/* Week 4 */}
          <div className="text-center">
            <div className="text-sm font-semibold text-gray-600 mb-3">WEEK 4</div>
            <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg p-6 border-2 border-purple-400">
              <div className="flex justify-center items-center mb-4">
                {/* Dense graph visualization */}
                <div className="grid grid-cols-5 gap-1">
                  {[...Array(25)].map((_, i) => (
                    <div
                      key={i}
                      className="w-4 h-4 bg-purple-500 rounded-full"
                    />
                  ))}
                </div>
              </div>
              <div className="text-3xl font-bold text-purple-700">
                {animatedNodesEnd} nodes
              </div>
            </div>
          </div>
        </div>

        {/* Metric Improvements */}
        <div className="space-y-3 border-t pt-6">
          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">Auto-Close Rate:</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {headline.auto_close_start}% → {animatedAutoCloseEnd}%
              </span>
              <span className="text-green-600 font-semibold">
                (+{autoCloseChange.toFixed(0)} pts)
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">MTTR:</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {headline.mttr_start} min → {animatedMttrEnd.toFixed(1)} min
              </span>
              <span className="text-green-600 font-semibold">
                (-{mttrChangePercent.toFixed(0)}%)
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">FP Investigations:</span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {headline.fp_investigations_start.toLocaleString()}/wk → {animatedFpEnd.toLocaleString()}/wk
              </span>
              <span className="text-green-600 font-semibold">
                (-{fpInvestigationsChangePercent.toFixed(0)}%)
              </span>
            </div>
          </div>
        </div>

        {/* Tagline */}
        <div className="mt-6 text-center">
          <p className="text-lg font-medium text-gray-700 italic">
            Same model. Same rules. More intelligence.
          </p>
        </div>
      </div>

      {/* Two Column Layout: Trend Chart + Two-Loop Visual */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Weekly Trend Chart */}
        <div className="bg-white rounded-lg border shadow p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">
            Weekly Trend
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={weekly_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="week"
                label={{ value: 'Week', position: 'insideBottom', offset: -5 }}
              />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="auto_close_rate"
                stroke="#8b5cf6"
                strokeWidth={2}
                name="Auto-Close %"
              />
              <Line
                type="monotone"
                dataKey="mttr_minutes"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="MTTR (min)"
              />
              <Line
                type="monotone"
                dataKey="fp_rate"
                stroke="#ef4444"
                strokeWidth={2}
                strokeDasharray="3 3"
                name="FP Rate %"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-4 gap-2 text-center text-sm">
            {weekly_trend.map((week) => (
              <div key={week.week} className="bg-gray-50 rounded p-2">
                <div className="font-semibold text-gray-900">Week {week.week}</div>
                <div className="text-xs text-gray-600">{week.pattern_count} patterns</div>
              </div>
            ))}
          </div>
        </div>

        {/* Three-Loop Architecture Diagram (Hero Visual) */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-lg border-2 border-purple-500 shadow-2xl p-5">
          <h3 className="text-xl font-bold text-white mb-1 text-center">
            Three-Loop Architecture
          </h3>
          <p className="text-xs text-gray-400 text-center mb-4">
            Three cross-layer loops. One living graph. Intelligence that compounds automatically.
          </p>

          {/* Top row: Loop 1 → Living Context Graph ← Loop 2 */}
          <div className="flex items-stretch gap-1.5 mb-1">

            {/* Loop 1 — Situation Analyzer (blue) */}
            <div className="flex-1 bg-blue-900/40 rounded border-2 border-blue-500 p-2.5">
              <div className="text-xs font-bold text-blue-300 uppercase tracking-wide mb-0.5">Loop 1</div>
              <div className="text-sm font-semibold text-blue-200 mb-0.5">Situation Analyzer</div>
              <div className="text-xs text-blue-300/60 italic mb-1.5">Smarter within each decision</div>
              <div className="space-y-0.5">
                <div className="flex items-start gap-1">
                  <div className="w-1 h-1 bg-blue-400 rounded-full mt-1.5 shrink-0" />
                  <span className="text-xs text-gray-300">Classifies situations</span>
                </div>
                <div className="flex items-start gap-1">
                  <div className="w-1 h-1 bg-blue-400 rounded-full mt-1.5 shrink-0" />
                  <span className="text-xs text-gray-300">Evaluates options</span>
                </div>
                <div className="flex items-start gap-1">
                  <div className="w-1 h-1 bg-blue-400 rounded-full mt-1.5 shrink-0" />
                  <span className="text-xs text-gray-300">Reasons over context</span>
                </div>
              </div>
              <div className="mt-1.5 pt-1.5 border-t border-blue-800 text-xs text-blue-400">Demo: Tab 3 →</div>
            </div>

            {/* Arrow → center */}
            <div className="flex items-center text-gray-500 text-sm font-bold shrink-0">→</div>

            {/* Center: Living Context Graph */}
            <div className="flex items-center justify-center w-28 shrink-0">
              <div className="bg-gradient-to-br from-purple-700 to-blue-700 rounded-lg p-3 border-2 border-yellow-400 shadow-xl animate-pulse text-center w-full">
                <Database className="w-5 h-5 text-white mx-auto mb-1" />
                <div className="text-xs font-bold text-white leading-tight">Living Context</div>
                <div className="text-xs font-bold text-white leading-tight">Graph</div>
                <div className="text-xs text-gray-300 mt-1">(Neo4j)</div>
              </div>
            </div>

            {/* Arrow center → */}
            <div className="flex items-center text-gray-500 text-sm font-bold shrink-0">←</div>

            {/* Loop 2 — AgentEvolver (purple) */}
            <div className="flex-1 bg-purple-900/40 rounded border-2 border-purple-500 p-2.5">
              <div className="text-xs font-bold text-purple-300 uppercase tracking-wide mb-0.5">Loop 2</div>
              <div className="text-sm font-semibold text-purple-200 mb-0.5">AgentEvolver</div>
              <div className="text-xs text-purple-300/60 italic mb-1.5">Smarter across decisions</div>
              <div className="space-y-0.5">
                <div className="flex items-start gap-1">
                  <div className="w-1 h-1 bg-purple-400 rounded-full mt-1.5 shrink-0" />
                  <span className="text-xs text-gray-300">Tracks variants</span>
                </div>
                <div className="flex items-start gap-1">
                  <div className="w-1 h-1 bg-purple-400 rounded-full mt-1.5 shrink-0" />
                  <span className="text-xs text-gray-300">Evolves behavior</span>
                </div>
                <div className="flex items-start gap-1">
                  <div className="w-1 h-1 bg-purple-400 rounded-full mt-1.5 shrink-0" />
                  <span className="text-xs text-gray-300">Promotes winners</span>
                </div>
              </div>
              <div className="mt-1.5 pt-1.5 border-t border-purple-800 text-xs text-purple-400">Demo: Tab 2 →</div>
            </div>
          </div>

          {/* Vertical connector from Loop 3 up to center graph */}
          <div className="flex justify-center">
            <div className="text-amber-500/50 text-sm leading-none">↑</div>
          </div>

          {/* Loop 3 — RL Reward / Penalty (amber), centered below graph */}
          <div className="flex justify-center mb-3">
            <div className="bg-amber-900/40 rounded border-2 border-amber-500 p-2.5 w-3/5 text-center">
              <div className="text-xs font-bold text-amber-300 uppercase tracking-wide mb-0.5">Loop 3</div>
              <div className="text-sm font-semibold text-amber-200 mb-0.5">RL Reward / Penalty</div>
              <div className="text-xs text-amber-300/60 italic mb-1.5">Governs both loops</div>
              <div className="flex justify-center gap-2 flex-wrap">
                <span className="text-xs text-gray-300">+0.3 reward</span>
                <span className="text-gray-600">·</span>
                <span className="text-xs text-gray-300">−6.0 penalty</span>
                <span className="text-gray-600">·</span>
                <span className="text-xs text-gray-300">20:1 ratio</span>
              </div>
              <div className="mt-1.5 pt-1.5 border-t border-amber-800 text-xs text-amber-400">Demo: Tab 2 →</div>
            </div>
          </div>

          {/* TRIGGERED_EVOLUTION write-back badge */}
          <div className="text-center mb-4">
            <div className="inline-block bg-gradient-to-r from-blue-700 via-purple-700 to-amber-700 rounded-lg px-4 py-2 border border-yellow-400/60">
              <div className="text-xs font-bold text-white">
                ALL THREE WRITE BACK → TRIGGERED_EVOLUTION
              </div>
            </div>
          </div>

          {/* Four Layers context strip */}
          <div className="mb-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide text-center mb-2">
              Four Dependency-Ordered Layers
            </div>
            <div className="flex items-center gap-1">
              {/* Layer 1: UCL — gray, not highlighted */}
              <div className="flex-1 bg-slate-700/60 rounded border border-gray-600 px-1.5 py-1.5 text-center min-w-0">
                <div className="text-xs font-semibold text-gray-300 truncate">UCL</div>
                <div className="text-xs text-gray-500 leading-tight truncate">CrowdStrike · Pulsedive · SIEM</div>
              </div>
              <div className="text-gray-600 text-xs shrink-0">→</div>
              {/* Layer 2: Agent Engineering — gray, not highlighted */}
              <div className="flex-1 bg-slate-700/60 rounded border border-gray-600 px-1.5 py-1.5 text-center min-w-0">
                <div className="text-xs font-semibold text-gray-300 truncate">Agent Engineering</div>
                <div className="text-xs text-gray-500 leading-tight truncate">Runtime evolution</div>
              </div>
              <div className="text-gray-600 text-xs shrink-0">→</div>
              {/* Layer 3: ACCP — blue border, highlighted */}
              <div className="flex-1 bg-blue-950/60 rounded border border-blue-500 px-1.5 py-1.5 text-center min-w-0">
                <div className="text-xs font-semibold text-blue-300 truncate">ACCP</div>
                <div className="text-xs text-blue-400/70 leading-tight truncate">Cognitive control</div>
              </div>
              <div className="text-gray-600 text-xs shrink-0">→</div>
              {/* Layer 4: SOC Copilot — green border, highlighted */}
              <div className="flex-1 bg-green-950/60 rounded border border-green-500 px-1.5 py-1.5 text-center min-w-0">
                <div className="text-xs font-semibold text-green-300 truncate">{domainConfig.displayName}</div>
                <div className="text-xs text-green-400/70 leading-tight truncate">Domain copilot</div>
              </div>
            </div>
            <div className="text-right mt-1">
              <span className="text-xs text-blue-400/50 italic">← this demo shows layers 3 &amp; 4</span>
            </div>
          </div>

          {/* Stats Row — 4 items (2×2 grid) */}
          <div className="pt-4 border-t border-gray-700">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-800/50 rounded p-2 border border-blue-500/30 text-center">
                <div className="text-xs text-gray-400 mb-0.5">Situation Types</div>
                <div className="text-base font-bold text-blue-400">2 → 6</div>
              </div>
              <div className="bg-slate-800/50 rounded p-2 border border-purple-500/30 text-center">
                <div className="text-xs text-gray-400 mb-0.5">Prompt Variants Evolved</div>
                <div className="text-base font-bold text-purple-400">0 → 4</div>
              </div>
              <div className="bg-slate-800/50 rounded p-2 border border-green-500/30 text-center">
                <div className="text-xs text-gray-400 mb-0.5">Cross-Alert Patterns</div>
                <div className="text-sm font-bold text-green-400">Travel: 47 | Phish: 31</div>
              </div>
              <div className="bg-slate-800/50 rounded p-2 border border-amber-500/30 text-center">
                <div className="text-xs text-gray-400 mb-0.5">Asymmetric Ratio</div>
                <div className="text-base font-bold text-amber-400">20:1 penalty</div>
              </div>
            </div>
          </div>

          {/* Key Message */}
          <div className="mt-4 text-center">
            <p className="text-xs italic text-gray-400">
              💡 "SIEMs get better rules. Our copilot <span className="text-purple-400 font-semibold">becomes</span> a better copilot."
            </p>
          </div>
        </div>
      </div>

      {/* Compounding Proof Panel (F4c) */}
      <div className="bg-slate-900 rounded-lg border border-purple-500 shadow-2xl p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              The Compounding Curve
            </h3>
            <p className="text-sm text-gray-400 mt-0.5">
              Same model, same code, smarter graph.
            </p>
          </div>
          <button
            onClick={loadCompoundingProof}
            disabled={proofLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-purple-900/50 hover:bg-purple-800/60 text-purple-300 rounded-lg text-sm font-medium transition-colors border border-purple-600 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${proofLoading ? 'animate-spin' : ''}`} />
            {proofLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {/* Section A: Weight Evolution */}
        <div className="mb-5">
          <p className="text-xs font-semibold text-purple-300 uppercase tracking-wide mb-1">
            A · Weight Evolution
          </p>
          <p className="text-xs text-gray-500 mb-3">
            Prompt variant success rates after each decision
          </p>
          <div className="bg-white rounded-md p-3">
            {weightChartData.length === 0 ? (
              <div className="py-8 text-center text-gray-400 italic text-sm">
                No decisions recorded yet — analyze alerts in Tab 3 to populate.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={weightChartData} margin={{ top: 5, right: 10, left: -10, bottom: 18 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="decision"
                    tick={{ fontSize: 10 }}
                    label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }}
                  />
                  <YAxis
                    domain={[0.5, 1.0]}
                    tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                    tick={{ fontSize: 10 }}
                  />
                  <Tooltip formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {weightVariantNames.map((name) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      stroke={VARIANT_COLORS[name] ?? '#6b7280'}
                      strokeWidth={2}
                      dot={false}
                      name={name.replace(/_/g, ' ')}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Section B: Confidence Trajectory */}
        <div className="mb-5">
          <p className="text-xs font-semibold text-blue-300 uppercase tracking-wide mb-1">
            B · Confidence Trajectory
          </p>
          <p className="text-xs text-gray-500 mb-3">
            Agent confidence per situation type — ascending trend = compounding
          </p>
          <div className="bg-white rounded-md p-3">
            {confChartData.length === 0 ? (
              <div className="py-8 text-center text-gray-400 italic text-sm">
                No decisions recorded yet — analyze alerts in Tab 3 to populate.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={confChartData} margin={{ top: 5, right: 10, left: -10, bottom: 18 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="decision"
                    tick={{ fontSize: 10 }}
                    label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }}
                  />
                  <YAxis
                    domain={[0.5, 1.0]}
                    tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                    tick={{ fontSize: 10 }}
                  />
                  <Tooltip formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {confSituationTypes.map((sit) => (
                    <Line
                      key={sit}
                      type="monotone"
                      dataKey={sit}
                      stroke={SITUATION_COLORS[sit] ?? '#6b7280'}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name={sit.replace(/_/g, ' ')}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Section C: Before / After Comparison (F4d) */}
        {compareData && (
          <div className="mb-5">
            <p className="text-xs font-semibold text-green-300 uppercase tracking-wide mb-1">
              C · Before / After
            </p>
            <p className="text-xs text-gray-500 mb-3">
              First vs. latest decision — situation type with the most data
            </p>

            {/* Side-by-side cards */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              {/* First Decision */}
              <div className="bg-slate-800 rounded-lg border border-gray-600 p-4">
                <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">
                  First Decision
                </div>
                <div className="text-3xl font-bold text-gray-300 mb-1">
                  {Math.round(compareData.first.confidence * 100)}%
                </div>
                <div className="text-xs text-gray-500">Confidence</div>
                <div className="mt-2 text-xs text-gray-400">
                  Decision #{compareData.first.decision}
                </div>
                <div className="mt-1 text-xs text-gray-500 italic truncate">
                  {compareData.situationType.replace(/_/g, ' ')}
                </div>
              </div>

              {/* Latest Decision */}
              <div className="bg-slate-800 rounded-lg border border-green-500 p-4">
                <div className="text-xs text-green-400 uppercase tracking-wide mb-2">
                  Latest Decision
                </div>
                <div className="text-3xl font-bold text-green-300 mb-1">
                  {Math.round(compareData.latest.confidence * 100)}%
                </div>
                <div className="text-xs text-gray-500">Confidence</div>
                <div className="mt-2 text-xs text-gray-400">
                  Decision #{compareData.latest.decision}
                </div>
                <div className="mt-1 text-xs text-gray-500 italic truncate">
                  {compareData.situationType.replace(/_/g, ' ')}
                </div>
              </div>
            </div>

            {/* Delta highlight bar */}
            <div className="bg-green-900/30 border border-green-500/50 rounded-lg px-4 py-3 text-center">
              <span className="text-green-300 font-bold text-lg">
                +{compareData.deltaPoints} pp
              </span>
              <span className="text-gray-400 text-sm ml-2">
                Confidence improved {compareData.deltaPoints} percentage points
              </span>
            </div>
          </div>
        )}

        {/* Section D: Summary Metrics */}
        <div className="grid grid-cols-3 gap-3 pt-4 border-t border-gray-700">
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">
              {weightHistory?.total ?? 0}
            </div>
            <div className="text-xs text-gray-400 mt-0.5">Decisions processed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">
              {confidenceTrajectory?.situation_types?.length ?? 0}
            </div>
            <div className="text-xs text-gray-400 mt-0.5">Situation types seen</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">
              {weightHistory?.total ?? 0}
            </div>
            <div className="text-xs text-gray-400 mt-0.5">Weight adjustments</div>
          </div>
        </div>
      </div>

      {/* Trust Curve Panel (F6b) */}
      {trustData && (
        <div className="bg-slate-900 rounded-lg border border-red-500/60 shadow-2xl p-6">

          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span className="text-red-400 text-lg">⚠</span>
                Trust Curve
              </h3>
              <p className="text-sm text-red-300 font-medium mt-0.5">
                This system earns trust slowly and loses it fast.
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                20:1 asymmetry — one wrong decision erases twenty right ones.
              </p>
            </div>
            <button
              onClick={loadTrustData}
              disabled={trustLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-red-900/30 hover:bg-red-800/40 text-red-300 rounded-lg text-sm font-medium transition-colors border border-red-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${trustLoading ? 'animate-spin' : ''}`} />
              {trustLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {/* Line chart */}
          <div className="bg-white rounded-md p-3 mb-4">
            {trustChartData.length === 0 ? (
              <div className="py-8 text-center text-gray-400 italic text-sm">
                No trust data yet — submit feedback on a triage decision to populate.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trustChartData} margin={{ top: 5, right: 10, left: -10, bottom: 18 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="decision"
                    tick={{ fontSize: 10 }}
                    label={{ value: 'Decision #', position: 'insideBottom', offset: -10, fontSize: 10 }}
                  />
                  <YAxis
                    domain={[0, 1.0]}
                    tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                    tick={{ fontSize: 10 }}
                  />
                  <Tooltip formatter={(v: any) => `${(Number(v) * 100).toFixed(0)}%`} />
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  {/* Red dashed threshold at 30% — below here: human review required */}
                  <ReferenceLine
                    y={0.3}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    label={{ value: 'Review threshold (30%)', fill: '#ef4444', fontSize: 9, position: 'insideTopRight' }}
                  />
                  {trustSituationTypes.map((sit) => (
                    <Line
                      key={sit}
                      type="monotone"
                      dataKey={sit}
                      stroke={SITUATION_COLORS[sit] ?? '#6b7280'}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name={sit.replace(/_/g, ' ')}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Worst-drop annotation */}
          {annotationText && (
            <div className="mb-4 bg-red-900/30 border border-red-500/40 rounded-lg px-4 py-2.5 text-sm text-red-300 italic">
              {annotationText}
            </div>
          )}

          {/* Per-situation trust status cards */}
          {Object.keys(trustData.trust_scores).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Current Trust Status
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(trustData.trust_scores).map(([sit, status]) => (
                  <div
                    key={sit}
                    className={`rounded-lg border p-3 flex items-center justify-between ${
                      status.human_review_required
                        ? 'bg-red-900/20 border-red-500/50'
                        : 'bg-green-900/20 border-green-500/50'
                    }`}
                  >
                    <div>
                      <div className="text-xs text-gray-400 italic mb-0.5">
                        {sit.replace(/_/g, ' ')}
                      </div>
                      <div className={`text-2xl font-bold ${status.human_review_required ? 'text-red-300' : 'text-green-300'}`}>
                        {Math.round(status.trust_score * 100)}%
                      </div>
                    </div>
                    <span
                      className={`text-xs font-bold px-2 py-1 rounded ${
                        status.human_review_required
                          ? 'bg-red-500 text-white'
                          : 'bg-green-500 text-white'
                      }`}
                    >
                      {status.human_review_required ? 'HUMAN REVIEW' : 'TRUSTED'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}

      {/* Evidence Ledger */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-start justify-between mb-4 gap-4">
          <div>
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600" />
              Evidence Ledger
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Tamper-evident decision audit trail
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap justify-end">
            {/* Chain verification badge */}
            {auditVerification && (
              auditVerification.verified ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-green-100 text-green-700 border border-green-300">
                  <CheckCircle className="w-4 h-4" />
                  Chain verified ✓
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-red-100 text-red-700 border border-red-300">
                  Chain broken ✗
                  {auditVerification.broken_at_index !== undefined && (
                    <span className="font-normal">(at #{auditVerification.broken_at_index})</span>
                  )}
                </span>
              )
            )}

            {/* Download CSV */}
            <a
              href="/api/audit/decisions?format=csv"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-semibold transition-colors border border-gray-200"
            >
              <Download className="w-4 h-4" />
              Download CSV
            </a>

            {/* Refresh */}
            <button
              onClick={loadAuditData}
              disabled={auditLoading}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm font-semibold transition-colors border border-blue-200 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${auditLoading ? 'animate-spin' : ''}`} />
              {auditLoading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Table */}
        {auditDecisions.length === 0 ? (
          <div className="py-8 text-center text-gray-400 italic text-sm">
            No decisions recorded yet — run a triage in Tab 3 to populate.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-2 text-left font-semibold text-gray-600 pr-4">Timestamp</th>
                  <th className="pb-2 text-left font-semibold text-gray-600 pr-4">Alert</th>
                  <th className="pb-2 text-left font-semibold text-gray-600 pr-4">Action</th>
                  <th className="pb-2 text-left font-semibold text-gray-600 pr-4">Outcome</th>
                  <th className="pb-2 text-left font-semibold text-gray-600">Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditDecisions.map((decision) => (
                  <tr key={decision.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-2.5 pr-4 text-gray-500 text-xs tabular-nums">
                      {decision.timestamp.split('T')[1]?.slice(0, 8) ?? decision.timestamp}
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className="font-mono text-xs text-blue-700 font-semibold">
                        {decision.alert_id}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className="text-xs text-gray-700">
                        {decision.action_taken.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4">
                      {decision.outcome ? (
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                          decision.outcome === 'correct'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {decision.outcome}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 italic">pending</span>
                      )}
                    </td>
                    <td className="py-2.5">
                      <span className="font-mono text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                        {decision.hash ? `${decision.hash.slice(0, 8)}...` : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {auditVerification && auditVerification.chain_length > 0 && (
              <div className="mt-3 text-xs text-gray-400 text-right">
                {auditVerification.chain_length} record{auditVerification.chain_length !== 1 ? 's' : ''} in chain
                {auditVerification.first_record && (
                  <span> · from {auditVerification.first_record.split('T')[1]?.slice(0, 8)}</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Evolution Events */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-600" />
            Recent Evolution Events
          </h3>
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
          <div className={`mb-3 px-3 py-2 rounded text-xs font-medium ${
            reseedMessage.startsWith('Re-seed complete')
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {reseedMessage}
          </div>
        )}

        <div className="space-y-2">
          {evolution_events.map((event) => {
            const timeAgo = formatTimeAgo(event.timestamp)
            return (
              <div
                key={event.id}
                className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200 hover:bg-purple-100 transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className="text-sm font-mono text-purple-700 font-semibold">
                    {event.id}
                  </div>
                  <div className="text-sm text-gray-600">
                    {formatEventType(event.event_type)}
                  </div>
                  <div className="text-sm font-semibold text-gray-900">
                    {event.description}
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  {timeAgo}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* The Moat Message */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg p-8 text-center">
        <p className="text-2xl font-bold text-white leading-relaxed">
          "When a competitor deploys at a new customer, they start at zero.
          <br />
          We start at <span className="text-yellow-300">{animatedNodesEnd} patterns</span>. That's the moat."
        </p>
      </div>

      {/* ROI Calculator Modal */}
      <ROICalculatorModal
        isOpen={showROI}
        onClose={() => setShowROI(false)}
      />
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
