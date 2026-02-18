/**
 * Policy Conflict Component (v2.5)
 * Shows when multiple policies apply to an alert and conflict with each other.
 * Demonstrates policy resolution using priority and security-first principles.
 */
import { useState, useEffect } from 'react'
import { AlertTriangle, Shield, ShieldCheck, Award, Scale } from 'lucide-react'
import { checkPolicyConflict } from '../lib/api'

interface PolicyDefinition {
  id: string
  name: string
  description: string
  action: string
  priority: number
  scope: string
}

interface PolicyResolution {
  winning_policy: string
  losing_policy: string
  reason: string
  action_adjusted: string
  original_action: string
  audit_id: string
  narrative: string
}

interface PolicyConflictData {
  alert_id: string
  has_conflict: boolean
  policies_applied: PolicyDefinition[]
  conflicting_policies: PolicyDefinition[]
  resolution: PolicyResolution | null
}

interface PolicyConflictProps {
  alertId: string
  isVisible: boolean
}

export default function PolicyConflict({ alertId, isVisible }: PolicyConflictProps) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<PolicyConflictData | null>(null)

  useEffect(() => {
    if (isVisible && alertId) {
      checkConflict()
    }
  }, [isVisible, alertId])

  const checkConflict = async () => {
    try {
      setLoading(true)
      const result = (await checkPolicyConflict(alertId)) as PolicyConflictData
      setData(result)
    } catch (error) {
      console.error('[PolicyConflict] Failed to check policy conflict:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!isVisible) {
    return null
  }

  if (loading) {
    return (
      <div className="text-center py-2 text-gray-400 text-sm">
        Checking policy conflicts...
      </div>
    )
  }

  if (!data) {
    return null
  }

  // No conflict - simple one-liner
  if (!data.has_conflict) {
    return (
      <div className="flex items-center gap-2 py-2 text-sm">
        <ShieldCheck className="w-4 h-4 text-green-400" />
        <span className="text-gray-300">
          Policies evaluated: {data.policies_applied.map((p) => p.name).join(', ')}.
        </span>
        <span className="text-green-400 font-semibold">No conflicts detected.</span>
      </div>
    )
  }

  // Conflict detected - full panel
  const losingPolicy = data.conflicting_policies.find(
    (p) => p.id === data.resolution?.losing_policy
  )
  const winningPolicy = data.conflicting_policies.find(
    (p) => p.id === data.resolution?.winning_policy
  )

  if (!losingPolicy || !winningPolicy || !data.resolution) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-amber-900/20 to-orange-900/20 rounded-lg border-2 border-amber-500/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-amber-500/50 bg-amber-900/30">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h3 className="font-semibold text-amber-300">POLICY CONFLICT DETECTED</h3>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Multiple policies apply with different actions. Resolving by priority...
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Policy Cards Side by Side */}
        <div className="grid grid-cols-2 gap-3">
          {/* Losing Policy */}
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
            <div className="flex items-start justify-between mb-2">
              <Shield className="w-5 h-5 text-red-400 flex-shrink-0" />
              <span className="px-2 py-0.5 bg-red-500/20 rounded text-xs font-semibold text-red-300">
                LOSES
              </span>
            </div>
            <div className="space-y-2">
              <div>
                <div className="text-xs text-gray-500">Policy</div>
                <div className="font-mono text-sm text-red-300">{losingPolicy.id}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Name</div>
                <div className="text-sm font-semibold text-gray-200">{losingPolicy.name}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Action</div>
                <div className="text-sm font-mono text-red-300">{losingPolicy.action}</div>
              </div>
              <div className="flex gap-3">
                <div>
                  <div className="text-xs text-gray-500">Priority</div>
                  <div className="text-sm font-bold text-red-300">{losingPolicy.priority}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Scope</div>
                  <div className="text-sm text-gray-400">{losingPolicy.scope}</div>
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Description</div>
                <div className="text-xs text-gray-400 leading-relaxed">
                  {losingPolicy.description}
                </div>
              </div>
            </div>
          </div>

          {/* Winning Policy */}
          <div className="bg-green-900/20 border-2 border-green-500/50 rounded-lg p-3">
            <div className="flex items-start justify-between mb-2">
              <Shield className="w-5 h-5 text-green-400 flex-shrink-0" />
              <div className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 rounded">
                <Award className="w-3 h-3 text-green-300" />
                <span className="text-xs font-semibold text-green-300">WINNER</span>
              </div>
            </div>
            <div className="space-y-2">
              <div>
                <div className="text-xs text-gray-500">Policy</div>
                <div className="font-mono text-sm text-green-300">{winningPolicy.id}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Name</div>
                <div className="text-sm font-semibold text-gray-200">{winningPolicy.name}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Action</div>
                <div className="text-sm font-mono text-green-300">{winningPolicy.action}</div>
              </div>
              <div className="flex gap-3">
                <div>
                  <div className="text-xs text-gray-500">Priority</div>
                  <div className="text-sm font-bold text-green-300">{winningPolicy.priority}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Scope</div>
                  <div className="text-sm text-gray-400">{winningPolicy.scope}</div>
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Description</div>
                <div className="text-xs text-gray-400 leading-relaxed">
                  {winningPolicy.description}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Resolution Box */}
        <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="w-5 h-5 text-amber-400" />
            <h4 className="font-semibold text-amber-300">RESOLUTION</h4>
          </div>

          <div className="space-y-2">
            <div>
              <span className="text-sm text-gray-300">
                <span className="font-semibold text-green-300">{winningPolicy.name}</span> takes
                precedence
              </span>
            </div>

            <div className="text-xs text-gray-400 leading-relaxed">{data.resolution.reason}</div>

            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400">Action adjusted:</span>
              <span className="font-mono font-semibold text-green-300">
                {data.resolution.action_adjusted}
              </span>
              <span className="text-gray-500">
                (was: <span className="line-through">{data.resolution.original_action}</span>)
              </span>
            </div>

            <div className="pt-2 border-t border-amber-500/20">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Audit ID:</span>
                <span className="font-mono text-xs text-amber-400">
                  {data.resolution.audit_id}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Narrative */}
        <div className="bg-soc-bg/30 rounded border border-gray-700 p-3">
          <p className="text-sm italic text-gray-300 leading-relaxed">
            {data.resolution.narrative}
          </p>
        </div>

        {/* Security Principle Callout */}
        <div className="p-3 bg-green-900/10 rounded border border-green-500/30">
          <p className="text-sm font-semibold italic text-center text-green-300">
            "Security-first principle: When policies conflict, the higher-priority policy always
            wins to ensure no security gaps."
          </p>
        </div>
      </div>
    </div>
  )
}
