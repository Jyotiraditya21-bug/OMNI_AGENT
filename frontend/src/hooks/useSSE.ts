import { useState } from 'react'
import { Message, AgentStatus, SSEEvent } from '../types'
import { API_BASE, getAccessToken } from '../lib/api'

export function useSSE() {
  const [messages, setMessages] = useState<Message[]>([])
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus>>({
    research: { name: 'Research', status: 'idle' },
    code: { name: 'Code', status: 'idle' },
    email: { name: 'Email', status: 'idle' },
    calendar: { name: 'Calendar', status: 'idle' },
    file: { name: 'File', status: 'idle' },
    data: { name: 'Data', status: 'idle' },
    scraper: { name: 'Scraper', status: 'idle' }
  })
  const [isLoading, setIsLoading] = useState(false)

  const run = async (task: string, googleToken?: string) => {
    setIsLoading(true)
    
    // Reset statuses before launch
    const freshStatuses: Record<string, AgentStatus> = {
      research: { name: 'Research', status: 'idle' },
      code: { name: 'Code', status: 'idle' },
      email: { name: 'Email', status: 'idle' },
      calendar: { name: 'Calendar', status: 'idle' },
      file: { name: 'File', status: 'idle' },
      data: { name: 'Data', status: 'idle' },
      scraper: { name: 'Scraper', status: 'idle' }
    }
    setAgentStatuses(freshStatuses)

    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: task,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])

    try {
      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAccessToken() || ''}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          task,
          google_token: googleToken || null
        })
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || 'Pipeline failed to initialize.')
      }

      if (!response.body) {
        throw new Error('ReadableStream is not supported by backend response.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let streamBuffer = ''
      const loggedAgents = new Set<string>()

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        streamBuffer += decoder.decode(value, { stream: true })
        const lines = streamBuffer.split('\n')
        // Retain any incomplete chunk
        streamBuffer = lines.pop() || ''

        for (const line of lines) {
          const row = line.trim()
          if (!row || !row.startsWith('data:')) continue

          const jsonStr = row.slice(5).trim()
          if (!jsonStr) continue

          try {
            const dataObj: SSEEvent = JSON.parse(jsonStr)

            if (dataObj.event === 'agent_start' && dataObj.agent) {
              loggedAgents.add(dataObj.agent)
              setAgentStatuses(prev => ({
                ...prev,
                [dataObj.agent!]: {
                  name: prev[dataObj.agent!]?.name || dataObj.agent!,
                  status: 'working',
                  message: dataObj.message || 'Processing subtask...'
                }
              }))
            } else if (dataObj.event === 'agent_done' && dataObj.agent) {
              setAgentStatuses(prev => ({
                ...prev,
                [dataObj.agent!]: {
                  name: prev[dataObj.agent!]?.name || dataObj.agent!,
                  status: 'done',
                  message: dataObj.message || 'Completed subtask.',
                  result: dataObj.result
                }
              }))
            } else if (dataObj.event === 'thinking' && dataObj.agent) {
              setAgentStatuses(prev => ({
                ...prev,
                [dataObj.agent!]: {
                  name: prev[dataObj.agent!]?.name || dataObj.agent!,
                  status: 'working',
                  message: dataObj.message || 'Thinking...'
                }
              }))
            } else if (dataObj.event === 'final') {
              const assistantMessage: Message = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: dataObj.result || '',
                timestamp: new Date(),
                agentsUsed: Array.from(loggedAgents)
              }
              setMessages(prev => [...prev, assistantMessage])
            } else if (dataObj.event === 'error') {
              if (dataObj.agent) {
                setAgentStatuses(prev => ({
                  ...prev,
                  [dataObj.agent!]: {
                    name: prev[dataObj.agent!]?.name || dataObj.agent!,
                    status: 'error',
                    message: dataObj.message || 'Subtask encountered error.'
                  }
                }))
              } else {
                const errorMsg: Message = {
                  id: crypto.randomUUID(),
                  role: 'assistant',
                  content: `### Execution Failure\n\n${dataObj.message || 'Unknown orchestrator error.'}`,
                  timestamp: new Date()
                }
                setMessages(prev => [...prev, errorMsg])
              }
            }
          } catch (jsonErr) {
            console.error('Failed to parse SSE line JSON:', jsonErr)
          }
        }
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error)
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `### Pipeline Connection Error\n\n${msg}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  return { messages, agentStatuses, isLoading, run, setMessages }
}
