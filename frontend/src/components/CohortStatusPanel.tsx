import { useEffect, useMemo, useState } from 'react'
import { Activity, BarChart3, CheckCircle2, Clock3, FlaskConical, RadioTower } from 'lucide-react'
import { getCohortStatus, type CohortStatusResponse, type CohortStatusState } from '../lib/api'

const STATE_COPY: Record<CohortStatusState, { label: string; tone: string; icon: typeof CheckCircle2 }> = {
  INSTRUMENT_VALIDATED: {
    label: 'INSTRUMENT_VALIDATED',
    tone: 'border-cyan-200 bg-cyan-50 text-cyan-800',
    icon: CheckCircle2,
  },
  ACCUMULATING: {
    label: 'ACCUMULATING',
    tone: 'border-amber-200 bg-amber-50 text-amber-800',
    icon: Clock3,
  },
  MEASURED: {
    label: 'MEASURED',
    tone: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    icon: BarChart3,
  },
}

function formatCount(value: number | undefined): string {
  return typeof value === 'number' ? value.toLocaleString() : '0'
}

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== 'number') return 'Pending'
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}pp`
}

function progressPercent(real: CohortStatusResponse['real']): number {
  const threshold = real.threshold_k ?? 50
  if (threshold <= 0) return 0
  const treatment = Math.min(real.treatment_n ?? 0, threshold)
  const control = Math.min(real.control_n ?? 0, threshold)
  return Math.round(((treatment + control) / (threshold * 2)) * 100)
}

export default function CohortStatusPanel() {
  const [status, setStatus] = useState<CohortStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    getCohortStatus()
      .then((payload) => {
        if (!active) return
        setStatus(payload)
        setError(false)
      })
      .catch(() => {
        if (!active) return
        setError(true)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const state = status?.state ?? 'INSTRUMENT_VALIDATED'
  const real = status?.real ?? {}
  const instrument = status?.instrument ?? {}
  const structure = status?.structure
  const stateMeta = STATE_COPY[state] ?? STATE_COPY.INSTRUMENT_VALIDATED
  const StateIcon = stateMeta.icon
  const progress = useMemo(() => progressPercent(real), [real])
  const experiments = instrument.experiments ?? []
  const passedExperiments = experiments.filter((experiment) => experiment.pass).length

  return (
    <section
      data-testid="cohort-status-panel"
      className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
      aria-label="Campaign Measurement Status"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-slate-700" />
            <h3 data-testid="cohort-status-title" className="text-lg font-semibold text-slate-900">
              Campaign Measurement Status
            </h3>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            Oracle instrument evidence is separated from real campaign cohorts.
          </p>
        </div>
        <span
          data-testid="cohort-status-state-badge"
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${stateMeta.tone}`}
        >
          <StateIcon className="h-3.5 w-3.5" />
          {stateMeta.label}
        </span>
      </div>

      {loading && (
        <div data-testid="cohort-status-loading" className="mt-4 text-sm text-slate-500">
          Loading cohort status...
        </div>
      )}

      {error && (
        <div data-testid="cohort-status-error" className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Cohort status endpoint unavailable.
        </div>
      )}

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div data-testid="cohort-status-instrument" className="rounded-lg border border-cyan-100 bg-cyan-50/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-cyan-700" />
              <h4 className="text-sm font-semibold text-slate-900">Instrument</h4>
            </div>
            <span
              data-testid="cohort-status-instrument-tier"
              className="rounded-full border border-cyan-200 bg-white px-2 py-0.5 text-[11px] font-semibold text-cyan-700"
            >
              T-O
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Oracle checks</div>
              <div className="mt-1 font-semibold text-slate-900">
                {passedExperiments}/{experiments.length || 0} passed
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Artifact</div>
              <div className="mt-1 truncate font-semibold text-slate-900">
                {instrument.validated ? 'validated' : 'pending'}
              </div>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-600">
            Source: {instrument.provenance ?? 'oracle'}
          </div>
        </div>

        <div data-testid="cohort-status-real" className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <RadioTower className="h-4 w-4 text-emerald-700" />
              <h4 className="text-sm font-semibold text-slate-900">Real cohort</h4>
            </div>
            <span
              data-testid="cohort-status-real-tier"
              className="rounded-full border border-emerald-200 bg-white px-2 py-0.5 text-[11px] font-semibold text-emerald-700"
            >
              T-R
            </span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Treatment</div>
              <div className="mt-1 font-semibold text-slate-900">{formatCount(real.treatment_n)}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Control</div>
              <div className="mt-1 font-semibold text-slate-900">{formatCount(real.control_n)}</div>
            </div>
            <div data-testid="cohort-status-lift">
              <div className="text-xs uppercase tracking-wide text-slate-500">Lift</div>
              <div className="mt-1 font-semibold text-slate-900">{formatPercent(real.lift)}</div>
            </div>
          </div>

          <div data-testid="cohort-status-progress" className="mt-4">
            <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
              <span>Real cohort progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${progress}%` }} />
            </div>
            <div className="mt-2 text-xs text-slate-600">
              Threshold: {formatCount(real.threshold_k)} per arm
            </div>
          </div>
        </div>
      </div>

      {structure?.present && (
        <div data-testid="cohort-status-structure" className="mt-4 text-xs text-slate-500">
          Sample structure loaded: treatment {formatCount(structure.treatment_n)}, control {formatCount(structure.control_n)}.
        </div>
      )}
    </section>
  )
}
