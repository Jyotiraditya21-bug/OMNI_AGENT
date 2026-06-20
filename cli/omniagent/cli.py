import os
import json
import time
import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

app = typer.Typer(help="OmniAgent CLI — Universal Swarm Assistant Console Client")
config_subapp = typer.Typer(help="Manage configuration credentials and server endpoints")
app.add_typer(config_subapp, name="config")

console = Console()

CONFIG_DIR = os.path.expanduser("~/.omniagent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def load_config() -> dict:
    """
    Loads saved configurations from the user's home directory.
    """
    if not os.path.exists(CONFIG_FILE):
        return {"auth_token": "", "backend_url": "http://localhost:8000"}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"auth_token": "", "backend_url": "http://localhost:8000"}

def save_config(config: dict):
    """
    Saves configurations to target JSON file.
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

@config_subapp.command("set-key")
def set_key(
    key: str = typer.Option(..., prompt="Enter your OmniAgent Session JWT", hide_input=True)
):
    """
    Saves your backend authentication JWT token to client config.
    """
    config = load_config()
    config["auth_token"] = key.strip()
    save_config(config)
    console.print("[green]✔ Authentication token saved successfully.[/green]")

@config_subapp.command("set-url")
def set_url(
    url: str = typer.Option(..., prompt="Enter backend API URL", default="http://localhost:8000")
):
    """
    Saves the target backend API host URL.
    """
    config = load_config()
    config["backend_url"] = url.strip().rstrip("/")
    save_config(config)
    console.print(f"[green]✔ Backend API URL mapped to: {config['backend_url']}[/green]")

@app.command("run")
def run(task: str):
    """
    Triggers orchestrator execution on backend and streams live agent updates.
    """
    config = load_config()
    token = config.get("auth_token")
    backend_url = config.get("backend_url", "http://localhost:8000")

    if not token:
        console.print("[red]✖ Error: Session JWT token is missing.[/red]")
        console.print("Run [bold]omniagent config set-key[/bold] to configure your credentials first.")
        raise typer.Exit(code=1)

    console.print(f"[bold indigo]🚀 Initializing Swarm Execution...[/bold indigo]")
    console.print(f"[dim]Backend Target: {backend_url}[/dim]")
    
    start_time = time.time()
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # Standard HTTP client to POST to /run and handle response stream
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", f"{backend_url}/run", headers=headers, json={"task": task}) as response:
                if response.status_code != 200:
                    console.print(f"[red]✖ Connection failed with status {response.status_code}: {response.read().decode()}[/red]")
                    raise typer.Exit(code=1)
                
                final_result = ""
                buffer = ""
                
                for chunk in response.iter_text():
                    buffer += chunk
                    lines = buffer.split("\n")
                    buffer = lines.pop()
                    
                    for line in lines:
                        row = line.strip()
                        if not row or not row.startswith("data:"):
                            continue
                        
                        json_str = row[5:].strip()
                        if not json_str:
                            continue
                            
                        try:
                            event_data = json.loads(json_str)
                            event_type = event_data.get("event")
                            agent = event_data.get("agent")
                            msg = event_data.get("message")
                            
                            if event_type == "agent_start" and agent:
                                console.print(f"[bold blue]● {agent.capitalize()}:[/bold blue] {msg}")
                            elif event_type == "agent_done" and agent:
                                console.print(f"[bold green]✔ {agent.capitalize()}:[/bold green] Done")
                            elif event_type == "thinking" and agent:
                                console.print(f"[bold dim]● {agent.capitalize()}:[/bold dim] {msg}")
                            elif event_type == "final":
                                final_result = event_data.get("result", "")
                            elif event_type == "error":
                                if agent:
                                    console.print(f"[bold red]✖ {agent.capitalize()}:[/bold red] {msg}")
                                else:
                                    console.print(f"[bold red]✖ Orchestrator Error:[/bold red] {msg}")
                        except Exception:
                            pass
                            
                total_time = time.time() - start_time
                
                if final_result:
                    console.print("\n")
                    console.print(Panel(
                        Markdown(final_result),
                        title="[bold indigo]Synthesis Result[/bold indigo]",
                        border_style="indigo"
                    ))
                    console.print(f"[dim]Execution completed in {total_time:.2f} seconds.[/dim]")
                else:
                    console.print("[yellow]⚠ Pipeline exited without returning final result summary.[/yellow]")

    except Exception as e:
        console.print(f"[red]✖ Execution failed: {e}[/red]")
        raise typer.Exit(code=1)

@app.command("history")
def history(
    limit: int = typer.Option(10, help="Number of records to return")
):
    """
    Displays the past sessions from database history logs.
    """
    config = load_config()
    token = config.get("auth_token")
    backend_url = config.get("backend_url", "http://localhost:8000")

    if not token:
        console.print("[red]✖ Error: Config token is empty.[/red]")
        raise typer.Exit(code=1)

    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = httpx.get(f"{backend_url}/history?limit={limit}", headers=headers)
        if res.status_code != 200:
            console.print(f"[red]✖ Failed to load history: {res.text}[/red]")
            raise typer.Exit(code=1)
            
        sessions = res.json()
        if not sessions:
            console.print("[dim]No sessions found in history.[/dim]")
            return

        table = Table(title="[bold indigo]OmniAgent Session History[/bold indigo]")
        table.add_column("#", justify="center")
        table.add_column("Task Description", max_width=40)
        table.add_column("Agents Used", justify="left")
        table.add_column("Created At", justify="right")

        for idx, item in enumerate(sessions):
            agents = ", ".join(item.get("agents_used", []))
            table.add_row(
                str(idx + 1),
                item.get("task", ""),
                agents if agents else "None",
                item.get("created_at", "")
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]✖ Failed connection: {e}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
