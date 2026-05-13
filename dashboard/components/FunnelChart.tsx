'use client'

import { FunnelStep } from '@/lib/types'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { TrendingDown } from 'lucide-react'

interface Props { steps: FunnelStep[] }

const STEP_COLORS = ['#94a3b8', '#60a5fa', '#a78bfa', '#f59e0b', '#00E87A']

const STEP_LABELS: Record<string, string> = {
  homepage:     'Homepage',
  products:     'Products',
  cart:         'Cart',
  checkout:     'Checkout',
  order_placed: 'Order placed',
}

export default function FunnelChart({ steps }: Props) {
  const data = steps.map(s => ({ ...s, name: STEP_LABELS[s.step] || s.step }))

  interface TooltipEntry { payload: FunnelStep & { name: string } }
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: TooltipEntry[] }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-3.5 text-xs shadow-[0_4px_16px_rgba(0,0,0,0.08)]">
        <div className="text-[var(--text)] font-bold mb-1">{d.name}</div>
        <div className="text-[var(--muted)]">{d.sessions} sessions</div>
        <div className="text-[var(--muted)]">{d.pct_of_total}% of total</div>
        {d.dropoff_from_prev > 0 && (
          <div className="text-[var(--red)] mt-1 flex items-center gap-1">
            <TrendingDown size={11} /> {d.dropoff_from_prev}% drop from previous
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="border border-[var(--border)] rounded-[32px] p-8">
      <div className="text-[11px] text-[var(--muted)] uppercase tracking-[0.12em] mb-6 font-semibold">
        Conversion Funnel
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barCategoryGap="30%">
          <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis hide />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,232,122,0.06)' }} />
          <Bar dataKey="sessions" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={STEP_COLORS[i] ?? '#94a3b8'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-2 flex-wrap mt-3">
        {steps.filter(s => s.dropoff_from_prev > 15).map(s => (
          <span
            key={s.step}
            className="flex items-center gap-1 text-[11px] font-medium bg-[rgba(239,68,68,0.08)] text-[var(--red)] border border-[rgba(239,68,68,0.2)] rounded-full px-2.5 py-0.5"
          >
            <TrendingDown size={11} />
            {s.dropoff_from_prev}% at {STEP_LABELS[s.step]}
          </span>
        ))}
      </div>
    </div>
  )
}
