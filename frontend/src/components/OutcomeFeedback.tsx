/**
 * Outcome Feedback Component (v2.5)
 * Loop 3: Learning from Results
 *
 * Allows users to report whether a decision outcome was correct or incorrect.
 * Shows graph updates and demonstrates self-correction in action.
 */
import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, TrendingUp, TrendingDown, Clock } from 'lucide-react'
import { getOutcomeStatus, reportOutcome } from '../lib/api'

interface GraphUpdate {
  entity: string
  field: string
  before: number
  after: number
  direction: 'strengthened' | 'weakened'
}

interface NextAlertsOverride {
  action: string
  count: number
  reason: string
}

interface OutcomeResponse {
  alert_id: string
  outcome: string
  graph_updates: GraphUpdate[]
  consequence: string
  next_alerts_override: NextAlertsOverride | null
  narrative: string
}

interface OutcomeFeedbackProps {
  alertId: string
  decisionId: string
  isVisible: boolean
}

export default function OutcomeFeedback({ alertId, decisionId, isVisible }: OutcomeFeedbackProps) {
  const [hasFeedback, setHasFeedback] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<OutcomeResponse | null>(null)

  useEffect(() => {
    if (isVisible && alertId) {
      checkFeedbackStatus()
    }
  }, [isVisible, alertId])

  const checkFeedbackStatus = async () => {
    try {
      setLoading(true)
      const status = (await getOutcomeStatus(alertId)) as { has_feedback: boolean }

      if (status.has_feedback) {
        setHasFeedback(true)
        // If feedback already given, we don't fetch the full result here
        // User would need to see it in history or we'd need to store it
      }
    } catch (error) {
      console.error('[OutcomeFeedback] Failed to check status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleOutcome = async (outcome: 'correct' | 'incorrect') => {
    try {
      setSubmitting(true)
      const response = (await reportOutcome(alertId, decisionId, outcome)) as OutcomeResponse
      setResult(response)
      setHasFeedback(true)
    } catch (error) {
      console.error('[OutcomeFeedback] Failed to report outcome:', error)
      alert('Failed to report outcome. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!isVisible) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 rounded-lg border-2 border-purple-500/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-purple-500/50 bg-purple-900/30">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-purple-400" />
          <h3 className="font-semibold text-purple-300">
            OUTCOME FEEDBACK (Loop 3: Learning from Results)
          </h3>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          24 hours later — was this decision correct?
        </p>
      </div>

      <div className="p-4 space-y-4">
        {loading ? (
          <div className="text-center py-4 text-gray-400">
            Checking feedback status...
          </div>
        ) : !hasFeedback && !result ? (
          /* Initial state - show buttons */
          <div className="space-y-4">
            <p className="text-sm text-gray-300">
              Report the outcome of this decision to help the system learn.
            </p>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleOutcome('correct')}
                disabled={submitting}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors text-white"
              >
                <CheckCircle className="w-5 h-5" />
                <span>Confirmed Correct</span>
              </button>

              <button
                onClick={() => handleOutcome('incorrect')}
                disabled={submitting}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors text-white"
              >
                <XCircle className="w-5 h-5" />
                <span>Incorrect — Real Threat</span>
              </button>
            </div>

            {submitting && (
              <p className="text-xs text-center text-gray-400">
                Reporting outcome...
              </p>
            )}
          </div>
        ) : result ? (
          /* Show result after feedback given */
          <div className="space-y-4">
            {/* Consequence Banner */}
            <div
              className={`p-3 rounded-lg border-2 ${
                result.outcome === 'correct'
                  ? 'bg-green-900/20 border-green-500/50'
                  : 'bg-amber-900/20 border-amber-500/50'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                {result.outcome === 'correct' ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-amber-400" />
                )}
                <span
                  className={`font-semibold ${
                    result.outcome === 'correct' ? 'text-green-300' : 'text-amber-300'
                  }`}
                >
                  Outcome: {result.outcome === 'correct' ? 'Correct' : 'Incorrect'}
                </span>
              </div>
              <p
                className={`text-sm ${
                  result.outcome === 'correct' ? 'text-green-200' : 'text-amber-200'
                }`}
              >
                {result.consequence}
              </p>
            </div>

            {/* Graph Updates Table */}
            <div className="bg-soc-bg/50 rounded border border-gray-700 overflow-hidden">
              <div className="px-3 py-2 border-b border-gray-700 bg-gray-800/50">
                <h4 className="text-sm font-semibold text-gray-300">Graph Updates</h4>
              </div>
              <div className="divide-y divide-gray-700">
                {result.graph_updates.map((update, idx) => (
                  <div key={idx} className="px-3 py-2 flex items-center justify-between text-xs">
                    <div className="flex-1">
                      <div className="font-mono text-gray-400">{update.entity}</div>
                      <div className="text-gray-500">{update.field}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400">
                        {typeof update.before === 'number' && update.field !== 'precedent_count'
                          ? (update.before * 100).toFixed(1) + '%'
                          : update.before}
                      </span>
                      <span className="text-gray-600">→</span>
                      <span
                        className={
                          update.direction === 'strengthened' ? 'text-green-400' : 'text-red-400'
                        }
                      >
                        {typeof update.after === 'number' && update.field !== 'precedent_count'
                          ? (update.after * 100).toFixed(1) + '%'
                          : update.after}
                      </span>
                      {update.direction === 'strengthened' ? (
                        <TrendingUp className="w-4 h-4 text-green-400" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-400" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Next Alerts Override (if incorrect) */}
            {result.next_alerts_override && (
              <div className="bg-amber-900/20 border-2 border-amber-500/50 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="text-sm font-semibold text-amber-300 mb-1">
                      Threshold Review Triggered
                    </div>
                    <p className="text-xs text-amber-200">
                      Next {result.next_alerts_override.count} similar alerts will be routed to{' '}
                      <span className="font-semibold">Tier 2 analysts</span> for manual review.
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Reason: {result.next_alerts_override.reason}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Narrative */}
            <div className="bg-soc-bg/30 rounded border border-gray-700 p-3">
              <p className="text-sm italic text-gray-300 leading-relaxed">{result.narrative}</p>
            </div>

            {/* Self-Correction Callout */}
            <div
              className={`p-3 rounded border-2 ${
                result.outcome === 'correct'
                  ? 'bg-green-900/10 border-green-500/30'
                  : 'bg-purple-900/10 border-purple-500/30'
              }`}
            >
              <p
                className={`text-sm font-semibold italic text-center ${
                  result.outcome === 'correct' ? 'text-green-300' : 'text-purple-300'
                }`}
              >
                {result.outcome === 'correct'
                  ? '"The system gets more confident with every validation."'
                  : '"This is self-correction in action — the system learned from this mistake."'}
              </p>
            </div>
          </div>
        ) : (
          /* Feedback already given (from previous session) */
          <div className="text-center py-4">
            <p className="text-sm text-gray-400">
              Feedback has already been provided for this alert.
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Outcomes are immutable once recorded.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
