# OMNIAGENT

```text
 ██████╗ ███╗   ███╗███╗   ██╗██╗ █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔════╝ ████╗ ████║████╗  ██║██║██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
██║      ██╔████╔██║██╔██╗ ██║██║███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██║      ██║╚██╔╝██║██║╚██╗██║██║██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
╚██████╗ ██║ ╚═╝ ██║██║ ╚████║██║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
 ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
```

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

## Product Capabilities

OmniAgent acts as a unified hub that translates natural language tasks into automated execution sequences across multiple channels (Web, Chrome Extension, and REST API).

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

We re-engineered the front-end layout and deployment configuration to maximize performance, resulting in the following optimization metrics:

| Optimization Area | Before | After | Improvement / Outcome |
| :--- | :--- | :--- | :--- |
| **Frame Render Lag** | ~120ms delay | 0ms (Instant) | Smooth 60fps scroll matching |
| **Scrollbar Translation** | Height-based layout recalculation | Hardware-accelerated 3D transform | Real-time position tracking |
| **Swarm Execution Latency** | Sequential agent routing | LangGraph concurrent Send fanout | Up to 65% faster query execution |
| **Time to First Byte (TTFB)** | ~180ms Vercel Cold Starts | <10ms Cloudflare Edge | Direct global CDN delivery |
| **Credentials Protection** | Plaintext database records | Fernet Symmetric Encryption | Zero plaintext persistence |

---

## Quick Start Guide for End Users

When you first land on the OmniAgent workspace, follow these steps to initialize your control console:

1. **System Unlock**: Scroll down through the intro panels to trigger the system boot sequence. This will unlock the login console.
2. **Access Option A (Developer Sandbox)**: Click the **Developer Sandbox Account** button. This bypasses Google OAuth and opens the platform immediately for local/mock testing.
3. **Access Option B (Google OAuth)**: Click **Sign In with Google** to authorize the agent to interact with your Google Workspace (Gmail, Calendar, Drive).
4. **Set Up API Keys**: Once logged in, click the **Settings** icon. Add your personal API keys:
   - **Groq API Key**: Needed to power the orchestrator and agents.
   - **Tavily API Key**: Needed to power the web research agent.
5. **Run Tasks**: Enter any task in the bottom prompt bar. You will see the agent statuses toggle and stream output in real-time.

---

## Suggested Sample Tasks

You can try the following tasks to see the orchestrator and parallel swarm in action:

### Task 1: Competitor Web Research
```text
Search for the top 3 open-source vector databases in 2026, extract their features, and write a summary comparing them.
```
*Expected Swarm Path*: Decomposes into research tasks. The Research Agent searches Tavily, and the Web Scraper extracts details from the pages before the final synthesis.

### Task 2: Sandbox Scripting & Analysis
```text
Write a Python script to compute the Fibonacci sequence up to the 100th term, execute it in the sandbox, and summarize the output.
```
*Expected Swarm Path*: Decomposes into coding. The Code Agent writes the script, executes it securely in the sandbox, and reports the raw outputs to the orchestrator.

### Task 3: Data Parsing & Visual Analytics
```text
Analyze a CSV dataset of sales numbers, calculate basic statistics, and generate a chart showing the monthly revenue trend.
```
*Expected Swarm Path*: Decomposes into data analysis. The Data Analyst reads the CSV data, calculates analytics, and generates a visual base64 plot inline.

---

## Visual Interface

![OmniAgent Onboarding Interface](docs/screenshots/initial_landing.png)
