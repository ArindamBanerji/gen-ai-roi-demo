/**
 * ExecutiveNarrativeTab.tsx — F12 Tab 5
 *
 * Fetches GET /api/soc/executive-narrative and renders a structured
 * digest for CISO / executive audiences. Includes a PDF download button.
 */

import { useEffect, useState } from 'react'
import { FileText, Download, TrendingUp, Search, Brain, Activity, Shield, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react'
import { ensureArray, safeKey } from '../../lib/guards'
import {
  downloadGovernanceReportCsv,
  downloadGovernanceReportJson,
  fetchGovernanceSummary,
} from '../../lib/api'

const SOC_API = 'http://localhost:8001'

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
  health_status: 'GREEN' | 'AMBER' | 'RED' | 'CALIBRATING'
  operational_knowledge_status?: 'GREEN' | 'AMBER' | 'RED'
  pre_activation?: boolean
  conservation_narrative?: string
}

interface Metrics {
  alerts_total: number
  decisions_verified: number
  campaigns_detected: number
  iks_current: number
}

interface NarrativeCategory {
  name: string
  accuracy: number
}

interface NarrativeRecommendationItem {
  type?: string
  category?: string
  message?: string
}

interface NarrativeSection {
  title: string
  content?: string
  status?: string
  verified_count?: number
  correct_count?: number
  q?: number
  theta_min?: number
  iks?: number
  decision_count?: number
  strongest_categories?: NarrativeCategory[]
  weakest_category?: NarrativeCategory | null
  items?: NarrativeRecommendationItem[]
}

interface NarrativeData {
  headline: string
  what_changed: WhatChanged
  what_discovered: WhatDiscovered
  what_knows: WhatKnows
  metrics: Metrics
  generated_at: string
  pdf_available: boolean
  sections?: NarrativeSection[]
}

interface GovernanceSummarySection {
  article: string
  title: string
  status: string
  evidence_count: number
  legal_disclaimer: string
}

interface GovernanceSummaryData {
  title: string
  generated_at: string
  overall_assessment: string
  legal_disclaimer: string
  sections: GovernanceSummarySection[]
}

interface GovernanceReportSection extends GovernanceSummarySection {
  summary: string
  evidence: Record<string, unknown>
}

interface GovernanceReportData extends GovernanceSummaryData {
  report_id: string
  system_version: string
  decision_count: number
  evidence_item_count: number
  known_risks: Array<Record<string, string>>
  sections: GovernanceReportSection[]
}

interface DomainApplicabilityRow {
  name?: string
  short?: string
  categories?: number
  actions?: number
  factors?: number
  tensor_size?: number
  penalty_ratio?: number
  engineering_days?: number | null
  status?: string
  verification?: string
  categories_list?: string[]
  actions_list?: string[]
}

interface DomainApplicabilityResponse {
  domains?: DomainApplicabilityRow[]
  total?: number
  live?: number
  specified?: number
  designed?: number
  engine_version?: string
  note?: string
  cross_domain_surfaces?: string
}

const GOVERNANCE_DISCLAIMER =
  'Evidence supporting human oversight only. This report is not a compliance certification or legal determination.'

