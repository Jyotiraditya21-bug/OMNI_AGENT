from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Google Drive MCP Server")

class ListFilesRequest(BaseModel):
    token: str

class ReadDocRequest(BaseModel):
    doc_id: str
    token: str

class CreateDocRequest(BaseModel):
    title: str
    content: str
    token: str

@app.post("/tools/list_files")
async def list_files(req: ListFilesRequest):
    """
    MCP tool to retrieve list of files from user Google Drive.
    """
    headers = {
        "Authorization": f"Bearer {req.token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        url = "https://www.googleapis.com/drive/v3/files?pageSize=15&orderBy=createdTime+desc&fields=files(id,name,mimeType)"
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Drive API error: {res.text}")
        return {"tool": "list_files", "result": res.json().get("files", [])}

@app.post("/tools/read_doc")
async def read_doc(req: ReadDocRequest):
    """
    MCP tool to read file contents from Google Drive or export Google Docs.
    """
    headers = {
        "Authorization": f"Bearer {req.token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # Fetch metadata
        meta_url = f"https://www.googleapis.com/drive/v3/files/{req.doc_id}?fields=name,mimeType"
        meta_res = await client.get(meta_url, headers=headers)
        if meta_res.status_code != 200:
            raise HTTPException(status_code=meta_res.status_code, detail=f"Metadata error: {meta_res.text}")
            
        meta = meta_res.json()
        name = meta.get("name", "Document")
        mime = meta.get("mimeType", "")
        
        if "google-apps.document" in mime:
            # Export Google Doc to plain text
            export_url = f"https://www.googleapis.com/drive/v3/files/{req.doc_id}/export?mimeType=text/plain"
            res = await client.get(export_url, headers=headers)
        else:
            # Direct media download
            download_url = f"https://www.googleapis.com/drive/v3/files/{req.doc_id}?alt=media"
            res = await client.get(download_url, headers=headers)
            
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Fetch file error: {res.text}")
            
        return {"tool": "read_doc", "result": {"name": name, "content": res.text}}

@app.post("/tools/create_doc")
async def create_doc(req: CreateDocRequest):
    """
    MCP tool to create a new Google Doc and write text paragraphs to it.
    """
    headers = {
        "Authorization": f"Bearer {req.token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Create file record in Drive
        create_url = "https://www.googleapis.com/drive/v3/files"
        body = {
            "name": req.title,
            "mimeType": "application/vnd.google-apps.document"
        }
        create_res = await client.post(create_url, headers=headers, json=body)
        if create_res.status_code != 200:
            raise HTTPException(status_code=create_res.status_code, detail=f"Drive doc creation error: {create_res.text}")
            
        doc_id = create_res.json().get("id")
        
        # 2. Append content to Google Doc using the Docs Batch Update API
        if req.content:
            write_url = f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate"
            write_body = {
                "requests": [
                    {
                        "insertText": {
                            "text": req.content,
                            "location": {"index": 1}
                        }
                    }
                ]
            }
            write_res = await client.post(write_url, headers=headers, json=write_body)
            if write_res.status_code != 200:
                raise HTTPException(status_code=write_res.status_code, detail=f"Docs text insertion error: {write_res.text}")
                
        return {
            "tool": "create_doc",
            "result": {
                "id": doc_id,
                "title": req.title,
                "link": f"https://docs.google.com/document/d/{doc_id}/edit"
            }
        }
