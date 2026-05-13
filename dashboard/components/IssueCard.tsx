'use client'

import { Issue, Journey } from '@/lib/types'
import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertOctagon, AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { EventTimeline } from './EventTimeline'

interface Props {
  issue: Issue
  journeys: Journey[]
}

const SEVERITY_CONFIG = {
  critical: { color: 'var(--red)',    bg: 'rgba(239,68,68,0.08)',   label: 'CRITICAL', Icon: AlertOctagon },
  high:     { color: 'var(--orange)', bg: 'rgba(249,115,22,0.08)',  label: 'HIGH',     Icon: AlertTriangle },
  medium:   { color: 'var(--yellow)', bg: 'rgba(245,158,11,0.08)',  label: 'MEDIUM',   Icon: AlertCircle },
  low:      { color: 'var(--muted)',  bg: 'rgba(107,114,128,0.08)', label: 'LOW',      Icon: Info },
}

export default function IssueCard({ issue, journeys }: Props) {
  const [open, setOpen]               = useState(false)
  const [openSession, setOpenSession] = useState<string | null>(null)
  const cfg = SEVERITY_CONFIG[issue.severity]

  function toggleSession(id: string) {
    setOpenSession(prev => prev === id ? null : id)
  }

  function findJourney(id: string): Journey | undefined {
    return journeys.find(j => j.session_id === id)
  }

  return (
    <div className="border border-[var(--border)] rounded-[32px] overflow-hidden">

      <button
        onClick={() => { setOpen(!open); setOpenSession(null) }}
        className="row-hover w-full bg-transparent border-none cursor-pointer px-7 py-5 flex items-center gap-4 text-left"
      >
        <span
          className="flex items-center gap-1.5 text-[10px] font-bold tracking-[0.1em] px-2.5 py-1 rounded-[20px] whitespace-nowrap"
          style={{ color: cfg.color, background: cfg.bg }}
        >
          <cfg.Icon size={11} />
          {cfg.label}
        </span>
        <span className="flex-1 text-[var(--text)] text-sm font-semibold">
          {issue.title}
        </span>
        <span className="text-[var(--muted)] text-xs whitespace-nowrap">
          {issue.affected_sessions.length} session{issue.affected_sessions.length > 1 ? 's' : ''}
        </span>
        <ChevronDown
          size={14} color="var(--muted)"
          style={{ transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none', flexShrink: 0 }}
        />
      </button>

      {open && (
        <div className="border-t border-[var(--border)]">

          <div className="px-7 py-5 border-b border-[var(--border)]">
            <p className="text-[var(--muted)] text-[13px] leading-relaxed">
              {issue.description}
            </p>
            <div className="mt-4 bg-[var(--bg3)] rounded-2xl px-5 py-4 border-l-[3px] border-[var(--green)]">
              <div className="text-[10px] text-[var(--green)] tracking-[0.12em] mb-1.5 uppercase font-bold">
                Recommendation
              </div>
              <p className="text-[13px] text-[var(--text)] leading-relaxed">
                {issue.recommendation}
              </p>
            </div>
          </div>

          <div className="px-7 py-4 flex flex-col gap-2">
            <div className="text-[10px] text-[var(--muted)] uppercase tracking-[0.1em] mb-1 font-semibold">
              Affected sessions
            </div>
            {issue.affected_sessions.map(id => {
              const journey = findJourney(id)
              const isOpen  = openSession === id

              return (
                <div key={id} className="border border-[var(--border)] rounded-2xl overflow-hidden">
                  <button
                    onClick={() => journey && toggleSession(id)}
                    disabled={!journey}
                    className={journey ? 'row-hover' : undefined}
                    style={{
                      width: '100%', background: 'none', border: 'none',
                      cursor: journey ? 'pointer' : 'default',
                      padding: '0.6rem 1rem',
                      display: 'flex', alignItems: 'center', gap: '0.75rem',
                      textAlign: 'left',
                    }}
                  >
                    <code className="text-[11px] text-[var(--text)] flex-1">
                      {id.slice(0, 8)}…
                    </code>
                    {journey && (
                      <>
                        <span className="text-[11px] text-[var(--muted)]">
                          {journey.event_count} events
                        </span>
                        <ChevronRight
                          size={13} color="var(--muted)"
                          style={{ transition: 'transform 0.2s', transform: isOpen ? 'rotate(90deg)' : 'none', flexShrink: 0 }}
                        />
                      </>
                    )}
                  </button>

                  {isOpen && journey && (
                    <div className="border-t border-[var(--border)] p-4 pl-5 bg-[var(--bg3)]">
                      <EventTimeline events={journey.events} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>

        </div>
      )}
    </div>
  )
}
