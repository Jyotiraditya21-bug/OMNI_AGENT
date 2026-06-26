import os
import json
import httpx
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import base64

TOKEN_PATH = "/Users/jimmycodes/OMNI_AGENT/backend/token.json"

def get_google_access_token():
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(f"Google credentials token.json not found at: {TOKEN_PATH}. Run google_auth.py first.")
    
    with open(TOKEN_PATH, "r") as f:
        creds = json.load(f)
        
    if "token" in creds:
        # Check if we need to refresh
        if "refresh_token" in creds:
            client_id = creds.get("client_id")
            client_secret = creds.get("client_secret")
            refresh_token = creds.get("refresh_token")
            
            # Send refresh request
            try:
                res = httpx.post("https://oauth2.googleapis.com/token", data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }, timeout=10)
                if res.status_code == 200:
                    new_token = res.json().get("access_token")
                    creds["token"] = new_token
                    with open(TOKEN_PATH, "w") as fw:
                        json.dump(creds, fw)
                    return new_token
            except Exception as e:
                print(f"[WARNING] Token refresh connection failed: {e}. Trying to use current token...")
        return creds["token"]
    raise ValueError("Invalid token.json format.")

def scrape_hacker_news():
    print("Scraping Hacker News headlines...")
    response = httpx.get("https://news.ycombinator.com/", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = soup.select('.titleline > a')
    top_headlines = []
    
    for i, link in enumerate(links[:5]):
        title = link.text
        url = link.get('href')
        top_headlines.append(f"{i+1}. {title} - {url}")
        
    return top_headlines

def send_gmail_api(recipient, subject, body):
    token = get_google_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    mime_msg = MIMEText(body)
    mime_msg["to"] = recipient
    mime_msg["subject"] = subject
    raw_bytes = mime_msg.as_bytes()
    encoded_msg = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
    
    print(f"Sending email to {recipient} via Gmail API...")
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    response = httpx.post(url, headers=headers, json={"raw": encoded_msg}, timeout=10)
    
    if response.status_code == 200:
        print("[SUCCESS] Email sent successfully!")
    else:
        print(f"[FAIL] Error sending email: {response.text}")

def main():
    try:
        headlines = scrape_hacker_news()
        
        email_body = "Here are the top 5 headlines from Hacker News today:\n\n"
        email_body += "\n".join(headlines)
        email_body += "\n\nSent automatically via OmniAgent Local Swarm Service."
        
        print("\n--- Scraped Content ---")
        print(email_body)
        print("-----------------------\n")
        
        send_gmail_api(
            recipient="jimmycodes2110@gmail.com",
            subject="Top Hacker News Summary",
            body=email_body
        )
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
