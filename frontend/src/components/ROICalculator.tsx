/**
 * ROI Calculator Modal Component (v2.5)
 * Overlays on Tab 4 - allows prospects to input their SOC metrics and see projected savings
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Calculator,
  TrendingUp,
  DollarSign,
  Clock,
  Users,
  AlertCircle,
  ChevronRight,
  Download,
  X,
} from 'lucide-react'
import type { ROIRequest, ROIResponse, ROIDefaults } from '../types/roi'

// ============================================================================
// Custom Hook: Counter Animation (from CompoundingTab)
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

// ============================================================================
// API Functions
// ============================================================================

const API_BASE = '/api'

async function fetchDefaults(): Promise<ROIDefaults> {
  const response = await fetch(`${API_BASE}/roi/defaults`)
  if (!response.ok) throw new Error('Failed to fetch defaults')
  const data = await response.json()
  return data.defaults
}

async function calculateROI(inputs: ROIRequest): Promise<ROIResponse> {
  const response = await fetch(`${API_BASE}/roi/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(inputs),
  })
  if (!response.ok) throw new Error('Failed to calculate ROI')
  return await response.json()
}

// ============================================================================
// Main Component
// ============================================================================

interface ROICalculatorModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function ROICalculatorModal({ isOpen, onClose }: ROICalculatorModalProps) {
  // Input state
  const [inputs, setInputs] = useState<ROIRequest>({
    alerts_per_day: 500,
    analysts: 8,
    avg_salary: 85000,
    current_mttr_minutes: 18,
    current_auto_close_pct: 0.35,
    avg_escalation_cost: 150,
  })

  // Results state
  const [result, setResult] = useState<ROIResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Debounce timer
  const debounceTimer = useRef<NodeJS.Timeout | null>(null)

  // Animated counters for results
  const prevResult = useRef<ROIResponse | null>(null)
  const animatedAutoClose = useCountUp(
    prevResult.current?.projected.auto_close_pct ?? inputs.current_auto_close_pct,
    result?.projected.auto_close_pct ?? inputs.current_auto_close_pct,
    1000,
    2,
    !!result
  )
  const animatedMttr = useCountUp(
    prevResult.current?.projected.mttr_minutes ?? inputs.current_mttr_minutes,
    result?.projected.mttr_minutes ?? inputs.current_mttr_minutes,
    1000,
    1,
    !!result
  )
  const animatedAlertsHandled = useCountUp(
    prevResult.current?.projected.alerts_auto_handled_daily ?? 0,
    result?.projected.alerts_auto_handled_daily ?? 0,
    1000,
    0,
    !!result
  )
  const animatedHoursFreed = useCountUp(
    prevResult.current?.projected.analyst_hours_freed_monthly ?? 0,
    result?.projected.analyst_hours_freed_monthly ?? 0,
    1000,
    0,
    !!result
  )
  const animatedTotalSavings = useCountUp(
    prevResult.current?.savings.total_annual ?? 0,
    result?.savings.total_annual ?? 0,
    1500,
    0,
    !!result
  )

  // Update prevResult when result changes
  useEffect(() => {
    if (result) {
      prevResult.current = result
    }
  }, [result])

  // Fetch defaults on mount
  useEffect(() => {
    if (isOpen) {
      fetchDefaults()
        .then((defaults) => {
          setInputs({
            alerts_per_day: defaults.alerts_per_day,
            analysts: defaults.analysts,
            avg_salary: defaults.avg_salary,
            current_mttr_minutes: defaults.current_mttr_minutes,
            current_auto_close_pct: defaults.current_auto_close_pct,
            avg_escalation_cost: defaults.avg_escalation_cost,
          })
          // Calculate with defaults
          calculateROI({
            alerts_per_day: defaults.alerts_per_day,
            analysts: defaults.analysts,
            avg_salary: defaults.avg_salary,
            current_mttr_minutes: defaults.current_mttr_minutes,
            current_auto_close_pct: defaults.current_auto_close_pct,
            avg_escalation_cost: defaults.avg_escalation_cost,
          })
            .then(setResult)
            .catch((err) => setError(err.message))
        })
        .catch((err) => setError(err.message))
    }
  }, [isOpen])

  // Debounced calculation on input change
  const triggerCalculation = useCallback((newInputs: ROIRequest) => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    debounceTimer.current = setTimeout(() => {
      setLoading(true)
      setError(null)
      calculateROI(newInputs)
        .then(setResult)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false))
    }, 300)
  }, [])

  // Handle input changes
  const updateInput = <K extends keyof ROIRequest>(key: K, value: ROIRequest[K]) => {
    const newInputs = { ...inputs, [key]: value }
    setInputs(newInputs)
    triggerCalculation(newInputs)
  }

  // Handle export (placeholder)
  const handleExport = () => {
    console.log('[ROI] Export to PDF requested')
    console.log('[ROI] Inputs:', inputs)
    console.log('[ROI] Results:', result)
    alert('PDF export not yet implemented')
  }

  // Don't render if not open
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-slate-900 rounded-lg shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-y-auto border border-slate-700">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Calculator className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">ROI Calculator</h2>
                <p className="text-sm text-slate-400">Calculate your projected savings</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>

          {/* Content - Two Columns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
            {/* LEFT COLUMN - Inputs */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  Your Environment
                </h3>

                <div className="space-y-5">
                  {/* Alerts per day */}
                  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-slate-300">
                        Alerts per day
                      </label>
                      <span className="text-sm font-mono text-blue-400">
                        {inputs.alerts_per_day.toLocaleString()}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="50"
                      max="50000"
                      step="50"
                      value={inputs.alerts_per_day}
                      onChange={(e) => updateInput('alerts_per_day', parseInt(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>50</span>
                      <span>50,000</span>
                    </div>
                  </div>

                  {/* SOC analysts */}
                  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-slate-300">
                        SOC analysts
                      </label>
                      <span className="text-sm font-mono text-blue-400">
                        {inputs.analysts}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="200"
                      step="1"
                      value={inputs.analysts}
                      onChange={(e) => updateInput('analysts', parseInt(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>1</span>
                      <span>200</span>
                    </div>
                  </div>

                  {/* Average analyst salary */}
                  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                    <label className="text-sm font-medium text-slate-300 block mb-2">
                      Average analyst salary
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                        $
                      </span>
                      <input
                        type="number"
                        min="40000"
                        max="250000"
                        step="1000"
                        value={inputs.avg_salary}
                        onChange={(e) => updateInput('avg_salary', parseInt(e.target.value))}
                        className="w-full pl-7 pr-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  {/* Current MTTR */}
                  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-slate-300">
                        Current MTTR (minutes)
                      </label>
                      <span className="text-sm font-mono text-blue-400">
                        {inputs.current_mttr_minutes} min
                      </span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="120"
                      step="1"
                      value={inputs.current_mttr_minutes}
                      onChange={(e) => updateInput('current_mttr_minutes', parseInt(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>1</span>
                      <span>120</span>
                    </div>
                  </div>

                  {/* Current auto-close % */}
                  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium text-slate-300">
                        Current auto-close rate
                      </label>
                      <span className="text-sm font-mono text-blue-400">
                        {(inputs.current_auto_close_pct * 100).toFixed(0)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="0.95"
                      step="0.05"
                      value={inputs.current_auto_close_pct}
                      onChange={(e) => updateInput('current_auto_close_pct', parseFloat(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>0%</span>
                      <span>95%</span>
                    </div>
                  </div>

                  {/* Average escalation cost */}
                  <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                    <label className="text-sm font-medium text-slate-300 block mb-2">
                      Average escalation cost
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                        $
                      </span>
                      <input
                        type="number"
                        min="50"
                        max="1000"
                        step="10"
                        value={inputs.avg_escalation_cost}
                        onChange={(e) => updateInput('avg_escalation_cost', parseInt(e.target.value))}
                        className="w-full pl-7 pr-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN - Results */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  Projected Impact
                </h3>

                {error && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-4">
                    <div className="flex items-center gap-2 text-red-400">
                      <AlertCircle className="w-5 h-5" />
                      <span className="text-sm">{error}</span>
                    </div>
                  </div>
                )}

                {loading && !result && (
                  <div className="text-center py-8 text-slate-400">
                    <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
                    <p>Calculating...</p>
                  </div>
                )}

                {result && (
                  <>
                    {/* Metric Cards - 2x2 Grid */}
                    <div className="grid grid-cols-2 gap-3 mb-6">
                      {/* Auto-close rate */}
                      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
                        <div className="text-xs text-slate-400 mb-1">Auto-close rate</div>
                        <div className="flex items-center gap-1 text-lg font-bold text-white">
                          <span className="text-slate-500">
                            {(inputs.current_auto_close_pct * 100).toFixed(0)}%
                          </span>
                          <ChevronRight className="w-4 h-4 text-green-400" />
                          <span className="text-green-400">{(animatedAutoClose * 100).toFixed(0)}%</span>
                        </div>
                      </div>

                      {/* MTTR */}
                      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
                        <div className="text-xs text-slate-400 mb-1">MTTR</div>
                        <div className="flex items-center gap-1 text-lg font-bold text-white">
                          <span className="text-slate-500">
                            {inputs.current_mttr_minutes} min
                          </span>
                          <ChevronRight className="w-4 h-4 text-green-400" />
                          <span className="text-green-400">{animatedMttr.toFixed(1)} min</span>
                        </div>
                      </div>

                      {/* Alerts auto-handled */}
                      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
                        <div className="text-xs text-slate-400 mb-1">Alerts auto-handled</div>
                        <div className="text-lg font-bold text-blue-400">
                          {animatedAlertsHandled.toLocaleString()}/day
                        </div>
                      </div>

                      {/* Analyst hours freed */}
                      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
                        <div className="text-xs text-slate-400 mb-1">Hours freed</div>
                        <div className="text-lg font-bold text-purple-400">
                          {animatedHoursFreed.toLocaleString()}/mo
                        </div>
                      </div>
                    </div>

                    {/* Large Annual Savings Card */}
                    <div className="bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30 rounded-lg p-6 mb-6">
                      <div className="flex items-center gap-2 mb-2">
                        <DollarSign className="w-5 h-5 text-purple-400" />
                        <span className="text-sm font-medium text-purple-300">Annual Savings</span>
                      </div>
                      <div className="text-4xl font-bold text-white mb-4">
                        ${animatedTotalSavings.toLocaleString()}
                      </div>
                      <div className="flex items-center gap-6 text-sm">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-blue-400" />
                          <span className="text-slate-300">
                            Payback: <span className="font-semibold text-white">
                              {result.savings.payback_weeks} weeks
                            </span>
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-green-400" />
                          <span className="text-slate-300">
                            ROI: <span className="font-semibold text-white">
                              {result.savings.roi_multiple}x
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Savings Breakdown */}
                    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-4">
                      <div className="text-sm font-medium text-slate-300 mb-3">
                        Savings Breakdown
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-400">Analyst time</span>
                          <span className="font-mono text-white">
                            ${result.savings.analyst_time_annual.toLocaleString()}
                            <span className="text-slate-500 ml-2">
                              ({((result.savings.analyst_time_annual / result.savings.total_annual) * 100).toFixed(0)}%)
                            </span>
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-400">Escalation cost</span>
                          <span className="font-mono text-white">
                            ${result.savings.escalation_cost_annual.toLocaleString()}
                            <span className="text-slate-500 ml-2">
                              ({((result.savings.escalation_cost_annual / result.savings.total_annual) * 100).toFixed(0)}%)
                            </span>
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-400">Compliance</span>
                          <span className="font-mono text-white">
                            ${result.savings.compliance_annual.toLocaleString()}
                            <span className="text-slate-500 ml-2">
                              ({((result.savings.compliance_annual / result.savings.total_annual) * 100).toFixed(0)}%)
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Narrative */}
                    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                      <p className="text-sm text-slate-300 italic leading-relaxed">
                        {result.narrative}
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700">
            <button
              onClick={handleExport}
              disabled={!result}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Export as PDF
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
