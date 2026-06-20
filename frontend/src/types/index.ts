export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  agentsUsed?: string[]
}

export interface AgentStatus {
  name: string
  status: 'idle' | 'working' | 'done' | 'error'
  message?: string
  result?: string
}

export interface Session {
  id: string
  task: string
  result: string
  agents_used: string[]
  created_at: string
}

export interface User {
  id: string
  email: string
  name: string
  avatar_url: string
}

export interface SSEEvent {
  event: 'agent_start' | 'agent_done' | 'thinking' | 'final' | 'done' | 'error'
  agent?: string
  message?: string
  result?: string
  session_id?: string
}
