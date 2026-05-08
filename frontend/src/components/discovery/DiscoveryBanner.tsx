import { useEffect, useState } from 'react'
import { Network, X } from 'lucide-react'
import { ensureArray, ensureNumber, ensureString } from '../../lib/guards'

interface DiscoveryCache {
  hit: boolean
  stale: boolean
  ttl_seconds: number | null
}

interface DiscoveryItem {
  discovery_id: string
  domain: string
  source_domains: string[]
  type: string
  severity: string
  title: string
  description: string
  score: number | null
  discovered_at: string
  involved_entity_ids: string[]
  involved_alert_ids: string[]
  involved_decision_ids: string[]
  threat_indicator_ids: string[]
  entity_summary: string
  category_summary: string
  temporal_summary: string
  factor_summary: string
}

interface DiscoveryEnvelope {
  domain: string
  source_domains: string[]
  generated_at: string | null
  as_of_epoch_ms: number | null
  cache: DiscoveryCache
  discoveries: DiscoveryItem[]
  total: number
  errors: string[]
}

const EMPTY_CACHE: DiscoveryCache = {
  hit: false,
  stale: false,
  ttl_seconds: null,
}

const DISCOVERIES_ENDPOINT = '/api/discoveries?domain=soc'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function normalizeCache(value: unknown): DiscoveryCache {
  const cache = asRecord(value)
  const ttl = cache.ttl_seconds

  return {
    hit: Boolean(cache.hit),
    stale: Boolean(cache.stale),
    ttl_seconds: typeof ttl === 'number' ? ttl : null,
  }
}

function normalizeDiscovery(value: unknown): DiscoveryItem | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null

  const discovery = asRecord(value)
  const score = discovery.score
  const title = ensureString(discovery.title)
  const description = ensureString(discovery.description)
  const discoveredAt = ensureString(discovery.discovered_at)
  const involvedEntityIds = ensureArray<string>(discovery.involved_entity_ids)
  const involvedAlertIds = ensureArray<string>(discovery.involved_alert_ids)
  const involvedDecisionIds = ensureArray<string>(discovery.involved_decision_ids)
  const threatIndicatorIds = ensureArray<string>(discovery.threat_indicator_ids)
  const entitySummary = ensureString(discovery.entity_summary)
  const categorySummary = ensureString(discovery.category_summary)
  const temporalSummary = ensureString(discovery.temporal_summary)
  const factorSummary = ensureString(discovery.factor_summary)
  const hasEvidence =
    Boolean(ensureString(discovery.discovery_id)) ||
    Boolean(title) ||
    Boolean(description) ||
    Boolean(discoveredAt) ||
    involvedEntityIds.length > 0 ||
    involvedAlertIds.length > 0 ||
    involvedDecisionIds.length > 0 ||
    threatIndicatorIds.length > 0 ||
    Boolean(entitySummary) ||
    Boolean(categorySummary) ||
    Boolean(temporalSummary) ||
    Boolean(factorSummary)

  if (!hasEvidence) return null

  return {
    discovery_id: ensureString(discovery.discovery_id),
    domain: ensureString(discovery.domain, 'soc'),
    source_domains: ensureArray<string>(discovery.source_domains),
    type: ensureString(discovery.type),
    severity: ensureString(discovery.severity),
    title,
    description,
    score: typeof score === 'number' && Number.isFinite(score) ? score : null,
    discovered_at: discoveredAt,
    involved_entity_ids: involvedEntityIds,
    involved_alert_ids: involvedAlertIds,
    involved_decision_ids: involvedDecisionIds,
    threat_indicator_ids: threatIndicatorIds,
    entity_summary: entitySummary,
    category_summary: categorySummary,
    temporal_summary: temporalSummary,
    factor_summary: factorSummary,
  }
}

function normalizeEnvelope(value: unknown): DiscoveryEnvelope {
  const envelope = asRecord(value)
  const discoveries = ensureArray<unknown>(envelope.discoveries).reduce<DiscoveryItem[]>((items, item) => {
    const discovery = normalizeDiscovery(item)
    if (discovery) items.push(discovery)
    return items
  }, [])

  return {
    domain: ensureString(envelope.domain, 'soc'),
    source_domains: ensureArray<string>(envelope.source_domains),
    generated_at: typeof envelope.generated_at === 'string' ? envelope.generated_at : null,
    as_of_epoch_ms: typeof envelope.as_of_epoch_ms === 'number' ? envelope.as_of_epoch_ms : null,
    cache: envelope.cache ? normalizeCache(envelope.cache) : EMPTY_CACHE,
    discoveries,
    total: ensureNumber(envelope.total, discoveries.length),
    errors: ensureArray<string>(envelope.errors),
  }
}

function severityClasses(level: string): string {
  switch (level.toLowerCase()) {
    case 'high':
      return 'bg-red-500/20 text-red-300 border-red-500/40'
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
    default:
      return 'bg-blue-500/20 text-blue-300 border-blue-500/40'
  }
}

