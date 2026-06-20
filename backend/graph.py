import asyncio
import json
import re
import operator
from typing import TypedDict, Annotated
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

try:
    from langgraph.types import Send
except ImportError:
    try:
        from langgraph.constants import Send
    except ImportError:
        from langgraph.graph import Send

# Define the state dictionary schema for the orchestrator
class AgentState(TypedDict):
    task: str
    subtasks: list[str]
    agent_assignments: dict[str, str]  # agent_name -> subtask_prompt
    agent_results: Annotated[dict[str, str], operator.or_]
    final_response: str
    session_id: str
    user_id: str
    groq_key: str
    tavily_key: str
    google_token: str
    queue: any  # asyncio.Queue

# 1. Task Decomposition Node
async def decompose_node(state: AgentState):
    await state["queue"].put({
        "agent": "orchestrator",
        "status": "working",
        "message": "Decomposing task into subtasks..."
    })
    
    llm = ChatGroq(
        api_key=state["groq_key"],
        model_name="llama-3.3-70b-versatile",
        temperature=0.1
    )
    
    prompt = f"""
You are the Master Orchestrator for OmniAgent.
Analyze the user task: "{state['task']}"
Break it down into distinct subtasks, and assign each subtask to the correct agent from the list:

1. "research" - Searches the web for information using Tavily.
2. "code" - Writes, explains, debugs, or executes Python code.
3. "email" - Reads, drafts, or sends emails. (Requires Google Account)
4. "calendar" - Schedules, lists, or finds free slots in a calendar. (Requires Google Account)
5. "file" - Lists, reads, or creates Google Docs. (Requires Google Account)
6. "data" - Performs data analysis or visualizes CSV tables using Pandas and Matplotlib.
7. "scraper" - Scrapes text information from specific website links.

Return a valid JSON string matching the schema. DO NOT output markdown blocks. Output raw JSON.

Schema:
{{
  "subtasks": ["subtask description 1", "subtask description 2"],
  "agent_assignments": {{
    "agent_name": "subtask description for this agent"
  }}
}}

Rules:
- Only assign to agents that are actually needed.
- If google_token is empty, avoid assigning Google Workspace agents (email, calendar, file) unless absolutely necessary, or warn that a Google login is required.
"""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = re.sub(r"```json|```", "", response.content).strip()
    
    try:
        data = json.loads(content)
        subtasks = data.get("subtasks", [])
        assignments = data.get("agent_assignments", {})
    except Exception:
        # Fallback to research agent
        subtasks = [state["task"]]
        assignments = {"research": state["task"]}
        
    if not assignments:
        assignments = {"research": state["task"]}
        
    await state["queue"].put({
        "agent": "orchestrator",
        "status": "done",
        "message": f"Assigned {len(assignments)} agents: {list(assignments.keys())}"
    })
    
    return {
        "subtasks": subtasks,
        "agent_assignments": assignments
    }

# 2. Worker Parallel Sub-agent Nodes
async def research_node(state: dict):
    from agents.research import run_research_agent
    res = await run_research_agent(state["current_subtask"], state["groq_key"], state["tavily_key"], state["queue"])
    return {"agent_results": {"research": res}}

async def code_node(state: dict):
    from agents.code import run_code_agent
    res = await run_code_agent(state["current_subtask"], state["groq_key"], state["queue"])
    return {"agent_results": {"code": res}}

async def email_node(state: dict):
    from agents.email_agent import run_email_agent
    res = await run_email_agent(state["current_subtask"], state["groq_key"], state["google_token"], state["queue"])
    return {"agent_results": {"email": res}}

async def calendar_node(state: dict):
    from agents.calendar_agent import run_calendar_agent
    res = await run_calendar_agent(state["current_subtask"], state["groq_key"], state["google_token"], state["queue"])
    return {"agent_results": {"calendar": res}}

async def file_node(state: dict):
    from agents.file_agent import run_file_agent
    res = await run_file_agent(state["current_subtask"], state["groq_key"], state["google_token"], state["queue"])
    return {"agent_results": {"file": res}}

