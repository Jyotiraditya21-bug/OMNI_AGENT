import asyncio
import subprocess
import sys
import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

async def run_code_agent(subtask: str, groq_key: str, queue: asyncio.Queue) -> str:
    """
    Runs the Code Agent. Writes, explains, or debugs code.
    If the subtask asks to run/execute/output the code, it executes the code block in a local subprocess with a 10s timeout.
    """
    try:
        await queue.put({
            "agent": "code",
            "status": "working",
            "message": "Initializing Code Agent..."
        })
        
        if not groq_key:
            raise ValueError("Groq key must be provided for the code agent.")

        # Initialize the ChatGroq model
        llm = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1
        )
        
        await queue.put({
            "agent": "code",
            "status": "working",
            "message": "Generating/debugging code solution..."
        })

        prompt = f"""
You are a highly capable AI software engineer. 
Analyze the task: {subtask}
Implement a complete Python script to solve it if necessary.
If writing Python code, enclose it in a single ```python markdown code block.
Include explanations and details.
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Check if the subtask implies execution
        execution_requested = any(w in subtask.lower() for w in ["run", "execute", "output", "calculate", "compute", "test"])
        execution_output = ""
        
        if execution_requested:
            # Extract code from the markdown block
            code_blocks = re.findall(r"```python\s*(.*?)\s*```", content, re.DOTALL)
            if code_blocks:
                code_to_run = code_blocks[0]
                await queue.put({
                    "agent": "code",
                    "status": "working",
                    "message": "Executing Python script in sandbox..."
                })
                
                try:
                    # Run the code as a subprocess
                    process = await asyncio.create_subprocess_exec(
                        sys.executable, "-c", code_to_run,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    try:
                        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
                        stdout_str = stdout.decode().strip()
                        stderr_str = stderr.decode().strip()
                        
                        execution_output = "\n\n### Code Execution Output\n"
                        if stdout_str:
                            execution_output += f"**stdout:**\n```\n{stdout_str}\n```\n"
                        if stderr_str:
                            execution_output += f"**stderr:**\n```\n{stderr_str}\n```\n"
                        if not stdout_str and not stderr_str:
                            execution_output += "*Code executed successfully with no stdout/stderr output.*\n"
                            
                    except asyncio.TimeoutError:
                        process.kill()
                        execution_output = "\n\n### Code Execution Output\n**Error:** Code execution timed out after 10.0 seconds.\n"
                except Exception as run_err:
                    execution_output = f"\n\n### Code Execution Output\n**Error:** Failed to execute script: {run_err}\n"
            else:
                execution_output = "\n\n*(No code blocks found to execute)*\n"
                
        await queue.put({
            "agent": "code",
            "status": "done",
            "message": "Code agent execution completed."
        })
        return content + execution_output
        
    except Exception as e:
        error_message = f"Code agent failed: {e}"
        await queue.put({
            "agent": "code",
            "status": "error",
            "message": error_message
        })
        return error_message
