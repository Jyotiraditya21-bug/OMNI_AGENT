# Trigger rebuild to clear stuck Hugging Face build queue
import asyncio
import json
import uuid
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from auth import get_current_user, verify_google_token, get_or_create_user, create_session_token
from keys import save_user_keys, get_user_keys, mask_key
from memory.chroma import save_session, get_history, search_similar
from graph import run_graph
from config import FRONTEND_URL

app = FastAPI(title="OmniAgent API Server")

# Add CORS configuration
cors_origins = ["http://localhost:5173"]
if FRONTEND_URL:
    for origin in FRONTEND_URL.split(","):
        trimmed = origin.strip()
        if trimmed and trimmed not in cors_origins:
            cors_origins.append(trimmed)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class GoogleAuthRequest(BaseModel):
    token: str

class SaveKeysRequest(BaseModel):
    groq_key: str
    tavily_key: str

class RunRequest(BaseModel):
    task: str
    google_token: Optional[str] = None

# Routes
@app.post("/auth/google")
async def auth_google(req: GoogleAuthRequest):
    """
    Authenticates a user via Google OAuth token, creates user row in Supabase, and returns a session JWT.
    """
    user_info = verify_google_token(req.token)
    user_row = get_or_create_user(user_info)
    access_token = create_session_token(user_row["id"])
    return {
        "access_token": access_token,
        "user": {
            "id": user_row["id"],
            "email": user_row["email"],
            "name": user_row["name"],
            "avatar_url": user_row["avatar_url"]
        }
    }

@app.post("/keys/save")
async def save_keys(req: SaveKeysRequest, user_id: str = Depends(get_current_user)):
    """
    Saves encrypted Groq and Tavily API keys for the current authenticated user.
    """
    save_user_keys(user_id, req.groq_key, req.tavily_key)
    return {"success": True}

@app.get("/keys/get")
async def get_keys(user_id: str = Depends(get_current_user)):
    """
    Retrieves the masked API credentials for display in frontend settings.
    """
    keys = get_user_keys(user_id)
    return {
        "groq_key_masked": mask_key(keys.get("groq_key", "")),
        "tavily_key_masked": mask_key(keys.get("tavily_key", ""))
    }

@app.post("/run")
async def run(req: RunRequest, user_id: str = Depends(get_current_user)):
    """
    Trigger orchestrator task. Streams live activity updates as SSE.
    """
    # Fetch decrypted keys
    user_credentials = get_user_keys(user_id)
    groq_key = user_credentials.get("groq_key", "")
    tavily_key = user_credentials.get("tavily_key", "")
    
    if not groq_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Groq API key is missing. Add it to your Settings first."
        )

    google_token = req.google_token
    if not google_token or (isinstance(google_token, str) and google_token.startswith("mock_developer_")):
        try:
            from google_auth import get_offline_google_token
            offline_token = get_offline_google_token()
            if offline_token:
                google_token = offline_token
        except Exception as e:
            print(f"[WARNING] Failed to load offline google token: {e}")

    session_id = str(uuid.uuid4())
    queue = asyncio.Queue()

    async def sse_event_generator():
        # Start graph execution in the background
        graph_task = asyncio.create_task(
            run_graph(
                task=req.task,
                user_id=user_id,
                session_id=session_id,
                groq_key=groq_key,
                tavily_key=tavily_key,
                google_token=google_token or "",
                queue=queue
            )
        )
        
        agents_used = set()
        
        try:
            # Poll status queue and yield events
            while True:
                # Flush all current queue elements
                while not queue.empty():
                    item = queue.get_nowait()
                    agent_name = item.get("agent")
                    status_val = item.get("status")
                    message = item.get("message")
                    result = item.get("result")
                    
                    if agent_name:
                        agents_used.add(agent_name)
                    
                    # Map queue statuses to appropriate SSE event names
                    event_type = "thinking"
                    if agent_name and agent_name != "orchestrator":
                        if status_val == "working":
                            event_type = "agent_start"
                        elif status_val == "done":
                            event_type = "agent_done"
                        elif status_val == "error":
                            event_type = "error"
                    
                    yield {
                        "event": event_type,
                        "data": json.dumps({
                            "event": event_type,
                            "agent": agent_name,
                            "message": message,
                            "result": result
                        })
                    }
                    queue.task_done()
                    
                if graph_task.done():
                    break
                    
                await asyncio.sleep(0.1)
                
            # Final output compilation
            final_text = await graph_task
            
            yield {
                "event": "final",
                "data": json.dumps({
                    "event": "final",
                    "result": final_text,
                    "session_id": session_id
                })
            }
            
            # Save session to persistent local and cloud memory
            save_session(
                session_id=session_id,
                user_id=user_id,
                task=req.task,
                result=final_text,
                agents_used=list(agents_used)
            )
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({
                    "event": "error",
                    "message": f"Execution error: {str(e)}"
                })
            }
        finally:
            yield {
                "event": "done",
                "data": json.dumps({"event": "done"})
            }
            
    return EventSourceResponse(sse_event_generator())

@app.get("/history")
async def history(limit: int = Query(20), user_id: str = Depends(get_current_user)):
    """
    Fetches the authenticated user's session history.
    """
    return get_history(user_id, limit=limit)

@app.get("/history/search")
async def history_search(q: str = Query(...), user_id: str = Depends(get_current_user)):
    """
    Retrieves semantically similar session histories.
    """
    return search_similar(user_id, query=q)

@app.get("/health")
async def health():
    """
    API Server health check.
    """
    return {"status": "ok", "version": "1.0.0"}
