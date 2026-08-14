import { useEffect, useState } from 'react'

type DomainStatus = 'live' | 'specified' | 'designed' | 'unavailable'

interface Domain {
  domain: string
  name?: string
  status?: string
}

interface DomainApplicabilityResponse {
  domains?: Domain[]
}

const FALLBACK_DOMAINS: Domain[] = [
  { domain: 'SOC', name: 'Security Operations', status: 'live' },
  { domain: 'S2P', name: 'Source-to-Pay', status: 'unavailable' },
  { domain: 'Trading', status: 'live' },
  { domain: 'Purchasing', status: 'live' },
  { domain: 'DataOps', status: 'live' },
  { domain: 'Customer Support', status: 'specified' },
  { domain: 'Finance', status: 'specified' },
  { domain: 'HR', status: 'designed' },
  { domain: 'Healthcare', status: 'designed' },
]

function normalizeStatus(value: string | undefined): DomainStatus {
  if (value === 'live' || value === 'specified' || value === 'designed') return value
  return 'unavailable'
}

export default function DomainApplicabilityPanel() {
  const [domains, setDomains] = useState<Domain[]>(FALLBACK_DOMAINS)

  useEffect(() => {
    let cancelled = false

    async function loadApplicability() {
      const [tableResult, s2pHealthResult] = await Promise.allSettled([
        fetch('/api/platform/domain-applicability'),
        // The S2P service exposes its liveness route at /health.  Keep this
        // request on the frontend proxy so the service's route prefix is not
        // mistaken for an S2P backend route.
        fetch('/s2p-health'),
      ])

      if (cancelled) return

      let nextDomains = FALLBACK_DOMAINS
      if (tableResult.status === 'fulfilled' && tableResult.value.ok) {
        try {
          const payload = await tableResult.value.json() as DomainApplicabilityResponse
          if (Array.isArray(payload.domains) && payload.domains.length > 0) {
            nextDomains = payload.domains.map((domain) => ({
              ...domain,
              status: normalizeStatus(domain.status),
            }))
          }
        } catch {
          // Keep the static fail-closed domain list.
        }
      }

      // S2P availability is enrichment only. It must never remove the panel.
      if (s2pHealthResult.status === 'rejected' || !s2pHealthResult.value.ok) {
        nextDomains = nextDomains.map((domain) =>
          domain.domain === 'S2P' ? { ...domain, status: 'unavailable' } : domain,
        )
      }
      setDomains(nextDomains)
    }

    void loadApplicability()
    return () => { cancelled = true }
  }, [])

  const counts = domains.reduce<Record<DomainStatus, number>>((result, domain) => {
    const status = normalizeStatus(domain.status)
    result[status] += 1
    return result
  }, { live: 0, specified: 0, designed: 0, unavailable: 0 })

  return (
    <section data-testid="domain-applicability-panel" className="rounded-lg border border-gray-800 bg-soc-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-100">Domain Applicability</h2>
          <p className="mt-1 text-sm text-gray-400">Nine domains, one engine.</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-gray-400">
          <span>{counts.live} live</span>
          <span>{counts.specified} specified</span>
          <span>{counts.designed} designed</span>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-3">
        {domains.map((domain) => {
          const status = normalizeStatus(domain.status)
          return (
            <div key={domain.domain} className="flex items-center justify-between rounded border border-gray-800 bg-slate-950/60 px-3 py-2">
              <span className="text-sm text-gray-200">{domain.domain}</span>
              <span className="text-xs uppercase tracking-wide text-gray-500">{status}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
