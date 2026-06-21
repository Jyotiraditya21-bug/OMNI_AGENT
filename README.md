# OmniAgent: Universal AI Assistant Platform

Live Workspace: https://omni-agent-94t.pages.dev

OmniAgent is an enterprise-grade autonomous assistant platform designed to orchestrate complex workflows through parallel agent execution. Powered by a central LangGraph state controller, OmniAgent decomposes user requests into discrete tasks, dispatches them to a network of specialized agent nodes, and streams real-time execution feedback via Server-Sent Events.

The system is designed with a premium, low-contrast matte grey workspace that offers an immersive, distraction-free environment for developer workflows.

---

## System Workflow

```text
           ┌────────────────────────────────────────┐
           │           User Task / Prompt           │
           └───────────────────┬────────────────────┘
                               │
                               ▼
           ┌────────────────────────────────────────┐
           │        LangGraph Orchestrator          │
           └──────┬──────────────────────────┬──────┘
                  │ (Concurrent Send Fanout) │
                  ▼                          ▼
       ┌──────────────────────┐   ┌──────────────────────┐
       │     Research Node    │   │  Secure Code Sandbox │
       │     (Tavily API)     │   │ (Isolated Subprocess)│
       └──────────────────────┘   └──────────────────────┘
                  │                          │
                  ▼                          ▼
       ┌──────────────────────┐   ┌──────────────────────┐
       │     Web Scraper      │   │     Data Analyst     │
       │    (BeautifulSoup)   │   │   (Pandas & Plots)   │
       └──────────────────────┘   └──────────────────────┘
                  │                          │
                  ▼                          ▼
       ┌──────────────────────┐   ┌──────────────────────┐
       │      Gmail Node      │   │    Calendar Node     │
       │  (Workspace API)     │   │   (Workspace API)    │
       └──────────────────────┘   └──────────────────────┘
                  │                          │
                  └────────────┬─────────────┘
                               ▼
                    ┌─────────────────────┐
                    │      Drive Node     │
                    │   (Workspace API)   │
                    └──────────┬──────────┘
                               ▼
           ┌────────────────────────────────────────┐
           │    Synthesis Node (Aggregated State)   │
           └───────────────────┬────────────────────┘
                               │
                               ▼
           ┌────────────────────────────────────────┐
           │   Real-Time Stream Output (SSE stream) │
           └────────────────────────────────────────┘
```

---

## What the Product Does

OmniAgent acts as a unified hub that translates natural language tasks into automated execution sequences across multiple channels (Web, Chrome Extension, CLI, and REST API). 

### Orchestrator Node
The core agent is powered by a central orchestrator utilizing LangGraph. It evaluates the user prompt, determines the execution path, and manages the state machine dynamically.

### Specialized Agent Swarm
- **Research Node**: Automates online search using Tavily's search index to pull current context.
- **Secure Code Sandbox**: Safely executes Python code blocks in an isolated subprocess environment with strict resource limits and timeouts.
- **Web Scraper**: Extracts raw content, metadata, and OpenGraph tags from custom HTTP endpoints.
- **Data Analyst**: Analyzes CSV datasets using Pandas and generates inline visualizations and charts.
- **Integration Nodes**: Fully manages Google Workspace API calls (Gmail modify, Calendar scheduling, and Google Drive creations) based on the user request.

### Memory and Key Management
- **Semantic Vector Storage**: Leverages ChromaDB locally to embed session history, enabling semantic search and context retention across interactions.
- **Symmetric Encryption Shield**: Implements a Bring Your Own Key (BYOK) paradigm. Groq and Tavily credentials are encrypted with Fernet before database writes and decrypted only in-memory during agent execution.

---

## Technical Performance Optimization Metrics

| Optimization Area | Before | After | Improvement / Outcome |
| :--- | :--- | :--- | :--- |
| **Frame Render Lag** | ~120ms delay | 0ms (Instant) | Smooth 60fps scroll matching |
| **Scrollbar Translation** | Height-based layout recalculation | Hardware-accelerated 3D transform | Real-time position tracking |
| **Swarm Execution Latency** | Sequential agent routing | LangGraph concurrent Send fanout | Up to 65% faster query execution |
| **Time to First Byte (TTFB)** | ~180ms Vercel Cold Starts | <10ms Cloudflare Edge | Direct global CDN delivery |
| **Credentials Protection** | Plaintext database records | Fernet Symmetric Encryption | Zero plaintext persistence |


---

## Visual Interface

![OmniAgent Onboarding Interface](docs/screenshots/initial_landing.png)

