import { useState, useEffect } from 'react'
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Network,
  Play,
  ChevronRight,
  FileText,
  TrendingDown,
  RefreshCw,
} from 'lucide-react'
import { getAlerts, analyzeAlert, executeAction, resetAlerts } from '../../lib/api'

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

export default function AlertTriageTab() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [closedLoop, setClosedLoop] = useState<ClosedLoopResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [activeStep, setActiveStep] = useState(0)
  const [resetting, setResetting] = useState(false)

  useEffect(() => {
    loadAlertQueue()
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

      if (data.alerts.length > 0) {
        setSelectedAlert(data.alerts[0])
        console.log('[AlertTriageTab] Selected first alert:', data.alerts[0])
      } else {
        console.log('[AlertTriageTab] No alerts in response')
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

    try {
      const data = await analyzeAlert(alert.id)
      setAnalysis(data)
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

          {/* Recommendation Panel */}
          {analysis && (
            <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
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
                  {executing ? 'Executing...' : closedLoop ? 'Executed' : 'Apply Recommendation'}
                </button>
              </div>
            </div>
          )}

          {/* Closed Loop Execution */}
          {closedLoop && (
            <div className="bg-gradient-to-r from-soc-success/20 to-soc-primary/20 rounded-lg border-2 border-soc-success/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-soc-success/50 flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-soc-success" />
                <h3 className="font-semibold text-soc-success">
                  ✓ CLOSED LOOP (What SIEMs don't do)
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
        </div>
      </div>
    </div>
  )
}
