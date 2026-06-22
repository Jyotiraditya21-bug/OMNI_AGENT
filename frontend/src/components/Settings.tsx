import { useState, useEffect } from 'react'
import { X, Key, Eye, EyeOff, Save, LogOut, Info } from 'lucide-react'
import { User as UserType } from '../types'
import { saveKeys, getKeys } from '../lib/api'

interface SettingsProps {
  user: UserType
  onClose: () => void
  onSignOut: () => void
  googleToken: string
  onConnectGoogle: () => void
  onDisconnectGoogle: () => void
}

export function Settings({ 
  user, 
  onClose, 
  onSignOut,
  googleToken,
  onConnectGoogle,
  onDisconnectGoogle
}: SettingsProps) {
  const [groqKey, setGroqKey] = useState('')
  const [tavilyKey, setTavilyKey] = useState('')
  const [showGroq, setShowGroq] = useState(false)
  const [showTavily, setShowTavily] = useState(false)
  const [maskedGroq, setMaskedGroq] = useState('')
  const [maskedTavily, setMaskedTavily] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const loadKeys = async () => {
    try {
      const data = await getKeys()
      setMaskedGroq(data.groq_key_masked)
      setMaskedTavily(data.tavily_key_masked)
    } catch (err) {
      console.warn('Masked credentials fetch error:', err)
    }
  }

  useEffect(() => {
    loadKeys()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage(null)

    if (!groqKey.trim() && !tavilyKey.trim()) {
      setMessage({ type: 'error', text: 'Please fill in at least one API key value.' })
      return
    }

    try {
      setSaving(true)
      await saveKeys(groqKey, tavilyKey)
      setMessage({ type: 'success', text: 'API Credentials updated and securely encrypted.' })
      setGroqKey('')
      setTavilyKey('')
      loadKeys()
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Keys save error.'
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm px-4">
      <div className="w-full max-w-lg bg-zinc-950 border border-zinc-850 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-900">
          <h2 className="text-sm font-bold text-zinc-100 uppercase tracking-wider">Console Settings</h2>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-200 transition">
            <X size={18} />
          </button>
        </div>

        {/* Form Container */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[85vh]">
          {/* Profile Card */}
          <div className="bg-zinc-900/40 border border-zinc-850 p-4 rounded-xl flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <img src={user.avatar_url} alt={user.name} className="w-10 h-10 rounded-full object-cover bg-zinc-900 border border-zinc-800" />
              <div>
                <h3 className="text-xs font-bold text-zinc-200">{user.name}</h3>
                <p className="text-[11px] text-zinc-500">{user.email}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onSignOut}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 border border-zinc-800 text-zinc-200 hover:bg-zinc-850 rounded-lg text-xs font-semibold transition"
            >
              <LogOut size={13} />
              Sign Out
            </button>
          </div>

          {/* Google Integration Section */}
          <div className="border border-zinc-900 bg-zinc-900/10 p-4 rounded-xl space-y-3">
            <div className="flex items-center gap-2 text-zinc-100">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]" />
              <h3 className="text-xs font-bold uppercase tracking-wider">Google Workspace Integration</h3>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Authorize OmniAgent to run tasks involving Google Calendar, Drive, and Gmail.
            </p>
            {googleToken ? (
              <div className="flex items-center justify-between gap-3 bg-emerald-950/20 border border-emerald-900/50 p-2.5 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-semibold text-emerald-400">Connected to Google</span>
                </div>
                <button
                  type="button"
                  onClick={onDisconnectGoogle}
                  className="px-2.5 py-1.5 bg-zinc-900 border border-zinc-800 hover:bg-zinc-850 hover:text-rose-450 text-zinc-400 rounded-lg text-[10px] font-bold transition font-mono"
                >
                  DISCONNECT
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={onConnectGoogle}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-950 font-bold rounded-xl text-xs transition shadow-md"
              >
                Connect Google Account
              </button>
            )}
          </div>

          {/* BYOK Section */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-2 text-zinc-100">
              <Key size={16} />
              <h3 className="text-xs font-bold uppercase tracking-wider">Bring Your Own Key (BYOK)</h3>
            </div>
            
            <p className="text-xs text-zinc-400 leading-relaxed">
              OmniAgent processes LLM requests using your own free-tier API tokens. 
              API keys are encrypted using Fernet before database writes.
            </p>

            {/* Groq Input */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Groq API Key</label>
                <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer" className="text-[10px] text-zinc-300 hover:underline">
                  Retrieve Groq Key
                </a>
              </div>
              <div className="relative flex items-center">
                <input
                  type={showGroq ? 'text' : 'password'}
                  value={groqKey}
                  onChange={(e) => setGroqKey(e.target.value)}
                  placeholder={maskedGroq ? `${maskedGroq} (Active)` : 'Enter Groq API Key (gsk_...)'}
                  className="w-full pl-3 pr-10 py-2 bg-zinc-950 border border-zinc-900 focus:border-zinc-500 rounded-lg text-xs outline-none text-zinc-250 placeholder:text-zinc-650"
                />
                <button
                  type="button"
                  onClick={() => setShowGroq(!showGroq)}
                  className="absolute right-3 text-zinc-550 hover:text-zinc-300"
                >
                  {showGroq ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Tavily Input */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Tavily API Key</label>
                <a href="https://dashboard.tavily.com" target="_blank" rel="noreferrer" className="text-[10px] text-zinc-300 hover:underline">
                  Retrieve Tavily Key
                </a>
              </div>
              <div className="relative flex items-center">
                <input
                  type={showTavily ? 'text' : 'password'}
                  value={tavilyKey}
                  onChange={(e) => setTavilyKey(e.target.value)}
                  placeholder={maskedTavily ? `${maskedTavily} (Active)` : 'Enter Tavily API Key (tvly-...)'}
                  className="w-full pl-3 pr-10 py-2 bg-zinc-950 border border-zinc-900 focus:border-zinc-500 rounded-lg text-xs outline-none text-zinc-250 placeholder:text-zinc-650"
                />
                <button
                  type="button"
                  onClick={() => setShowTavily(!showTavily)}
                  className="absolute right-3 text-zinc-550 hover:text-zinc-300"
                >
                  {showTavily ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Feedback Message */}
            {message && (
              <div className={`p-3 rounded-lg border text-xs leading-relaxed flex items-center gap-2 ${
                message.type === 'success' ? 'bg-zinc-900 border-zinc-800 text-zinc-200' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              }`}>
                <Info size={14} />
                {message.text}
              </div>
            )}

            {/* Submit Trigger */}
            <button
              type="submit"
              disabled={saving}
              className="w-full py-2 bg-zinc-100 hover:bg-zinc-200 disabled:bg-zinc-900 disabled:text-zinc-700 text-zinc-950 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition"
            >
              <Save size={13} />
              {saving ? 'Securing Credentials...' : 'Save Credentials'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
