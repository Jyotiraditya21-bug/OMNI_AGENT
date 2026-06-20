import io
import base64
import re
import asyncio
import pandas as pd
import matplotlib
# Set non-interactive Agg backend to avoid GUI errors
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

async def run_data_agent(subtask: str, groq_key: str, queue: asyncio.Queue) -> str:
    """
    Runs the Data Agent. Parses CSV data, calculates pandas summary statistics,
    generates matplotlib visualizations, and produces LLM insights.
    """
    try:
        await queue.put({
            "agent": "data",
            "status": "working",
            "message": "Initializing Data Agent..."
        })
        
        if not groq_key:
            raise ValueError("Groq API key must be provided.")

        df = None
        source_name = "Sample generated dataset"
        
        # 1. Search for CSV URL
        urls = re.findall(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", subtask)
        csv_url = None
        for url in urls:
            if url.endswith(".csv") or "csv" in url.lower():
                csv_url = url
                break
                
        if csv_url:
            await queue.put({
                "agent": "data",
                "status": "working",
                "message": f"Downloading CSV from {csv_url}..."
            })
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    res = await client.get(csv_url)
                    if res.status_code == 200:
                        df = pd.read_csv(io.StringIO(res.text))
                        source_name = f"Downloaded CSV: {csv_url}"
            except Exception as download_err:
                await queue.put({
                    "agent": "data",
                    "status": "working",
                    "message": f"Could not download CSV: {download_err}. Searching for inline data..."
                })
                
        # 2. Check for inline CSV code blocks
        if df is None:
            csv_blocks = re.findall(r"```csv\s*(.*?)\s*```", subtask, re.DOTALL)
            if csv_blocks:
                await queue.put({
                    "agent": "data",
                    "status": "working",
                    "message": "Parsing CSV text block..."
                })
                df = pd.read_csv(io.StringIO(csv_blocks[0]))
                source_name = "Markdown-embedded CSV"
            else:
                # Fallback: check if subtask has comma-separated values in text
                lines = [line.strip() for line in subtask.split("\n") if "," in line]
                if len(lines) >= 3:
                    try:
                        df = pd.read_csv(io.StringIO("\n".join(lines)))
                        source_name = "Inline raw CSV"
                    except Exception:
                        pass
                        
        # 3. Fallback mock generation if no CSV is available
        if df is None:
            await queue.put({
                "agent": "data",
                "status": "working",
                "message": "No CSV found. Generating business mockup dataset..."
            })
            mock_data = {
                "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                "Revenue": [12000, 15000, 18000, 14000, 22000, 26000, 21000, 24000, 28000, 31000, 35000, 42000],
                "Expenses": [10000, 11000, 12500, 11500, 14000, 16000, 15000, 16500, 18000, 19500, 21000, 24000]
            }
            df = pd.DataFrame(mock_data)
            source_name = "Mock revenue dashboard data"
            
        await queue.put({
            "agent": "data",
            "status": "working",
            "message": "Calculating data metrics and summary stats..."
        })
        
        # Calculate summaries
        summary_stats = df.describe(include="all").to_markdown()
        head_str = df.head(10).to_markdown()
        
        # Load Groq model
        llm = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.2
        )
        
        prompt = f"""
You are an expert data science agent. 
Analyze this dataset from source: {source_name}
Subtask requested by user: {subtask}

First 10 rows:
{head_str}

Descriptive Statistics:
{summary_stats}

Provide a structured, data-driven report. Include:
1. Data Overview (number of rows, columns, data types).
2. Key Insights & Business Trends.
3. Logical Recommendations.
Write in beautiful, professional markdown.
"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        insights = response.content
        
        # Generate and save chart
        await queue.put({
            "agent": "data",
            "status": "working",
            "message": "Generating data visualization plot..."
        })
        
        plt.figure(figsize=(9, 5))
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
        
        x_col = categorical_cols[0] if categorical_cols else (numeric_cols[0] if numeric_cols else None)
        
        if numeric_cols:
            if x_col and x_col in df.columns:
                for col in numeric_cols:
                    if col != x_col:
                        plt.plot(df[x_col], df[col], marker="o", label=col, linewidth=2)
                plt.xlabel(x_col)
            else:
                for col in numeric_cols:
                    plt.plot(df[col], marker="o", label=col, linewidth=2)
                plt.xlabel("Index")
                
            plt.ylabel("Values")
            plt.title(f"Data Chart - {source_name}")
            plt.legend()
            plt.grid(True, linestyle=":", alpha=0.7)
            plt.tight_layout()
            
            # Save plot to base64
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format="png", dpi=120)
            plt.close()
            img_buf.seek(0)
            b64_string = base64.b64encode(img_buf.read()).decode("utf-8")
            
            chart_markdown = f"\n\n### Chart Visualization\n![Data Chart](data:image/png;base64,{b64_string})\n"
        else:
            plt.close()
            chart_markdown = "\n\n*(No plot generated: dataset contains no numeric values)*\n"
            
        await queue.put({
            "agent": "data",
            "status": "done",
            "message": "Finished data operations."
        })
        return insights + chart_markdown
        
    except Exception as e:
        err_msg = f"Data agent failed: {e}"
        await queue.put({
            "agent": "data",
            "status": "error",
            "message": err_msg
        })
        return err_msg
