/**
 * Tab 4: Compounding Dashboard
 * Purpose: Prove the compounding effect - "Watch the Moat Grow"
 * Energy: 15%
 */

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getCompoundingMetrics, resetAllDemoData } from '../../lib/api'
import { TrendingUp, Database, Activity, RefreshCw, Clock, DollarSign, TrendingDown, CheckCircle } from 'lucide-react'

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

export default function CompoundingTab() {
  const [data, setData] = useState<CompoundingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)

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

  const handleReset = async () => {
    setResetting(true)
    try {
      console.log('[CompoundingTab] Resetting all demo data...')
      await resetAllDemoData()
      console.log('[CompoundingTab] Demo data reset successfully, reloading...')
      await loadData()
    } catch (error) {
      console.error('[CompoundingTab] Failed to reset demo:', error)
    } finally {
      setResetting(false)
    }
  }

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          SOC Compounding — "Watch the Moat Grow"
        </h2>
        <p className="text-gray-600">
          Same model. Same rules. More intelligence. When competitors deploy, they start at zero. We start at {animatedNodesEnd} patterns.
        </p>
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
                Analyst Hours Saved / Month
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
                Alert Backlog Eliminated / Month
              </div>
            </div>
          </div>

          {/* Executive Note */}
          <div className="mt-4 text-center">
            <p className="text-sm italic text-gray-700">
              💼 Present these numbers to your CFO — this is the business case for AI-augmented security operations.
            </p>
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

        {/* Two-Loop Architecture Diagram (Hero Visual) */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-lg border-2 border-purple-500 shadow-2xl p-8">
          <h3 className="text-xl font-bold text-white mb-2 text-center">
            Two-Loop Architecture
          </h3>
          <p className="text-sm text-gray-400 text-center mb-6">
            The VC Story: Both loops write to the same graph
          </p>

          <div className="relative">
            {/* Center: Context Graph */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
              <div className="bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg p-6 border-4 border-yellow-400 shadow-2xl animate-pulse">
                <div className="text-center">
                  <Database className="w-8 h-8 text-white mx-auto mb-2" />
                  <div className="text-lg font-bold text-white">
                    CONTEXT GRAPH
                  </div>
                  <div className="text-xs text-gray-200 font-semibold">(Neo4j)</div>
                  <div className="mt-2 text-xs text-gray-300 border-t border-gray-400 pt-2">
                    Patterns | Users | Assets<br />Decisions | Playbooks
                  </div>
                </div>
              </div>
            </div>

            {/* Layout grid for loops */}
            <div className="grid grid-cols-2 gap-12 mb-4" style={{ minHeight: '350px' }}>
              {/* Left: Loop 1 - Situation Analyzer */}
              <div className="relative">
                <div className="bg-blue-900/40 rounded-lg border-2 border-blue-400 p-5 h-full">
                  <div className="mb-3">
                    <div className="text-lg font-bold text-blue-300 mb-1">
                      LOOP 1: SITUATION ANALYZER
                    </div>
                    <div className="text-xs text-blue-200 italic mb-3">
                      Smarter WITHIN each decision
                    </div>
                  </div>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full mt-1.5" />
                      <div className="text-sm text-gray-300">Classifies situations</div>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full mt-1.5" />
                      <div className="text-sm text-gray-300">Evaluates options</div>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full mt-1.5" />
                      <div className="text-sm text-gray-300">Reasons over context</div>
                    </div>
                  </div>

                  <div className="mt-auto pt-4 border-t border-blue-700">
                    <div className="text-xs text-blue-300 font-semibold">
                      Demo: Tab 3 →
                    </div>
                  </div>
                </div>

                {/* Connecting line to center */}
                <div className="absolute top-1/2 right-0 w-12 h-0.5 bg-blue-400" style={{ transform: 'translateX(100%)' }} />
              </div>

              {/* Right: Loop 2 - Agent Evolver */}
              <div className="relative">
                <div className="bg-purple-900/40 rounded-lg border-2 border-purple-400 p-5 h-full">
                  <div className="mb-3">
                    <div className="text-lg font-bold text-purple-300 mb-1">
                      LOOP 2: AGENT EVOLVER
                    </div>
                    <div className="text-xs text-purple-200 italic mb-3">
                      Smarter ACROSS all decisions
                    </div>
                  </div>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-purple-400 rounded-full mt-1.5" />
                      <div className="text-sm text-gray-300">Tracks prompt success</div>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-purple-400 rounded-full mt-1.5" />
                      <div className="text-sm text-gray-300">Evolves behavior</div>
                    </div>
                    <div className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-purple-400 rounded-full mt-1.5" />
                      <div className="text-sm text-gray-300">Promotes winners</div>
                    </div>
                  </div>

                  <div className="mt-auto pt-4 border-t border-purple-700">
                    <div className="text-xs text-purple-300 font-semibold">
                      Demo: Tab 2 →
                    </div>
                  </div>
                </div>

                {/* Connecting line to center */}
                <div className="absolute top-1/2 left-0 w-12 h-0.5 bg-purple-400" style={{ transform: 'translateX(-100%)' }} />
              </div>
            </div>

            {/* Bottom: Write Back Connection */}
            <div className="text-center mt-6">
              <div className="inline-block bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 rounded-lg px-6 py-3 border-2 border-yellow-400">
                <div className="text-sm font-bold text-white">
                  BOTH WRITE BACK → TRIGGERED_EVOLUTION
                </div>
              </div>
            </div>
          </div>

          {/* Stats Row */}
          <div className="mt-8 pt-6 border-t border-gray-700">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-slate-800/50 rounded-lg p-3 border border-blue-500/30">
                <div className="text-xs text-gray-400 mb-1">Situation Types</div>
                <div className="text-lg font-bold text-blue-400">
                  2 → 6
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 border border-purple-500/30">
                <div className="text-xs text-gray-400 mb-1">Prompt Variants Evolved</div>
                <div className="text-lg font-bold text-purple-400">
                  0 → 4
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 border border-green-500/30">
                <div className="text-xs text-gray-400 mb-1">Cross-Alert Patterns</div>
                <div className="text-lg font-bold text-green-400">
                  Travel: 47 | Phish: 31
                </div>
              </div>
            </div>
          </div>

          {/* Key Message */}
          <div className="mt-6 text-center">
            <p className="text-sm italic text-gray-400">
              💡 "SIEMs get better rules. Our copilot <span className="text-purple-400 font-semibold">becomes</span> a better copilot."
            </p>
          </div>
        </div>
      </div>

      {/* Recent Evolution Events */}
      <div className="bg-white rounded-lg border shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Database className="w-5 h-5 text-purple-600" />
            Recent Evolution Events
          </h3>
          <button
            onClick={handleReset}
            disabled={resetting}
            className="flex items-center gap-2 px-4 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors disabled:opacity-50 font-semibold"
            title="Reset all demo data: alerts, patterns, decisions, and evolution events"
          >
            <RefreshCw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} />
            {resetting ? 'Resetting All...' : 'Reset All Demo Data'}
          </button>
        </div>

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
