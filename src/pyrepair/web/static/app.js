const runList = document.querySelector("#run-list");
const status = document.querySelector("#run-status");

function show(value, fallback) {
  return value ? JSON.stringify(value, null, 2) : fallback;
}

function firstStepWith(run, field) {
  return (run.steps || []).find((step) => step[field]);
}

function selectRun(run) {
  const feedback = firstStepWith(run, "feedback");
  const patch = (run.steps || []).find((step) => step.tool_result?.patch_record);
  const guardrail = firstStepWith(run, "guardrail_decision");
  document.querySelector("#failure-summary").textContent = show(feedback?.feedback, "No failing test feedback recorded.");
  document.querySelector("#diff").textContent = patch?.tool_result?.patch_record?.diff || "No patch recorded.";
  document.querySelector("#guardrails").textContent = show(guardrail?.guardrail_decision, "No guardrail decision recorded.");
}

function renderRuns(runs) {
  runList.replaceChildren();
  if (!runs.length) {
    const empty = document.createElement("li");
    empty.textContent = "No demo runs yet.";
    runList.append(empty);
    return;
  }
  runs.slice().reverse().forEach((run) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.className = "run-item";
    button.textContent = `${run.status} | ${run.final_summary || run.id}`;
    button.addEventListener("click", () => selectRun(run));
    item.append(button);
    runList.append(item);
  });
}

async function refreshRuns() {
  const response = await fetch("/api/runs");
  renderRuns(await response.json());
}

document.querySelectorAll("[data-demo]").forEach((button) => {
  button.addEventListener("click", async () => {
    status.textContent = "Running deterministic demo...";
    const response = await fetch(`/api/demo/${button.dataset.demo}`, { method: "POST" });
    const run = await response.json();
    status.textContent = `Completed: ${run.status}`;
    await refreshRuns();
    selectRun(run);
  });
});

refreshRuns();