async def data_node(state: dict):
    from agents.data_agent import run_data_agent
    res = await run_data_agent(state["current_subtask"], state["groq_key"], state["queue"])
    return {"agent_results": {"data": res}}

async def scraper_node(state: dict):
    from agents.scraper import run_scraper_agent
    res = await run_scraper_agent(state["current_subtask"], state["groq_key"], state["queue"])
    return {"agent_results": {"scraper": res}}

# 3. Router logic for parallel execution via Send API
def route_agents(state: AgentState):
    sends = []
    assignments = state.get("agent_assignments", {})
    
    for agent_name, subtask in assignments.items():
        node_name = f"{agent_name}_node"
        payload = {
            "task": state["task"],
            "groq_key": state["groq_key"],
            "tavily_key": state["tavily_key"],
            "google_token": state["google_token"],
            "queue": state["queue"],
            "subtasks": state["subtasks"],
            "agent_assignments": state["agent_assignments"],
            "current_subtask": subtask
        }
        sends.append(Send(node_name, payload))
        
    return sends

# 4. Result Synthesis Node
async def synthesize_node(state: AgentState):
    await state["queue"].put({
        "agent": "orchestrator",
        "status": "working",
        "message": "Synthesizing agent results..."
    })
    
    llm = ChatGroq(
        api_key=state["groq_key"],
        model_name="llama-3.3-70b-versatile",
        temperature=0.2
    )
    
    results_str = ""
    for name, text in state.get("agent_results", {}).items():
        results_str += f"\n### Result from {name.capitalize()} Agent:\n{text}\n"
        
    prompt = f"""
You are the Master Orchestrator for OmniAgent.
Synthesize the findings of all sub-agents into a final, coherent response to the user's initial task.

Initial User Task: {state['task']}

Sub-Agent Results:
{results_str}

Format the final response nicely in markdown. 
Make sure you retain all URLs, data tables, and embedded chart figures (base64 img markdown elements) outputted by the sub-agents!
"""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    await state["queue"].put({
        "agent": "orchestrator",
        "status": "done",
        "message": "Orchestrator synthesis completed."
    })
    return {"final_response": response.content}

# Compile state graph
workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("decompose_node", decompose_node)
workflow.add_node("research_node", research_node)
workflow.add_node("code_node", code_node)
workflow.add_node("email_node", email_node)
workflow.add_node("calendar_node", calendar_node)
workflow.add_node("file_node", file_node)
workflow.add_node("data_node", data_node)
workflow.add_node("scraper_node", scraper_node)
workflow.add_node("synthesize_node", synthesize_node)

# Set up routing flow
workflow.add_edge(START, "decompose_node")

workflow.add_conditional_edges(
    "decompose_node",
    route_agents,
    ["research_node", "code_node", "email_node", "calendar_node", "file_node", "data_node", "scraper_node"]
)

# Connect parallel branches to joining synthesis node
workflow.add_edge("research_node", "synthesize_node")
workflow.add_edge("code_node", "synthesize_node")
workflow.add_edge("email_node", "synthesize_node")
workflow.add_edge("calendar_node", "synthesize_node")
workflow.add_edge("file_node", "synthesize_node")
workflow.add_edge("data_node", "synthesize_node")
workflow.add_edge("scraper_node", "synthesize_node")

workflow.add_edge("synthesize_node", END)

# Export graph runner
app_graph = workflow.compile()

async def run_graph(
    task: str,
    user_id: str,
    session_id: str,
    groq_key: str,
    tavily_key: str,
    google_token: str,
    queue: asyncio.Queue
) -> str:
    """
    Executes the LangGraph orchestrator asynchronously, populating results in parent state.
    """
    initial_state = {
        "task": task,
        "subtasks": [],
        "agent_assignments": {},
        "agent_results": {},
        "final_response": "",
        "session_id": session_id,
        "user_id": user_id,
        "groq_key": groq_key,
        "tavily_key": tavily_key,
        "google_token": google_token,
        "queue": queue
    }
    result = await app_graph.ainvoke(initial_state)
    return result.get("final_response", "")
