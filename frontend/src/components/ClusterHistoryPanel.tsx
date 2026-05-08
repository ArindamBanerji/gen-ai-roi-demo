import { CheckCircle, History, Minus, TrendingDown, TrendingUp, XCircle } from 'lucide-react'

export interface ClusterHistoryEntry {
  decision_id: string
  category: string
  action: string
  outcome: string
  confidence: number
  days_ago: number
}

export interface ClusterHistoryData {
  source_user: string
  total_prior: number
  per_category: Record<string, number>
  per_action: Record<string, number>
  precision: number
  trend: 'escalating' | 'stable' | 'declining' | 'new'
  trend_detail: string
  recent: ClusterHistoryEntry[]
  current_position: number
}

function formatLabel(value: string) {
  return value.replace(/_/g, ' ')
}

function trendStyle(trend: ClusterHistoryData['trend']) {
  if (trend === 'escalating') {
    return {
      icon: <TrendingUp className="h-4 w-4 text-amber-300" />,
      label: 'Escalating',
      className: 'border-amber-500/40 bg-amber-950/30 text-amber-200',
    }
  }
  if (trend === 'declining') {
    return {
      icon: <TrendingDown className="h-4 w-4 text-green-300" />,
      label: 'Declining',
      className: 'border-green-500/40 bg-green-950/30 text-green-200',
    }
  }
  if (trend === 'new') {
    return {
      icon: <History className="h-4 w-4 text-blue-300" />,
      label: 'New pattern',
      className: 'border-blue-500/40 bg-blue-950/30 text-blue-200',
    }
  }
  return {
    icon: <Minus className="h-4 w-4 text-gray-300" />,
    label: 'Stable',
    className: 'border-gray-700 bg-gray-900/60 text-gray-300',
  }
}

export default function ClusterHistoryPanel({ history }: { history?: ClusterHistoryData | null }) {
  if (!history) return null

  const trend = trendStyle(history.trend)
  const precisionPct = Math.round((history.precision || 0) * 100)
  const recent = Array.isArray(history.recent) ? history.recent : []

  return (
    <div className="bg-soc-card rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold">Cluster History</h3>
          <p className="text-xs text-gray-500 mt-1">
            Prior verified decisions for {history.source_user || 'this user'}
          </p>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold ${trend.className}`}>
          {trend.icon}
          {trend.label}
        </span>
      </div>

      <div className="p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Seen before</p>
            <p className="text-xl font-semibold text-gray-100">{history.total_prior}</p>
            <p className="text-xs text-gray-500">Current alert is #{history.current_position}</p>
          </div>
          <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Precision</p>
            <p className="text-xl font-semibold text-gray-100">{precisionPct}%</p>
            <p className="text-xs text-gray-500">Historical verified outcomes</p>
          </div>
          <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Trend</p>
            <p className="text-sm font-semibold text-gray-200">{trend.label}</p>
            <p className="text-xs text-gray-500">{history.trend_detail}</p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-2">Categories</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(history.per_category || {}).map(([category, count]) => (
                <span key={category} className="rounded border border-gray-700 bg-gray-900 px-2.5 py-1 text-xs text-gray-300">
                  {formatLabel(category)} <span className="text-gray-500">x{count}</span>
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-2">Actions</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(history.per_action || {}).map(([action, count]) => (
                <span key={action} className="rounded border border-gray-700 bg-gray-900 px-2.5 py-1 text-xs text-gray-300">
                  {formatLabel(action)} <span className="text-gray-500">x{count}</span>
                </span>
              ))}
            </div>
          </div>
        </div>

        {recent.length > 0 && (
          <div className="pt-3 border-t border-gray-800">
            <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-2">Recent verified decisions</p>
            <div className="space-y-2">
              {recent.map((entry) => {
                const correct = entry.outcome === 'correct'
                return (
                  <div key={entry.decision_id} className="flex items-start justify-between gap-3 rounded border border-gray-800 bg-gray-900/50 px-3 py-2">
                    <div className="min-w-0">
                      <p className="text-sm text-gray-300">
                        {formatLabel(entry.category)} · {formatLabel(entry.action)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {entry.days_ago < 0.1 ? 'today' : `${entry.days_ago.toFixed(1)}d ago`} · {(entry.confidence * 100).toFixed(0)}% confidence
                      </p>
                    </div>
                    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${correct ? 'text-green-300' : 'text-red-300'}`}>
                      {correct ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                      {correct ? 'Correct' : 'Incorrect'}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