function formatType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function renderInlineList(label: string, items: string[]) {
  if (items.length === 0) return null

  return (
    <div className="rounded border border-amber-500/20 bg-amber-950/20 px-3 py-2 text-xs text-amber-100/80">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-300/70">{label}</div>
      <div className="mt-1 font-mono text-amber-50">
        {items.slice(0, 4).join(', ')}
        {items.length > 4 ? ` +${items.length - 4}` : ''}
      </div>
    </div>
  )
}

function parseDiscoveryTime(value: string): number {
  const time = Date.parse(value)
  return Number.isFinite(time) ? time : 0
}

function selectStrongestDiscovery(discoveries: DiscoveryItem[]): DiscoveryItem | null {
  if (discoveries.length === 0) return null

  return discoveries.reduce((best, candidate) => {
    const bestAlertCount = ensureArray<string>(best.involved_alert_ids).length
    const candidateAlertCount = ensureArray<string>(candidate.involved_alert_ids).length
    if (candidateAlertCount !== bestAlertCount) {
      return candidateAlertCount > bestAlertCount ? candidate : best
    }

    const bestTime = parseDiscoveryTime(best.discovered_at)
    const candidateTime = parseDiscoveryTime(candidate.discovered_at)
    if (candidateTime !== bestTime) {
      return candidateTime > bestTime ? candidate : best
    }

    return best
  }, discoveries[0])
}

async function fetchDiscoveryEnvelope(): Promise<DiscoveryEnvelope> {
  const response = await fetch(DISCOVERIES_ENDPOINT)
  if (!response.ok) {
    throw new Error(`Discovery request failed: ${response.status}`)
  }
  return normalizeEnvelope(await response.json())
}

function DiscoveryAnchor({ discovery, onDismiss }: { discovery: DiscoveryItem; onDismiss: () => void }) {
  const alertIds = ensureArray<string>(discovery.involved_alert_ids)
  const entitySummary = ensureString(discovery.entity_summary)
  const categorySummary = ensureString(discovery.category_summary)
  const temporalSummary = ensureString(discovery.temporal_summary)
  const factorSummary = ensureString(discovery.factor_summary)
  const indicators = ensureArray<string>(discovery.threat_indicator_ids)
  const metadataItems = [
    discovery.score !== null ? `Discovery score ${discovery.score.toFixed(2)}` : '',
    discovery.discovered_at ? `Discovered ${discovery.discovered_at}` : '',
    factorSummary,
  ].filter(Boolean)

  return (
    <section data-testid="discovery-banner" className="overflow-hidden rounded-lg border border-amber-500/40 bg-amber-950/20 shadow-lg">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-amber-500/20 px-5 py-4">
        <div className="flex min-w-0 gap-3">
          <div className="mt-0.5 rounded-full border border-amber-400/30 bg-amber-500/15 p-2">
            <Network className="h-5 w-5 text-amber-300" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-amber-50">Cross-Category Pattern Detected</h3>
              {discovery.severity && (
                <span className={`rounded border px-2 py-0.5 text-xs font-medium ${severityClasses(discovery.severity)}`}>
                  {discovery.severity.toUpperCase()}
                </span>
              )}
              {discovery.type && (
                <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-100">
                  {formatType(discovery.type)}
                </span>
              )}
            </div>
            {discovery.title && <p className="mt-1 text-sm font-medium text-amber-100">{discovery.title}</p>}
            {discovery.description && <p className="mt-1 max-w-4xl text-sm leading-6 text-amber-100/75">{discovery.description}</p>}
          </div>
        </div>

        <button
          type="button"
          onClick={onDismiss}
          className="rounded border border-amber-500/30 p-1.5 text-amber-100/70 transition-colors hover:border-amber-400 hover:text-amber-50"
          aria-label="Dismiss discovery banner"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-4 px-5 py-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {entitySummary && renderInlineList('Entity', [entitySummary])}
          {categorySummary && renderInlineList('Categories', [categorySummary])}
          {temporalSummary && renderInlineList('Time window', [temporalSummary])}
          {alertIds.length > 0 && renderInlineList('Alerts', [`${alertIds.length} matched`, ...alertIds])}
          {renderInlineList('Indicators', indicators)}
        </div>

        {metadataItems.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-amber-100/65">
            {metadataItems.map((item, index) => (
              <span key={item} className="inline-flex items-center gap-2">
                {index > 0 && <span className="text-amber-500/60">·</span>}
                <span>{item}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export default function DiscoveryBanner() {
  const [selectedDiscovery, setSelectedDiscovery] = useState<DiscoveryItem | null>(null)
  const [dismissed, setDismissed] = useState(false)

  const loadDiscoveries = async () => {
    try {
      const payload = await fetchDiscoveryEnvelope()
      setSelectedDiscovery(selectStrongestDiscovery(ensureArray<DiscoveryItem>(payload.discoveries)))
    } catch (err) {
      console.debug('[DiscoveryBanner] Discovery service unavailable', err)
      setSelectedDiscovery(null)
    }
  }

  useEffect(() => {
    loadDiscoveries()
  }, [])

  if (dismissed || !selectedDiscovery) return null

  return <DiscoveryAnchor discovery={selectedDiscovery} onDismiss={() => setDismissed(true)} />
}
