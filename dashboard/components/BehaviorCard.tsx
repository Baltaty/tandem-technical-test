'use client'

import { Behavior } from '@/lib/types'
import { MessageSquare, ShoppingCart, Globe, Shuffle, BarChart2, UserX } from 'lucide-react'

interface Props { behavior: Behavior }

const ICONS: Record<string, React.ReactNode> = {
  negative_comment_then_purchase: <MessageSquare size={20} />,
  cart_then_logout:               <ShoppingCart  size={20} />,
  multilingual_user_conversion:   <Globe         size={20} />,
  random_as_search_entry:         <Shuffle       size={20} />,
  comment_without_purchase:       <UserX         size={20} />,
}

export default function BehaviorCard({ behavior }: Props) {
  return (
    <div className="border border-[var(--border)] rounded-[32px] p-7 flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <span className="text-[var(--muted)] shrink-0 mt-0.5">
          {ICONS[behavior.id] ?? <BarChart2 size={20} />}
        </span>
        <h3 className="text-sm font-bold text-[var(--text)] leading-snug">
          {behavior.title}
        </h3>
      </div>

      <p className="text-[13px] text-[var(--muted)] leading-relaxed">
        {behavior.description}
      </p>

      <div className="bg-[rgba(0,232,122,0.06)] border border-[rgba(0,232,122,0.2)] rounded-2xl px-4 py-3.5">
        <div className="text-[10px] text-[var(--green)] tracking-widest uppercase mb-1 font-bold">
          Insight
        </div>
        <p className="text-xs text-[var(--text)] leading-relaxed">
          {behavior.insight}
        </p>
      </div>
    </div>
  )
}
