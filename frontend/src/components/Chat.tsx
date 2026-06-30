import { useRef, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Cpu } from 'lucide-react'
import { Message } from '../types'

interface ChatProps {
  messages: Message[]
  isLoading: boolean
  onSubmit: (task: string) => void
}

export function Chat({ messages, isLoading, onSubmit }: ChatProps) {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    onSubmit(input)
    setInput('')
  }

  return (
    <div className="flex flex-col min-h-0 bg-zinc-900/40 border-x border-zinc-900 flex-1">
      {/* Chat Title Panel */}
      <div className="flex items-center justify-between px-6 py-4 bg-zinc-950 border-b border-zinc-900">
        <div className="flex items-center gap-2">
          <div className="bg-zinc-900 p-2 rounded-lg text-zinc-400 border border-zinc-850">
            <Cpu size={16} />
          </div>
          <div>
            <h2 className="text-xs font-bold text-zinc-200 uppercase tracking-wider">Task Workspace</h2>
            <p className="text-[10px] text-zinc-500 font-mono">LANGGRAPH // LIVE_STREAM_SESSION</p>
          </div>
        </div>
        {isLoading && (
          <div className="flex items-center gap-2 px-3 py-1 bg-zinc-900/60 text-zinc-300 text-[11px] font-mono rounded-lg border border-zinc-800 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            SWARM RUNNING...
          </div>
        )}
      </div>

      {/* Messages viewport */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto space-y-5">
            <div className="bg-zinc-900 p-4 rounded-full text-zinc-400 border border-zinc-800 shadow-xl animate-pulse">
              <Cpu size={32} />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider">Universal Orchestrator</h3>
              <p className="text-xs text-zinc-500 uppercase tracking-widest font-mono">// Parallel LangGraph State Swarm</p>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Submit a multi-step instruction. The agent cluster will automatically partition tasks, delegate to research, code, scrape, and data analysts, and synthesize a solution.
            </p>
            <div className="text-[11px] font-mono bg-zinc-950 text-zinc-500 border border-zinc-900 p-3.5 rounded-lg leading-relaxed text-left">
              <span className="text-zinc-700 block mb-1.5"># EXAMPLE INSTANCE</span>
              "Scrape content from https://news.ycombinator.com, extract top headlines, compile a brief summary and draft it in an email to manager@company.com"
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} message-appear`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-5 py-3.5 shadow-md border ${
                  msg.role === 'user'
                    ? 'bg-zinc-900 text-zinc-150 border-zinc-800 rounded-tr-none'
                    : 'bg-zinc-900/30 text-zinc-300 border-zinc-900 rounded-tl-none'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="text-xs whitespace-pre-wrap leading-relaxed font-sans">{msg.content}</p>
                ) : (
                  <div className="prose prose-invert max-w-none text-xs leading-relaxed prose-pre:bg-zinc-950 prose-pre:border prose-pre:border-zinc-900 prose-code:text-zinc-150 font-sans">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                    {msg.agentsUsed && msg.agentsUsed.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-zinc-900/80 flex flex-wrap gap-2 items-center">
                        <span className="text-[9px] font-mono text-zinc-650 uppercase tracking-wider">Agents Utilized:</span>
                        {msg.agentsUsed.map((agent) => (
                          <span
                            key={agent}
                            className="px-1.5 py-0.5 bg-zinc-950 border border-zinc-900 text-zinc-500 rounded text-[9px] font-mono uppercase tracking-wider"
                          >
                            {agent}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-zinc-900 bg-zinc-950/40 backdrop-blur-md">
        <div className="relative flex items-center">
          <span className="absolute left-4 font-mono text-zinc-600 text-xs">$</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder={isLoading ? 'Collaborating sub-agents, please wait...' : 'Type a task for the agent swarm...'}
            className="w-full pl-8 pr-12 py-3 bg-zinc-950 border border-zinc-900 focus:border-zinc-800 rounded-xl text-xs placeholder:text-zinc-650 text-zinc-200 outline-none transition disabled:opacity-50 disabled:cursor-not-allowed font-sans"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-2 p-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 disabled:border-zinc-900 disabled:bg-transparent text-zinc-400 disabled:text-zinc-700 hover:text-zinc-200 rounded-lg transition"
          >
            <Send size={14} />
          </button>
        </div>
      </form>
    </div>
  )
}
