export interface ResearchPlan {
  original_query: string
  sub_queries: string[]
  assigned_agents: string[]
  estimated_duration_seconds: number
  estimated_tokens: number
}

export interface Source {
  title: string
  url: string
  snippet: string
  source_type: 'web' | 'news' | 'financial' | 'wikipedia'
}

export interface StartResponse {
  session_id: string
  status: string
  plan: ResearchPlan
  message: string
}

export interface ResultResponse {
  session_id: string
  query: string
  final_report: string
  citations: Source[]
  total_tokens_used: number
  total_cost_usd: number
  agents_used: string[]
  status: string
}

export type AgentName = 'web_research' | 'market_data' | 'news_sentiment' | 'synthesis'

export interface StreamEvent {
  event: 'agent_start' | 'agent_complete' | 'complete' | 'error'
  agent?: AgentName
  session_id?: string
  status?: string
  message?: string
}

export type AgentStatus = 'pending' | 'running' | 'done' | 'error'

export interface AgentState {
  name: AgentName
  label: string
  status: AgentStatus
  startedAt?: number
  durationMs?: number
}
