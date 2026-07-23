import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ResultResponse, Source } from '../types/research'

interface Props {
  result: ResultResponse
  onNewResearch: () => void
}

const SOURCE_ICON: Record<string, string> = {
  web: '🌐',
  news: '📰',
  financial: '📈',
  wikipedia: '📚',
}

export default function FinalReport({ result, onNewResearch }: Props) {
  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-4xl mx-auto">
        {/* Header bar */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase
                             tracking-widest text-emerald-400 bg-emerald-400/10
                             border border-emerald-400/20 rounded-full px-3 py-1 mb-3">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Research complete
            </span>
            <h1 className="text-2xl font-bold text-white">Research Report</h1>
            <p className="text-slate-400 text-sm mt-1 line-clamp-2">"{result.query}"</p>
          </div>
          <button
            onClick={onNewResearch}
            className="flex-shrink-0 px-4 py-2 rounded-lg border border-slate-700
                       text-slate-400 hover:text-slate-200 hover:border-slate-500
                       text-sm font-medium transition-colors duration-150"
          >
            New research
          </button>
        </div>

        {/* Metadata pills */}
        <div className="flex flex-wrap gap-3 mb-8">
          <MetaPill icon="🤖" label={`${result.agents_used.length} agents`} />
          <MetaPill icon="🪙" label={`${result.total_tokens_used.toLocaleString()} tokens`} />
          <MetaPill icon="💵" label={`$${result.total_cost_usd.toFixed(4)} est. cost`} />
          <MetaPill icon="📎" label={`${result.citations.length} sources`} />
        </div>

        {/* Report body */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 mb-8">
          <div className="prose prose-invert max-w-none
                          prose-headings:font-bold prose-headings:tracking-tight
                          prose-h2:text-xl prose-h3:text-lg
                          prose-li:marker:text-slate-500
                          prose-code:bg-slate-800 prose-code:rounded prose-code:px-1 prose-code:py-0.5
                          prose-blockquote:border-l-indigo-500">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {result.final_report}
            </ReactMarkdown>
          </div>
        </div>

        {/* Citations */}
        {result.citations.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-500 mb-4">
              Sources
            </h2>
            <div className="space-y-3">
              {result.citations.map((src, i) => (
                <CitationRow key={src.url || i} index={i + 1} source={src} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function CitationRow({ index, source }: { index: number; source: Source }) {
  const icon = SOURCE_ICON[source.source_type] ?? '🔗'
  return (
    <div className="flex gap-3 text-sm">
      <span className="flex-shrink-0 w-6 h-6 rounded bg-slate-800 text-slate-500
                       text-xs font-mono flex items-center justify-center">
        {index}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span>{icon}</span>
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-300 hover:text-indigo-400 font-medium truncate
                         transition-colors duration-150"
            >
              {source.title || source.url}
            </a>
          ) : (
            <span className="text-slate-300 font-medium">{source.title}</span>
          )}
        </div>
        {source.snippet && (
          <p className="text-slate-600 text-xs mt-0.5 line-clamp-2">{source.snippet}</p>
        )}
      </div>
    </div>
  )
}

function MetaPill({ icon, label }: { icon: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-400
                     bg-slate-900 border border-slate-800 rounded-full px-3 py-1.5">
      <span>{icon}</span>
      {label}
    </span>
  )
}
