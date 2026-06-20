import base64
import json
import re
import asyncio
import httpx
from email.mime.text import MIMEText
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

async def run_email_agent(subtask: str, groq_key: str, gmail_token: str, queue: asyncio.Queue) -> str:
    """
    Runs the Email Agent. Parses tasks to read last N emails, draft, or send emails using user's Google Auth Token.
    """
    try:
        await queue.put({
            "agent": "email",
            "status": "working",
            "message": "Initializing Email Agent..."
        })
        
        if not gmail_token:
            err_msg = "Gmail OAuth token is missing. Please log in with Google first."
            await queue.put({
                "agent": "email",
                "status": "error",
                "message": err_msg
            })
            return err_msg

        if not groq_key:
            raise ValueError("Groq API key must be provided.")

        llm = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1
        )
        
        await queue.put({
            "agent": "email",
            "status": "working",
            "message": "Parsing email request details..."
        })
        
        # Instruct LLM to output parameter schema
        prompt = f"""
Analyze the subtask: {subtask}
Classify the action as one of: "read", "draft", "send".
Extract key variables in valid JSON format. Output ONLY the raw JSON block without markdown wrappers.

JSON keys:
- "action": "read" | "draft" | "send"
- "to": "recipient email address"
- "subject": "email subject line"
- "body": "full body of email (draft or create structured text if task requires writing an email)"
- "n": integer number of messages to fetch (default 5)
"""
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        clean_json = re.sub(r"```json|```", "", response.content).strip()
        
        try:
            params = json.loads(clean_json)
        except Exception:
            # Fallback simple parsing
            params = {"action": "read", "n": 5}
            if "send" in subtask.lower():
                params["action"] = "send"
            elif "draft" in subtask.lower():
                params["action"] = "draft"
        
        action = params.get("action", "read")
        headers = {
            "Authorization": f"Bearer {gmail_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if action == "read":
                n = params.get("n", 5)
                await queue.put({
                    "agent": "email",
                    "status": "working",
                    "message": f"Fetching the last {n} emails..."
                })
                
                list_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={n}"
                res = await client.get(list_url, headers=headers)
                if res.status_code != 200:
                    raise Exception(f"Gmail List API error: {res.text}")
                
                messages = res.json().get("messages", [])
                emails_summary = []
                
                for msg in messages:
                    msg_id = msg["id"]
                    detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                    detail_res = await client.get(detail_url, headers=headers)
                    if detail_res.status_code == 200:
                        detail = detail_res.json()
                        snippet = detail.get("snippet", "")
                        headers_list = detail.get("payload", {}).get("headers", [])
                        
                        subject = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "(No Subject)")
                        from_user = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "(Unknown Sender)")
                        
                        emails_summary.append(f"- **From:** {from_user}\n  **Subject:** {subject}\n  **Snippet:** {snippet}\n")
                
                if not emails_summary:
                    result = "No recent emails found in your inbox."
                else:
                    result = "### Recent Emails:\n" + "\n".join(emails_summary)
                    
            elif action in ["send", "draft"]:
                to_addr = params.get("to")
                subj = params.get("subject", "Automated message from OmniAgent")
                body = params.get("body", "Sent via OmniAgent.")
                
                if not to_addr:
                    raise ValueError("A recipient address 'to' is required for sending or drafting.")
                    
                await queue.put({
                    "agent": "email",
                    "status": "working",
                    "message": f"Constructing {action} to {to_addr}..."
                })
                
                # Construct MIME content
                mime_msg = MIMEText(body)
                mime_msg["to"] = to_addr
                mime_msg["subject"] = subj
                raw_bytes = mime_msg.as_bytes()
                encoded_msg = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
                
                if action == "send":
                    send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                    res = await client.post(send_url, headers=headers, json={"raw": encoded_msg})
                    if res.status_code != 200:
                        raise Exception(f"Gmail Send API error: {res.text}")
                    result = f"### Email Sent Successfully!\n- **To:** {to_addr}\n- **Subject:** {subj}\n\n**Body:**\n{body}"
                else:
                    draft_url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
                    res = await client.post(draft_url, headers=headers, json={"message": {"raw": encoded_msg}})
                    if res.status_code != 200:
                        raise Exception(f"Gmail Draft API error: {res.text}")
                    result = f"### Email Draft Created Successfully!\n- **To:** {to_addr}\n- **Subject:** {subj}\n\n**Body:**\n{body}"
            
        await queue.put({
            "agent": "email",
            "status": "done",
            "message": "Gmail operations completed successfully."
        })
        return result
        
    except Exception as e:
        err_str = f"Email agent failed: {e}"
        await queue.put({
            "agent": "email",
            "status": "error",
            "message": err_str
        })
        return err_str
