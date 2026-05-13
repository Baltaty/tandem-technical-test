'use client'

import { Insights, Issue } from '@/lib/types'
import FunnelChart from './FunnelChart'
import IssueCard from './IssueCard'
import BehaviorCard from './BehaviorCard'
import SessionList from './SessionList'
import JourneyList from './JourneyList'
import { AlertTriangle } from 'lucide-react'

interface Props { insights: Insights }

const SEVERITY_ORDER: Record<Issue['severity'], number> = { critical: 0, high: 1, medium: 2, low: 3 }

export default function Dashboard({ insights }: Props) {
  const { meta, funnel, issues, behaviors, journeys } = insights
  const sorted = [...issues].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity])

  return (
    <div className="min-h-screen px-16 py-12 max-w-[1200px] mx-auto">

      <header className="text-center mb-14">
        <img src="/logo.png" alt="Data Explorer by Tandem" className="h-20 object-contain mx-auto" />
        {meta.missing_timestamps > 0 && (
          <div className="mt-3 text-xs text-[var(--yellow)] flex items-center justify-center gap-1">
            <AlertTriangle size={13} /> {meta.missing_timestamps} event(s) with missing timestamp
          </div>
        )}
      </header>

      <h2 className="text-center text-[1.6rem] font-bold mb-12">Session Analysis</h2>

      {/* KPI row */}
      <section className="grid grid-cols-4 gap-6 mb-16">
        {[
          { label: 'Events',        value: meta.total_events,                    alert: false },
          { label: 'Users',         value: meta.total_users,                     alert: false },
          { label: 'Sessions',      value: meta.total_sessions,                  alert: false },
          { label: 'Checkout → Order', value: `${funnel.checkout_conversion_rate}%`, alert: funnel.checkout_conversion_rate < 70 },
        ].map(({ label, value, alert }) => (
          <div
            key={label}
            className={`border-2 rounded-[32px] px-8 py-6 ${alert ? 'border-[var(--red)]' : 'border-[var(--green)]'}`}
          >
            <div className="text-[11px] text-[var(--muted)] uppercase tracking-[0.12em] mb-2 font-medium">
              {label}
            </div>
            <div className={`text-[2.2rem] font-extrabold ${alert ? 'text-[var(--red)]' : 'text-[var(--text)]'}`}>
              {value}
            </div>
          </div>
        ))}
      </section>

      {/* Conversion Funnel */}
      <section className="mb-16">
        <SectionTitle title="Conversion Funnel" />
        <div className="grid grid-cols-2 gap-6">
          <FunnelChart steps={funnel.steps} />
          <CheckoutOutcomes outcomes={funnel.checkout_outcomes} />
        </div>
      </section>

      {/* Most Common Journeys */}
      <section className="mb-16">
        <SectionTitle title="Most Common Journeys" subtitle={`top ${journeys.most_common.length} paths`} />
        <JourneyList journeys={journeys.most_common} />
      </section>

      {/* Sessions */}
      <section className="mb-16">
        <SectionTitle title="Sessions" subtitle={`${journeys.all.length} sessions`} />
        <SessionList sessions={journeys.all} />
      </section>

      {/* Detected Issues */}
      <section className="mb-16">
        <SectionTitle title="Detected Issues" subtitle={`${issues.length} issues found`} />
        <div className="flex flex-col gap-4">
          {sorted.map(issue => <IssueCard key={issue.id} issue={issue} journeys={journeys.all} />)}
        </div>
      </section>

      {/* Interesting Behaviors */}
      <section className="mb-16">
        <SectionTitle title="Interesting Behaviors" subtitle={`${behaviors.length} patterns surfaced`} />
        <div className="grid grid-cols-2 gap-4">
          {behaviors.map(b => <BehaviorCard key={b.id} behavior={b} />)}
        </div>
      </section>

    </div>
  )
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="flex items-baseline gap-3 mb-6">
      <h2 className="text-2xl font-bold">{title}</h2>
      {subtitle && <span className="text-[13px] text-[var(--muted)]">{subtitle}</span>}
    </div>
  )
}

function CheckoutOutcomes({ outcomes }: { outcomes: Record<string, number> }) {
  const total = Object.values(outcomes).reduce((a, b) => a + b, 0)
  const colors: Record<string, string> = {
    completed:            'var(--green)',
    cancelled:            'var(--red)',
    retried_then_dropped: 'var(--orange)',
    dropped_silently:     'var(--muted)',
  }
  const labels: Record<string, string> = {
    completed:            'Completed',
    cancelled:            'Cancelled',
    retried_then_dropped: 'Retried & dropped',
    dropped_silently:     'Silent drop',
  }

  return (
    <div className="border border-[var(--border)] rounded-[32px] p-8">
      <div className="text-[11px] text-[var(--muted)] uppercase tracking-[0.12em] mb-6 font-semibold">
        Checkout Outcomes
      </div>
      <div className="flex flex-col gap-5">
        {Object.entries(outcomes).map(([key, count]) => (
          <div key={key}>
            <div className="flex justify-between mb-1.5">
              <span className="text-[13px] font-medium" style={{ color: colors[key] ?? 'var(--text)' }}>
                {labels[key] ?? key}
              </span>
              <span className="text-[13px] text-[var(--muted)]">{count} / {total}</span>
            </div>
            <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-[width] duration-[600ms] ease-in-out"
                style={{ width: `${(count / total) * 100}%`, background: colors[key] ?? 'var(--green)' }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