function healthColor(status: string) {
  if (status === 'GREEN') return 'text-green-400'
  if (status === 'AMBER') return 'text-amber-400'
  if (status === 'CALIBRATING') return 'text-blue-400'
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

function formatPct(value: unknown): string {
  const n = toNumber(value)
  return `${(n * 100).toFixed(1)}%`
}

function NarrativeSectionCards({ sections }: { sections: NarrativeSection[] }) {
  if (sections.length === 0) return null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {sections.map((section, index) => {
        const strongest = ensureArray<NarrativeCategory>(section.strongest_categories)
        const items = ensureArray<NarrativeRecommendationItem>(section.items)
        return (
          <div
            key={safeKey(section.title, index)}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4"
          >
            <div className="flex items-center justify-between gap-3 mb-3">
              <h3 className="text-sm font-semibold text-gray-200">{section.title}</h3>
              {section.status && (
                <span className={`text-xs font-semibold ${healthColor(section.status)}`}>
                  {section.status}
                </span>
              )}
            </div>

            {section.content && (
              <p className="text-xs text-gray-300 leading-relaxed">{section.content}</p>
            )}

            {section.title === 'System Health' && (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-400">
                <div>
                  <div className="text-gray-500">Verified</div>
                  <div className="font-mono text-gray-200">{toNumber(section.verified_count)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Correct</div>
                  <div className="font-mono text-gray-200">{toNumber(section.correct_count)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Rolling accuracy</div>
                  <div className="font-mono text-gray-200">{formatPct(section.q)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Threshold</div>
                  <div className="font-mono text-gray-200">{formatPct(section.theta_min)}</div>
                </div>
              </div>
            )}

            {section.title === 'What the System Has Learned' && (
              <div className="mt-3 space-y-3 text-xs text-gray-400">
                <div className="flex justify-between">
                  <span>IKS</span>
                  <span className="font-mono text-gray-200">{toNumber(section.iks).toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Decisions processed</span>
                  <span className="font-mono text-gray-200">{toNumber(section.decision_count)}</span>
                </div>
                {strongest.length > 0 && (
                  <div>
                    <div className="text-gray-500 mb-1">Strongest categories</div>
                    <div className="space-y-1">
                      {strongest.map((category, categoryIndex) => (
                        <div
                          key={safeKey(category.name, categoryIndex)}
                          className="flex justify-between rounded bg-gray-800 px-2 py-1"
                        >
                          <span>{category.name.replace(/_/g, ' ')}</span>
                          <span className="font-mono text-gray-200">{formatPct(category.accuracy)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {section.weakest_category && (
                  <div className="rounded bg-gray-800 px-2 py-1">
                    <span className="text-gray-500">Weakest category: </span>
                    <span className="text-gray-200">
                      {section.weakest_category.name.replace(/_/g, ' ')}
                    </span>
                  </div>
                )}
              </div>
            )}

            {section.title === 'Recommendations' && (
              <div className="mt-3 space-y-2">
                {items.length > 0 ? (
                  items.map((item, itemIndex) => (
                    <div
                      key={safeKey(`${item.type || 'recommendation'}-${item.category || itemIndex}`, itemIndex)}
                      className="rounded bg-gray-800 px-3 py-2 text-xs text-gray-300"
                    >
                      <div className="font-semibold text-gray-200">
                        {(item.category || item.type || 'Recommendation').replace(/_/g, ' ')}
                      </div>
                      {item.message && <p className="mt-1 leading-relaxed">{item.message}</p>}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500">No category-specific action required.</p>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function statusTone(status: string) {
  if (status === 'READY' || status === 'GREEN') return 'bg-green-500/15 text-green-300 border-green-500/30'
  if (status === 'PAUSED' || status === 'AMBER') return 'bg-amber-500/15 text-amber-300 border-amber-500/30'
  if (status === 'CALIBRATING') return 'bg-blue-900/40 text-blue-400 border-blue-500/30'
  return 'bg-red-500/15 text-red-300 border-red-500/30'
}

function formatEvidenceValue(value: unknown): string {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function EvidenceValue({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    return (
      <div className="space-y-2">
        {value.map((item, index) => (
          <div key={index} className="rounded border border-gray-700 bg-gray-950/60 px-3 py-2 text-xs text-gray-300">
            <EvidenceValue value={item} />
          </div>
        ))}
      </div>
    )
  }

  if (value && typeof value === 'object') {
    return (
      <div className="space-y-2">
        {Object.entries(value).map(([key, nestedValue]) => (
          <div key={key} className="rounded border border-gray-700 bg-gray-950/60 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wide text-gray-500">{key.replace(/_/g, ' ')}</div>
            <div className="mt-1 text-xs text-gray-300">
              <EvidenceValue value={nestedValue} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <span>{formatEvidenceValue(value)}</span>
}

function toNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function domainStatusTone(status: string) {
  if (status === 'live') return 'bg-green-500/15 text-green-300 border-green-500/30'
  if (status === 'specified') return 'bg-blue-500/15 text-blue-300 border-blue-500/30'
  if (status === 'designed') return 'bg-gray-700/70 text-gray-300 border-gray-600'
  return 'bg-amber-500/15 text-amber-300 border-amber-500/30'
}

function DomainApplicabilityTable({ data }: { data: DomainApplicabilityResponse | null }) {
  const domains = ensureArray<DomainApplicabilityRow>(data?.domains)
  if (domains.length === 0) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-800 flex flex-wrap items-start gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">Domain Applicability</h3>
          <p className="mt-1 text-xs text-gray-500">Nine domains, one engine. Each row still requires domain engineering.</p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-full border border-green-500/30 bg-green-500/10 px-2 py-1 text-green-300">{toNumber(data?.live)} live</span>
          <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-blue-300">{toNumber(data?.specified)} specified</span>
          <span className="rounded-full border border-gray-600 bg-gray-800 px-2 py-1 text-gray-300">{toNumber(data?.designed)} designed</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-800 text-left text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Domain</th>
              <th className="px-4 py-3 font-medium">Shape</th>
              <th className="px-4 py-3 font-medium">Size</th>
              <th className="px-4 py-3 font-medium">Penalty</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Est.</th>
            </tr>
          </thead>
          <tbody>
            {domains.map((domain, index) => {
              const status = String(domain?.status || 'designed').toLowerCase()
              const categories = toNumber(domain?.categories)
              const actions = toNumber(domain?.actions)
              const factors = toNumber(domain?.factors)
              const engineeringDays = domain?.engineering_days
              return (
                <tr
                  key={safeKey(domain?.short || domain?.name, index)}
                  className="border-b border-gray-800/70 last:border-0 hover:bg-gray-800/30"
                  title={domain?.verification || undefined}
                >
                  <td className="px-4 py-3">
                    <div className="font-semibold text-gray-200">{domain?.short || 'Domain'}</div>
                    <div className="mt-0.5 text-[11px] text-gray-500">{domain?.name || 'Unnamed domain'}</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-300">({categories},{actions},{factors})</td>
                  <td className="px-4 py-3 font-mono text-gray-300">{toNumber(domain?.tensor_size)}</td>
                  <td className="px-4 py-3 font-mono text-gray-300">{toNumber(domain?.penalty_ratio)}:1</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full border px-2 py-1 text-[11px] uppercase tracking-wide ${domainStatusTone(status)}`}>
                      {status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {typeof engineeringDays === 'number' ? `${engineeringDays}d` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="border-t border-gray-800 px-5 py-3 text-xs text-gray-400 space-y-1">
        <p>{data?.note || 'Domain expansion requires explicit engineering for each domain surface.'}</p>
        <p className="text-gray-500">{data?.cross_domain_surfaces || 'Cross-domain surfaces grow with each additional domain.'}</p>
      </div>
    </div>
  )
}

export default function ExecutiveNarrativeTab() {
  const [data, setData] = useState<NarrativeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [govExpanded, setGovExpanded] = useState(false)
  const [governanceSummary, setGovernanceSummary] = useState<GovernanceSummaryData | null>(null)
  const [governanceReport, setGovernanceReport] = useState<GovernanceReportData | null>(null)
  const [governanceLoading, setGovernanceLoading] = useState(false)
  const [governanceError, setGovernanceError] = useState<string | null>(null)
  const [downloadingJson, setDownloadingJson] = useState(false)
  const [expandedArticle, setExpandedArticle] = useState<string | null>(null)
  const [domainApplicability, setDomainApplicability] = useState<DomainApplicabilityResponse | null>(null)

  useEffect(() => {
    fetch(`${SOC_API}/api/soc/executive-narrative`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetch(`${SOC_API}/api/platform/domain-applicability`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((payload) => setDomainApplicability(payload && typeof payload === 'object' ? payload : null))
      .catch((e) => {
        console.debug('[ExecutiveNarrativeTab] Domain applicability unavailable:', e)
        setDomainApplicability(null)
      })
  }, [])

  useEffect(() => {
    if (!govExpanded || governanceSummary || governanceLoading) return

    setGovernanceLoading(true)
    setGovernanceError(null)
    fetchGovernanceSummary()
      .then((summary) => setGovernanceSummary(summary as GovernanceSummaryData))
      .catch((e) => setGovernanceError(e instanceof Error ? e.message : 'Failed to load governance summary'))
      .finally(() => setGovernanceLoading(false))
  }, [govExpanded, governanceLoading, governanceSummary])

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
  const narrativeSections = ensureArray<NarrativeSection>(data.sections)
  const governanceSections = ensureArray<GovernanceSummarySection>(governanceSummary?.sections)

  async function handleGovernanceJsonDownload() {
    try {
      setDownloadingJson(true)
      setGovernanceError(null)
      const report = await downloadGovernanceReportJson() as GovernanceReportData
      setGovernanceReport(report)
    } catch (e) {
      setGovernanceError(e instanceof Error ? e.message : 'Failed to download governance report')
    } finally {
      setDownloadingJson(false)
    }
  }

  function handleGovernanceCsvDownload() {
    setGovernanceError(null)
    downloadGovernanceReportCsv()
  }

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
            href="/api/soc/executive-narrative/pdf"
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

      <NarrativeSectionCards sections={narrativeSections} />

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
          {ensureArray<Shift>(what_changed.top_shifts).length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Top shifts</p>
              {ensureArray<Shift>(what_changed.top_shifts).map((s, i) => (
                <div key={i} className="bg-gray-800 rounded p-2 text-xs text-gray-300">
                  {s.description}
                </div>
              ))}
            </div>
          )}
          {ensureArray<Shift>(what_changed.top_shifts).length === 0 && (
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
          {ensureArray<string>(what_discovered.chain_summaries).length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Chain summaries</p>
              {ensureArray<string>(what_discovered.chain_summaries).map((s, i) => (
                <div key={i} className="bg-gray-800 rounded p-2 text-xs text-gray-300">{s}</div>
              ))}
            </div>
          )}
          {ensureArray<string>(what_discovered.chain_summaries).length === 0 && (
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
          {what_knows.conservation_narrative && (
            <div className="mt-3 bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Conservation & Audit Status</p>
              <p className="text-xs text-gray-300 leading-relaxed">{what_knows.conservation_narrative}</p>
            </div>
          )}
        </div>
      </div>

      <DomainApplicabilityTable data={domainApplicability} />

      {/* Governance & Compliance — governance evidence export */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
        <button
          onClick={() => setGovExpanded((v) => !v)}
          className="w-full flex items-center gap-3 px-5 py-4 hover:bg-gray-800/50 transition-colors text-left"
        >
          <Shield className="w-4 h-4 text-green-400 shrink-0" />
          <div className="flex-1">
            <span className="text-sm font-semibold text-gray-200">Governance &amp; Compliance</span>
            <span className="ml-3 text-xs text-gray-500">Evidence export and oversight review</span>
          </div>
          <div className="flex items-center gap-3">
            {governanceSummary && (
              <span className="text-xs font-semibold text-green-400">
                {governanceSummary.sections.length} Sections Ready
              </span>
            )}
            {govExpanded
              ? <ChevronDown className="w-4 h-4 text-gray-500" />
              : <ChevronRight className="w-4 h-4 text-gray-500" />}
          </div>
        </button>

        <div className="border-t border-gray-800 px-5 py-4">
          <div className="rounded-lg border border-yellow-500/30 bg-amber-500/10 px-4 py-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-300">Legal Disclaimer</div>
                <p className="mt-1 text-sm text-amber-100">{governanceSummary?.legal_disclaimer ?? GOVERNANCE_DISCLAIMER}</p>
              </div>
            </div>
          </div>
        </div>

        {govExpanded && (
          <div className="border-t border-gray-800 px-5 py-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-sm font-semibold text-gray-200">{governanceSummary?.title ?? 'Governance Evidence Export'}</div>
                <p className="mt-1 text-xs text-gray-400">
                  {governanceSummary?.overall_assessment ?? 'Expand this section to load the five-section governance summary.'}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleGovernanceJsonDownload}
                  disabled={downloadingJson}
                  className="inline-flex items-center gap-2 rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-sm font-medium text-sky-200 transition-colors hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Download className="h-4 w-4" />
                  {downloadingJson ? 'Downloading JSON...' : 'Download JSON'}
                </button>
                <button
                  type="button"
                  onClick={handleGovernanceCsvDownload}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-700"
                >
                  <Download className="h-4 w-4" />
                  Download CSV
                </button>
              </div>
            </div>

            {governanceLoading && (
              <div className="mt-4 rounded-lg border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-400">
                Loading governance summary…
              </div>
            )}

            {governanceError && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {governanceError}
              </div>
            )}

            {!governanceLoading && governanceSections.length > 0 && (
              <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-5">
                {governanceSections.map((section) => {
                  const isOpen = expandedArticle === section.article
                  const detailSection = governanceReport?.sections.find((entry) => entry.article === section.article)
                  return (
                    <div
                      key={section.article}
                      className="rounded-xl border border-gray-800 bg-gray-950/60 transition-colors hover:border-gray-700"
                    >
                      <button
                        type="button"
                        onClick={() => setExpandedArticle(isOpen ? null : section.article)}
                        className="w-full px-4 py-4 text-left"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-xs font-mono uppercase tracking-wide text-green-300">{section.article}</div>
                            <div className="mt-1 text-sm font-semibold text-gray-100">{section.title}</div>
                          </div>
                          <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${statusTone(section.status)}`}>
                            {section.status}
                          </span>
                        </div>
                        <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
                          <span>{section.evidence_count} evidence items</span>
                          <span className="inline-flex items-center gap-1">
                            {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                            Details
                          </span>
                        </div>
                      </button>

                      {isOpen && (
                        <div className="border-t border-gray-800 px-4 py-4">
                          {detailSection ? (
                            <div className="space-y-3">
                              <p className="text-xs text-gray-400">{detailSection.summary}</p>
                              <div className="space-y-3">
                                {Object.entries(detailSection.evidence).map(([key, value]) => (
                                  <div key={key} className="rounded-lg border border-gray-800 bg-gray-900/80 p-3">
                                    <div className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                                      {key.replace(/_/g, ' ')}
                                    </div>
                                    <div className="mt-2 text-xs text-gray-300">
                                      <EvidenceValue value={value} />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="rounded-lg border border-dashed border-gray-700 bg-gray-900/50 px-3 py-4 text-xs text-gray-400">
                              Detailed evidence is loaded only when you click <span className="font-semibold text-gray-200">Download JSON</span>.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {!governanceLoading && governanceSummary && (
              <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-gray-500">
                <span>Generated {governanceSummary.generated_at.replace('T', ' ').replace('Z', ' UTC')}</span>
                {governanceReport && (
                  <>
                    <span className="text-gray-600">•</span>
                    <span>{governanceReport.decision_count} decisions referenced</span>
                    <span className="text-gray-600">•</span>
                    <span>{governanceReport.evidence_item_count} evidence items in downloaded JSON</span>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Activity indicator */}
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <Activity className="w-3 h-3" />
        <span>Data reflects verified decisions stored in Neo4j. Refresh page to regenerate.</span>
      </div>
    </div>
  )
}
