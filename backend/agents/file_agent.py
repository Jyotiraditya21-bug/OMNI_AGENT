import json
import re
import asyncio
import httpx
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

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

        # Prompt LLM to classify action and extract metadata variables
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
                
                # Fetch metadata to determine if it is a Google Doc
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
                    # Export as raw text format
                    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
                    content_res = await client.get(export_url, headers=headers)
                    if content_res.status_code != 200:
                        raise Exception(f"Failed to export Google Doc to text: {content_res.text}")
                    content_body = content_res.text
                else:
                    # Standard file media download
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
