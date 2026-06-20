document.addEventListener("DOMContentLoaded", async () => {
  const taskInput = document.getElementById("taskInput");
  const runBtn = document.getElementById("runBtn");
  const outputContainer = document.getElementById("outputContainer");
  const jwtInput = document.getElementById("jwtInput");
  const backendInput = document.getElementById("backendInput");

  // Restore stored session items
  chrome.storage.local.get(["authToken", "backendUrl"], (data) => {
    if (data.authToken) jwtInput.value = data.authToken;
    if (data.backendUrl) backendInput.value = data.backendUrl;
  });

  // Pull highlighted selection from extension session storage
  chrome.storage.session.get("selectedText", (data) => {
    if (data.selectedText) {
      taskInput.value = data.selectedText;
      chrome.storage.session.remove("selectedText");
    }
  });

  // Keep monitoring changes to the session selection
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === "session" && changes.selectedText) {
      taskInput.value = changes.selectedText.newValue;
    }
  });

  // Write changes to storage
  const syncSettings = () => {
    chrome.storage.local.set({
      authToken: jwtInput.value.trim(),
      backendUrl: backendInput.value.trim()
    });
  };
  
  jwtInput.addEventListener("input", syncSettings);
  backendInput.addEventListener("input", syncSettings);

  runBtn.addEventListener("click", async () => {
    const prompt = taskInput.value.trim();
    const token = jwtInput.value.trim();
    const host = backendInput.value.trim() || "http://localhost:8000";

    if (!prompt) {
      alert("Please provide an instruction first.");
      return;
    }
    if (!token) {
      alert("Settings Error: Please authenticate with your Console JWT first.");
      return;
    }

    runBtn.disabled = true;
    outputContainer.innerHTML = `
      <div class="progress-spinner"></div>
      <p class="info-status">Sending request to orchestrator...</p>
    `;

    try {
      const response = await fetch(`${host}/run`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ task: prompt })
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Response status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamBuffer = "";
      
      outputContainer.innerHTML = "";
      const summaryBox = document.createElement("div");
      summaryBox.className = "summary-box";
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        streamBuffer += decoder.decode(value, { stream: true });
        const lines = streamBuffer.split("\n");
        streamBuffer = lines.pop() || "";

        for (const line of lines) {
          const row = line.trim();
          if (!row || !row.startsWith("data:")) continue;

          const jsonStr = row.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const dataObj = JSON.parse(jsonStr);

            if (dataObj.event === "agent_start" && dataObj.agent) {
              upsertStatusLine(dataObj.agent, "working", dataObj.message);
            } else if (dataObj.event === "agent_done" && dataObj.agent) {
              upsertStatusLine(dataObj.agent, "done", dataObj.message);
            } else if (dataObj.event === "thinking" && dataObj.agent) {
              upsertStatusLine(dataObj.agent, "working", dataObj.message);
            } else if (dataObj.event === "final") {
              summaryBox.innerHTML = `
                <div class="synthesis-header">Synthesis Completed</div>
                <div class="synthesis-text">${formatMarkdown(dataObj.result)}</div>
              `;
              if (!summaryBox.parentNode) {
                outputContainer.appendChild(summaryBox);
              }
            } else if (dataObj.event === "error") {
              if (dataObj.agent) {
                upsertStatusLine(dataObj.agent, "error", dataObj.message);
              } else {
                appendConsoleError(dataObj.message);
              }
            }
          } catch (jsonErr) {
            console.error("JSON read error inside stream:", jsonErr);
          }
        }
      }
      
    } catch (err) {
      appendConsoleError(err.message);
    } finally {
      runBtn.disabled = false;
    }
  });

  function upsertStatusLine(agent, status, message) {
    let lineEl = document.getElementById(`line-${agent}`);
    if (!lineEl) {
      lineEl = document.createElement("div");
      lineEl.id = `line-${agent}`;
      lineEl.className = "log-line animate-pulse";
      outputContainer.insertBefore(lineEl, outputContainer.firstChild);
    }

    let symbol = "●";
    let style = "status-idle";
    
    if (status === "working") {
      style = "status-working";
    } else if (status === "done") {
      style = "status-done";
      symbol = "✔";
      lineEl.classList.remove("animate-pulse");
    } else if (status === "error") {
      style = "status-error";
      symbol = "✖";
      lineEl.classList.remove("animate-pulse");
    }

    lineEl.innerHTML = `
      <span class="symbol ${style}">${symbol}</span>
      <span class="agent-name">${agent.toUpperCase()}:</span>
      <span class="agent-msg">${message}</span>
    `;
  }

  function appendConsoleError(msg) {
    const errBox = document.createElement("div");
    errBox.className = "error-container";
    errBox.innerText = `Orchestrator Error: ${msg}`;
    outputContainer.appendChild(errBox);
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    
    // Process markdown selectors
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.*?)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.*?)$/gm, "<h1>$1</h1>");
    html = html.replace(/^\- (.*?)$/gm, "<li>$1</li>");
    html = html.replace(/\n/g, "<br>");
    return html;
  }
});
