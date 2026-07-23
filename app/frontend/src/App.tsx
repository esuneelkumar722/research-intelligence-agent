import { useState, useEffect, useRef, useCallback } from 'react'
import type { ResearchPlan, AgentState, AgentName, StreamEvent, ResultResponse } from './types/research'
import { startResearch, streamResearch, getResult } from './api/research'
import QueryForm from './components/QueryForm'
import PlanReview from './components/PlanReview'
import ResearchProgress from './components/ResearchProgress'
import FinalReport from './components/FinalReport'

type Phase = 'idle' | 'starting' | 'awaiting_approval' | 'streaming' | 'complete' | 'error'

const RESEARCH_AGENTS: AgentName[] = ['web_research', 'market_data', 'news_sentiment']

function makeInitialAgentStates(assignedAgents: string[]): AgentState[] {
  const seen = new Set<string>()
  const agents = assignedAgents.filter(a => {
    if (!RESEARCH_AGENTS.includes(a as AgentName) || seen.has(a)) return false
    seen.add(a)
    return true
  }) as AgentName[]
  return agents.map(name => ({ name, label: name, status: 'pending' as const }))
}

export default function App() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [query, setQuery] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [plan, setPlan] = useState<ResearchPlan | null>(null)
  const [agentStates, setAgentStates] = useState<AgentState[]>([])
  const [result, setResult] = useState<ResultResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  // Keep a ref to the SSE cleanup fn so we can abort on unmount / cancel
  const closeStreamRef = useRef<(() => void) | null>(null)

  // ── Cleanup SSE on unmount ────────────────────────────────────────────────
  useEffect(() => {
    return () => { closeStreamRef.current?.() }
  }, [])

  // ── Step 1: Submit query → POST /start ───────────────────────────────────
  const handleQuerySubmit = useCallback(async (q: string) => {
    setQuery(q)
    setPhase('starting')
    setErrorMsg('')

    try {
      const res = await startResearch(q)
      setSessionId(res.session_id)
      setPlan(res.plan)
      setPhase('awaiting_approval')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to start research')
      setPhase('error')
    }
  }, [])

  // ── Step 2a: Approve → open SSE stream ───────────────────────────────────
  const handleApprove = useCallback(() => {
    if (!sessionId || !plan) return

    const initialAgents = makeInitialAgentStates(plan.assigned_agents)
    setAgentStates(initialAgents)
    setPhase('streaming')

    const cleanup = streamResearch(
      sessionId,
      true,
      '',
      (event: StreamEvent) => handleStreamEvent(event),
      () => fetchResult(sessionId),
      (msg) => {
        setErrorMsg(msg)
        setPhase('error')
      },
    )
    closeStreamRef.current = cleanup
  }, [sessionId, plan])

  // ── Step 2b: Reject → back to idle ───────────────────────────────────────
  const handleReject = useCallback(() => {
    setPhase('idle')
    setSessionId(null)
    setPlan(null)
    setQuery('')
  }, [])

  // ── Handle each SSE event ─────────────────────────────────────────────────
  const handleStreamEvent = useCallback((event: StreamEvent) => {
    if (event.event === 'agent_start' && event.agent) {
      const startedAt = Date.now()
      setAgentStates(prev =>
        prev.map(a =>
          a.name === event.agent ? { ...a, status: 'running', startedAt } : a,
        ),
      )
    }

    if (event.event === 'agent_complete' && event.agent) {
      setAgentStates(prev =>
        prev.map(a => {
          if (a.name !== event.agent) return a
          const durationMs = a.startedAt ? Date.now() - a.startedAt : undefined
          return { ...a, status: 'done', durationMs }
        }),
      )
    }
  }, [])

  // ── Step 3: Stream closed → GET /result ──────────────────────────────────
  const fetchResult = useCallback(async (sid: string) => {
    try {
      const res = await getResult(sid)
      setResult(res)
      setPhase('complete')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to fetch report')
      setPhase('error')
    }
  }, [])

  // ── Reset to idle ─────────────────────────────────────────────────────────
  const handleNewResearch = useCallback(() => {
    closeStreamRef.current?.()
    closeStreamRef.current = null
    setPhase('idle')
    setQuery('')
    setSessionId(null)
    setPlan(null)
    setAgentStates([])
    setResult(null)
    setErrorMsg('')
  }, [])

  // ── Render ────────────────────────────────────────────────────────────────
  if (phase === 'idle') {
    return <QueryForm onSubmit={handleQuerySubmit} loading={false} />
  }

  if (phase === 'starting') {
    return <QueryForm onSubmit={handleQuerySubmit} loading={true} />
  }

  if (phase === 'awaiting_approval' && plan) {
    return (
      <PlanReview
        plan={plan}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    )
  }

  if (phase === 'streaming') {
    return <ResearchProgress agents={agentStates} query={query} />
  }

  if (phase === 'complete' && result) {
    return <FinalReport result={result} onNewResearch={handleNewResearch} />
  }

  if (phase === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20
                          flex items-center justify-center mx-auto mb-6">
            <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
          <p className="text-slate-400 text-sm mb-8">{errorMsg}</p>
          <button
            onClick={handleNewResearch}
            className="px-6 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500
                       text-white text-sm font-semibold transition-colors duration-150"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return null
}
