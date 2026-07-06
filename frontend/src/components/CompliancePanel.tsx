import { type ReactNode, useEffect, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env
const S2P_API = env?.VITE_S2P_API_URL || 'http://127.0.0.1:8002'
// Provenance: default "context" - this endpoint returns a compliance report.
// Override: uses data.provenance if S2P backend adds it.
const DEFAULT_TIER = 'context'

type Payload = Record<string, unknown>

function numberValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function statusTone(value: unknown): 'green' | 'yellow' | 'red' | 'gray' {
  const text = String(value ?? '').toLowerCase()
  if (text.includes('red') || text.includes('flag') || text.includes('high')) return 'red'
  if (text.includes('amber') || text.includes('review') || text.includes('medium')) return 'yellow'
  if (text.includes('green') || text.includes('clear') || text.includes('low') || text.includes('pass')) return 'green'
  return 'gray'
}

function Badge({ children, tone }: { children: ReactNode; tone: 'green' | 'yellow' | 'red' | 'gray' }) {
  const classes = {
    green: 'border-green-500/40 bg-green-500/10 text-green-200',
    yellow: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200',
    red: 'border-red-500/40 bg-red-500/10 text-red-200',
    gray: 'border-gray-700 bg-slate-900 text-gray-300',
  }[tone]
  return <span className={`rounded border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${classes}`}>{children}</span>
}

function shortHash(value: unknown): string {
  const text = typeof value === 'string' ? value : ''
  return text ? text.slice(0, 12) : 'Unavailable'
}

export default function CompliancePanel() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(false)
      try {
        const response = await fetch(`${S2P_API}/api/s2p/compliance/report`)
        if (!response.ok) throw new Error(String(response.status))
        const payload = await response.json() as Payload
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) {
          setData(null)
          setError(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const screened = numberValue(data?.screened_count ?? data?.suppliers_screened ?? data?.high_risk_screened)
  const flags = numberValue(data?.flagged_count ?? data?.flags_raised ?? data?.uflpa_flags)
  const auditHash = data?.audit_hash ?? data?.proof_hash ?? (data?.conservation_proof as Payload | undefined)?.audit_hash
  const provenance = typeof data?.provenance === 'string' ? data.provenance : DEFAULT_TIER

  return (
    <section className="rounded-lg border border-gray-800 bg-soc-card p-5" aria-label="Compliance Screening">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">Compliance screening</p>
          <h3 className="mt-1 text-base font-semibold text-gray-100">Supplier risk controls</h3>
        </div>
        <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[11px] uppercase tracking-wide text-blue-200">F22</span>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-400">Loading compliance report...</p>}
      {error && <p className="mt-4 text-sm text-red-300">S2P backend unavailable</p>}
      {!loading && !error && data && (
        <>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge tone={statusTone(data.uflpa_status ?? data.uflpa)}>UFLPA {String(data.uflpa_status ?? data.uflpa ?? 'pending')}</Badge>
            <Badge tone={statusTone(data.csddd_status ?? data.csddd)}>CSDDD {String(data.csddd_status ?? data.csddd ?? 'pending')}</Badge>
            <Badge tone={statusTone(data.scope3_status ?? data.scope_3)}>Scope 3 {String(data.scope3_status ?? data.scope_3 ?? 'pending')}</Badge>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Suppliers screened</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-gray-100">
                <span>{screened === null ? 'Unavailable' : screened.toLocaleString()}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Flags raised</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-2xl text-yellow-200">
                <span>{flags === null ? 'Unavailable' : flags.toLocaleString()}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
            <div className="rounded border border-gray-800 bg-slate-950/60 p-4">
              <div className="text-xs text-gray-500">Audit hash</div>
              <div className="mt-2 flex items-center gap-2 font-mono text-sm text-gray-100">
                <span>{shortHash(auditHash)}</span>
                <ProvenanceBadge source={provenance} />
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-300">
            {screened === null ? 'Supplier screen count unavailable.' : `${screened.toLocaleString()} suppliers screened.`} {flags === null ? 'Flag count unavailable.' : `${flags.toLocaleString()} compliance flags.`} SHA-256 audit: {shortHash(auditHash)}.
          </p>
        </>
      )}
    </section>
  )
}
