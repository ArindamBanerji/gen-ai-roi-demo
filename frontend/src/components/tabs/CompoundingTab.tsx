/**
 * Tab 4: Compounding Dashboard
 * Purpose: Prove the compounding effect - "Watch the Moat Grow"
 * Energy: 15%
 */

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getCompoundingMetrics, resetAllDemoData } from '../../lib/api'
import { TrendingUp, Database, Activity, RefreshCw } from 'lucide-react'

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
}

export default function CompoundingTab() {
  const [data, setData] = useState<CompoundingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)

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

  // Calculate percentage changes
  const autoCloseChange = headline.auto_close_end - headline.auto_close_start
  const mttrChangePercent = ((headline.mttr_start - headline.mttr_end) / headline.mttr_start * 100)
  const fpInvestigationsChangePercent = ((headline.fp_investigations_start - headline.fp_investigations_end) / headline.fp_investigations_start * 100)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          SOC Compounding — "Watch the Moat Grow"
        </h2>
        <p className="text-gray-600">
          Same model. Same rules. More intelligence. When competitors deploy, they start at zero. We start at {headline.nodes_end} patterns.
        </p>
      </div>

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
                {headline.nodes_end} nodes
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
                {headline.auto_close_start}% → {headline.auto_close_end}%
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
                {headline.mttr_start} min → {headline.mttr_end} min
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
                {headline.fp_investigations_start.toLocaleString()}/wk → {headline.fp_investigations_end.toLocaleString()}/wk
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

        {/* Two-Loop Visual (Hero) */}
        <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg border-2 border-blue-200 shadow p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">
            Two-Loop Architecture
          </h3>
          <div className="space-y-6">
            {/* Traditional SIEM */}
            <div>
              <div className="text-sm font-semibold text-gray-700 mb-2">Traditional SIEM (One Loop)</div>
              <div className="bg-white rounded-lg p-4 border-2 border-gray-300">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-20 h-10 bg-blue-200 rounded flex items-center justify-center text-xs font-semibold">
                    Alert
                  </div>
                  <div className="text-xl">→</div>
                  <div className="w-20 h-10 bg-blue-300 rounded flex items-center justify-center text-xs font-semibold">
                    Detect
                  </div>
                  <div className="text-xl">→</div>
                  <div className="w-20 h-10 bg-blue-200 rounded flex items-center justify-center text-xs font-semibold">
                    Log
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-xl">↓</div>
                  <div className="text-xs text-gray-600">Manual Tuning</div>
                </div>
              </div>
              <div className="mt-2 text-sm italic text-gray-600">
                "Their SIEM gets better rules."
              </div>
            </div>

            {/* Our SOC Copilot */}
            <div>
              <div className="text-sm font-semibold text-purple-700 mb-2">Our SOC Copilot (Two Loops)</div>
              <div className="bg-white rounded-lg p-4 border-2 border-purple-400">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-20 h-10 bg-purple-200 rounded flex items-center justify-center text-xs font-semibold">
                    Alert
                  </div>
                  <div className="text-xl">→</div>
                  <div className="w-20 h-10 bg-purple-300 rounded flex items-center justify-center text-xs font-semibold">
                    Graph
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div className="bg-green-100 rounded p-2 border-2 border-green-400">
                    <div className="text-xs font-semibold text-green-800 text-center">Better Triage</div>
                    <div className="text-xs text-gray-600 text-center">(Context)</div>
                  </div>
                  <div className="bg-blue-100 rounded p-2 border-2 border-blue-400">
                    <div className="text-xs font-semibold text-blue-800 text-center">Better Agent</div>
                    <div className="text-xs text-gray-600 text-center">(Evolution)</div>
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xl mb-1">↓</div>
                  <div className="bg-purple-600 text-white rounded px-4 py-2 font-bold text-sm">
                    COMPOUNDING
                  </div>
                </div>
              </div>
              <div className="mt-2 text-sm italic text-purple-700 font-semibold">
                "Our copilot BECOMES a better copilot."
              </div>
            </div>
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
          We start at <span className="text-yellow-300">{headline.nodes_end} patterns</span>. That's the moat."
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
