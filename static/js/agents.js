/**
 * PreTwinShop AI - Agent Activity Controller
 */

let allAgentRuns = [];

async function loadAgentActivity() {
  const container = document.getElementById('agentLogsContainer');

  try {
    const data = await apiGet('/api/agent-runs');
    allAgentRuns = data.runs || [];

    populateRunSelector(allAgentRuns);
    renderPipelineStatus(allAgentRuns);
    renderAgentLogs(allAgentRuns);
  } catch (err) {
    console.error('Failed to load agent runs:', err);
    if (container) {
      container.innerHTML = `
        <div class="empty-state py-4 text-danger">
          <p>Failed to load agent traces: ${err.message}</p>
        </div>
      `;
    }
  }
}

function populateRunSelector(runs) {
  const select = document.getElementById('runSelect');
  if (!select) return;

  // Extract unique run_ids
  const runIds = [...new Set(runs.map((r) => r.run_id).filter(Boolean))];

  select.innerHTML = '<option value="">Latest Execution Run</option>' +
    runIds.map((id, idx) => `<option value="${id}">Run #${idx + 1} (${id.slice(0, 8)}...)</option>`).join('');
}

async function loadSelectedRun() {
  const select = document.getElementById('runSelect');
  if (!select) return;
  const runId = select.value;

  if (!runId) {
    renderPipelineStatus(allAgentRuns);
    renderAgentLogs(allAgentRuns);
    return;
  }

  try {
    const data = await apiGet(`/api/agent-runs?run_id=${encodeURIComponent(runId)}`);
    const filteredRuns = data.runs || [];
    renderPipelineStatus(filteredRuns);
    renderAgentLogs(filteredRuns);
  } catch (err) {
    showToast('Failed to filter by run ID', 'error');
  }
}

function renderPipelineStatus(runs) {
  const agents = ['A', 'B', 'C', 'D', 'E', 'F'];
  const agentMap = {
    A: 'ShoppingTwinAgent',
    B: 'PredictiveShoppingAgent',
    C: 'ProductDiscoveryAgent',
    D: 'ProductComparisonAgent',
    E: 'BudgetAwareRecommendationAgent',
    F: 'RecommendationExplanationAgent',
  };

  agents.forEach((letter) => {
    const name = agentMap[letter];
    const match = runs.find((r) => r.agent_name === name);
    const stepEl = document.getElementById(`step-${letter}`);
    const timingEl = document.getElementById(`timing-${letter}`);

    if (stepEl && match) {
      const circle = stepEl.querySelector('.step-circle');
      if (circle) {
        circle.className = `step-circle ${match.status === 'success' ? 'success' : 'error'}`;
      }
    }
    if (timingEl) {
      timingEl.textContent = match && match.execution_time_ms ? `${match.execution_time_ms}ms` : '<10ms';
    }
  });
}

function renderAgentLogs(runs) {
  const container = document.getElementById('agentLogsContainer');
  if (!container) return;

  if (runs.length === 0) {
    container.innerHTML = `
      <div class="empty-state py-5 w-100">
        <span class="empty-icon">🤖</span>
        <h4>No Agent Executions Recorded</h4>
        <p>Run the AI analysis pipeline to execute the 6 specialized shopping agents and inspect their live telemetry.</p>
        <button class="btn btn-primary mt-2" onclick="triggerGlobalAiRun()">Execute Multi-Agent Pipeline</button>
      </div>
    `;
    return;
  }

  container.innerHTML = runs.map((run) => {
    const isSuccess = run.status === 'success';
    const statusBadge = isSuccess ? 'badge-success' : 'badge-danger';
    const timeMs = run.execution_time_ms ? `${run.execution_time_ms}ms` : '<10ms';
    const created = formatDate(run.created_at);

    return `
      <div class="agent-card">
        <div class="agent-card-header">
          <div class="flex-align-gap">
            <span class="agent-avatar-pill">🤖</span>
            <div>
              <h4 class="agent-name">${run.agent_name}</h4>
              <span class="agent-task text-muted text-sm">${run.task || 'Autonomous pipeline subtask'}</span>
            </div>
          </div>
          <div class="agent-meta">
            <span class="badge ${statusBadge}">${run.status.toUpperCase()}</span>
            <span class="agent-timing">${timeMs}</span>
          </div>
        </div>

        <div class="agent-card-body">
          <div class="agent-summary-row">
            <strong class="text-sm">Input Summary:</strong>
            <p class="text-sm text-muted">${run.input_summary || 'Profile / state arguments received'}</p>
          </div>
          <div class="agent-summary-row mt-2">
            <strong class="text-sm">Output Summary:</strong>
            <p class="text-sm text-secondary">${run.output_summary || 'Task completed successfully'}</p>
          </div>
          ${run.error_message ? `
            <div class="agent-error-box mt-2 text-danger text-sm">
              <strong>Error Trace:</strong> ${run.error_message}
            </div>
          ` : ''}
        </div>

        <div class="agent-card-footer">
          <span class="text-xs text-muted">Run ID: <code>${(run.run_id || '').slice(0, 12)}...</code></span>
          <span class="text-xs text-muted">${created}</span>
        </div>
      </div>
    `;
  }).join('');
}

