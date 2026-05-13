'use client'

import { Journey } from '@/lib/types'
import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertTriangle, Check } from 'lucide-react'
import { EventTimeline, pageLabelColor } from './EventTimeline'

interface Props { sessions: Journey[] }
type View = 'all' | 'by_user'

export default function SessionList({ sessions }: Props) {
  const [view, setView] = useState<View>('all')

  return (
    <div className="border border-[var(--border)] rounded-[32px] overflow-hidden">
      <div className="flex gap-2 px-6 py-4 border-b border-[var(--border)]">
        {([['all', `All (${sessions.length})`], ['by_user', 'By User']] as const).map(([v, label]) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`rounded-full px-4 py-1.5 text-xs cursor-pointer border transition-all duration-150 ${
              view === v
                ? 'bg-[var(--text)] border-[var(--text)] text-white font-semibold'
                : 'bg-transparent border-[var(--border)] text-[var(--muted)] font-normal'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="max-h-[560px] overflow-y-auto">
        {view === 'all'
          ? sessions.map((s, i) => <SessionRow key={s.session_id} session={s} index={i} total={sessions.length} />)
          : <ByUserView sessions={sessions} />
        }
      </div>
    </div>
  )
}

// ── By User ───────────────────────────────────────────────────────────────────

function ByUserView({ sessions }: { sessions: Journey[] }) {
  const grouped = sessions.reduce<Record<string, Journey[]>>((acc, s) => {
    ;(acc[s.user_id] ??= []).push(s)
    return acc
  }, {})
  const sorted = Object.entries(grouped).sort((a, b) => b[1].length - a[1].length)
  return (
    <>
      {sorted.map(([uid, list], i) => (
        <UserGroup key={uid} userId={uid} sessions={list} index={i} total={sorted.length} />
      ))}
    </>
  )
}

function UserGroup({ userId, sessions, index, total }: {
  userId: string; sessions: Journey[]; index: number; total: number
}) {
  const [open, setOpen]    = useState(false)
  const hasErrors          = sessions.some(s => s.has_error)
  const hasCompleted       = sessions.some(s => s.completed_order)
  const totalEvents        = sessions.reduce((n, s) => n + s.event_count, 0)

  return (
    <div className={index < total - 1 ? 'border-b border-[var(--border)]' : ''}>
      <button
        onClick={() => setOpen(!open)}
        className="row-hover w-full bg-transparent border-none cursor-pointer px-6 py-4 grid items-center gap-4 text-left"
        style={{ gridTemplateColumns: '160px 1fr auto auto' }}
      >
        <code className="text-[11px] text-[var(--text)] font-semibold">
          {userId.slice(0, 12)}…
        </code>
        <span className="text-xs text-[var(--muted)]">
          {sessions.length} session{sessions.length > 1 ? 's' : ''} · {totalEvents} events
        </span>
        <div className="flex gap-1">
          {hasErrors    && <ErrBadge />}
          {hasCompleted && <OkBadge />}
        </div>
        <ChevronDown
          size={14} color="var(--muted)"
          style={{ transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}
        />
      </button>

      {open && (
        <div className="border-t border-[var(--border)] bg-[var(--bg3)]">
          {sessions.map((s, i) => (
            <SessionRow key={s.session_id} session={s} index={i} total={sessions.length} indent />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Session row ───────────────────────────────────────────────────────────────

function SessionRow({ session, index, total, indent = false }: {
  session: Journey; index: number; total: number; indent?: boolean
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className={index < total - 1 ? 'border-b border-[var(--border)]' : ''}>
      <button
        onClick={() => setOpen(!open)}
        className={`${indent ? 'row-hover-indent' : 'row-hover'} w-full bg-transparent border-none cursor-pointer grid items-center gap-4 text-left`}
        style={{
          padding: `0.875rem ${indent ? '2.5rem' : '1.5rem'}`,
          gridTemplateColumns: '140px 72px 1fr auto',
        }}
      >
        <code className="text-[11px] text-[var(--muted)]">
          {session.session_id.slice(0, 12)}…
        </code>
        <div className="flex gap-1">
          {session.has_error       && <ErrBadge />}
          {session.completed_order && <OkBadge />}
        </div>
        <div className="flex items-center gap-1 overflow-hidden">
          {session.pages.map((page, i) => (
            <span key={i} className="flex items-center gap-1 shrink-0">
              <span
                className="text-[10px] border rounded-[6px] px-1.5 py-px whitespace-nowrap"
                style={{
                  color:       pageLabelColor(page),
                  background:  indent ? 'var(--bg)' : 'var(--bg3)',
                  borderColor: 'var(--border)',
                }}
              >
                {page.replace('/products/', '~/')}
              </span>
              {i < session.pages.length - 1 && (
                <ChevronRight size={10} color="var(--border2)" />
              )}
            </span>
          ))}
        </div>
        <span className="text-[11px] text-[var(--muted)]">{session.event_count} events</span>
      </button>

      {open && (
        <div
          className="border-t border-[var(--border)]"
          style={{
            background:  indent ? 'var(--bg)' : 'var(--bg3)',
            padding:     '1.25rem 1.5rem',
            paddingLeft: indent ? '3rem' : '1.5rem',
          }}
        >
          <EventTimeline events={session.events} />
        </div>
      )}
    </div>
  )
}

function ErrBadge() {
  return (
    <span className="flex items-center bg-[rgba(239,68,68,0.08)] text-[var(--red)] border border-[rgba(239,68,68,0.2)] rounded-lg p-1">
      <AlertTriangle size={10} />
    </span>
  )
}

function OkBadge() {
  return (
    <span className="flex items-center bg-[rgba(0,232,122,0.08)] text-[var(--green)] border border-[rgba(0,232,122,0.25)] rounded-lg p-1">
      <Check size={10} />
    </span>
  )
}
