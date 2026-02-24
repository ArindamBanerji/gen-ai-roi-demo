import { useState, useEffect, useRef } from 'react'
import {
  Activity,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  DollarSign,
  Shield,
  Network,
  Play,
  ChevronRight,
  FileText,
  TrendingDown,
  RefreshCw,
} from 'lucide-react'
import { getAlerts, analyzeAlert, executeAction, resetAlerts, checkPolicyConflict, refreshThreatIntel, getDecisionFactors } from '../../lib/api'
import OutcomeFeedback from '../OutcomeFeedback'
import PolicyConflict from '../PolicyConflict'

interface Alert {
  id: string
  alert_type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  asset_hostname: string
  user_name: string
  timestamp: string
  status: string
  source_location: string
}

interface GraphNode {
  id: string
  label: string
  type: string
  properties: Record<string, any>
}

interface GraphRelationship {
  source: string
  target: string
  type: string
}

interface AnalysisResult {
  alert: any
  analysis: {
    root_cause: string
    severity_assessment: string
  }
  context: {
    nodes_count: number
    subgraphs_traversed: string[]
    patterns_matched: number
    key_facts: Array<{ source: string; fact: string }>
  }
  recommendation: {
    action: string
    confidence: number
    reasoning: string
    pattern_id?: string
    playbook_id?: string
  }
  graph_data: {
    nodes: GraphNode[]
    relationships: GraphRelationship[]
  }
  situation_analysis?: {
    situation_type: string
    situation_confidence: number
    factors_detected: string[]
    options_evaluated: Array<{
      action: string
      score: number
      factors: string[]
      estimated_resolution_time: string
      estimated_analyst_cost: number
      risk_if_wrong: string
    }>
    selected_option: string
    selection_reasoning: string
    decision_economics: {
      time_saved: string
      cost_avoided: string
      monthly_projection: string
    }
  }
}

interface ClosedLoopResult {
  receipt: {
    id: string
    action: string
    timestamp: string
    target_system: string
    target_system_response: string
  }
  verification: {
    verified: boolean
    verification_method: string
  }
  evidence: {
    decision_id: string
    trace_captured: boolean
    nodes_consulted: number
  }
  kpi_impact: {
    metric: string
    contribution: string
    previous_avg: number
    new_avg: number
  }
}

interface PolicyResolutionData {
  has_conflict: boolean
  resolution: {
    action_adjusted: string
    original_action: string
    winning_policy: string
  } | null
}

interface ThreatIntelStatus {
  source: string
  indicators_ingested: number
  timestamp: string
  enrichment_summary: Array<{
    value: string
    type: string
    severity: string
    source: string
    context: string
  }>
}

interface DecisionFactor {
  name: string
  value: number
  weight: number
  contribution: 'high' | 'medium' | 'low' | 'none'
  explanation: string
}

interface DecisionFactors {
  alert_id: string
  factors: DecisionFactor[]
  recommended_action: string
  confidence: number
  decision_method: string
  weights_note: string
}