function refreshAgentRuns() {
  showToast('Refreshing agent audit traces...', 'info');
  loadAgentActivity();
}

let currentActiveTaskId = null;

async function planAutonomousTask() {
  const goalInput = document.getElementById("agentTaskGoalInput");
  const budgetInput = document.getElementById("agentTaskBudgetInput");
  const goal = (goalInput ? goalInput.value : "").trim();
  const budget = parseFloat(budgetInput ? budgetInput.value : 10000);

  if (!goal) {
    alert("Please enter a shopping goal");
    return;
  }

  try {
    const res = await fetch("/api/agents/plan-task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, budget })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    currentActiveTaskId = data.task_id;

    // Display container
    const container = document.getElementById("activeTaskContainer");
    if (container) container.style.display = "block";

    document.getElementById("taskTitleDisplay").innerText = `Autonomous Plan: "${data.goal}" (Est: ₹${Math.round(data.total_estimated_cost).toLocaleString("en-IN")})`;

    // Steps
    const stepsBox = document.getElementById("taskStepsContainer");
    stepsBox.innerHTML = (data.steps || []).map(s => {
      const isPending = s.status === "pending_approval";
      return `
        <div style="background:#0f172a; border-left:3px solid ${isPending ? '#f59e0b' : '#10b981'}; padding:10px 14px; border-radius:4px; font-size:0.85rem;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:${isPending ? '#fbbf24' : '#f1f5f9'};">Step ${s.step_number}: ${s.title}</strong>
            <span style="font-size:0.75rem; color:${isPending ? '#fbbf24' : '#10b981'}; font-weight:700;">${isPending ? 'CHECKPOINT' : 'DONE'}</span>
          </div>
          <div style="color:#94a3b8; font-size:0.8rem; margin-top:4px;">${s.details}</div>
        </div>
      `;
    }).join("");

    // Items
    const itemsBox = document.getElementById("taskItemsContainer");
    itemsBox.innerHTML = (data.proposed_items || []).map(item => `
      <div style="background:#0f172a; border:1px solid #334155; border-radius:6px; padding:10px; display:flex; align-items:center; gap:10px;">
        ${item.image_url ? `<img src="${item.image_url}" style="width:40px; height:40px; object-fit:contain; border-radius:4px; background:#fff; padding:2px;">` : ""}
        <div>
          <div style="font-weight:600; color:#f1f5f9; font-size:0.85rem;">${item.name}</div>
          <div style="color:#10b981; font-weight:700; font-size:0.8rem;">₹${Math.round(item.price).toLocaleString("en-IN")}</div>
        </div>
      </div>
    `).join("");

    // Scroll to container
    container.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    alert("Task planning failed: " + err.message);
  }
}

async function approveCurrentTask() {
  if (!currentActiveTaskId) return;

  try {
    const res = await fetch(`/api/agents/approve-task/${currentActiveTaskId}`, {
      method: "POST"
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    // Update status badge
    const badge = document.getElementById("taskStatusBadge");
    if (badge) {
      badge.innerText = "COMPLETED & APPROVED";
      badge.style.background = "#10b981";
    }

    const strip = document.getElementById("approvalActionStrip");
    if (strip) {
      strip.innerHTML = `
        <div style="color:#10b981; font-weight:700; font-size:0.95rem;">
          ✓ Task Authorized by User! Autonomous execution completed.
        </div>
      `;
    }

    // Add items to local cart
    const items = data.items || [];
    let cart = [];
    try {
      cart = JSON.parse(localStorage.getItem("pretwin_cart") || "[]");
    } catch (e) {
      cart = [];
    }
    items.forEach(it => {
      cart.push({
        id: it.id,
        name: it.name,
        price: it.price,
        quantity: 1,
        category: it.category,
        image_url: it.image_url
      });
    });
    localStorage.setItem("pretwin_cart", JSON.stringify(cart));

    if (typeof showToast === "function") {
      showToast("Items added to your Smart Cart!", "success");
    }
  } catch (err) {
    alert("Approval error: " + err.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadAgentActivity();
});
