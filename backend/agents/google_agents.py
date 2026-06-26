import json
import re
import datetime
import asyncio
import httpx
import base64
from email.mime.text import MIMEText
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# ==============================================================================
# 1. EMAIL AGENT (GMAIL)
# ==============================================================================

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


# ==============================================================================
# 2. CALENDAR AGENT
# ==============================================================================

async def run_calendar_agent(subtask: str, groq_key: str, calendar_token: str, queue: asyncio.Queue) -> str:
    """
    Runs the Calendar Agent. Lists, schedules, or finds free time slots using the Google Calendar REST API.
    """
    try:
        await queue.put({
            "agent": "calendar",
            "status": "working",
            "message": "Initializing Calendar Agent..."
        })
        
        if not calendar_token:
            err_msg = "Google Calendar OAuth token is missing. Please authenticate with Google first."
            await queue.put({
                "agent": "calendar",
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
            "agent": "calendar",
            "status": "working",
            "message": "Analyzing schedule subtask..."
        })

        now_utc = datetime.datetime.utcnow()
        now_iso = now_utc.isoformat() + "Z"
        
        prompt = f"""
Analyze the subtask: {subtask}
Current time (UTC): {now_iso}
Classify the action as one of: "list", "create", "free_slots".
Extract key parameters into a valid JSON string. Output ONLY the JSON block.

JSON keys:
- "action": "list" | "create" | "free_slots"
- "title": "event subject/title"
- "description": "details/agenda"
- "start_time": "ISO 8601 start time (e.g. 2026-06-21T14:00:00Z)"
- "end_time": "ISO 8601 end time"
- "duration_minutes": integer (default 60)
- "days_ahead": integer (default 7 for free_slots, 3 for list)
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        clean_json = re.sub(r"```json|```", "", response.content).strip()
        
        try:
            params = json.loads(clean_json)
        except Exception:
            params = {"action": "list", "days_ahead": 3}
            
        action = params.get("action", "list")
        headers = {
            "Authorization": f"Bearer {calendar_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if action in ["list", "free_slots"]:
                days = params.get("days_ahead", 7 if action == "free_slots" else 3)
                await queue.put({
                    "agent": "calendar",
                    "status": "working",
                    "message": f"Fetching upcoming events for {days} days..."
                })
                
                time_min = now_iso
                time_max = (now_utc + datetime.timedelta(days=days)).isoformat() + "Z"
                
                url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={time_min}&timeMax={time_max}&singleEvents=true&orderBy=startTime"
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    raise Exception(f"Calendar list error: {res.text}")
                    
                items = res.json().get("items", [])
                
                if action == "list":
                    events_list = []
                    for item in items:
                        start_time = item.get("start", {}).get("dateTime", item.get("start", {}).get("date", ""))
                        summary = item.get("summary", "(No Subject)")
                        events_list.append(f"- **{summary}**\n  Start: {start_time}")
                    if not events_list:
                        result = "No upcoming events found."
                    else:
                        result = "### Calendar Events:\n" + "\n".join(events_list)
                else:
                    await queue.put({
                        "agent": "calendar",
                        "status": "working",
                        "message": "Calculating optimal free time slots..."
                    })
                    events_data = [{"summary": i.get("summary"), "start": i.get("start"), "end": i.get("end")} for i in items]
                    duration = params.get("duration_minutes", 60)
                    
                    slot_prompt = f"""
You are a calendar scheduler. 
User wants to find a free time slot of {duration} minutes.
Current time: {now_iso}
Existing schedule for the next {days} days:
{json.dumps(events_data)}

Determine 3 available options of {duration} minutes within normal hours (9:00 to 17:00 UTC).
Do not overlap with any existing events. Present options in clean markdown list.
"""
                    slot_res = await llm.ainvoke([HumanMessage(content=slot_prompt)])
                    result = slot_res.content
                    
            elif action == "create":
                title = params.get("title", "New Appointment")
                desc = params.get("description", "Created by OmniAgent")
                start = params.get("start_time")
                end = params.get("end_time")
                
                if not start:
                    tomorrow = (now_utc + datetime.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
                    start = tomorrow.isoformat() + "Z"
                if not end:
                    start_dt = datetime.datetime.fromisoformat(start.replace("Z", ""))
                    end = (start_dt + datetime.timedelta(hours=1)).isoformat() + "Z"
                    
                await queue.put({
                    "agent": "calendar",
                    "status": "working",
                    "message": f"Creating calendar event '{title}'..."
                })
                
                body = {
                    "summary": title,
                    "description": desc,
                    "start": {"dateTime": start},
                    "end": {"dateTime": end}
                }
                
                create_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                res = await client.post(create_url, headers=headers, json=body)
                if res.status_code != 200:
                    raise Exception(f"Calendar Create error: {res.text}")
                    
                result = f"### Event Scheduled Successfully!\n- **Title:** {title}\n- **Start Time:** {start}\n- **End Time:** {end}\n- **Details:** {desc}"
                
        await queue.put({
            "agent": "calendar",
            "status": "done",
            "message": "Calendar agent finished execution."
        })
        return result
        
    except Exception as e:
        err_str = f"Calendar agent failed: {e}"
        await queue.put({
            "agent": "calendar",
            "status": "error",
            "message": err_str
        })
        return err_str


# ==============================================================================
# 3. FILE AGENT (GOOGLE DRIVE/DOCS)
# ==============================================================================

async def run_file_agent(subtask: str, groq_key: str, drive_token: str, queue: asyncio.Queue) -> str:
    """
    Runs the File Agent. Interacts with Google Drive/Docs REST API to list, read, or write Google Docs.
    """
    try:
        await queue.put({
            "agent": "file",
            "status": "working",
            "message": "Initializing File Agent..."
        })
        
        if not drive_token:
            err_msg = "Google Drive OAuth token is missing. Please authenticate with Google first."
            await queue.put({
                "agent": "file",
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
            "agent": "file",
            "status": "working",
            "message": "Parsing file instruction details..."
        })

        prompt = f"""
