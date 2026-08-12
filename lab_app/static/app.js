const agents = [
  "GameDesigner",
  "TechnicalPlanner",
  "GameplayDeveloper",
  "Playtester",
  "BugReviewer",
];

const form = document.querySelector("#build-form");
const promptInput = document.querySelector("#prompt");
const promptCount = document.querySelector("#prompt-count");
const demoModeInput = document.querySelector("#demo-mode");
const refreshButton = document.querySelector("#refresh-button");
const statusDot = document.querySelector("#status-dot");
const statusText = document.querySelector("#status-text");
const runTitle = document.querySelector("#run-title");
const runId = document.querySelector("#run-id");
const runUpdated = document.querySelector("#run-updated");
const detailRunId = document.querySelector("#detail-run-id");
const detailStatus = document.querySelector("#detail-status");
const detailAgent = document.querySelector("#detail-agent");
const detailStage = document.querySelector("#detail-stage");
const detailUpdated = document.querySelector("#detail-updated");
const detailOutput = document.querySelector("#detail-output");
const readyCount = document.querySelector("#ready-count");
const totalCount = document.querySelector("#total-count");
const gameFrame = document.querySelector("#game-frame");
const emptyState = document.querySelector("#empty-state");
const openLink = document.querySelector("#open-link");
const downloadLink = document.querySelector("#download-link");
const runsList = document.querySelector("#runs-list");
const workflowRail = document.querySelector("#workflow-rail");
const agentList = document.querySelector("#agent-list");
const evidenceList = document.querySelector("#evidence-list");
const adkFlow = document.querySelector("#adk-flow");
const quickPrompts = document.querySelectorAll("[data-prompt]");

let activeJobId = null;
let pollTimer = null;
let selectedRunId = null;

