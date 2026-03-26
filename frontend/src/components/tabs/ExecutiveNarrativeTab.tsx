/**
 * ExecutiveNarrativeTab.tsx — F12 Tab 5
 *
 * Fetches GET /api/soc/executive-narrative and renders a structured
 * digest for CISO / executive audiences. Includes a PDF download button.
 */

import { useState, useEffect } from 'react'
import { FileText, Download, TrendingUp, Search, Brain, Activity } from 'lucide-react'

const API = 'http://localhost:8000'

interface Shift {
  label: string
  magnitude: number
  description: string
}

interface WhatChanged {
  total_verified: number
  total_centroid_updates: number
  top_shifts: Shift[]
  iks_delta: number
}

interface WhatDiscovered {
  attack_chains_detected: number
  chain_summaries: string[]
  new_entities: { users: number; assets: number; threat_indicators: number }
  graph_growth: { nodes_added: number; relationships_added: number }
}

interface WhatKnows {
  iks_current: number
  categories_calibrated: number
  categories_total: number
  health_status: 'GREEN' | 'AMBER' | 'RED'
}

interface Metrics {
  alerts_total: number
  decisions_verified: number
  campaigns_detected: number
  iks_current: number
}

interface NarrativeData {
  headline: string
  what_changed: WhatChanged
  what_discovered: WhatDiscovered
  what_knows: WhatKnows
  metrics: Metrics
  generated_at: string
  pdf_available: boolean
}

function healthColor(status: string) {
  if (status === 'GREEN') return 'text-green-400'
  if (status === 'AMBER') return 'text-yellow-400'
  return 'text-red-400'
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 text-center">
      <div className="text-2xl font-bold text-soc-primary">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
    </div>
  )
}

export default function ExecutiveNarrativeTab() {
  const [data, setData] = useState<NarrativeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/soc/executive-narrative`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        Loading executive narrative…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-48 text-red-400 text-sm">
        Failed to load narrative: {error ?? 'unknown error'}
      </div>
    )
  }

  const { headline, what_changed, what_discovered, what_knows, metrics, generated_at } = data

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-5 h-5 text-soc-primary" />
            <h2 className="text-lg font-semibold">Executive Narrative</h2>
            <span className="text-xs text-gray-500 ml-2">Generated {generated_at.replace('T', ' ').replace('Z', ' UTC')}</span>
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">{headline}</p>
        </div>
        {data.pdf_available && (
          <a
            href={`${API}/api/soc/executive-narrative/pdf`}
            download="executive_narrative.pdf"
            className="flex items-center gap-2 px-4 py-2 bg-soc-primary/10 text-soc-primary border border-soc-primary/30 rounded-lg text-sm hover:bg-soc-primary/20 transition-colors shrink-0"
          >
            <Download className="w-4 h-4" />
            Export PDF
          </a>
        )}
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard label="Alerts Processed" value={metrics.alerts_total} />
        <MetricCard label="Verified Decisions" value={metrics.decisions_verified} />
        <MetricCard label="Campaigns Detected" value={metrics.campaigns_detected} />
        <MetricCard label="IKS Score" value={metrics.iks_current} />
      </div>

      {/* Three sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Section 1: What Changed */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-gray-200">What Changed</h3>
          </div>
          <div className="space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Verified decisions</span>
              <span className="text-gray-200 font-mono">{what_changed.total_verified}</span>
            </div>
            <div className="flex justify-between">
              <span>Centroid updates</span>
              <span className="text-gray-200 font-mono">{what_changed.total_centroid_updates}</span>
            </div>
          </div>
          {what_changed.top_shifts.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Top shifts</p>
              {what_changed.top_shifts.map((s, i) => (
                <div key={i} className="bg-gray-800 rounded p-2 text-xs text-gray-300">
                  {s.description}
                </div>
              ))}
            </div>
          )}
          {what_changed.top_shifts.length === 0 && (
            <p className="mt-3 text-xs text-gray-600 italic">No centroid shifts recorded yet.</p>
          )}
        </div>

        {/* Section 2: What Was Discovered */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Search className="w-4 h-4 text-yellow-400" />
            <h3 className="text-sm font-semibold text-gray-200">What Was Discovered</h3>
          </div>
          <div className="space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Attack chains</span>
              <span className="text-gray-200 font-mono">{what_discovered.attack_chains_detected}</span>
            </div>
            <div className="flex justify-between">
              <span>Graph nodes</span>
              <span className="text-gray-200 font-mono">{what_discovered.graph_growth.nodes_added}</span>
            </div>
          </div>
          {what_discovered.chain_summaries.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Chain summaries</p>
              {what_discovered.chain_summaries.map((s, i) => (
                <div key={i} className="bg-gray-800 rounded p-2 text-xs text-gray-300">{s}</div>
              ))}
            </div>
          )}
          {what_discovered.chain_summaries.length === 0 && (
            <p className="mt-3 text-xs text-gray-600 italic">No chains detected yet.</p>
          )}
        </div>

        {/* Section 3: What the System Knows */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-gray-200">What the System Knows</h3>
          </div>
          <div className="space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>IKS score</span>
              <span className="text-gray-200 font-mono">{what_knows.iks_current}</span>
            </div>
            <div className="flex justify-between">
              <span>Categories calibrated</span>
              <span className="text-gray-200 font-mono">
                {what_knows.categories_calibrated} / {what_knows.categories_total}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>Health</span>
              <span className={`font-semibold ${healthColor(what_knows.health_status)}`}>
                {what_knows.health_status}
              </span>
            </div>
          </div>
          <div className="mt-3">
            <div className="w-full bg-gray-700 rounded-full h-1.5">
              <div
                className="bg-soc-primary h-1.5 rounded-full transition-all"
                style={{
                  width: `${Math.min(100, (what_knows.categories_calibrated / what_knows.categories_total) * 100)}%`,
                }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {what_knows.categories_calibrated} of {what_knows.categories_total} categories calibrated
            </p>
          </div>
        </div>
      </div>

      {/* Activity indicator */}
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <Activity className="w-3 h-3" />
        <span>Data reflects verified decisions stored in Neo4j. Refresh page to regenerate.</span>
      </div>
    </div>
  )
}
