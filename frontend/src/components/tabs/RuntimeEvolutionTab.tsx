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
} from 'lucide-react'
import {
  ComposedChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import * as api from '@/lib/api'
import { domainConfig } from '@/lib/domain'

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
  centroids: number[][][]   // shape (6, 4, 6)
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
  decision_number: number
  centroid_delta_norm: number
  correct: boolean
  category: string
  action: string
}

interface CentroidEvolutionData {
  evolution: CentroidEvolutionEntry[]
  message: string | null
}

const DEFAULT_ALERT_ID = 'ALERT-7823'

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
  const [centroidEvolution, setCentroidEvolution] = useState<CentroidEvolutionData | null>(null)
  const [centroidEvoLoading, setCentroidEvoLoading] = useState(false)
  const [centroidEvoError, setCentroidEvoError] = useState(false)
  const [activeSection, setActiveSection] = useState<'a' | 'b' | 'c' | 'd'>('a')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [pendingDecisionId, setPendingDecisionId] = useState<string | null>(null)

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
    if (result) {
      loadRewardSummary()
    }
  }, [result])

  useEffect(() => {
    if (result) {
      setVisibleChecks([])
      result.eval_gate.checks.forEach((_, index) => {
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
      const data = await fetch('/api/soc/profile').then(r => r.json())
      setProfileStateFull(data as ProfileStateWithIks)
      setProfileState(data as ProfileState)
    } catch (error) {
      console.error('Failed to load profile state:', error)
    }
  }

  const loadGraphStats = async () => {
    try {
      const data = await fetch('/api/soc/graph-stats').then(r => r.json())
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
      setCentroidEvolution(data as CentroidEvolutionData)
    } catch {
      setCentroidEvoError(true)
    } finally {
      setCentroidEvoLoading(false)
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
  const decisionCount = iks?.decision_count ?? profileState?.decision_count ?? 0

  const categoryStats = (() => {
    if (!centroidEvolution || centroidEvolution.evolution.length === 0) return null
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    centroidEvolution.evolution.forEach(e => {
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
    if (!centroidEvolution) return []
    if (categoryFilter === 'all') return centroidEvolution.evolution
    return centroidEvolution.evolution.filter(e => e.category === categoryFilter)
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
    if (!centroidEvolution) return []
    return [...new Set(centroidEvolution.evolution.map(e => e.category))]
  })()

  const categoryConvergenceRows = (() => {
    const cats = profileState?.categories ?? []
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    if (centroidEvolution) {
      centroidEvolution.evolution.forEach(e => {
        if (!grouped[e.category]) grouped[e.category] = []
        grouped[e.category].push(e)
      })
    }
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
    if (centroidEvolution) {
      centroidEvolution.evolution.forEach(e => {
        if (!grouped[e.category]) grouped[e.category] = []
        grouped[e.category].push(e)
      })
    }
    return cats.map(cat => {
      const entries = grouped[cat] ?? []
      if (entries.length < 5) return null
      const pct = Math.round(entries.filter(e => e.correct).length / entries.length * 100)
      return `${cat.replace(/_/g, ' ')}: your system resolves ${pct}% of decisions correctly after ${entries.length} verified decisions.`
    }).filter(Boolean) as string[]
  })()

  const driftAlerts = (() => {
    const D_MAX = 0.30
    if (!centroidEvolution || centroidEvolution.evolution.length < 50) return null
    const grouped: Record<string, CentroidEvolutionEntry[]> = {}
    centroidEvolution.evolution.forEach(e => {
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
            {iks?.current === null || iks?.current === undefined ? (
              <span className="text-gray-500 italic">&mdash; (baseline not established)</span>
            ) : (
              <>
                <span className="font-bold text-soc-secondary">{iks.current.toFixed(1)}</span>
                <span className="text-gray-400">{iksArrow}</span>
                <span className={`text-xs ${iks.delta_7d !== null && iks.delta_7d !== undefined && iks.delta_7d > 0 ? 'text-green-400' : 'text-gray-500'}`}>
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
              <div className="bg-soc-card rounded-lg border border-gray-800 p-8 text-center">
                <Activity className="w-8 h-8 mx-auto mb-3 text-gray-600" />
                <p className="text-gray-500 text-sm">
                  {pendingDecisionId
                    ? `Decision ${pendingDecisionId} was recorded \u2014 process a new alert to see live decision trace.`
                    : `No verified decisions yet \u2014 click \u201cProcess Alert\u201d above to begin.`}
                </p>
              </div>
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
                    {result.eval_gate.checks.map((check, index) => {
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
                        {result.gae_scoring.factor_names.map((name, i) => (
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
                        {Object.entries(result.gae_scoring.action_probabilities).sort(([, a], [, b]) => b - a).map(([action, prob]) => (
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
                {centroidEvolution && centroidEvolution.evolution.length > 0 && (() => {
                  const last = centroidEvolution.evolution[centroidEvolution.evolution.length - 1]
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
                            {profileState.actions.map(action => (
                              <th key={action} style={{ width: 80, textAlign: 'center', padding: '4px 8px', fontSize: 11, color: '#9ca3af', fontWeight: 500, textTransform: 'capitalize' }}>{action}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {profileState.categories.map((cat, cIdx) => (
                            <tr key={cat}>
                              <td style={{ padding: '4px 8px', fontSize: 11, color: '#d1d5db', whiteSpace: 'nowrap' }}>{cat.replace(/_/g, ' ')}</td>
                              {profileState.actions.map((_, aIdx) => {
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
                            {Object.entries(result.gae_summary.w_norms).map(([action, norm]) => (
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

              {/* F1. IKS Block */}
              <div className="bg-soc-card rounded-lg border border-gray-800 p-5">
                <h4 className="text-sm font-semibold text-gray-200 mb-3">Institutional Knowledge Score (IKS)</h4>
                {!iks ? (
                  <div className="text-sm text-gray-500 py-2">Loading IKS&hellip;</div>
                ) : iks.current === null ? (
                  <div className="text-sm text-gray-400 italic">IKS: &mdash; (baseline not established)</div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="text-3xl font-bold font-mono text-soc-secondary">{iks.current.toFixed(1)}</div>
                        <div className="text-xs text-gray-500">/ 100</div>
                      </div>
                      <div>
                        <div className={`text-lg font-semibold ${iks.delta_7d !== null && iks.delta_7d !== undefined && iks.delta_7d > 0 ? 'text-green-400' : iks.delta_7d !== null && iks.delta_7d !== undefined && iks.delta_7d < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                          {iksArrow} {iksDeltaLabel}
                        </div>
                      </div>
                    </div>
                    <div className="bg-soc-bg rounded border border-gray-700 p-3">
                      <p className="text-sm text-gray-300 italic">{iks.interpretation}</p>
                    </div>
                    {iks.estimated && (!iks.trend || iks.trend.length === 0) && (
                      <p className="text-xs text-gray-500 italic">(Drift trend available after first 50 verified decisions)</p>
                    )}
                  </div>
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

            </div>
          </div>

        </div>{/* end main sections */}
      </div>{/* end left-rail + sections flex */}

    </div>
  )
}
