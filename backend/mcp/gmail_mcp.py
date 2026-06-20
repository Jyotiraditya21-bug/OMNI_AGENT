import base64
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from email.mime.text import MIMEText

app = FastAPI(title="Gmail MCP Server")

class ReadEmailsRequest(BaseModel):
    n: int = 5
    token: str

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    token: str

class DraftEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    token: Optional[str] = None

@app.post("/tools/read_emails")
async def read_emails(req: ReadEmailsRequest):
    """
    MCP tool to read recent email messages using user authorization credentials.
    """
    headers = {
        "Authorization": f"Bearer {req.token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={req.n}"
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Gmail API error: {res.text}")
            
        messages = res.json().get("messages", [])
        summaries = []
        
        for msg in messages:
            msg_id = msg["id"]
            d_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
            d_res = await client.get(d_url, headers=headers)
            if d_res.status_code == 200:
                detail = d_res.json()
                headers_list = detail.get("payload", {}).get("headers", [])
                
                subject = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "(No Subject)")
                from_addr = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "(Unknown)")
                
                summaries.append({
                    "id": msg_id,
                    "from": from_addr,
                    "subject": subject,
                    "snippet": detail.get("snippet", "")
                })
        
        return {"tool": "read_emails", "result": summaries}

@app.post("/tools/send_email")
async def send_email(req: SendEmailRequest):
    """
    MCP tool to send an email.
    """
    headers = {
        "Authorization": f"Bearer {req.token}",
        "Content-Type": "application/json"
    }
    
    mime_msg = MIMEText(req.body)
    mime_msg["to"] = req.to
    mime_msg["subject"] = req.subject
    raw_bytes = mime_msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
    
    async with httpx.AsyncClient() as client:
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        res = await client.post(url, headers=headers, json={"raw": raw_b64})
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Gmail Send error: {res.text}")
            
        return {"tool": "send_email", "result": f"Email successfully sent to {req.to}."}

@app.post("/tools/draft_email")
async def draft_email(req: DraftEmailRequest):
    """
    MCP tool to draft an email. Saves directly to Google Drafts if a token is supplied; otherwise returns the raw draft formatting.
    """
    if req.token:
        headers = {
            "Authorization": f"Bearer {req.token}",
            "Content-Type": "application/json"
        }
        
        mime_msg = MIMEText(req.body)
        mime_msg["to"] = req.to
        mime_msg["subject"] = req.subject
        raw_bytes = mime_msg.as_bytes()
        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
        
        async with httpx.AsyncClient() as client:
            url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
            res = await client.post(url, headers=headers, json={"message": {"raw": raw_b64}})
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"Gmail Draft error: {res.text}")
            return {"tool": "draft_email", "result": f"Draft created in Gmail. Draft ID: {res.json().get('id')}"}
    else:
        text_draft = f"To: {req.to}\nSubject: {req.subject}\n\n{req.body}"
        return {"tool": "draft_email", "result": text_draft}
