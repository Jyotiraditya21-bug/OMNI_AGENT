# OmniAgent — Universal AI Assistant Platform

OmniAgent is a modular, zero-cost AI assistant console. Users submit complex natural language requests, and a central LangGraph state orchestrator decomposes the workflow, triggers up to seven specialized sub-agents in parallel, and streams live activity updates back via Server-Sent Events (SSE).

---

## Technical Stack

| Layer | Tool / Service |
|---|---|
| **Core Framework** | FastAPI, Uvicorn, Python 3.11 |
| **Orchestration** | LangGraph State Machine |
| **Language Model** | ChatGroq (`llama-3.3-70b-versatile`) |
| **Search Engine** | Tavily Web Search API |
| **Embeddings** | Local `sentence-transformers/all-MiniLM-L6-v2` |
| **Local Memory** | ChromaDB (Vector Store persistence inside `./chroma_db`) |
| **Cloud Storage** | Supabase (User tables, Session logs, Encrypted BYOK key management) |
| **Auth** | Google OAuth 2.0 Identity Token |
| **Frontend** | React, Vite, TailwindCSS, TypeScript |
| **Chrome Extension** | Manifest V3 side panel |
| **CLI Client** | Typer, Rich, HTTPX |
| **Package Manager** | `uv` (Fast Python dependency compiler) |

---

## System Architecture

```
                 [Access Channels]
 ┌───────────────┬───────────────────┬──────────────┐
 │               │                   │              │
 ▼               ▼                   ▼              ▼
Web App   Chrome Extension      Python CLI      REST API
 │               │                   │              │
 └───────────────┼─────────┬─────────┴──────────────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │ FastAPI Backend  │ ◄───► [Supabase DB Cloud]
                 └─────────┬────────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │    LangGraph     │ ◄───► [ChromaDB Vector Store]
                 │   Orchestrator   │
                 └─────────┬────────┘
                           │ (Send Parallel Fanout)
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Research    │    │     Code     │    │    Email     │ ... [7 Agents Total]
│  (Tavily)    │    │ (Subprocess) │    │   (Gmail)    │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Database Schema (Supabase SQL)

Run these migrations inside your Supabase project SQL Editor:

```sql
-- User account profiles synced from Google
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  google_id text unique not null,
  email text unique not null,
  name text,
  avatar_url text,
  created_at timestamptz default now()
);

-- Encrypted Groq and Tavily credentials
create table if not exists user_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  groq_key_encrypted text,
  tavily_key_encrypted text,
  updated_at timestamptz default now(),
  unique(user_id)
);

-- Sessions cache
create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  task text not null,
  result text,
  agents_used text[],
  created_at timestamptz default now()
);

create index on sessions(user_id, created_at desc);
```

---

## Setup & Running Guide

### Prerequisites
- Install [uv](https://github.com/astral-sh/uv) package manager.
- Install Node.js (v20+ recommended).

### 1. Configure backend environment
Clone this workspace, copy the template env file, and fill in credentials:
```bash
cd backend
cp .env.example .env
```
Ensure you provide a 32-byte url-safe encryption key inside `ENCRYPTION_SECRET`. You can generate one via python:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 2. Start the Backend API
Use `uv` to install dependencies and boot the ASGI server:
```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```
*(Verify api server starts on `http://localhost:8000/health`)*

### 3. Start the Frontend App
Open a separate terminal window, compile tailwind variables, and spin up the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
*(Vite app runs on `http://localhost:5173`)*

### 4. Install the Python CLI
You can install the CLI locally:
```bash
cd cli
uv pip install -e .
```
Verify CLI commands:
```bash
omniagent --help
```
Save your JWT login token and call a task:
```bash
omniagent config set-key
omniagent run "Research top AI model sizes and write them in a table"
```

### 5. Load the Chrome Extension
1. Open Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** in the top right corner.
3. Click **Load unpacked** in the top left.
4. Select the `extension/` directory.


---

## Deployment

### Backend: Hugging Face Spaces (Docker Space)

The backend is deployed to Hugging Face Spaces using the Docker SDK. The deploy workflow automatically pushes the `backend/` directory contents to Hugging Face Spaces.

To configure deployment:
1. Create a Hugging Face Space of type **Docker** (select **Blank** or **Docker** template).
2. Set the following environment variables (Secrets) in your Hugging Face Space settings:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `JWT_SECRET`
   - `ENCRYPTION_SECRET` (A 32-byte url-safe encryption key)
3. Generate a Hugging Face User Access Token with Write permissions (`HF_TOKEN`) and add it to your GitHub repository secrets as `HF_TOKEN`.

### Frontend: Vercel

The frontend is deployed to Vercel. Set up the following secrets in your GitHub Action settings to enable automated deployment:
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

---

## API Endpoints

- `POST /auth/google` - Exchanges Google tokens for local session JWT.
- `POST /keys/save` - Securely saves user's encrypted Groq & Tavily keys.
- `GET /keys/get` - Gets masked keys for display in UI settings.
- `POST /run` - Runs orchestrator and returns Server-Sent Event updates.
- `GET /history` - Fetches the past 20 sessions.
- `GET /history/search?q=` - Vector similarity query matching task memories.
- `GET /health` - Health check.
