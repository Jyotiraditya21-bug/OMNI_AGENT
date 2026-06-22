import time
import chromadb
from chromadb.utils import embedding_functions

# Initialize persistent ChromaDB client inside backend/chroma_db
client = chromadb.PersistentClient(path="./chroma_db")

# Initialize Local Embeddings using sentence-transformers/all-MiniLM-L6-v2
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Initialize/Get collection
collection = client.get_or_create_collection(
    name="sessions",
    embedding_function=embedding_fn
)

def save_session(session_id: str, user_id: str, task: str, result: str, agents_used: list[str]):
    """
    Saves session details to ChromaDB vector store and attempts database sync.
    """
    timestamp = time.time()
    
    # Save to Supabase DB if available
    from config import supabase
    is_mock = user_id == "11111111-1111-1111-1111-111111111111"
    if supabase and not is_mock:
        try:
            supabase.table("sessions").upsert({
                "id": session_id,
                "user_id": user_id,
                "task": task,
                "result": result,
                "agents_used": agents_used
            }).execute()
        except Exception as e:
            print(f"[WARNING] Database sync failed: {e}")
            
    # Add to ChromaDB
    collection.add(
        documents=[task],
        metadatas=[{
            "session_id": session_id,
            "user_id": user_id,
            "result": result,
            "agents_used": ",".join(agents_used),
            "timestamp": timestamp,
            "task": task
        }],
        ids=[session_id]
    )

def get_history(user_id: str, limit: int = 20) -> list[dict]:
    """
    Retrieves all past sessions for a user, sorted by timestamp descending.
    """
    try:
        results = collection.get(
            where={"user_id": user_id},
            limit=limit
        )
    except Exception as e:
        print(f"[WARNING] Chroma get error: {e}")
        return []
        
    sessions = []
    if results and "metadatas" in results and results["metadatas"]:
        for meta in results["metadatas"]:
            if meta:
                sessions.append({
                    "id": meta.get("session_id"),
                    "task": meta.get("task", ""),
                    "result": meta.get("result", ""),
                    "agents_used": meta.get("agents_used", "").split(",") if meta.get("agents_used") else [],
                    "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(meta.get("timestamp", 0)))
                })
        # Sort in reverse chronological order
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return sessions

def search_similar(user_id: str, query: str, limit: int = 5) -> list[dict]:
    """
    Performs semantic search over the user's sessions based on vector similarity.
    """
    try:
        res = collection.query(
            query_texts=[query],
            where={"user_id": user_id},
            n_results=limit
        )
    except Exception as e:
        print(f"[WARNING] Chroma query error: {e}")
        return []
        
    sessions = []
    if res and "metadatas" in res and res["metadatas"] and len(res["metadatas"]) > 0:
        for meta in res["metadatas"][0]:
            if meta:
                sessions.append({
                    "id": meta.get("session_id"),
                    "task": meta.get("task", ""),
                    "result": meta.get("result", ""),
                    "agents_used": meta.get("agents_used", "").split(",") if meta.get("agents_used") else [],
                    "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(meta.get("timestamp", 0)))
                })
    return sessions
