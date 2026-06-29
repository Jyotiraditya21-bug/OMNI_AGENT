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
    pending_agents: list[str]

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
- CRITICAL: When writing the subtask description for an agent, you MUST preserve all specific user variables/details (such as recipient email addresses, contact names, event times/dates, URLs, filenames, and numeric values). Do NOT omit them. For example, if the user specifies sending an email to "xyz@example.com", the "email" agent's subtask description MUST explicitly contain "xyz@example.com".
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
        "agent_assignments": assignments,
        "pending_agents": list(assignments.keys())
    }

# Helper to inject context from previous agents
def get_context_subtask(state: dict, agent_name: str) -> str:
    subtask = state.get("agent_assignments", {}).get(agent_name, "")
    results = state.get("agent_results", {})
    if results:
        context = "Context from previous agents:\n"
        for k, v in results.items():
            context += f"--- {k.upper()} ---\n{v}\n\n"
        subtask = f"{context}\nNow complete this subtask:\n{subtask}"
    return subtask

def update_pending(state: dict, agent_name: str) -> list[str]:
    pending = state.get("pending_agents", [])
    return [a for a in pending if a != agent_name]

# 2. Worker Sequential Sub-agent Nodes
async def research_node(state: dict):
    from agents.research import run_research_agent
    subtask = get_context_subtask(state, "research")
    res = await run_research_agent(subtask, state["groq_key"], state["tavily_key"], state["queue"])
    return {"agent_results": {"research": res}, "pending_agents": update_pending(state, "research")}

async def code_node(state: dict):
    from agents.code import run_code_agent
    subtask = get_context_subtask(state, "code")
    res = await run_code_agent(subtask, state["groq_key"], state["queue"])
    return {"agent_results": {"code": res}, "pending_agents": update_pending(state, "code")}

async def email_node(state: dict):
    from agents.google_agents import run_email_agent
    subtask = get_context_subtask(state, "email")
    res = await run_email_agent(subtask, state["groq_key"], state["google_token"], state["queue"])
    return {"agent_results": {"email": res}, "pending_agents": update_pending(state, "email")}

async def calendar_node(state: dict):
    from agents.google_agents import run_calendar_agent
    subtask = get_context_subtask(state, "calendar")
    res = await run_calendar_agent(subtask, state["groq_key"], state["google_token"], state["queue"])
    return {"agent_results": {"calendar": res}, "pending_agents": update_pending(state, "calendar")}

async def file_node(state: dict):
    from agents.google_agents import run_file_agent
    subtask = get_context_subtask(state, "file")
    res = await run_file_agent(subtask, state["groq_key"], state["google_token"], state["queue"])
    return {"agent_results": {"file": res}, "pending_agents": update_pending(state, "file")}

async def data_node(state: dict):
    from agents.data_agent import run_data_agent
    subtask = get_context_subtask(state, "data")
    res = await run_data_agent(subtask, state["groq_key"], state["queue"])
    return {"agent_results": {"data": res}, "pending_agents": update_pending(state, "data")}

async def scraper_node(state: dict):
    from agents.scraper import run_scraper_agent
    subtask = get_context_subtask(state, "scraper")
    res = await run_scraper_agent(subtask, state["groq_key"], state["queue"])
    return {"agent_results": {"scraper": res}, "pending_agents": update_pending(state, "scraper")}

# 3. Router logic for sequential execution
def route_agents(state: AgentState):
    pending = state.get("pending_agents", [])
    if not pending:
        return "synthesize_node"
    return f"{pending[0]}_node"

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

Formatting Rules:
1. Be extremely concise, readable, and executive-ready. Avoid wordy introductions (e.g. "Here is the synthesized response...") or recapping which agent did what task unless requested.
2. Structure the response using clean subheadings, bullet points, and key-value pairings.
3. HIDE long logs, raw code structures, or extensive tables inside clean HTML details tabs:
   <details>
     <summary>Click to view raw code / raw details</summary>
     [detailed text here]
   </details>
4. CRITICAL: You MUST retain all URLs, data tables, and visual chart base64 image markdown tags (`![Data Chart](data:image/png;base64,...)`) exactly as output by the sub-agents!
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

# List of all possible next nodes
route_nodes = ["research_node", "code_node", "email_node", "calendar_node", "file_node", "data_node", "scraper_node", "synthesize_node"]

workflow.add_conditional_edges(
    "decompose_node",
    route_agents,
    route_nodes
)

# Connect all agent nodes back to the router to allow sequential execution
for node_name in ["research_node", "code_node", "email_node", "calendar_node", "file_node", "data_node", "scraper_node"]:
    workflow.add_conditional_edges(
        node_name,
        route_agents,
        route_nodes
    )

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
        "queue": queue,
        "pending_agents": []
    }
    result = await app_graph.ainvoke(initial_state)
    return result.get("final_response", "")
