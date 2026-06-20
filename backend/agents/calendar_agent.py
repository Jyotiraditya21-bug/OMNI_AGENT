import json
import re
import datetime
import asyncio
import httpx
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

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
        
        # System instructions to extract parameters
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
                    # Free slot calculation using ChatGroq reasoning
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
                    # Default tomorrow 10:00 UTC
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
