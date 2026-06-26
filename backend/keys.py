from cryptography.fernet import Fernet
from config import get_fernet
from fastapi import HTTPException, status
import os
import json

KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys.json")

def load_keys_file() -> dict:
    if not os.path.exists(KEYS_FILE):
        return {}
    try:
        with open(KEYS_FILE, "r") as f:
            encrypted_data = f.read()
        if not encrypted_data:
            return {}
        # Decrypt using Fernet
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted_data.encode()).decode()
        return json.loads(decrypted)
    except Exception as e:
        print(f"[WARNING] Failed to load keys.json: {e}")
        return {}

def save_keys_file(data: dict):
    try:
        fernet = get_fernet()
        encrypted = fernet.encrypt(json.dumps(data).encode()).decode()
        with open(KEYS_FILE, "w") as f:
            f.write(encrypted)
    except Exception as e:
        print(f"[ERROR] Failed to save keys.json: {e}")

# Pre-populated developer sandbox keys from environment variables
SANDBOX_KEYS_PRESET = {
    "groq_key": os.getenv("GROQ_API_KEY", ""),
    "tavily_key": os.getenv("TAVILY_API_KEY", "")
}

def save_user_keys(user_id: str, groq_key: str, tavily_key: str):
    """
    Encrypts the Groq and Tavily keys and stores them locally in keys.json.
    """
    try:
        data = load_keys_file()
        data[user_id] = {
            "groq_key": groq_key,
            "tavily_key": tavily_key
        }
        save_keys_file(data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving keys locally: {e}"
        )

def get_user_keys(user_id: str) -> dict:
    """
    Fetches the keys for the user from local keys.json file.
    """
    try:
        data = load_keys_file()
        user_keys = data.get(user_id)
        if user_keys:
            return user_keys
        # Fallback to pre-populated sandbox keys
        if user_id == "11111111-1111-1111-1111-111111111111":
            return SANDBOX_KEYS_PRESET
        return {"groq_key": "", "tavily_key": ""}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving keys locally: {e}"
        )

def mask_key(key: str) -> str:
    """
    Returns the first 4 characters of a key followed by '••••••••' for secure client rendering.
    """
    if not key:
        return ""
    return key[:4] + "••••••••"
