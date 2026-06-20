import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

async def run_scraper_agent(subtask: str, groq_key: str, queue: asyncio.Queue) -> str:
    """
    Runs the Scraper Agent. Extract web url from subtask, scrapes text content,
    and runs LLM reasoning to summarize and extract relevant information.
    """
    try:
        await queue.put({
            "agent": "scraper",
            "status": "working",
            "message": "Initializing Scraper Agent..."
        })
        
        if not groq_key:
            raise ValueError("Groq API key must be provided.")

        # Extract URL using regular expressions
        urls = re.findall(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", subtask)
        if not urls:
            err_msg = "No valid URL found in the scraper subtask. Please supply a web link."
            await queue.put({
                "agent": "scraper",
                "status": "error",
                "message": err_msg
            })
            return err_msg

        target_url = urls[0]
        if target_url.startswith("www."):
            target_url = "https://" + target_url

        await queue.put({
            "agent": "scraper",
            "status": "working",
            "message": f"Fetching HTML content from {target_url}..."
        })

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Download HTML content
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            res = await client.get(target_url, headers=headers)
            if res.status_code != 200:
                raise Exception(f"HTTP error {res.status_code} fetching page.")
            html = res.text
            
        await queue.put({
            "agent": "scraper",
            "status": "working",
            "message": "Parsing and cleaning page elements..."
        })
        
        # Clean HTML elements
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
            tag.decompose()
            
        # Get raw text
        raw_text = soup.get_text(separator="\n")
        
        # Clean multiple spaces and blank lines
        lines = (line.strip() for line in raw_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Truncate content to avoid token limit errors
        body_text = cleaned_text[:8000]
        
        await queue.put({
            "agent": "scraper",
            "status": "working",
            "message": "Extracting key findings with LLM..."
        })
        
        # Initialize Groq LLM
        llm = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1
        )
        
        prompt = f"""
You are an expert web scraper extraction agent.
Goal: Extract details from the page below to satisfy the subtask: {subtask}
Page URL: {target_url}

Page Scraped Content (Truncated):
---
{body_text}
---

Provide a clean, structured summary in markdown of the relevant information extracted from the website. 
If the information is not present in the content, explain what is missing.
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = response.content
        
        await queue.put({
            "agent": "scraper",
            "status": "done",
            "message": "Scraper operations completed."
        })
        return result
        
    except Exception as e:
        err_str = f"Scraper agent failed: {e}"
        await queue.put({
            "agent": "scraper",
            "status": "error",
            "message": err_str
        })
        return err_str
