import type { ResearchPlan } from '../types/research'

interface Props {
  plan: ResearchPlan
  onApprove: () => void
  onReject: () => void
}

const AGENT_META: Record<string, { label: string; icon: string; color: string }> = {
  web_research:   { label: 'Web Research',    icon: '🌐', color: 'indigo' },
  market_data:    { label: 'Market Data',     icon: '📈', color: 'emerald' },
  news_sentiment: { label: 'News Sentiment',  icon: '📰', color: 'amber' },
}

export default function PlanReview({ plan, onApprove, onReject }: Props) {
  const estMin = Math.ceil(plan.estimated_duration_seconds / 60)

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-8">
          <span className="inline-block text-xs font-semibold uppercase tracking-widest
                           text-indigo-400 bg-indigo-400/10 border border-indigo-400/20
                           rounded-full px-3 py-1 mb-4">
            Plan ready — review before starting
          </span>
          <h2 className="text-2xl font-bold text-white mb-2">Research Plan</h2>
          <p className="text-slate-400 text-sm leading-relaxed line-clamp-3">
            "{plan.original_query}"
          </p>
        </div>

        {/* Sub-questions */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Sub-questions
          </h3>
          <ol className="space-y-2">
            {plan.sub_queries.map((q, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-800
                                 text-slate-500 text-xs flex items-center justify-center font-mono">
                  {i + 1}
                </span>
                {q}
              </li>
            ))}
          </ol>
        </div>

        {/* Agents */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Agents assigned
          </h3>
          <div className="flex flex-wrap gap-2">
            {plan.assigned_agents.map((agent, i) => {
              const meta = AGENT_META[agent] ?? { label: agent, icon: '🤖', color: 'slate' }
              return (
                <span key={`${agent}-${i}`}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg
                             bg-slate-800 border border-slate-700 text-sm text-slate-200">
                  <span>{meta.icon}</span>
                  {meta.label}
                </span>
              )
            })}
          </div>
        </div>

        {/* Estimates */}
        <div className="grid grid-cols-2 gap-3 mb-8">
          <Stat label="Estimated time" value={`~${estMin} min`} />
          <Stat label="Estimated tokens" value={plan.estimated_tokens.toLocaleString()} />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onApprove}
            className="flex-1 py-3 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500
                       text-white font-semibold text-sm transition-colors duration-150"
          >
            Approve &amp; Start Research
          </button>
          <button
            onClick={onReject}
            className="px-6 py-3 rounded-xl border border-slate-700 text-slate-400
                       hover:border-slate-500 hover:text-slate-200 text-sm font-semibold
                       transition-colors duration-150"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-5 py-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-slate-100">{value}</p>
    </div>
  )
}
