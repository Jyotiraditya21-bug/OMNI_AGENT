from datetime import datetime, timedelta
import urllib.request
import json
from fastapi import Header, HTTPException, status
from jose import jwt, JWTError
from google.oauth2 import id_token
from google.auth.transport import requests
from config import GOOGLE_CLIENT_ID, JWT_SECRET, ALGORITHM

def verify_google_token(token: str) -> dict:
    """
    Verifies a Google OAuth token (either ID token or Access token).
    If the token is valid, returns user details: google_id, email, name, avatar_url.
    If token starts with 'mock_', bypasses verification for local testing purposes.
    """
    if token.startswith("mock_"):
        parts = token.split("_")
        name_part = parts[1] if len(parts) > 1 else "user"
        email = f"{name_part}@example.com"
        name = name_part.capitalize()
        return {
            "google_id": f"google_{name_part}_id",
            "email": email,
            "name": name,
            "avatar_url": f"https://api.dicebear.com/7.x/adventurer/svg?seed={name}"
        }
        
    # Detect if it's a JWT (ID Token) or an Access Token
    # JWTs always have 3 parts separated by dots
    if len(token.split(".")) == 3:
        try:
            # Verify the ID token using Google API
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            return {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "name": idinfo.get("name", ""),
                "avatar_url": idinfo.get("picture", "")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google OAuth ID token verification failed: {e}"
            )
    else:
        # Verify as an Access Token via the Google userinfo endpoint
        try:
            url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                user_info = json.loads(response.read().decode("utf-8"))
            
            if "email" not in user_info:
                raise ValueError("Token does not have email scope or is invalid.")
                
            return {
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "avatar_url": user_info.get("picture", "")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google OAuth Access token verification failed: {e}"
            )

def get_or_create_user(user_info: dict) -> dict:
    """
    Returns user details using a local static developer ID, bypassing Supabase.
    """
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "google_id": user_info["google_id"],
        "email": user_info["email"],
        "name": user_info["name"],
        "avatar_url": user_info["avatar_url"]
    }

def create_session_token(user_id: str) -> str:
    """
    Creates a JWT session token for the user.
    """
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {
        "sub": str(user_id),
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_session_token(token: str) -> str:
    """
    Verifies JWT token and extracts user_id.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: User ID is missing."
            )
        return user_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired session: {e}"
        )

def get_current_user(authorization: str = Header(...)) -> str:
    """
    FastAPI dependency that extracts authorization token and returns user_id.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with Bearer."
        )
    token = authorization.split(" ")[1]
    return verify_session_token(token)
