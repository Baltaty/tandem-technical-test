'use client'

import { ChevronRight } from 'lucide-react'
import { pageLabelColor } from './EventTimeline'

interface Journey { path: string[]; count: number; pct: number }
interface Props    { journeys: Journey[] }

export default function JourneyList({ journeys }: Props) {
  const max = journeys[0]?.count ?? 1

  return (
    <div className="border border-[var(--border)] rounded-[32px] overflow-hidden">
      {journeys.map((j, i) => (
        <div
          key={i}
          className={`px-7 py-5 ${i < journeys.length - 1 ? 'border-b border-[var(--border)]' : ''}`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              {j.path.map((page, pi) => (
                <span key={pi} className="flex items-center gap-1.5">
                  <span
                    className="text-[11px] font-semibold px-2 py-0.5 rounded-lg border"
                    style={{
                      color:       pageLabelColor(page),
                      background:  'var(--bg3)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    {page}
                  </span>
                  {pi < j.path.length - 1 && <ChevronRight size={11} color="var(--border2)" className="shrink-0" />}
                </span>
              ))}
            </div>
            <span className="text-[13px] font-semibold text-[var(--text)] ml-4 shrink-0">
              {j.count}×
              <span className="text-[11px] text-[var(--muted)] font-normal ml-1">{j.pct}%</span>
            </span>
          </div>
          <div className="h-1 bg-[var(--border)] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--green)] transition-[width] duration-[600ms] ease-in-out"
              style={{ width: `${(j.count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
