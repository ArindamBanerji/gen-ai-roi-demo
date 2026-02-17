import { useState, useEffect } from 'react'
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
} from 'lucide-react'
import * as api from '@/lib/api'

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
}

export default function RuntimeEvolutionTab() {
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<ProcessResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDeployments()
  }, [])

  const loadDeployments = async () => {
    try {
      const data = await api.getDeployments()
      setDeployments(data.deployments)
    } catch (error) {
      console.error('Failed to load deployments:', error)
    } finally {
      setLoading(false)
    }
  }

  const processAlert = async (alertId: string = 'ALERT-7823') => {
    setProcessing(true)
    setResult(null)

    try {
      const data = await api.processAlert(alertId, false)
      setResult(data)
    } catch (error) {
      console.error('Failed to process alert:', error)
    } finally {
      setProcessing(false)
    }
  }

  const simulateFailedGate = async () => {
    setProcessing(true)
    setResult(null)

    try {
      const data = await api.processAlert('ALERT-7823', true)
      setResult(data)
    } catch (error) {
      console.error('Failed to simulate failure:', error)
    } finally {
      setProcessing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading deployments...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-gradient-to-r from-soc-secondary/20 to-soc-primary/20 rounded-lg p-6 border border-soc-secondary/50">
        <div className="flex items-center gap-3 mb-4">
          <Zap className="w-6 h-6 text-soc-secondary" />
          <h2 className="text-xl font-semibold">Runtime Evolution</h2>
          <span className="ml-2 px-3 py-1 bg-soc-secondary/30 text-soc-secondary text-xs font-bold rounded-full">
            THE DIFFERENTIATOR
          </span>
        </div>
        <p className="text-gray-300 mb-4">
          Watch decisions trigger agent evolution. This is what SIEMs don't have.
        </p>
        <div className="flex items-center gap-2 text-sm text-soc-secondary">
          <Sparkles className="w-4 h-4" />
          <span className="font-semibold">
            "Splunk gets better rules. Our copilot gets smarter."
          </span>
        </div>
      </div>

      {/* Deployment Registry */}
      <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800">
          <h3 className="font-semibold flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Deployment Registry
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-soc-bg/50">
              <tr className="text-left text-sm text-gray-400">
                <th className="px-6 py-3">Agent</th>
                <th className="px-6 py-3">Version</th>
                <th className="px-6 py-3">Traffic</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Auto-Close Rate (7d)</th>
                <th className="px-6 py-3">Patterns</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {deployments.map((deployment) => (
                <tr key={deployment.version} className="text-sm">
                  <td className="px-6 py-4">{deployment.agent_name}</td>
                  <td className="px-6 py-4 font-mono font-semibold">
                    {deployment.version}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-soc-primary"
                          style={{ width: `${deployment.traffic_pct}%` }}
                        />
                      </div>
                      <span className="text-gray-400 text-xs">
                        {deployment.traffic_pct}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${
                        deployment.status === 'active'
                          ? 'bg-soc-success/20 text-soc-success'
                          : 'bg-soc-warning/20 text-soc-warning'
                      }`}
                    >
                      <div
                        className={`w-2 h-2 rounded-full ${
                          deployment.status === 'active'
                            ? 'bg-soc-success'
                            : 'bg-soc-warning'
                        }`}
                      />
                      {deployment.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div>
                      <span className="font-semibold">
                        {deployment.auto_close_rate_7d}%
                      </span>
                      <span className="text-gray-500 text-xs ml-2">
                        (n={deployment.sample_count_7d.toLocaleString()})
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-semibold text-soc-secondary">
                      {deployment.pattern_count}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <button
          onClick={() => processAlert()}
          disabled={processing}
          className="flex items-center gap-2 px-6 py-3 bg-soc-primary hover:bg-soc-primary/80 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors"
        >
          {processing ? (
            <>
              <Clock className="w-4 h-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Activity className="w-4 h-4" />
              Process Alert (ALERT-7823)
            </>
          )}
        </button>

        <button
          onClick={simulateFailedGate}
          disabled={processing}
          className="flex items-center gap-2 px-6 py-3 bg-soc-danger/20 hover:bg-soc-danger/30 disabled:bg-gray-700 disabled:cursor-not-allowed border border-soc-danger/50 rounded-lg font-semibold transition-colors"
        >
          <AlertTriangle className="w-4 h-4" />
          Simulate Failed Gate
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Eval Gate Panel */}
          <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  Eval Gate — {result.alert_id}
                </h3>
                <div className="flex items-center gap-2">
                  {result.eval_gate.overall_passed ? (
                    <span className="flex items-center gap-1 text-soc-success text-sm font-semibold">
                      <CheckCircle className="w-4 h-4" />
                      ALL GATES PASSED
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-soc-danger text-sm font-semibold">
                      <XCircle className="w-4 h-4" />
                      BLOCKED
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {result.eval_gate.checks.map((check) => (
                <div
                  key={check.name}
                  className="flex items-center justify-between p-4 bg-soc-bg rounded border border-gray-800"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">{check.name}</span>
                      {check.passed ? (
                        <CheckCircle className="w-4 h-4 text-soc-success" />
                      ) : (
                        <XCircle className="w-4 h-4 text-soc-danger" />
                      )}
                    </div>
                    <p className="text-sm text-gray-400">{check.message}</p>
                  </div>
                  <div className="text-right ml-4">
                    <div className="font-mono text-lg font-bold">
                      {check.score.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500">
                      &gt; {check.threshold.toFixed(2)}
                    </div>
                  </div>
                </div>
              ))}

              <div className="mt-4 p-4 bg-soc-bg/50 rounded border border-gray-700">
                <div className="text-sm text-gray-400 mb-1">Overall Score</div>
                <div className="text-2xl font-bold">
                  {result.eval_gate.overall_score.toFixed(3)}
                </div>
              </div>
            </div>
          </div>

          {/* Decision Trace */}
          <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800">
              <h3 className="font-semibold flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Decision Trace — {result.decision_trace.id}
              </h3>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-gray-500 mb-1">Input</div>
                  <div className="font-semibold">{result.alert_id}</div>
                  <div className="text-xs text-gray-400">
                    {result.context_preview.user_name} on{' '}
                    {result.context_preview.asset_hostname}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Context</div>
                  <div className="font-semibold">
                    {result.decision_trace.nodes_consulted} graph nodes
                  </div>
                  <div className="text-xs text-gray-400">
                    {result.context_preview.pattern_count} patterns matched
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Decision</div>
                  <div className="font-semibold">
                    {result.decision_trace.action_taken.replace(/_/g, ' ')}
                  </div>
                  <div className="text-xs text-gray-400">
                    {(result.decision_trace.confidence * 100).toFixed(0)}%
                    confidence
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Verification</div>
                  <div className="flex items-center gap-1 text-soc-success">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-semibold">
                      {result.execution.status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-soc-bg rounded border border-gray-800">
                <div className="text-sm text-gray-500 mb-2">Reasoning</div>
                <p className="text-sm leading-relaxed">
                  {result.decision_trace.reasoning}
                </p>
              </div>
            </div>
          </div>

          {/* TRIGGERED_EVOLUTION Panel - THE KEY DIFFERENTIATOR */}
          {result.triggered_evolution.occurred && (
            <div className="bg-gradient-to-r from-soc-secondary/30 to-purple-900/30 rounded-lg border-2 border-soc-secondary p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-soc-secondary/20 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-soc-secondary" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-bold text-soc-secondary">
                      🔗 TRIGGERED_EVOLUTION
                    </h3>
                    <span className="px-2 py-1 bg-soc-secondary/20 text-soc-secondary text-xs font-bold rounded">
                      What SIEMs don't have
                    </span>
                  </div>
                  <p className="text-sm text-gray-300 mb-4">
                    This decision trace triggered agent evolution:
                  </p>

                  {result.triggered_evolution.changes?.map((change, idx) => (
                    <div
                      key={idx}
                      className="bg-soc-bg/50 rounded p-4 mb-3 border border-soc-secondary/30"
                    >
                      <div className="font-semibold mb-2">
                        {result.triggered_evolution.description}
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Before:</span>
                          <span className="ml-2 font-mono">
                            {change.before.confidence}%
                          </span>
                        </div>
                        <div className="text-gray-500">→</div>
                        <div>
                          <span className="text-gray-500">After:</span>
                          <span className="ml-2 font-mono font-bold text-soc-success">
                            {change.after.confidence}%
                          </span>
                        </div>
                        <div className="ml-auto text-soc-success font-semibold">
                          +{change.after.confidence - change.before.confidence}{' '}
                          pts
                        </div>
                      </div>
                    </div>
                  ))}

                  <div className="mt-4 p-3 bg-soc-secondary/10 rounded border border-soc-secondary/30">
                    <p className="text-sm italic text-soc-secondary font-semibold">
                      "Splunk gets better rules. Our copilot gets SMARTER."
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Execution Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-soc-card rounded-lg p-4 border border-gray-800">
              <div className="text-sm text-gray-500 mb-1">Execution Time</div>
              <div className="text-2xl font-bold">
                {result.execution_time_ms.toFixed(0)}ms
              </div>
            </div>
            <div className="bg-soc-card rounded-lg p-4 border border-gray-800">
              <div className="text-sm text-gray-500 mb-1">Routed To</div>
              <div className="text-2xl font-mono font-bold">
                {result.routed_to}
              </div>
            </div>
            <div className="bg-soc-card rounded-lg p-4 border border-gray-800">
              <div className="text-sm text-gray-500 mb-1">Event ID</div>
              <div className="text-lg font-mono font-bold text-soc-secondary">
                {result.triggered_evolution.event_id || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