function agentIndex(agentName) {
  const index = agents.indexOf(agentName);
  return index < 0 ? 0 : index;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setStatus(message, mode = "") {
  statusText.textContent = message;
  statusDot.className = `status-dot ${mode}`.trim();
}

function setLinks(run) {
  if (!run || !run.ready) {
    openLink.removeAttribute("href");
    downloadLink.removeAttribute("href");
    openLink.classList.add("disabled");
    downloadLink.classList.add("disabled");
    openLink.setAttribute("aria-disabled", "true");
    downloadLink.setAttribute("aria-disabled", "true");
    return;
  }

  openLink.href = `${run.game_url}index.html?v=${Date.now()}`;
  downloadLink.href = run.download_url;
  openLink.classList.remove("disabled");
  downloadLink.classList.remove("disabled");
  openLink.removeAttribute("aria-disabled");
  downloadLink.removeAttribute("aria-disabled");
}

function formatDate(seconds) {
  if (!seconds) return "-";
  return new Date(seconds * 1000).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function updatePromptCount() {
  promptCount.textContent = `${promptInput.value.length}/4000`;
}

const flowNodes = [
  { id: "start", label: "START", agent: null, detail: "Invocation" },
  { id: "designer", label: "GameDesigner", agent: "GameDesigner", detail: "Design" },
  { id: "workspace", label: "create_run_workspace", agent: "TechnicalPlanner", detail: "Workspace" },
  { id: "planner", label: "TechnicalPlanner", agent: "TechnicalPlanner", detail: "Plan" },
  { id: "developer", label: "GameplayDeveloper", agent: "GameplayDeveloper", detail: "Develop" },
  { id: "build", label: "build_gate", agent: "GameplayDeveloper", detail: "Typecheck/build" },
  { id: "playtester", label: "Playtester", agent: "Playtester", detail: "Browser test" },
  { id: "reviewer", label: "BugReviewer", agent: "BugReviewer", detail: "Review route" },
  { id: "finalize", label: "finalize_run", agent: "BugReviewer", detail: "Output" },
];

function renderFlow(nodeStates = {}) {
  adkFlow.innerHTML = flowNodes
    .map((node) => {
      const state = nodeStates[node.id] || "";
      return `
        <div class="flow-node ${state}">
          <div>
            <strong>${node.label}</strong>
            <em>${node.detail}</em>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderFlowUniform(state) {
  const nodeStates = {};
  for (const node of flowNodes) {
    nodeStates[node.id] = state ? `flow-${state}` : "";
  }
  renderFlow(nodeStates);
}

function renderFlowProgress(activeAgent, stage) {
  const stageMap = {
    DESIGNER: "designer",
    WORKSPACE: "workspace",
    DEPENDENCIES: "workspace",
    PLANNER: "planner",
    DEVELOPER: "developer",
    TYPECHECK: "build",
    BUILD: "build",
    PREVIEW: "playtester",
    PLAYTESTER: "playtester",
    REVIEWER: "reviewer",
    COMPLETE: "finalize",
    FAILED: "build",
  };

  const activeNodeId =
    stageMap[stage] ||
    flowNodes.find((node) => node.agent === activeAgent)?.id ||
    "designer";
  const activeIndex = flowNodes.findIndex((node) => node.id === activeNodeId);
  const nodeStates = {};

  flowNodes.forEach((node, index) => {
    if (index < activeIndex) {
      nodeStates[node.id] = "flow-ready";
    } else if (index === activeIndex) {
      nodeStates[node.id] = stage === "FAILED" ? "flow-error" : "flow-running";
    }
  });

  renderFlow(nodeStates);
}

function renderAgents(state = "ready", label = "Ready") {
  const itemClass = state ? `state-${state}` : "";
  const rail = agents
    .map(
      (agent, index) => `
        <div class="${itemClass}">
          <span>${index + 1}</span>
          <strong>${agent}</strong>
          <em>${label}</em>
        </div>
      `,
    )
    .join("");

  const list = agents
    .map(
      (agent, index) => `
        <li class="${itemClass}">
          <span>${index + 1}</span>
          <strong>${agent}</strong>
          <em>${label}</em>
        </li>
      `,
    )
    .join("");

  const evidence = agents
    .map(
      (agent) => `
        <li class="${state}">
          <span></span>
          ${agent}
          <em>${label}</em>
        </li>
      `,
    )
    .join("");

  workflowRail.innerHTML = rail;
  agentList.innerHTML = list;
  evidenceList.innerHTML = evidence;
  renderFlowUniform(state);
}

function renderAgentProgress(activeAgent, stage) {
  const activeIndex = agentIndex(activeAgent);
  const normalizedStage = stage && stage !== "Queued" ? stage : "STARTING";

  const itemFor = (agent, index, compact = false) => {
    let state = "";
    let label = "Queued";
    if (index < activeIndex) {
      state = "state-ready";
      label = "Done";
    } else if (index === activeIndex) {
      state = "state-running";
      label = compact ? "Active" : normalizedStage;
    }
    return { state, label };
  };

  workflowRail.innerHTML = agents
    .map((agent, index) => {
      const item = itemFor(agent, index);
      return `
        <div class="${item.state}">
          <span>${index + 1}</span>
          <strong>${agent}</strong>
          <em>${item.label}</em>
        </div>
      `;
    })
    .join("");

  agentList.innerHTML = agents
    .map((agent, index) => {
      const item = itemFor(agent, index, true);
      return `
        <li class="${item.state}">
          <span>${index + 1}</span>
          <strong>${agent}</strong>
          <em>${item.label}</em>
        </li>
      `;
    })
    .join("");

  evidenceList.innerHTML = agents
    .map((agent, index) => {
      const item = itemFor(agent, index, true);
      const evidenceState = item.state.replace("state-", "");
      return `
        <li class="${evidenceState}">
          <span></span>
          ${agent}
          <em>${item.label}</em>
        </li>
      `;
    })
    .join("");
  renderFlowProgress(activeAgent, normalizedStage);
}

function clearSelection(message = "No run selected") {
  selectedRunId = null;
  runTitle.textContent = message;
  runId.textContent = "No run selected";
  runUpdated.textContent = "";
  detailRunId.textContent = "None";
  detailStatus.textContent = "Waiting";
  detailAgent.textContent = "-";
  detailStage.textContent = "-";
  detailUpdated.textContent = "-";
  detailOutput.textContent = "-";
  gameFrame.removeAttribute("src");
  emptyState.classList.remove("hidden");
  setLinks(null);
  renderAgents("", "Waiting");
}

function selectRun(run) {
  selectedRunId = run.run_id;
  runTitle.textContent = run.title || run.run_id;
  runId.textContent = run.run_id;
  runUpdated.textContent = formatDate(run.updated_at);
  detailRunId.textContent = run.run_id;
  detailStatus.textContent = run.ready ? "Ready" : "Not built";
  detailAgent.textContent = run.ready ? "BugReviewer" : "-";
  detailStage.textContent = run.ready ? "COMPLETE" : "-";
  detailUpdated.textContent = formatDate(run.updated_at);
  detailOutput.textContent = run.ready ? "HTML5 game" : run.failure_reason || "Missing dist";
  setLinks(run);

  if (run.ready) {
    gameFrame.src = `${run.game_url}index.html?autostart=1&v=${Date.now()}`;
    emptyState.classList.add("hidden");
    setStatus("Ready", "ready");
    renderAgents("ready", "Ready");
  } else {
    gameFrame.removeAttribute("src");
    emptyState.classList.remove("hidden");
    setStatus(run.failure_reason || "Build output missing", "error");
    renderAgents("error", "Review");
  }

  document.querySelectorAll(".run-card").forEach((card) => {
    card.classList.toggle("selected", card.dataset.runId === selectedRunId);
  });
}

function renderRuns(runs) {
  runsList.innerHTML = "";
  const readyRuns = runs.filter((run) => run.ready);
  readyCount.textContent = `${readyRuns.length} ready`;
  totalCount.textContent = `${runs.length} total`;

  if (!runs.length) {
    runsList.innerHTML = `
      <button type="button" class="run-card" disabled>
        <strong>No generated runs</strong>
        <span>Waiting</span>
        <span>-</span>
        <span>-</span>
      </button>
    `;
    return;
  }

  for (const run of runs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "run-card";
    button.dataset.runId = run.run_id;
    button.innerHTML = `
      <strong>${escapeHtml(run.run_id)}</strong>
      <span class="status-label ${run.ready ? "ready" : "error"}">${run.ready ? "Ready" : "Not built"}</span>
      <span>${formatDate(run.updated_at)}</span>
      <span>${run.ready ? "Open" : escapeHtml(run.failure_reason || "Failed")}</span>
    `;
    button.addEventListener("click", () => selectRun(run));
    runsList.appendChild(button);
  }
}

async function loadRuns(selectLatest = true) {
  const response = await fetch("/api/runs");
  if (!response.ok) {
    throw new Error("Could not load runs");
  }

  const data = await response.json();
  renderRuns(data.runs);

  const latestReady = data.runs.find((run) => run.ready);
  const selected = data.runs.find((run) => run.run_id === selectedRunId);

  if (selected && !selectLatest) {
    selectRun(selected);
  } else if (selectLatest && latestReady) {
    selectRun(latestReady);
  } else if (!latestReady) {
    clearSelection("No built games yet");
    setStatus("No ready output", "error");
  }
}

async function pollJob() {
  if (!activeJobId) return;

  const response = await fetch(`/api/jobs/${activeJobId}`);
  if (!response.ok) {
    setStatus("Job status unavailable", "error");
    return;
  }

  const data = await response.json();
  const job = data.job;

  if (job.status === "running") {
    const currentAgent = job.current_agent || "GameDesigner";
    const currentStage = job.current_stage || "STARTING";
    setStatus(`${currentAgent}: ${currentStage}`, "running");
    detailStatus.textContent = "Building";
    detailRunId.textContent = job.run_id || "Pending";
    detailAgent.textContent = currentAgent;
    detailStage.textContent = currentStage;
    detailUpdated.textContent = formatDate(job.started_at);
    detailOutput.textContent = "Pending";
    renderAgentProgress(currentAgent, currentStage);
    return;
  }

  clearInterval(pollTimer);
  pollTimer = null;
  activeJobId = null;
  await loadRuns(false);

  if (job.run_id) {
    const runResponse = await fetch(`/api/runs/${job.run_id}`);
    if (runResponse.ok) {
      const run = await runResponse.json();
      selectRun(run);
      if (run.ready) {
        setStatus("Ready", "ready");
        detailStatus.textContent = "Ready";
        detailAgent.textContent = "BugReviewer";
        detailStage.textContent = "COMPLETE";
        detailOutput.textContent = "HTML5 game";
        renderAgents("ready", "Ready");
        return;
      }
      if (job.status !== "completed") {
        setStatus(job.error || "Build failed", "error");
        detailStatus.textContent = "Failed";
        detailAgent.textContent = job.current_agent || "GameplayDeveloper";
        detailStage.textContent = job.current_stage || "FAILED";
        detailOutput.textContent = "No built output";
        renderAgentProgress(job.current_agent || "GameplayDeveloper", job.current_stage || "FAILED");
      }
      return;
    }
  }

  setStatus(job.error || "Build did not produce ready output", "error");
  detailStatus.textContent = "Failed";
  detailAgent.textContent = job.current_agent || "GameplayDeveloper";
  detailStage.textContent = job.current_stage || "FAILED";
  detailOutput.textContent = "No built output";
  renderAgents("error", "Review");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;

  setStatus("Starting", "running");
  renderAgents("running", "Active");

  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, demo_mode: demoModeInput.checked }),
  });

  if (!response.ok) {
    setStatus("Build request failed", "error");
    renderAgents("error", "Review");
    return;
  }

  const data = await response.json();
  activeJobId = data.job.id;
  detailStatus.textContent = "Building";
  detailRunId.textContent = "Pending";
  detailAgent.textContent = "GameDesigner";
  detailStage.textContent = "Queued";
  detailUpdated.textContent = formatDate(data.job.started_at);
  detailOutput.textContent = "Pending";
  clearInterval(pollTimer);
  pollTimer = setInterval(pollJob, 3000);
  pollJob();
});

refreshButton.addEventListener("click", () => {
  loadRuns(false).catch((error) => {
    console.error(error);
    setStatus("Lab API is not reachable", "error");
  });
});

promptInput.addEventListener("input", updatePromptCount);

quickPrompts.forEach((button) => {
  button.addEventListener("click", () => {
    promptInput.value = button.dataset.prompt;
    updatePromptCount();
    promptInput.focus();
  });
});

updatePromptCount();
clearSelection();
loadRuns(false).catch((error) => {
  console.error(error);
  setStatus("Lab API is not reachable", "error");
});
