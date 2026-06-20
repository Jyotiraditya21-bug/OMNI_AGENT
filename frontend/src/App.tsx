import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, LogIn } from 'lucide-react'
import { User, Session, Message } from './types'
import { getAccessToken, clearAccessToken, loginWithGoogle } from './lib/api'
import { History } from './components/History'
import { Chat } from './components/Chat'
import { AgentPanel } from './components/AgentPanel'
import { Settings } from './components/Settings'
import { useSSE } from './hooks/useSSE'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>()
  const [googleToken, setGoogleToken] = useState<string>('')
  
  const { messages, agentStatuses, isLoading, run, setMessages } = useSSE()

  const [scrollProgress, setScrollProgress] = useState(0)
  const [maxLetterSpacing, setMaxLetterSpacing] = useState(1.8)

  useEffect(() => {
    const updateSpacing = () => {
      if (window.innerWidth < 640) {
        setMaxLetterSpacing(0.6)
      } else if (window.innerWidth < 1024) {
        setMaxLetterSpacing(1.2)
      } else {
        setMaxLetterSpacing(2.0)
      }
    }
    updateSpacing()
    window.addEventListener('resize', updateSpacing)
    return () => window.removeEventListener('resize', updateSpacing)
  }, [])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const pct = el.scrollTop / (el.scrollHeight - el.clientHeight)
    setScrollProgress(pct)
  }

  // Restore session token on load
  useEffect(() => {
    const token = getAccessToken()
    if (token) {
      setUser({
        id: '11111111-1111-1111-1111-111111111111',
        email: 'developer@example.com',
        name: 'Developer Sandbox',
        avatar_url: 'https://api.dicebear.com/7.x/adventurer/svg?seed=Developer'
      })
    }
  }, [])

  // Google OAuth hash response processing
  useEffect(() => {
    const hash = window.location.hash
    if (hash) {
      const params = new URLSearchParams(hash.substring(1))
      const accessToken = params.get('access_token')
      const idToken = params.get('id_token')
      
      const targetToken = accessToken || idToken
      if (targetToken) {
        setGoogleToken(targetToken)
        loginWithGoogle(targetToken)
          .then((res) => {
            setUser(res.user)
            window.location.hash = ''
          })
          .catch((err) => {
            console.error('Google authorization synchronization failed:', err)
          })
      }
    }
  }, [])

  const handleMockLogin = async () => {
    try {
      const mockToken = 'mock_developer_' + Math.random().toString(36).substring(7)
      const data = await loginWithGoogle(mockToken)
      setUser(data.user)
      setGoogleToken(mockToken)
    } catch (err) {
      console.error('Mock authentication failed:', err)
    }
  }

  const handleRealGoogleLogin = () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'your_google_client_id'
    const redirectUri = window.location.origin
    const scope = 'openid email profile https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/drive.file'
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=token&scope=${encodeURIComponent(scope)}&include_granted_scopes=true`
    window.location.href = authUrl
  }

  const handleSignOut = () => {
    clearAccessToken()
    setUser(null)
    setMessages([])
    setCurrentSessionId(undefined)
    setScrollProgress(0)
  }

  const handleSelectSession = (session: Session) => {
    setCurrentSessionId(session.id)
    
    // Set chat history from memory
    const history: Message[] = [
      {
        id: `usr-${session.id}`,
        role: 'user',
        content: session.task,
        timestamp: new Date()
      },
      {
        id: `ast-${session.id}`,
        role: 'assistant',
        content: session.result || '',
        timestamp: new Date(),
        agentsUsed: session.agents_used
      }
    ]
    setMessages(history)
  }

  const handleTaskSubmit = (task: string) => {
    run(task, googleToken)
  }

  return (
    <div className="relative w-screen h-screen bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
      
      {/* 1. Onboarding & Boot Interface (Rendered and transitioned out when user logged in) */}
      <div className={`absolute inset-0 transition-all duration-700 ease-in-out z-20 ${
        user ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100'
      }`}>
        {/* Ambient background grid or glow */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.015)_0%,transparent_80%)] pointer-events-none" />

        {/* Center Title - Full Screen Transition */}
        <div className="fixed inset-0 flex flex-col items-center justify-center pointer-events-none z-20">
          <div 
            style={{
              opacity: Math.max(0, 1 - scrollProgress * 4.5),
              transform: `translateY(${-scrollProgress * 300}px) scale(${1 + scrollProgress * 0.05})`,
            }}
            className="text-center transition-all duration-75 flex flex-col items-center justify-center"
          >
            <span className="text-[10px] font-mono tracking-[0.3em] text-zinc-650 uppercase font-semibold block">
              // UNIVERSAL ORCHESTRATOR
            </span>
            <div className="h-6" />
            <h1 
              className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-black text-zinc-500 uppercase select-none transition-all duration-75 whitespace-nowrap"
              style={{ 
                letterSpacing: `${0.15 + Math.min(1, scrollProgress * 4.5) * maxLetterSpacing}rem`,
                marginRight: `-${0.15 + Math.min(1, scrollProgress * 4.5) * maxLetterSpacing}rem`
              }}
            >
              OMNIAGENT
            </h1>
            <div className="h-8" />
            
            {/* Scroll Assist Tag */}
            <div className="animate-pulse flex flex-col items-center gap-2">
              <span className="text-[9px] font-mono text-zinc-600 tracking-[0.2em] uppercase">// Scroll to unlock console</span>
              <div className="w-[1px] h-8 bg-gradient-to-b from-zinc-600 to-transparent" />
            </div>
          </div>
        </div>

        {/* Onboarding Scroll Container */}
        <div 
          onScroll={handleScroll}
          className="absolute inset-0 overflow-y-auto scrollbar-none z-10"
        >
          {/* Scroll Content Sections */}
          <div className="max-w-xl mx-auto px-6 py-20">
            
            {/* Spacer Section 1: Reserved for the Title */}
            <div className="h-[140vh] flex items-end justify-center pb-8">
              <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest animate-bounce">
                ↓ Scroll to initialize system nodes
              </span>
            </div>

            {/* Section 2: Intro / Entry */}
            <div className="h-[120vh] flex flex-col justify-center space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-widest text-zinc-600 uppercase font-semibold">// 01 / System Entry</span>
                <span className="h-[1px] w-12 bg-zinc-900" />
              </div>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-300 uppercase font-sans">
                Universal AI Assistant
              </h2>
              <p className="text-sm text-zinc-400 leading-relaxed font-sans max-w-md">
                A single control interface that orchestrates 7 parallel autonomous sub-agent nodes running on a LangGraph state machine. Booting environment...
              </p>
            </div>

            {/* Section 3: Agent Swarm */}
            <div className="h-[130vh] flex flex-col justify-center space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-widest text-zinc-600 uppercase font-semibold">// 02 / Autonomous Swarm</span>
                <span className="h-[1px] w-12 bg-zinc-900" />
              </div>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-300 uppercase">
                Parallel Sub-Agents
              </h2>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-md">
                Task requests are dynamically decomposed, routing commands to specialized worker nodes operating in parallel to minimize response latency.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                {[
                  { name: 'Research Node', desc: 'Tavily search' },
                  { name: 'Sandbox Code', desc: 'Secure execution' },
                  { name: 'Web Scraper', desc: 'Structure extraction' },
                  { name: 'Data Analyst', desc: 'Pandas & charts' },
                  { name: 'Gmail API', desc: 'Mail control' },
                  { name: 'Calendar API', desc: 'Scheduling' },
                  { name: 'Drive API', desc: 'Docs management' }
                ].map(agent => (
                  <div key={agent.name} className="border border-zinc-900 bg-zinc-900/30 p-2.5 rounded-lg flex flex-col gap-0.5">
                    <span className="text-xs font-mono text-zinc-300 font-semibold">■ {agent.name}</span>
                    <span className="text-[10px] font-mono text-zinc-500">{agent.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 4: Semantic Vector Memory */}
            <div className="h-[120vh] flex flex-col justify-center space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-widest text-zinc-600 uppercase font-semibold">// 03 / Memory Layer</span>
                <span className="h-[1px] w-12 bg-zinc-900" />
              </div>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-300 uppercase">
                ChromaDB Integration
              </h2>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-md">
                Maintains system context across operations by embedding execution history with sentence-transformers and searching relevant vectors.
              </p>
            </div>

            {/* Section 5: Security Shield */}
            <div className="h-[120vh] flex flex-col justify-center space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-widest text-zinc-600 uppercase font-semibold">// 04 / Security Shield</span>
                <span className="h-[1px] w-12 bg-zinc-900" />
              </div>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-300 uppercase">
                Symmetric Encryption
              </h2>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-md">
                Bring Your Own Key (BYOK) system keys are encrypted with Fernet prior to database writes. Decrypted solely during execution.
              </p>
            </div>

            {/* Section 6: End / Integrated Login Console Card */}
            <div className="h-[100vh] flex flex-col justify-center items-center">
              <div className="w-full max-w-md bg-zinc-900/40 border border-zinc-900 rounded-2xl p-8 space-y-6 text-center shadow-xl backdrop-blur-sm">
                <div className="bg-zinc-950 p-4 rounded-full w-fit mx-auto text-zinc-500 border border-zinc-900 shadow-xl">
                  <SettingsIcon size={32} className="animate-spin duration-3000" />
                </div>
                
                <div className="space-y-2">
                  <h3 className="text-xl font-bold tracking-tight text-zinc-300 uppercase">
                    Initialize Console
                  </h3>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">
                    System boot complete // auth gate
                  </p>
                </div>
                
                <div className="space-y-3 pt-2">
                  <button
                    onClick={handleMockLogin}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-zinc-950 border border-zinc-800 hover:bg-zinc-900 text-zinc-450 font-semibold rounded-xl text-sm transition"
                  >
                    <LogIn size={16} />
                    Developer Sandbox Account
                  </button>
                  <button
                    onClick={handleRealGoogleLogin}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-zinc-100 hover:bg-zinc-200 text-zinc-950 font-bold rounded-xl text-sm shadow-lg shadow-zinc-100/5 transition"
                  >
                    <LogIn size={16} />
                    Sign In with Google
                  </button>
                </div>
                
                <p className="text-[10px] text-zinc-650 leading-relaxed font-sans">
                  Google authorization enables Calendar scheduling, Drive creations, and Gmail lookups.
                </p>
              </div>
            </div>

            {/* Minimal High-Fashion Footer */}
            <div className="pt-16 pb-8 border-t border-zinc-900/60 mt-12 flex flex-col sm:flex-row items-center justify-between gap-4 text-[9px] font-mono text-zinc-600 uppercase tracking-widest">
              <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
                <span>© 2026 OMNIAGENT</span>
                <span className="text-zinc-800">|</span>
                <span>All Rights Reserved</span>
                <span className="text-zinc-800">|</span>
                <span>Distributed Swarm Console</span>
              </div>
              <div className="flex items-center gap-4">
                <span>v0.4.0-Beta</span>
                <span className="text-zinc-800">|</span>
                <span className="animate-pulse">Secure Link Active</span>
              </div>
            </div>

          </div>
        </div>

        {/* Scroll Progress Fixed Indicator */}
        <div className={`fixed right-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-4 transition-opacity duration-500 z-30 ${
          user ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}>
          <span 
            className="text-[9px] font-mono text-zinc-500 select-none uppercase tracking-widest"
            style={{ writingMode: 'vertical-lr' }}
          >
            Integrity
          </span>
          <div className="w-[1px] h-32 bg-zinc-900 relative">
            <div 
              className="w-[1px] bg-white absolute top-0 transition-all duration-150" 
              style={{ height: `${Math.min(100, scrollProgress * 100)}%` }}
            />
          </div>
          <span className="text-xs font-mono text-zinc-400">
            {Math.min(100, Math.round(scrollProgress * 100))}%
          </span>
        </div>
      </div>

      {/* 2. Main Workspace (Console Dashboard - crossfades in when user logged in) */}
      <div className={`absolute inset-0 flex transition-all duration-700 ease-in-out z-10 ${
        user ? 'opacity-100 scale-100 pointer-events-auto' : 'opacity-0 scale-105 pointer-events-none'
      }`}>
        {/* Searchable Sidebar */}
        <History onSelectSession={handleSelectSession} currentSessionId={currentSessionId} />

        {/* Main workspace */}
        <div className="flex-1 flex flex-col h-full bg-zinc-900/10">
          {/* Workspace Toolbar */}
          <div className="flex items-center justify-between px-6 py-4 bg-zinc-950 border-b border-zinc-900">
            <div className="flex items-center gap-2.5">
              <h1 className="text-sm font-bold tracking-widest text-zinc-200 uppercase font-mono">OMNIAGENT</h1>
              <span className="text-[9px] bg-zinc-900 border border-zinc-800/80 px-2 py-0.5 rounded text-zinc-500 font-semibold uppercase font-mono tracking-wider">// SWARM_CONSOLE_V0.4.0</span>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowSettings(true)}
                className="p-2 text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-850 hover:bg-zinc-800 rounded-lg transition"
              >
                <SettingsIcon size={14} />
              </button>
            </div>
          </div>

          {/* Messaging Interface */}
          <Chat messages={messages} isLoading={isLoading} onSubmit={handleTaskSubmit} />
        </div>

        {/* Activity Panels */}
        <AgentPanel agentStatuses={agentStatuses} />

        {/* Settings Overlay */}
        {showSettings && user && (
          <Settings
            user={user}
            onClose={() => setShowSettings(false)}
            onSignOut={handleSignOut}
          />
        )}
      </div>

    </div>
  )
}
