import { useState, useEffect } from 'react'
import { Search, MessageSquare, Clock } from 'lucide-react'
import { Session } from '../types'
import { getHistory, searchHistory } from '../lib/api'

interface HistoryProps {
  onSelectSession: (session: Session) => void
  currentSessionId?: string
}

export function History({ onSelectSession, currentSessionId }: HistoryProps) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  const loadHistory = async () => {
    try {
      setLoading(true)
      const data = await getHistory(20)
      setSessions(data)
    } catch (err) {
      console.error('Failed to load history list:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [currentSessionId])

  const handleSearchChange = async (val: string) => {
    setSearch(val)
    if (!val.trim()) {
      loadHistory()
      return
    }
    try {
      setLoading(true)
      const results = await searchHistory(val)
      setSessions(results)
    } catch (err) {
      console.error('Failed search:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-72 h-full bg-zinc-950 flex flex-col border-r border-zinc-900 hidden md:flex">
      {/* Title */}
      <div className="px-6 py-4 border-b border-zinc-900">
        <h2 className="text-xs font-bold text-zinc-200 uppercase tracking-wider">Memory Log</h2>
        <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-wide">ChromaDB // Semantic Search</p>
      </div>

      {/* Search Input */}
      <div className="px-4 py-3 border-b border-zinc-900 bg-zinc-950/40">
        <div className="relative flex items-center">
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search past memories..."
            className="w-full pl-9 pr-3 py-1.5 bg-zinc-900 border border-zinc-900 focus:border-zinc-800 rounded-lg text-xs placeholder:text-zinc-650 text-zinc-300 outline-none transition"
          />
          <Search size={12} className="absolute left-3 text-zinc-600" />
        </div>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1.5">
        {loading && (
          <p className="text-[10px] font-mono text-zinc-600 text-center py-4 uppercase tracking-widest animate-pulse">Querying vectors...</p>
        )}
        {!loading && sessions.length === 0 ? (
          <div className="text-center py-10 px-4 space-y-3">
            <MessageSquare size={18} className="mx-auto text-zinc-800" />
            <h4 className="text-xs font-semibold text-zinc-550 uppercase tracking-wider">Memory Log Empty</h4>
            <p className="text-[10px] text-zinc-600 leading-relaxed max-w-[180px] mx-auto font-sans">
              Completed executions will register automatically here.
            </p>
          </div>
        ) : (
          sessions.map((item) => {
            const active = item.id === currentSessionId
            const dateStr = item.created_at
              ? new Date(item.created_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })
              : ''

            return (
              <button
                key={item.id}
                onClick={() => onSelectSession(item)}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 flex flex-col gap-2 ${
                  active
                    ? 'bg-zinc-900/40 border-zinc-900 border-l-zinc-500 border-l-2 text-zinc-100 shadow-sm'
                    : 'bg-transparent border-transparent text-zinc-500 hover:bg-zinc-900/20 hover:text-zinc-300'
                }`}
              >
                <h4 className="text-xs font-semibold line-clamp-2 leading-relaxed text-zinc-300">
                  {item.task}
                </h4>
                
                <div className="flex items-center justify-between gap-2 w-full">
                  <span className="text-[9px] text-zinc-600 flex items-center gap-1 font-mono uppercase">
                    <Clock size={9} />
                    {dateStr}
                  </span>

                  <div className="flex gap-1 flex-wrap justify-end">
                    {item.agents_used.slice(0, 2).map((agent) => (
                      <span
                        key={agent}
                        className="px-1.5 py-0.5 bg-zinc-950 text-zinc-550 rounded text-[8px] uppercase border border-zinc-900/60 font-mono tracking-wide"
                      >
                        {agent}
                      </span>
                    ))}
                    {item.agents_used.length > 2 && (
                      <span className="text-[8px] font-mono text-zinc-600 font-semibold">+{item.agents_used.length - 2}</span>
                    )}
                  </div>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
