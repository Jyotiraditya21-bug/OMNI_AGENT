import asyncio
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

async def run_research_agent(subtask: str, groq_key: str, tavily_key: str, queue: asyncio.Queue) -> str:
    """
    Runs the Research Agent. Searches the web using Tavily and summarizes the findings using ChatGroq.
    """
    try:
        await queue.put({
            "agent": "research",
            "status": "working",
            "message": "Initializing Research Agent..."
        })
        
        if not groq_key or not tavily_key:
            raise ValueError("Groq and Tavily keys must both be provided for the research agent.")

        # Initialize the ChatGroq model
        llm = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.2
        )
        
        # Initialize Tavily search tool
        search_tool = TavilySearch(
            tavily_api_key=tavily_key,
            max_results=5
        )
        
        # Create LangGraph ReAct agent
        agent = create_react_agent(llm, tools=[search_tool])
        
        await queue.put({
            "agent": "research",
            "status": "working",
            "message": f"Searching the web for: {subtask}"
        })
        
        # Run agent
        inputs = {
            "messages": [("user", f"Analyze and research the following task: {subtask}. Use the search tool to find relevant data, and write a structured, detailed summary brief.")]
        }
        result = await agent.ainvoke(inputs)
        
        # Get final output
        final_answer = result["messages"][-1].content
        
        await queue.put({
            "agent": "research",
            "status": "done",
            "message": "Finished research."
        })
        return final_answer
        
    except Exception as e:
        error_message = f"Research agent failed: {e}"
        await queue.put({
            "agent": "research",
            "status": "error",
            "message": error_message
        })
        return error_message
