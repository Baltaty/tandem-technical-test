'use client'

import { SessionEvent } from '@/lib/types'
import { AlertCircle, Check, ShoppingCart, MessageSquare, Search, ArrowRight } from 'lucide-react'

export function EventTimeline({ events }: { events: SessionEvent[] }) {
  return (
    <div className="flex flex-col">
      {events.map((evt, i) => (
        <EventRow
          key={`${evt.time ?? 'null'}-${evt.css ?? 'none'}-${i}`}
          evt={evt}
          prev={events[i - 1] ?? null}
          isLast={i === events.length - 1}
        />
      ))}
    </div>
  )
}

function EventRow({ evt, prev, isLast }: { evt: SessionEvent; prev: SessionEvent | null; isLast: boolean }) {
  const pageChanged = prev === null || prev.path !== evt.path
  const kind = eventKind(evt)

  return (
    <div className="flex gap-0">
      {/* Spine */}
      <div className="flex flex-col items-center w-6 shrink-0">
        <div
          className="w-2 h-2 rounded-full shrink-0 mt-[5px] z-10"
          style={{ background: kind.dot, boxShadow: kind.glow ? `0 0 0 3px ${kind.glow}` : 'none' }}
        />
        {!isLast && <div className="w-px flex-1 min-h-2 bg-[var(--border)] mt-0.5" />}
      </div>

      {/* Content */}
      <div
        className={`flex-1 pl-3 ${isLast ? '' : 'pb-2.5 mb-0.5'} ${kind.rowBg ? 'rounded-lg' : ''}`}
        style={{ background: kind.rowBg ?? 'transparent' }}
      >
        {pageChanged && (
          <div className="mb-0.5">
            <span
              className="text-[10px] font-bold tracking-[0.08em] rounded-[6px] px-1.5 py-px border"
              style={{
                color:       pageLabelColor(evt.path),
                background:  pageTagBg(evt.path),
                borderColor: pageTagBorder(evt.path),
              }}
            >
              {evt.path}
            </span>
          </div>
        )}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] text-[var(--muted)] tabular-nums min-w-[56px] shrink-0">
            {evt.time ? evt.time.split(' ')[1]?.slice(0, 8) : 'n/a'}
          </span>
          {kind.Icon && <kind.Icon size={11} color={kind.dot} className="shrink-0" />}
          <span className="text-[11px] font-mono" style={{ color: kind.cssColor ?? 'var(--muted)' }}>
            {evt.css ?? 'n/a'}
          </span>
          {(evt.value || evt.text) && (
            <>
              {evt.value && <ArrowRight size={10} color="var(--border2)" className="shrink-0" />}
              <span
                className="text-[11px] max-w-[300px] overflow-hidden text-ellipsis whitespace-nowrap"
                style={{
                  color:     evt.value ? (kind.valueColor ?? 'var(--text)') : 'var(--muted)',
                  fontStyle: evt.value ? 'normal' : 'italic',
                }}
              >
                {evt.value ? `"${evt.value}"` : evt.text}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

interface PageStyle { color: string; bg: string; border: string }

const PAGE_STYLES: Record<string, PageStyle> = {
  '/checkout': { color: '#d97706', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)' },
  '/cart':     { color: '#3b82f6', bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.25)' },
  '/faq':      { color: '#8b5cf6', bg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.25)' },
  '/random':   { color: '#f97316', bg: 'rgba(249,115,22,0.08)',  border: 'rgba(249,115,22,0.25)' },
}
const PRODUCTS_STYLE: PageStyle = { color: '#00a855', bg: 'rgba(0,232,122,0.08)', border: 'rgba(0,232,122,0.25)' }
const DEFAULT_STYLE:  PageStyle = { color: 'var(--muted)', bg: 'var(--bg3)', border: 'var(--border)' }

const C = {
  red:       '#ef4444',
  green:     '#00E87A',
  green2:    '#00a855',
  blue:      PAGE_STYLES['/cart'].color,     // #3b82f6
  purple:    PAGE_STYLES['/faq'].color,      // #8b5cf6
  amber:     PAGE_STYLES['/checkout'].color, // #d97706
  orange:    '#f59e0b',
  blueDot:   '#60a5fa',
  purpleDot: '#a78bfa',
} as const

function eventKind(evt: SessionEvent): {
  dot: string; glow?: string; rowBg?: string
  cssColor?: string; valueColor?: string
  Icon?: React.ElementType
} {
  const css = evt.css ?? ''
  if (css === 'div.error-message')  return { dot: C.red,       glow: 'rgba(239,68,68,0.2)',  rowBg: 'rgba(239,68,68,0.05)',  cssColor: C.red,    Icon: AlertCircle }
  if (css === 'button.place-order') return { dot: C.green,     glow: 'rgba(0,232,122,0.2)',  rowBg: 'rgba(0,232,122,0.05)',  cssColor: C.green2, valueColor: C.green2, Icon: Check }
  if (css === 'button.add-to-cart') return { dot: C.blueDot,   cssColor: C.blue,   valueColor: C.blue,   Icon: ShoppingCart }
  if (css === 'textarea.comment')   return { dot: C.purpleDot, cssColor: C.purple, valueColor: C.purple, Icon: MessageSquare }
  if (css === '#search-bar')        return { dot: C.orange,    cssColor: C.amber,  valueColor: C.amber,  Icon: Search }
  if (css === 'select.language')    return { dot: C.blueDot,   cssColor: C.blue,   valueColor: C.blue }
  return { dot: 'var(--border2)' }
}

function getPageStyle(path: string): PageStyle {
  if (path.startsWith('/products/')) return PRODUCTS_STYLE
  return PAGE_STYLES[path] ?? DEFAULT_STYLE
}

export function pageLabelColor(path: string) { return getPageStyle(path).color }
export function pageTagBg(path: string)      { return getPageStyle(path).bg }
export function pageTagBorder(path: string)  { return getPageStyle(path).border }
