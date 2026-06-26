import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration constants
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
ENCRYPTION_SECRET: str = os.getenv("ENCRYPTION_SECRET", "")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-replace-in-production")
ALGORITHM: str = "HS256"

def get_fernet() -> Fernet:
    """
    Returns a Fernet instance using the ENCRYPTION_SECRET.
    Ensures that keys stored in Supabase can be encrypted and decrypted securely.
    """
    if not ENCRYPTION_SECRET:
        raise ValueError("ENCRYPTION_SECRET is not set in environment variables.")
    
    # Fernet requires a 32-byte url-safe base64-encoded key
    # If the key is not valid, we encode it or pad/adjust
    key_bytes = ENCRYPTION_SECRET.encode()
    try:
        return Fernet(key_bytes)
    except Exception as e:
        # If it fails, generate a key based on raw hash or raise error
        # For simplicity and compliance, raise error so the user configures it properly
        raise ValueError(f"Invalid Fernet key in ENCRYPTION_SECRET: {e}. It must be a 32-byte url-safe base64-encoded key.")
