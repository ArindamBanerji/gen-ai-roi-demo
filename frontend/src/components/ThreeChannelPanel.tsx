import { useEffect, useState } from 'react'
import { ensureArray } from '../lib/guards'

interface Channel {
  id: string
  label: string
  contribution_pp: number
  status: string
  description: string
}

interface ChannelData {
  strategy: string
  channels: Channel[]
  total_improvement_pp: number
  irreducible_pp: number
  remaining_boundary_pp: number
  disclaimer: string
}

function channelColor(id: string): string {
  switch (id) {
    case 'scorer':
      return 'bg-blue-500'
    case 'graph':
      return 'bg-green-500'
    case 'labels':
      return 'bg-amber-500'
    default:
      return 'bg-gray-600'
  }
}

function statusBadge(status: string): { label: string; className: string } {
  if (status === 'active') {
    return { label: 'ACTIVE', className: 'bg-green-500/20 text-green-300 border-green-500/40' }
  }
  if (status === 'not_active') {
    return { label: 'PENDING', className: 'bg-gray-700 text-gray-300 border-gray-600' }
  }
  return { label: 'INACTIVE', className: 'bg-gray-700 text-gray-300 border-gray-600' }
}

export default function ThreeChannelPanel() {
  const [data, setData] = useState<ChannelData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadChannelData() {
      setLoading(true)
      try {
        const response = await fetch('/api/compounding/channel-decomposition')
        if (!response.ok) {
          if (!cancelled) setData(null)
          return
        }
        const payload = await response.json() as ChannelData
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadChannelData()
    return () => {
      cancelled = true
    }
  }, [])

  // Keep the panel structure visible while this independent request is in
  // flight (or unavailable). This prevents an unrelated Tab 4 load from
  // hiding the FW-10 evidence entirely.
  const channels = ensureArray<Channel>(data?.channels)
  const visibleChannels: Channel[] = channels.length > 0 ? channels : [
    { id: 'scorer', label: 'Channel 1 (Scorer)', contribution_pp: 0, status: 'inactive', description: 'Loading scorer calibration…' },
    { id: 'graph', label: 'Channel 2 (Graph)', contribution_pp: 0, status: 'active', description: 'Loading graph calibration…' },
    { id: 'labels', label: 'Channel 3 (Labels)', contribution_pp: 0, status: 'not_active', description: 'Loading label calibration…' },
  ]
  const totalImprovement = data?.total_improvement_pp ?? 0
  const remainingBoundary = data?.remaining_boundary_pp ?? 0
  const maxPP = Number.isFinite(data?.irreducible_pp) && (data?.irreducible_pp ?? 0) > 0
    ? data?.irreducible_pp ?? 0
    : totalImprovement + remainingBoundary
  const barScale = (value: number) => {
    if (maxPP <= 0) return '2%'
    return `${Math.max(2, Math.min(100, (value / maxPP) * 100))}%`
  }

  return (
    <div className="bg-slate-900 rounded-lg border border-purple-500/50 shadow-2xl p-6">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h3 className="text-base font-bold text-white"> Three-Channel Error Budget</h3>
          <p className="text-sm text-purple-300 font-medium mt-0.5">
          Estimated improvement: {loading ? 'loading…' : `+${totalImprovement}pp · Remaining: ${remainingBoundary}pp`}
          </p>
        </div>
        <span className="text-xs uppercase tracking-wide rounded border border-purple-500/40 bg-purple-500/10 px-2 py-1 text-purple-200">
          {data?.strategy ?? 'continuous'}
        </span>
      </div>

      <div className="h-4 bg-gray-800 rounded-full overflow-hidden flex mb-5">
        {visibleChannels.filter((channel) => channel.contribution_pp > 0).map((channel) => (
          <div
            key={channel.id}
            className={`${channelColor(channel.id)} h-full`}
            style={{ width: barScale(channel.contribution_pp) }}
            title={`${channel.label}: +${channel.contribution_pp}pp`}
          />
        ))}
        {remainingBoundary > 0 && (
          <div
            className="h-full bg-gray-700"
            style={{ width: barScale(remainingBoundary) }}
            title={`Remaining boundary: ${remainingBoundary}pp`}
          />
        )}
      </div>

      <div className="space-y-3">
        {visibleChannels.map((channel) => {
          const badge = statusBadge(channel.status)
          return (
            <div key={channel.id} className="rounded-lg border border-gray-800 bg-gray-900/60 p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`h-2.5 w-2.5 rounded-full ${channelColor(channel.id)}`} />
                    <h4 className="text-sm font-semibold text-gray-100">{channel.label}</h4>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${badge.className}`}>
                      {badge.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">{channel.description}</p>
                </div>
                <span className="shrink-0 text-sm font-bold text-gray-100">+{channel.contribution_pp}pp</span>
              </div>
            </div>
          )
        })}
      </div>

      <p className="mt-4 pt-4 border-t border-gray-800 text-xs text-gray-500 italic">
        {data?.disclaimer ?? 'Awaiting simulation calibration data.'}
      </p>
    </div>
  )
}
