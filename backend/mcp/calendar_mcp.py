from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import datetime

app = FastAPI(title="Google Calendar MCP Server")

class GetEventsRequest(BaseModel):
    days_ahead: int = 7
    token: str

class CreateEventRequest(BaseModel):
    title: str
    start: str
    end: str
    description: str
    token: str

class FindFreeSlotRequest(BaseModel):
    duration_minutes: int = 60
    token: str

@app.post("/tools/get_events")
async def get_events(req: GetEventsRequest):
    """
    MCP tool to retrieve schedule items for upcoming days.
    """
    headers = {"Authorization": f"Bearer {req.token}"}
    time_min = datetime.datetime.utcnow().isoformat() + "Z"
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=req.days_ahead)).isoformat() + "Z"
    
    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={time_min}&timeMax={time_max}&singleEvents=true&orderBy=startTime"
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Calendar API error: {res.text}")
        return {"tool": "get_events", "result": res.json().get("items", [])}

@app.post("/tools/create_event")
async def create_event(req: CreateEventRequest):
    """
    MCP tool to create a new Calendar event.
    """
    headers = {
        "Authorization": f"Bearer {req.token}",
        "Content-Type": "application/json"
    }
    body = {
        "summary": req.title,
        "description": req.description,
        "start": {"dateTime": req.start},
        "end": {"dateTime": req.end}
    }
    
    async with httpx.AsyncClient() as client:
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        res = await client.post(url, headers=headers, json=body)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Create event error: {res.text}")
        return {"tool": "create_event", "result": res.json()}

@app.post("/tools/find_free_slot")
async def find_free_slot(req: FindFreeSlotRequest):
    """
    MCP tool to find the next open workspace slot of standard duration.
    Calculates availability algorithmically by scanning against calendar busy ranges.
    """
    headers = {"Authorization": f"Bearer {req.token}"}
    time_min = datetime.datetime.utcnow().isoformat() + "Z"
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"
    
    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={time_min}&timeMax={time_max}&singleEvents=true&orderBy=startTime"
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Events fetch error: {res.text}")
            
        events = res.json().get("items", [])
        busy_intervals = []
        for e in events:
            start_str = e.get("start", {}).get("dateTime")
            end_str = e.get("end", {}).get("dateTime")
            if start_str and end_str:
                try:
                    s_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    e_dt = datetime.datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    busy_intervals.append((s_dt, e_dt))
                except Exception:
                    pass
        
        # Algorithmic scan
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        duration = datetime.timedelta(minutes=req.duration_minutes)
        current_day = now_dt.date()
        proposed_slot = None
        
        for i in range(7):
            day = current_day + datetime.timedelta(days=i)
            # Scan 9 AM to 5 PM UTC
            scan_time = datetime.datetime.combine(day, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
            end_work = datetime.datetime.combine(day, datetime.time(17, 0), tzinfo=datetime.timezone.utc)
            
            while scan_time + duration <= end_work:
                if scan_time > now_dt:
                    overlap = False
                    slot_start = scan_time
                    slot_end = scan_time + duration
                    
                    for b_start, b_end in busy_intervals:
                        if max(slot_start, b_start) < min(slot_end, b_end):
                            overlap = True
                            break
                            
                    if not overlap:
                        proposed_slot = {
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "duration_minutes": req.duration_minutes
                        }
                        break
                scan_time += datetime.timedelta(minutes=30)
            if proposed_slot:
                break
                
        if not proposed_slot:
            # Fallback suggestion
            tomorrow_start = datetime.datetime.combine(now_dt.date() + datetime.timedelta(days=1), datetime.time(10, 0), tzinfo=datetime.timezone.utc)
            proposed_slot = {
                "start": tomorrow_start.isoformat(),
                "end": (tomorrow_start + duration).isoformat(),
                "duration_minutes": req.duration_minutes,
                "note": "No open slots found in active hours. Proposing fallback tomorrow at 10:00 AM UTC."
            }
            
        return {"tool": "find_free_slot", "result": proposed_slot}