export default function AlertTriageTab() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [closedLoop, setClosedLoop] = useState<ClosedLoopResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [activeStep, setActiveStep] = useState(0)
  const [resetting, setResetting] = useState(false)
  const [policyResolution, setPolicyResolution] = useState<PolicyResolutionData | null>(null)

  // Ref to preserve feedback panel visibility (avoids stale closure bug)
  const preserveFeedbackRef = useRef(false)

  const [threatIntel, setThreatIntel] = useState<ThreatIntelStatus | null>(null)
  const [threatIntelLoading, setThreatIntelLoading] = useState(false)

  const [decisionFactors, setDecisionFactors] = useState<DecisionFactors | null>(null)
  const [decisionFactorsCollapsed, setDecisionFactorsCollapsed] = useState(false)

  useEffect(() => {
    loadAlertQueue()
  }, [])

  const handleRefreshThreatIntel = async () => {
    setThreatIntelLoading(true)
    try {
      const data = await refreshThreatIntel()
      setThreatIntel(data as ThreatIntelStatus)
    } catch {
      // Badge remains in "Not loaded" state
    } finally {
      setThreatIntelLoading(false)
    }
  }

  // Auto-fetch on mount so badge shows data immediately if backend is up
  useEffect(() => {
    handleRefreshThreatIntel()
  }, [])

  useEffect(() => {
    console.log('[AlertTriageTab] alerts state updated:', alerts)
    console.log('[AlertTriageTab] alerts.length:', alerts.length)
  }, [alerts])

  const loadAlertQueue = async () => {
    try {
      console.log('[AlertTriageTab] Loading alert queue...')
      const data = await getAlerts()
      console.log('[AlertTriageTab] Received data:', data)
      console.log('[AlertTriageTab] data.alerts:', data.alerts)
      console.log('[AlertTriageTab] Number of alerts:', data.alerts?.length)

      if (!data || !data.alerts) {
        console.error('[AlertTriageTab] Invalid response structure:', data)
        setAlerts([])
        return
      }

      if (!Array.isArray(data.alerts)) {
        console.error('[AlertTriageTab] data.alerts is not an array:', typeof data.alerts)
        setAlerts([])
        return
      }

      setAlerts(data.alerts)
      console.log('[AlertTriageTab] Set alerts state to:', data.alerts)

      // Only auto-select first alert on initial load or manual refresh
      // Don't auto-select if preserveFeedbackRef is true (user just executed action, needs to give feedback)
      // Using ref avoids stale closure bug where closedLoop state is captured as null
      if (data.alerts.length > 0 && !preserveFeedbackRef.current) {
        setSelectedAlert(data.alerts[0])
        console.log('[AlertTriageTab] Selected first alert:', data.alerts[0])
      } else if (data.alerts.length === 0) {
        console.log('[AlertTriageTab] No alerts in response')
      } else if (preserveFeedbackRef.current) {
        console.log('[AlertTriageTab] Skipped auto-select (preserving feedback state)')
      }
    } catch (error) {
      console.error('[AlertTriageTab] Failed to load alerts:', error)
      setAlerts([])
    }
  }

  const analyzeAlertHandler = async (alert: Alert) => {
    setLoading(true)
    setAnalysis(null)
    setClosedLoop(null)
    setActiveStep(0)
    setPolicyResolution(null)
    setDecisionFactors(null)

    try {
      const data = await analyzeAlert(alert.id)
      setAnalysis(data)
      try {
        const policyData = await checkPolicyConflict(alert.id)
        setPolicyResolution(policyData as PolicyResolutionData)
      } catch {
        // Non-critical — PolicyConflict component handles its own display
      }
      try {
        const factorsData = await getDecisionFactors(alert.id)
        setDecisionFactors(factorsData as DecisionFactors)
      } catch {
        // Non-critical — fail silently, panel won't render
      }
    } catch (error) {
      console.error('Failed to analyze alert:', error)
    } finally {
      setLoading(false)
    }
  }

  const executeActionHandler = async () => {
    if (!selectedAlert || !analysis) return

    setExecuting(true)
    setClosedLoop(null)

    try {
      const data = await executeAction(selectedAlert.id)
      setClosedLoop(data)

      // Preserve feedback panel visibility when queue reloads
      preserveFeedbackRef.current = true

      // Animate steps
      for (let i = 0; i < 4; i++) {
        setTimeout(() => setActiveStep(i + 1), i * 800)
      }

      // Refresh alert queue
      setTimeout(loadAlertQueue, 3200)
    } catch (error) {
      console.error('Failed to execute action:', error)
    } finally {
      setTimeout(() => setExecuting(false), 3200)
    }
  }

  const handleAlertSelect = (alert: Alert) => {
    // Clear feedback preservation when user manually selects a different alert
    preserveFeedbackRef.current = false
    setSelectedAlert(alert)
    analyzeAlertHandler(alert)
  }

  const handleResetAlerts = async () => {
    setResetting(true)
    try {
      console.log('[AlertTriageTab] Resetting alerts...')
      await resetAlerts()
      console.log('[AlertTriageTab] Alerts reset successfully, reloading queue...')
      await loadAlertQueue()
      // Clear current selection
      setSelectedAlert(null)
      setAnalysis(null)
      setClosedLoop(null)
      setPolicyResolution(null)
      setDecisionFactors(null)
    } catch (error) {
      console.error('[AlertTriageTab] Failed to reset alerts:', error)
    } finally {
      setResetting(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50'
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50'
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50'
      case 'low':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50'
    }
  }

  const getActionLabel = (action: string) => {
    return action.replace(/_/g, ' ').toUpperCase()
  }

  // True when policy conflict resolution requires escalation, overriding the AI recommendation
  const policyOverrideActive =
    policyResolution?.has_conflict === true &&
    policyResolution?.resolution?.action_adjusted === 'escalate_tier2'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-soc-card rounded-lg p-6 border border-gray-800">
        <div className="flex items-center gap-3 mb-2">
          <Activity className="w-6 h-6 text-soc-primary" />
          <h2 className="text-xl font-semibold">Alert Triage</h2>
        </div>
        <p className="text-gray-400 text-sm">
          Watch the security graph think. 47 nodes consulted for contextual
          decision-making.
        </p>
        <div className="mt-3 text-sm text-soc-primary">
          "A SIEM stops at detect. We close the loop."
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Alert Queue Sidebar */}
        <div className="col-span-1 bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm">Alert Queue</h3>
              <span className="px-2 py-1 bg-soc-primary/20 text-soc-primary text-xs rounded">
                {alerts.length}
              </span>
            </div>
            <button
              onClick={handleResetAlerts}
              disabled={resetting}
              className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed rounded text-xs transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${resetting ? 'animate-spin' : ''}`} />
              {resetting ? 'Resetting...' : 'Reset Alerts'}
            </button>
          </div>

          <div className="divide-y divide-gray-800">
            {alerts.map((alert) => (
              <button
                key={alert.id}
                onClick={() => handleAlertSelect(alert)}
                className={`w-full px-4 py-3 text-left hover:bg-soc-bg transition-colors ${
                  selectedAlert?.id === alert.id ? 'bg-soc-bg border-l-2 border-soc-primary' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="font-mono text-sm font-semibold">
                    {alert.id}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-semibold border ${getSeverityColor(alert.severity)}`}
                  >
                    {alert.severity.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  {alert.alert_type.replace(/_/g, ' ')}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {alert.user_name} • {alert.asset_hostname}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="col-span-2 space-y-6">

          {/* Threat Intel status badge — always visible */}
          <div className="flex items-center gap-2 text-xs bg-soc-card rounded-lg px-4 py-2 border border-gray-800">
            <span>🛡️</span>
            <span className="text-gray-400">Threat Intel:</span>
            {threatIntel ? (
              <>
                <span className="font-semibold text-white">
                  {threatIntel.indicators_ingested} indicators
                </span>
                <span className="text-gray-600">·</span>
                <span
                  className={
                    threatIntel.source.includes('pulsedive')
                      ? 'font-semibold text-green-400'
                      : 'font-semibold text-amber-400'
                  }
                >
                  {threatIntel.source.includes('pulsedive') ? 'Pulsedive (live)' : 'Local fallback'}
                </span>
                <span className="text-gray-600">·</span>
                <span className="text-gray-500">
                  Last refreshed:{' '}
                  {threatIntel.timestamp.split('T')[1]?.slice(0, 8) ?? threatIntel.timestamp}
                </span>
              </>
            ) : (
              <span className="text-gray-500 italic">Not loaded · Click Refresh</span>
            )}
            <button
              onClick={handleRefreshThreatIntel}
              disabled={threatIntelLoading}
              className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-gray-300 transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${threatIntelLoading ? 'animate-spin' : ''}`} />
              {threatIntelLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {/* Selected Alert Details */}
          {selectedAlert && (
            <div className="bg-soc-card rounded-lg p-4 border border-gray-800">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Selected: {selectedAlert.id}</h3>
                {loading && (
                  <Clock className="w-4 h-4 text-gray-400 animate-spin" />
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Type:</span>{' '}
                  {selectedAlert.alert_type.replace(/_/g, ' ')}
                </div>
                <div>
                  <span className="text-gray-500">Source:</span>{' '}
                  {selectedAlert.source_location}
                </div>
                <div>
                  <span className="text-gray-500">Asset:</span>{' '}
                  {selectedAlert.asset_hostname}
                </div>
                <div>
                  <span className="text-gray-500">User:</span> {selectedAlert.user_name}
                </div>
              </div>
            </div>
          )}

          {/* Graph Visualization */}
          {analysis && (
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Network className="w-4 h-4" />
                    Security Context Graph
                    <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide bg-blue-500 text-white">
                      CONSUME
                    </span>
                  </h3>
                  <div className="flex gap-3 text-xs text-gray-400">
                    <span>[{analysis.context.nodes_count} nodes]</span>
                    <span>[{analysis.context.subgraphs_traversed.length} subgraphs]</span>
                    <span>[{analysis.context.patterns_matched} patterns]</span>
                  </div>
                </div>

              </div>

              {/* Simple Graph Visualization */}
              <div className="p-6 bg-soc-bg/50">
                <div className="flex flex-wrap items-center justify-center gap-4">
                  {analysis.graph_data.nodes.map((node) => (
                    <div
                      key={node.id}
                      className={`px-4 py-3 rounded-lg border-2 ${
                        node.type === 'Alert'
                          ? 'bg-red-500/10 border-red-500/50 text-red-400'
                          : node.type === 'User'
                          ? 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                          : node.type === 'Asset'
                          ? 'bg-green-500/10 border-green-500/50 text-green-400'
                          : node.type === 'TravelContext'
                          ? 'bg-purple-500/10 border-purple-500/50 text-purple-400'
                          : node.type === 'AttackPattern'
                          ? 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400'
                          : 'bg-gray-500/10 border-gray-500/50 text-gray-400'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1">{node.type}</div>
                      <div className="text-sm font-bold">{node.label}</div>
                      {Object.keys(node.properties).length > 0 && (
                        <div className="text-xs mt-1 opacity-70">
                          {Object.entries(node.properties)
                            .slice(0, 2)
                            .map(([key, value]) => (
                              <div key={key}>
                                {key}: {String(value)}
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Key Facts */}
                <div className="mt-4 space-y-2">
                  <h4 className="text-sm font-semibold text-gray-400">Key Facts:</h4>
                  {analysis.context.key_facts.map((fact, idx) => (
                    <div
                      key={idx}
                      className="text-sm bg-soc-card/50 rounded p-2 border border-gray-800"
                    >
                      <span className="text-gray-500">[{fact.source}]</span>{' '}
                      {fact.fact}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Situation Analyzer Panel */}
          {analysis && analysis.situation_analysis && (
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-800">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold flex items-center gap-2">
                      🔍 Situation Analysis
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide bg-blue-500 text-white">
                        CONSUME
                      </span>
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      (Loop 1: Smarter WITHIN this run)
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Situation Type Badge */}
                <div className="flex items-center gap-4">
                  <div
                    className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm ${
                      analysis.situation_analysis.situation_type === 'travel_login_anomaly'
                        ? 'bg-blue-500/20 text-blue-400 border-2 border-blue-500/50'
                        : analysis.situation_analysis.situation_type === 'known_phishing_campaign'
                        ? 'bg-orange-500/20 text-orange-400 border-2 border-orange-500/50'
                        : analysis.situation_analysis.situation_type === 'malware_on_critical_asset'
                        ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50'
                        : analysis.situation_analysis.situation_type === 'vip_after_hours'
                        ? 'bg-amber-500/20 text-amber-400 border-2 border-amber-500/50'
                        : analysis.situation_analysis.situation_type === 'data_exfil_attempt'
                        ? 'bg-red-500/20 text-red-400 border-2 border-red-500/50'
                        : 'bg-gray-500/20 text-gray-400 border-2 border-gray-500/50'
                    }`}
                  >
                    {analysis.situation_analysis.situation_type.toUpperCase().replace(/_/g, ' ')}
                  </div>
                  <div className="text-sm text-gray-400">
                    <span className="font-semibold text-white">
                      {(analysis.situation_analysis.situation_confidence * 100).toFixed(0)}%
                    </span>{' '}
                    confidence
                  </div>
                </div>

                {/* Factors Detected */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-400 mb-3">Factors Detected:</h4>
                  <div className="space-y-2">
                    {analysis.situation_analysis.factors_detected.map((factor, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-soc-success mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-gray-300">{factor}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Options Evaluated */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-400 mb-3">Options Evaluated:</h4>
                  <div className="space-y-3">
                    {analysis.situation_analysis.options_evaluated.map((option, idx) => {
                      const isSelected = option.action === analysis.situation_analysis?.selected_option
                      const percentage = (option.score * 100).toFixed(0)
                      const widthPercentage = option.score * 100

                      return (
                        <div key={idx} className="space-y-1">
                          <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <span
                                className={`font-semibold ${
                                  isSelected ? 'text-soc-success' : 'text-gray-400'
                                }`}
                              >
                                {option.action.toUpperCase().replace(/_/g, ' ')}
                              </span>
                              {isSelected && (
                                <span className="px-2 py-0.5 bg-soc-success/20 text-soc-success text-xs font-bold rounded">
                                  Selected ✓
                                </span>
                              )}
                            </div>
                            <span className={isSelected ? 'text-white font-bold' : 'text-gray-500'}>
                              {percentage}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${
                                isSelected ? 'bg-soc-success' : 'bg-gray-600'
                              }`}
                              style={{ width: `${widthPercentage}%` }}
                            />
                          </div>
                          {/* Decision Economics Row */}
                          <div className="flex items-center gap-4 text-xs mt-2">
                            <div className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-gray-500" />
                              <span className={isSelected ? 'text-green-400 font-semibold' : 'text-gray-500'}>
                                {option.estimated_resolution_time}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <DollarSign className="w-3 h-3 text-gray-500" />
                              <span className={isSelected ? 'text-green-400 font-semibold' : 'text-gray-500'}>
                                ${option.estimated_analyst_cost.toFixed(0)}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Shield className="w-3 h-3 text-gray-500" />
                              <span className="text-gray-500">
                                {option.risk_if_wrong.split(' — ')[0]}
                              </span>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Decision Economics Summary */}
                {analysis.situation_analysis.decision_economics && (
                  <div className="p-4 bg-gradient-to-r from-green-900/20 to-blue-900/20 rounded-lg border border-green-500/30">
                    <h4 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
                      <DollarSign className="w-4 h-4" />
                      Decision Economics
                    </h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-start gap-2">
                        <Clock className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-300">
                          <span className="font-semibold text-white">Time saved:</span>{' '}
                          {analysis.situation_analysis.decision_economics.time_saved}
                        </span>
                      </div>
                      <div className="flex items-start gap-2">
                        <DollarSign className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-300">
                          <span className="font-semibold text-white">Cost avoided:</span>{' '}
                          {analysis.situation_analysis.decision_economics.cost_avoided}
                        </span>
                      </div>
                      <div className="flex items-start gap-2">
                        <TrendingDown className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-300">
                          <span className="font-semibold text-white">Monthly projection:</span>{' '}
                          {analysis.situation_analysis.decision_economics.monthly_projection}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Selection Reasoning */}
                <div className="p-3 bg-soc-bg/50 rounded border border-gray-800">
                  <p className="text-sm italic text-gray-400">
                    {analysis.situation_analysis.selection_reasoning}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Why This Decision? Panel (v3.0) */}
          {analysis && decisionFactors && (
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">🔎 Why This Decision?</h3>
                    <p className="text-xs text-gray-500 mt-1">Factor breakdown for this alert</p>
                  </div>
                  <button
                    onClick={() => setDecisionFactorsCollapsed((c) => !c)}
                    className="p-1 hover:bg-gray-700 rounded transition-colors"
                    aria-label={decisionFactorsCollapsed ? 'Expand' : 'Collapse'}
                  >
                    {decisionFactorsCollapsed
                      ? <ChevronDown className="w-4 h-4 text-gray-400" />
                      : <ChevronUp className="w-4 h-4 text-gray-400" />
                    }
                  </button>
                </div>
              </div>

              {!decisionFactorsCollapsed && (
                <div className="p-6 space-y-4">
                  {decisionFactors.factors.map((factor) => {
                    const barWidth = Math.round(factor.value * factor.weight * 100)
                    const isThreatIntel = factor.name === 'threat_intel_enrichment'
                    const isPulsedive = isThreatIntel && factor.explanation.includes('Pulsedive')
                    const displayName = factor.name
                      .split('_')
                      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                      .join(' ')

                    const barColor =
                      factor.contribution === 'high'
                        ? 'bg-green-500'
                        : factor.contribution === 'medium'
                        ? 'bg-amber-500'
                        : 'bg-gray-600'

                    const labelColor =
                      factor.contribution === 'high'
                        ? 'text-green-400'
                        : factor.contribution === 'medium'
                        ? 'text-amber-400'
                        : 'text-gray-500'

                    return (
                      <div
                        key={factor.name}
                        className={`space-y-1 ${
                          isThreatIntel
                            ? 'ring-1 ring-blue-500/30 rounded-md p-2 -mx-2 bg-blue-500/5'
                            : ''
                        }`}
                      >
                        <div className="flex items-center justify-between text-sm">
                          <span
                            className={`font-medium ${
                              isThreatIntel ? 'text-blue-300' : 'text-gray-300'
                            }`}
                          >
                            {isPulsedive && <span className="mr-1">🛡️</span>}
                            {displayName}
                          </span>
                          <span className={`text-xs font-semibold uppercase tracking-wide ${labelColor}`}>
                            {factor.contribution}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${barColor} transition-all duration-500`}
                              style={{ width: `${barWidth}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500 w-8 text-right shrink-0">
                            {barWidth}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 leading-relaxed">
                          {factor.explanation}
                        </p>
                      </div>
                    )
                  })}

                  <div className="pt-3 border-t border-gray-800 space-y-1">
                    <p className="text-xs text-gray-400">
                      <span className="font-semibold">Decision method:</span>{' '}
                      {decisionFactors.decision_method}
                    </p>
                    <p className="text-xs text-gray-600 italic">
                      {decisionFactors.weights_note}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Policy Conflict (v2.5) */}
          {analysis && selectedAlert && (
            <PolicyConflict alertId={selectedAlert.id} isVisible={!!analysis} />
          )}

          {/* Recommendation Panel */}
          {analysis && (
            <div
              className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden"
              style={{ opacity: policyOverrideActive ? 0.6 : 1 }}
            >
              {/* Policy Override Banner — bright amber, prominent, dark text on amber-500 */}
              {policyOverrideActive && (
                <div className="px-4 py-3 bg-amber-500 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-gray-900 mt-0.5 shrink-0" />
                  <p className="text-sm text-gray-900 font-medium">
                    <span className="font-bold">⚠ Policy Override:</span>{' '}
                    Security policy requires escalation. See Policy Conflict panel above.
                  </p>
                </div>
              )}

              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                <h3 className="font-semibold">Recommendation</h3>
                <span className="text-sm text-gray-400">
                  Confidence: {(analysis.recommendation.confidence * 100).toFixed(0)}%
                </span>
              </div>

              <div className="p-4 space-y-4">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-soc-success" />
                  <span className="text-lg font-semibold text-soc-success">
                    {getActionLabel(analysis.recommendation.action)}
                  </span>
                </div>

                <p className="text-sm leading-relaxed text-gray-300">
                  {analysis.recommendation.reasoning}
                </p>

                {analysis.recommendation.pattern_id && (
                  <div className="text-xs text-gray-500">
                    Pattern: {analysis.recommendation.pattern_id}
                  </div>
                )}

                <button
                  onClick={executeActionHandler}
                  disabled={executing || !!closedLoop}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-soc-primary hover:bg-soc-primary/80 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors"
                >
                  <Play className="w-4 h-4" />
                  {executing
                    ? 'Executing...'
                    : closedLoop
                    ? 'Executed'
                    : policyOverrideActive
                    ? 'Apply Policy Resolution'
                    : 'Apply Recommendation'}
                </button>
              </div>
            </div>
          )}

          {/* Closed Loop Execution */}
          {closedLoop && (
            <div className="bg-gradient-to-r from-soc-success/20 to-soc-primary/20 rounded-lg border-2 border-soc-success/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-soc-success/50 flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-soc-success" />
                <h3 className="font-semibold text-soc-success flex items-center gap-2">
                  ✓ CLOSED LOOP (What SIEMs don't do)
                  <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide bg-green-500 text-white">
                    ACTIVATE
                  </span>
                </h3>
              </div>

              <div className="p-4 space-y-3">
                {/* Step 1: EXECUTED */}
                <div
                  className={`flex items-start gap-3 p-3 rounded border transition-all ${
                    activeStep >= 1
                      ? 'bg-soc-success/10 border-soc-success/50'
                      : 'bg-soc-bg/50 border-gray-700 opacity-50'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {activeStep >= 1 ? (
                      <CheckCircle className="w-5 h-5 text-soc-success" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm mb-1">1. EXECUTED</div>
                    <div className="text-xs text-gray-400">
                      {closedLoop.receipt.target_system_response}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Target: {closedLoop.receipt.target_system}
                    </div>
                  </div>
                  {activeStep >= 1 && <ChevronRight className="w-4 h-4 text-soc-success mt-1" />}
                </div>

                {/* Step 2: VERIFIED */}
                <div
                  className={`flex items-start gap-3 p-3 rounded border transition-all ${
                    activeStep >= 2
                      ? 'bg-soc-success/10 border-soc-success/50'
                      : 'bg-soc-bg/50 border-gray-700 opacity-50'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {activeStep >= 2 ? (
                      <CheckCircle className="w-5 h-5 text-soc-success" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm mb-1">2. VERIFIED</div>
                    <div className="text-xs text-gray-400">
                      Outcome confirmed via {closedLoop.verification.verification_method}
                    </div>
                  </div>
                  {activeStep >= 2 && <ChevronRight className="w-4 h-4 text-soc-success mt-1" />}
                </div>

                {/* Step 3: EVIDENCE */}
                <div
                  className={`flex items-start gap-3 p-3 rounded border transition-all ${
                    activeStep >= 3
                      ? 'bg-soc-success/10 border-soc-success/50'
                      : 'bg-soc-bg/50 border-gray-700 opacity-50'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {activeStep >= 3 ? (
                      <FileText className="w-5 h-5 text-soc-success" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm mb-1">3. EVIDENCE</div>
                    <div className="text-xs text-gray-400">
                      Decision trace {closedLoop.evidence.decision_id} captured
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {closedLoop.evidence.nodes_consulted} nodes consulted
                    </div>
                  </div>
                  {activeStep >= 3 && <ChevronRight className="w-4 h-4 text-soc-success mt-1" />}
                </div>

                {/* Step 4: KPI IMPACT */}
                <div
                  className={`flex items-start gap-3 p-3 rounded border transition-all ${
                    activeStep >= 4
                      ? 'bg-soc-success/10 border-soc-success/50'
                      : 'bg-soc-bg/50 border-gray-700 opacity-50'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {activeStep >= 4 ? (
                      <TrendingDown className="w-5 h-5 text-soc-success" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm mb-1">4. KPI IMPACT</div>
                    <div className="text-xs text-gray-400">
                      This resolution: {closedLoop.kpi_impact.metric}{' '}
                      <span className="text-soc-success font-bold">
                        {closedLoop.kpi_impact.contribution}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Previous: {closedLoop.kpi_impact.previous_avg.toFixed(1)} min →{' '}
                      New: {closedLoop.kpi_impact.new_avg.toFixed(1)} min
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-3 bg-soc-success/10 rounded border border-soc-success/30">
                  <p className="text-sm italic text-soc-success font-semibold text-center">
                    "A SIEM stops at detect. We close the loop."
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Outcome Feedback (v2.5 - Loop 3) */}
          {closedLoop && selectedAlert && (
            <OutcomeFeedback
              alertId={selectedAlert.id}
              decisionId={closedLoop.evidence.decision_id}
              isVisible={!!closedLoop}
            />
          )}
        </div>
      </div>
    </div>
  )
}
