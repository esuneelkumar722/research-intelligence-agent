import { useState } from 'react'

interface Props {
  onSubmit: (query: string) => void
  loading: boolean
}

const EXAMPLES = [
  'Analyse Tesla\'s competitive position in the EV market in 2025',
  'What is the current state of generative AI adoption in enterprise?',
  'Compare Microsoft and Google cloud strategies and financial performance',
]

export default function QueryForm({ onSubmit, loading }: Props) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = query.trim()
    if (trimmed.length >= 10) onSubmit(trimmed)
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 py-16">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-6">
          <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>
        <h1 className="text-4xl font-bold text-white tracking-tight mb-3">
          Research Intelligence Agent
        </h1>
        <p className="text-slate-400 text-lg max-w-xl">
          Multi-agent research platform. Combines web search, financial data, and
          news sentiment — synthesised into a structured report.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl">
        <div className="relative">
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Enter your research query…"
            rows={3}
            maxLength={1000}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-5 py-4 pr-36
                       text-slate-100 placeholder-slate-500 resize-none
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       text-base leading-relaxed"
          />
          <button
            type="submit"
            disabled={loading || query.trim().length < 10}
            className="absolute bottom-4 right-4 px-5 py-2 rounded-lg
                       bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700
                       text-white text-sm font-semibold
                       transition-colors duration-150
                       disabled:cursor-not-allowed disabled:text-slate-400"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Spinner size={14} />
                Starting…
              </span>
            ) : 'Research'}
          </button>
        </div>
        <p className="text-slate-600 text-xs mt-2 text-right">
          {query.length}/1000
        </p>
      </form>

      {/* Example queries */}
      <div className="w-full max-w-2xl mt-8">
        <p className="text-slate-500 text-xs uppercase tracking-widest mb-3">Try an example</p>
        <div className="flex flex-col gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuery(ex)}
              className="text-left text-slate-400 hover:text-slate-200 text-sm
                         bg-slate-900/50 hover:bg-slate-800/60 border border-slate-800
                         rounded-lg px-4 py-3 transition-colors duration-150"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Architecture note */}
      <div className="mt-12 flex gap-6 text-slate-600 text-xs">
        {['LangGraph', 'Azure OpenAI', 'Tavily', 'yfinance'].map(tag => (
          <span key={tag} className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/60" />
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}

function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      className="animate-spin"
      style={{ width: size, height: size }}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