Analyze the subtask: {subtask}
Classify the action as one of: "list", "read", "create".
Extract key parameters into a valid JSON string. Output ONLY the JSON block.

JSON keys:
- "action": "list" | "read" | "create"
- "file_id": "google drive file id (required for read)"
- "title": "google doc title (required for create)"
- "content": "body text for document creation"
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        clean_json = re.sub(r"```json|```", "", response.content).strip()
        
        try:
            params = json.loads(clean_json)
        except Exception:
            params = {"action": "list"}
            
        action = params.get("action", "list")
        headers = {
            "Authorization": f"Bearer {drive_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if action == "list":
                await queue.put({
                    "agent": "file",
                    "status": "working",
                    "message": "Listing recent files in Drive..."
                })
                
                url = "https://www.googleapis.com/drive/v3/files?pageSize=10&orderBy=createdTime+desc&fields=files(id,name,mimeType)"
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    raise Exception(f"Google Drive listing error: {res.text}")
                    
                files = res.json().get("files", [])
                file_lines = []
                for f in files:
                    file_lines.append(f"- **{f['name']}** (ID: {f['id']}, MimeType: {f['mimeType']})")
                
                if not file_lines:
                    result = "No files found in Google Drive."
                else:
                    result = "### Recent Google Drive Files:\n" + "\n".join(file_lines)
                    
            elif action == "read":
                file_id = params.get("file_id")
                if not file_id:
                    raise ValueError("A Google Drive 'file_id' is required for reading document contents.")
                    
                await queue.put({
                    "agent": "file",
                    "status": "working",
                    "message": f"Retrieving file metadata for {file_id}..."
                })
                
                meta_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType"
                meta_res = await client.get(meta_url, headers=headers)
                if meta_res.status_code != 200:
                    raise Exception(f"Drive fetch metadata error: {meta_res.text}")
                
                meta = meta_res.json()
                name = meta.get("name", "Document")
                mime_type = meta.get("mimeType", "")
                
                await queue.put({
                    "agent": "file",
                    "status": "working",
                    "message": f"Downloading text content from {name}..."
                })
                
                if "google-apps.document" in mime_type:
                    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
                    content_res = await client.get(export_url, headers=headers)
                    if content_res.status_code != 200:
                        raise Exception(f"Failed to export Google Doc to text: {content_res.text}")
                    content_body = content_res.text
                else:
                    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                    content_res = await client.get(download_url, headers=headers)
                    if content_res.status_code != 200:
                        raise Exception(f"Failed to read file media: {content_res.text}")
                    content_body = content_res.text
                    
                result = f"### File Contents ({name}):\n\n{content_body}"
                
            elif action == "create":
                title = params.get("title", "New Document")
                content = params.get("content", "")
                
                await queue.put({
                    "agent": "file",
                    "status": "working",
                    "message": f"Creating Google Doc '{title}'..."
                })
                
                create_url = "https://www.googleapis.com/drive/v3/files"
                body = {
                    "name": title,
                    "mimeType": "application/vnd.google-apps.document"
                }
                res = await client.post(create_url, headers=headers, json=body)
                if res.status_code != 200:
                    raise Exception(f"Failed to create Google Doc file row: {res.text}")
                
                doc_id = res.json().get("id")
                
                if content:
                    await queue.put({
                        "agent": "file",
                        "status": "working",
                        "message": "Writing content blocks to document..."
                    })
                    write_url = f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate"
                    write_body = {
                        "requests": [
                            {
                                "insertText": {
                                    "text": content,
                                    "location": {"index": 1}
                                }
                            }
                        ]
                    }
                    write_res = await client.post(write_url, headers=headers, json=write_body)
                    if write_res.status_code != 200:
                        raise Exception(f"Google Docs API text write error: {write_res.text}")
                        
                result = f"### Document Created Successfully!\n- **Title:** {title}\n- **ID:** {doc_id}\n- **URL:** https://docs.google.com/document/d/{doc_id}/edit"
                
        await queue.put({
            "agent": "file",
            "status": "done",
            "message": "File agent operations completed."
        })
        return result
        
    except Exception as e:
        err_str = f"File agent failed: {e}"
        await queue.put({
            "agent": "file",
            "status": "error",
            "message": err_str
        })
        return err_str
