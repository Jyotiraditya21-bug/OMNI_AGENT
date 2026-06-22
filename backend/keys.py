from cryptography.fernet import Fernet
from config import get_fernet, supabase
from fastapi import HTTPException, status

def encrypt_key(raw_key: str) -> str:
    """
    Encrypts a raw string using Fernet and returns a base64 string representation.
    """
    if not raw_key:
        return ""
    try:
        f = get_fernet()
        return f.encrypt(raw_key.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption error: {e}"
        )

def decrypt_key(encrypted_key: str) -> str:
    """
    Decrypts a Fernet encrypted string back to raw text.
    """
    if not encrypted_key:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decryption error: {e}"
        )

# In-memory storage for developer sandbox keys to bypass Supabase foreign key constraint issues
SANDBOX_KEYS = {}

def save_user_keys(user_id: str, groq_key: str, tavily_key: str):
    """
    Encrypts the Groq and Tavily keys and upserts them in Supabase.
    """
    if user_id == "11111111-1111-1111-1111-111111111111":
        SANDBOX_KEYS[user_id] = {
            "groq_key": groq_key,
            "tavily_key": tavily_key
        }
        return

    enc_groq = encrypt_key(groq_key)
    enc_tavily = encrypt_key(tavily_key)
    
    if not supabase:
        # Development fallback (mock behavior)
        return
        
    try:
        supabase.table("user_keys").upsert({
            "user_id": user_id,
            "groq_key_encrypted": enc_groq,
            "tavily_key_encrypted": enc_tavily
        }).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error saving user credentials: {e}"
        )

def get_user_keys(user_id: str) -> dict:
    """
    Fetches the encrypted keys for the user from Supabase and decrypts them.
    """
    if user_id == "11111111-1111-1111-1111-111111111111":
        return SANDBOX_KEYS.get(user_id, {"groq_key": "", "tavily_key": ""})

    if not supabase:
        # Development mock fallback
        return {"groq_key": "", "tavily_key": ""}
        
    try:
        res = supabase.table("user_keys").select("*").eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            groq = decrypt_key(row.get("groq_key_encrypted", ""))
            tavily = decrypt_key(row.get("tavily_key_encrypted", ""))
            return {"groq_key": groq, "tavily_key": tavily}
        return {"groq_key": "", "tavily_key": ""}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error fetching user credentials: {e}"
        )

def mask_key(key: str) -> str:
    """
    Returns the first 4 characters of a key followed by '••••••••' for secure client rendering.
    """
    if not key:
        return ""
    return key[:4] + "••••••••"
