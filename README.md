# OMNI-AGENT

```text
  ██████╗ ███╗   ███╗███╗   ██╗██╗                █████╗  ██████╗ ███████╗███╗   ██╗████████╗
 ██╔═══██╗████╗ ████║████╗  ██║██║               ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
 ██║   ██║██╔████╔██║██╔██╗ ██║██║    ┌═════┐    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
 ██║   ██║██║╚██╔╝██║██║╚██╗██║██║    ╚═════╝    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
 ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║               ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝               ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
```


Live Workspace: https://jyotiraditya21-bug.github.io/OMNI_AGENT/

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

## Developer Quick Start (Local Setup)

OmniAgent is now configured as a fully self-contained, offline-first developer project. All external database (Supabase) requirements have been decoupled in favor of secure local file-based storage.

### 1. Configure Environment Variables

**Backend:**
Create a `.env` file in the `backend/` folder (or copy `backend/.env.example` to `backend/.env`) and configure the following credentials:
```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
ENCRYPTION_SECRET=your_32_byte_base64_fernet_key
JWT_SECRET=any_random_secure_jwt_secret_string

# Optional presets for developer sandbox:
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

**Frontend:**
Create a `.env` file in the `frontend/` folder (or copy `frontend/.env.example` to `frontend/.env`):
```env
VITE_GOOGLE_CLIENT_ID=your_google_client_id
VITE_BACKEND_URL=http://localhost:8000
```


### 2. Boot the Entire Workspace in 1 Command
Simply run the bootstrapper script from the project root. This will verify/create the Python virtual environment, install npm dependencies, sync python packages, and run both dev servers:
```bash
./start.sh
```
- **Vite React Frontend:** [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend Server:** [http://localhost:8000](http://localhost:8000) (Logs piped to `backend/uvicorn.log`)

---

## Google Workspace Offline Authorization (One-time Setup)

To allow the Calendar, Gmail, and Google Drive agents to run locally without browser redirect URI limits, complete this one-time offline credentials setup:

1. **Add Redirect URI:** In your Google Cloud Console Client ID settings, add `http://localhost:8080/` to your **Authorized redirect URIs**.
2. **Enable APIs:** Enable these APIs in your Google Cloud Project:
   - [Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
   - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
   - [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
3. **Run CLI Auth:** Execute the CLI authentication script locally:
   ```bash
   cd backend
   .venv/bin/python google_auth.py
   ```
4. Complete the authorization prompts in the browser window that opens. This saves your credentials to `backend/token.json`.
5. Launch the **Sandbox Console** on your site. The backend will silently load and refresh your credentials from the token file during execution!

---

## Local Storage Details

- **Symmetric Encryption Shield:** Groove/Tavily keys entered in Settings are encrypted locally via Fernet and saved securely to `backend/keys.json`. No external database is ever used.
- **Persistent Vector Memory:** Session history is embedded with SentenceTransformers and saved locally to `backend/chroma_db/`.

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
