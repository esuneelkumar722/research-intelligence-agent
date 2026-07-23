import type { AgentState } from '../types/research'

interface Props {
  agents: AgentState[]
  query: string
}

export default function ResearchProgress({ agents, query }: Props) {
  // Hide agents that were assigned but never started once others have finished
  const anyDone = agents.some(a => a.status === 'done')
  const visibleAgents = agents.filter(a => a.status !== 'pending' || !anyDone)
  const total = visibleAgents.length
  const done = visibleAgents.filter(a => a.status === 'done').length
  const percent = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-10">
          <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase
                           tracking-widest text-emerald-400 bg-emerald-400/10
                           border border-emerald-400/20 rounded-full px-3 py-1 mb-4">
            <PulsingDot />
            Researching
          </span>
          <h2 className="text-2xl font-bold text-white mb-2">Agents Working</h2>
          <p className="text-slate-400 text-sm line-clamp-2">"{query}"</p>
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-slate-500 mb-2">
            <span>{done} of {total} agents complete</span>
            <span>{percent}%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-700"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>

        {/* Agent cards */}
        <div className="space-y-3">
          {visibleAgents.map(agent => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>

        {/* Synthesis indicator — shown when all research agents are done */}
        {done === total && total > 0 && (
          <div className="mt-6 flex items-center gap-3 bg-indigo-500/10 border border-indigo-500/30
                          rounded-xl px-5 py-4">
            <div className="flex-shrink-0">
              <Spinner />
            </div>
            <div>
              <p className="text-sm font-semibold text-indigo-300">Synthesising report…</p>
              <p className="text-xs text-slate-500 mt-0.5">
                gpt-5-mini is combining all findings into a structured report
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function AgentCard({ agent }: { agent: AgentState }) {
  const meta: Record<string, { icon: string; label: string; description: string }> = {
    web_research: {
      icon: '🌐',
      label: 'Web Research',
      description: 'Tavily search + Wikipedia',
    },
    market_data: {
      icon: '📈',
      label: 'Market Data',
      description: 'Stock prices, financials via yfinance',
    },
    news_sentiment: {
      icon: '📰',
      label: 'News Sentiment',
      description: 'Recent headlines + sentiment analysis',
    },
    synthesis: {
      icon: '📝',
      label: 'Synthesis',
      description: 'Combining all findings into report',
    },
  }

  const m = meta[agent.name] ?? { icon: '🤖', label: agent.name, description: '' }
  const durationSec = agent.durationMs ? (agent.durationMs / 1000).toFixed(1) : null

  return (
    <div className={`flex items-center gap-4 bg-slate-900 border rounded-xl px-5 py-4
                     transition-all duration-300
                     ${agent.status === 'running' ? 'border-indigo-500/50 shadow-lg shadow-indigo-500/5'
                       : agent.status === 'done' ? 'border-emerald-500/30'
                       : 'border-slate-800'}`}>
      {/* Icon */}
      <span className="text-2xl flex-shrink-0">{m.icon}</span>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-200">{m.label}</p>
        <p className="text-xs text-slate-500 truncate">{m.description}</p>
      </div>

      {/* Status */}
      <div className="flex-shrink-0 flex items-center gap-2">
        {agent.status === 'pending' && (
          <span className="text-xs text-slate-600">Waiting</span>
        )}
        {agent.status === 'running' && (
          <span className="flex items-center gap-2 text-xs text-indigo-400">
            <Spinner /> Running
          </span>
        )}
        {agent.status === 'done' && (
          <span className="flex items-center gap-2 text-xs text-emerald-400">
            <CheckIcon />
            {durationSec ? `${durationSec}s` : 'Done'}
          </span>
        )}
        {agent.status === 'error' && (
          <span className="text-xs text-red-400">Partial</span>
        )}
      </div>
    </div>
  )
}

function PulsingDot() {
  return (
    <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
    </span>
  )
}

function Spinner() {
  return (
    <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  )
}
