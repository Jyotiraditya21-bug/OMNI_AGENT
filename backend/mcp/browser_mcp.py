from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = FastAPI(title="Browser MCP Server")

class UrlRequest(BaseModel):
    url: str

@app.post("/tools/fetch_page")
async def fetch_page(req: UrlRequest):
    """
    MCP tool to read text bodies from web targets, removing formatting wrappers.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        try:
            res = await client.get(req.url, headers=headers)
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"HTTP response status {res.status_code}")
                
            soup = BeautifulSoup(res.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()
                
            cleaned = " ".join(soup.get_text().split())
            return {"tool": "fetch_page", "result": cleaned[:8000]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {e}")

@app.post("/tools/extract_links")
async def extract_links(req: UrlRequest):
    """
    MCP tool to index URLs found on a target document.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        try:
            res = await client.get(req.url, headers=headers)
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"HTTP response status {res.status_code}")
                
            soup = BeautifulSoup(res.text, "html.parser")
            link_elements = soup.find_all("a", href=True)
            links = []
            
            for item in link_elements:
                href = item["href"]
                absolute = urljoin(req.url, href)
                text = item.get_text(strip=True) or "[No link description]"
                links.append({"text": text, "url": absolute})
                
            return {"tool": "extract_links", "result": links[:100]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

@app.post("/tools/get_metadata")
async def get_metadata(req: UrlRequest):
    """
    MCP tool to gather metadata, og tag variables, and headers.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        try:
            res = await client.get(req.url, headers=headers)
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"HTTP response status {res.status_code}")
                
            soup = BeautifulSoup(res.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            description = desc_tag["content"].strip() if desc_tag and desc_tag.has_attr("content") else ""
            
            og_title_tag = soup.find("meta", attrs={"property": "og:title"})
            og_title = og_title_tag["content"].strip() if og_title_tag and og_title_tag.has_attr("content") else ""
            
            og_image_tag = soup.find("meta", attrs={"property": "og:image"})
            og_image = og_image_tag["content"].strip() if og_image_tag and og_image_tag.has_attr("content") else ""
            
            return {
                "tool": "get_metadata",
                "result": {
                    "title": title,
                    "description": description,
                    "og_title": og_title,
                    "og_image": og_image
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Meta extraction failed: {e}")
