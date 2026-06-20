import { Search, Code, Mail, Calendar, FileText, BarChart2, Globe } from 'lucide-react'
import { AgentStatus } from '../types'

interface AgentPanelProps {
  agentStatuses: Record<string, AgentStatus>
}

const AGENT_DEFS = {
  research: { title: 'Research Agent', icon: Search },
  code: { title: 'Code Execution', icon: Code },
  email: { title: 'Email Assistant', icon: Mail },
  calendar: { title: 'Calendar Scheduler', icon: Calendar },
  file: { title: 'File Manager', icon: FileText },
  data: { title: 'Data Analyst', icon: BarChart2 },
  scraper: { title: 'Web Scraper', icon: Globe }
}

export function AgentPanel({ agentStatuses }: AgentPanelProps) {
  return (
    <div className="w-80 h-full bg-zinc-950 flex flex-col border-l border-zinc-900 hidden lg:flex">
      {/* Title */}
      <div className="px-6 py-4 border-b border-zinc-900">
        <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Agent Swarm Activity</h2>
        <p className="text-xs text-zinc-555 font-normal">Live sub-agent execution logs</p>
      </div>

      {/* Agents cards */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {Object.entries(AGENT_DEFS).map(([key, def]) => {
          const stateObj = agentStatuses[key] || { status: 'idle' }
          const Icon = def.icon

          let badgeColor = 'bg-zinc-950 border-zinc-900/60 text-zinc-500'
          let stateLabel = 'Idle'
          let iconTheme = 'bg-zinc-950 text-zinc-600 border border-zinc-900/40'
          let dotClass = 'bg-zinc-800'

          if (stateObj.status === 'working') {
            badgeColor = 'bg-zinc-900/50 border-zinc-700/80 text-zinc-200'
            stateLabel = 'Active'
            iconTheme = 'bg-zinc-900 text-zinc-100 border border-zinc-750 shadow-md shadow-zinc-950/40'
            dotClass = 'bg-emerald-500 animate-pulse'
          } else if (stateObj.status === 'done') {
            badgeColor = 'bg-zinc-900/20 border-zinc-850 text-zinc-400'
            stateLabel = 'Done'
            iconTheme = 'bg-zinc-950 text-zinc-500 border border-zinc-900'
            dotClass = 'bg-zinc-600'
          } else if (stateObj.status === 'error') {
            badgeColor = 'bg-zinc-900/20 border-zinc-850 text-rose-500'
            stateLabel = 'Failed'
            iconTheme = 'bg-zinc-900/40 text-rose-450 border border-zinc-850'
            dotClass = 'bg-rose-500'
          }

          return (
            <div
              key={key}
              className={`p-3.5 rounded-xl border bg-zinc-900/10 transition-all duration-300 ${
                stateObj.status === 'working' 
                  ? 'border-zinc-800 bg-zinc-900/30 shadow-md scale-[1.01]' 
                  : 'border-zinc-900/60 hover:border-zinc-800/80 hover:bg-zinc-900/20'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg transition-colors ${iconTheme}`}>
                    <Icon size={16} />
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-zinc-300">{def.title}</h3>
                    <p className="text-[9px] font-mono text-zinc-500 uppercase tracking-widest">{key}</p>
                  </div>
                </div>

                <span className={`text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border flex items-center gap-1.5 transition-colors ${badgeColor}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
                  {stateLabel}
                </span>
              </div>

              {stateObj.message && stateObj.status !== 'idle' && (
                <div className="mt-3 text-[11px] text-zinc-400 bg-zinc-950 border border-zinc-900/80 rounded-lg px-2.5 py-2 leading-relaxed font-mono">
                  <span className="text-zinc-600 mr-1">&gt;</span>
                  {stateObj.message}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
