import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

# Load Google Client Configuration
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
]

TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")

def run_auth_flow():
    """
    Runs the desktop OAuth flow locally and saves the credentials to token.json.
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\n[ERROR] GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing in backend/.env")
        print("Please configure them in your .env file first.\n")
        return

    client_config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
    }

    # We use InstalledAppFlow to run a local redirect server on port 8080.
    # Note: Make sure http://localhost:8080/ is added to your Authorized Redirect URIs in Google Cloud.
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri="http://localhost:8080/"
    )

    print("\n==================================================================")
    print("           OMNI-AGENT GOOGLE OFFLINE AUTHENTICATOR")
    print("==================================================================")
    print("\nStarting local server on http://localhost:8080/ to authenticate...")
    print("Please follow the prompts in the browser window that opens.")
    print("==================================================================\n")

    try:
        creds = flow.run_local_server(port=8080, prompt='consent')
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
        print(f"\n[SUCCESS] Saved offline Google credentials to: {os.path.abspath(TOKEN_PATH)}")
        print("OmniAgent will now use this token to access Google Workspace silently!\n")
    except Exception as e:
        print(f"\n[ERROR] OAuth flow failed: {e}\n")

def get_offline_google_token() -> str:
    """
    Loads the credentials from token.json, refreshes them if expired, and returns the access token.
    """
    if not os.path.exists(TOKEN_PATH):
        return ""
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
        return creds.token if creds else ""
    except Exception as e:
        print(f"[WARNING] Error reading or refreshing Google token.json: {e}")
        return ""

if __name__ == "__main__":
    run_auth_flow()
