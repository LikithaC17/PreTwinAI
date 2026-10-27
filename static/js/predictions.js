/**
 * PreTwinShop AI - Predictive Shopping Intelligence Controller (Agent B)
 */

let allPredictions = [];
let activeConfidenceFilter = 'all';

async function loadPredictions() {
  const grid = document.getElementById('predictionsGrid');
  const countEl = document.getElementById('predCount');

  try {
    const data = await apiGet('/api/predictions');
    allPredictions = data.predictions || [];

    if (countEl) countEl.textContent = allPredictions.length;
    renderPredictions();
    renderUpcomingNeedsTimeline();
    await loadSeasonalSuggestions();
  } catch (err) {
    console.error('Failed to load predictions:', err);
    if (grid) {
      grid.innerHTML = `
        <div class="empty-state py-4 w-100" style="text-align:center; padding:30px; grid-column:1/-1;">
          <p class="text-danger" style="color:#ef4444;">Failed to load predictions. Please try regenerating.</p>
          <button class="btn btn-sm btn-primary mt-2" onclick="generateNewPredictions()">Generate Predictions</button>
        </div>
      `;
    }
  }
}

function filterPredictions(filter) {
  activeConfidenceFilter = filter;

  // Update pills styling
  const pills = document.querySelectorAll('#predFilterPills .pill');
  pills.forEach((p) => {
    if (p.textContent.toLowerCase().includes(filter.toLowerCase())) {
      p.style.borderColor = '#6366f1';
      p.style.background = 'rgba(99,102,241,0.2)';
      p.style.color = '#c4b5fd';
    } else {
      p.style.borderColor = '#334155';
      p.style.background = '#1e293b';
      p.style.color = '#94a3b8';
    }
  });

  renderPredictions();
}

/**
 * Render Upcoming Needs Timeline Cards
 */
function renderUpcomingNeedsTimeline() {
  const timeline = document.getElementById('upcomingNeedsTimeline');
  if (!timeline) return;

  if (allPredictions.length === 0) {
    timeline.innerHTML = `
      <div style="grid-column:1/-1; text-align:center; padding:24px; color:#64748b;">
        No timeline forecasts currently available. Click "Generate Fresh Predictions" above.
      </div>
    `;
    return;
  }

  // Build timeline sorted by confidence / urgency
  const sorted = [...allPredictions].sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));

  timeline.innerHTML = sorted.slice(0, 3).map((p, idx) => {
    const score = Math.round((p.confidence_score || 0.6) * 100);
    const scoreColor = score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#94a3b8';
    const category = p.predicted_category || 'General';
    const product = p.predicted_product || category;
    const timeframe = p.estimated_timeframe || (idx === 0 ? 'Within 3-7 days' : idx === 1 ? 'In 2-3 weeks' : 'Next month');
    const badgeLabel = idx === 0 ? '⚡ Immediate Replenishment' : idx === 1 ? '⏳ Near Term Need' : '📅 Forward Horizon';

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:18px; display:flex; flex-direction:column; justify-content:space-between; position:relative;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:0.75rem; font-weight:700; color:#38bdf8; background:rgba(56,189,248,0.15); padding:2px 8px; border-radius:10px; border:1px solid rgba(56,189,248,0.3);">
              ${badgeLabel}
            </span>
            <span style="font-size:0.75rem; font-weight:700; color:${scoreColor};">
              ● ${score}% Certainty
            </span>
          </div>

          <h4 style="margin:0 0 6px 0; color:#f1f5f9; font-size:1.05rem; font-weight:700;">
            ${product}
          </h4>
          <div style="font-size:0.8rem; color:#c4b5fd; margin-bottom:8px;">
            ${category} • Target Window: <strong>${timeframe}</strong>
          </div>

          <!-- Transparent Explanation -->
          <div style="background:#0f172a; border-left:3px solid #6366f1; padding:8px 10px; border-radius:0 6px 6px 0; font-size:0.75rem; color:#cbd5e1; margin-bottom:14px; line-height:1.4;">
            <strong style="color:#a855f7;">Heuristic Reason:</strong> ${p.reason || 'Calculated from voluntary purchase velocity and category cadence.'}
          </div>
        </div>

        <!-- Direct Recommendation Link -->
        <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #334155; padding-top:12px; margin-top:8px;">
          <span style="font-size:0.75rem; color:#94a3b8;">${p.recommended_action || 'Review matched options'}</span>
          <a href="/discovery?category=${encodeURIComponent(category)}" style="background:linear-gradient(135deg, #6366f1, #a855f7); color:#fff; text-decoration:none; padding:6px 12px; border-radius:6px; font-size:0.8rem; font-weight:600; display:inline-flex; align-items:center; gap:4px;">
            Shop ${category} ➔
          </a>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Render All Predictions Grid
 */
function renderPredictions() {
  const grid = document.getElementById('predictionsGrid');
  if (!grid) return;

  let filtered = allPredictions;
  if (activeConfidenceFilter === 'High') {
    filtered = allPredictions.filter((p) => (p.confidence_score || 0) >= 0.7);
  } else if (activeConfidenceFilter === 'Medium') {
    filtered = allPredictions.filter((p) => (p.confidence_score || 0) >= 0.5 && (p.confidence_score || 0) < 0.7);
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-state py-5 w-100" style="text-align:center; padding:30px; grid-column:1/-1;">
        <span class="empty-icon" style="font-size:2rem; display:block; margin-bottom:8px;">🔮</span>
        <h4 style="color:#f1f5f9; margin:0 0 6px;">No Predictions in this View</h4>
        <p style="color:#94a3b8; font-size:0.85rem;">No predicted shopping needs match your current filter. Generate fresh predictions to re-analyze your profile.</p>
        <button class="btn btn-primary mt-2" onclick="generateNewPredictions()" style="background:#6366f1; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-size:0.85rem; cursor:pointer;">Generate Fresh Predictions</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map((p, idx) => {
    const score = Math.round((p.confidence_score || 0.6) * 100);
    const scoreClass = score >= 70 ? 'badge-success' : score >= 50 ? 'badge-warning' : 'badge-secondary';
    const category = p.predicted_category || 'General';
    const productName = p.predicted_product || category;
    const ruleReason = p.reason || 'Pattern observed in voluntary purchase history.';
    const timeframe = p.estimated_timeframe || 'Within 1-3 weeks';
    const action = p.recommended_action || 'Review candidate items';

    return `
      <div class="prediction-card" style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:18px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <div class="prediction-card-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span class="category-pill" style="font-size:0.75rem; background:rgba(99,102,241,0.15); color:#c4b5fd; padding:2px 8px; border-radius:10px; border:1px solid rgba(99,102,241,0.3);">${category}</span>
            <span class="badge ${scoreClass}" style="font-size:0.75rem; padding:2px 8px; border-radius:10px;">${score}% Confidence</span>
          </div>

          <div class="prediction-card-body">
            <h4 class="pred-title" style="margin:0 0 8px 0; color:#f1f5f9; font-size:1rem; font-weight:700;">${productName}</h4>
            <p class="pred-reason" style="margin:0 0 12px 0; color:#cbd5e1; font-size:0.85rem; line-height:1.4;">${ruleReason}</p>

            <div class="pred-meta-grid" style="background:#0f172a; padding:10px; border-radius:8px; font-size:0.75rem; color:#94a3b8; display:grid; gap:4px; margin-bottom:12px;">
              <div><strong style="color:#cbd5e1;">⏱️ Timeframe:</strong> ${timeframe}</div>
              <div><strong style="color:#cbd5e1;">💡 Suggested Action:</strong> ${action}</div>
            </div>
          </div>
        </div>

        <div class="prediction-card-footer" style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #334155; padding-top:12px; margin-top:8px;">
          <button class="btn btn-sm btn-outline-danger" onclick="dismissPrediction(${idx})" style="background:transparent; border:1px solid #ef4444; color:#ef4444; padding:4px 10px; border-radius:6px; font-size:0.75rem; cursor:pointer;">Dismiss</button>
          <a href="/discovery?category=${encodeURIComponent(category)}" class="btn btn-sm btn-primary" style="background:#6366f1; color:#fff; text-decoration:none; padding:5px 12px; border-radius:6px; font-size:0.8rem; font-weight:600;">
            Find Products ➔
          </a>
        </div>
      </div>
    `;
  }).join('');
}

function dismissPrediction(idx) {
  allPredictions.splice(idx, 1);
  const countEl = document.getElementById('predCount');
  if (countEl) countEl.textContent = allPredictions.length;
  renderPredictions();
  renderUpcomingNeedsTimeline();
  showToast('Prediction dismissed', 'info');
}

async function generateNewPredictions() {
  showToast('Agent B generating predictive needs...', 'info');
  try {
    await apiPost('/api/predictions');
    showToast('Fresh predictions generated!', 'success');
    await loadPredictions();
  } catch (err) {
    showToast(`Failed to generate predictions: ${err.message}`, 'error');
  }
}

/**
 * Seasonal & Event Intelligence Suggestions
 */
async function loadSeasonalSuggestions() {
  const container = document.getElementById('seasonalSuggestionsGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/products?limit=16');
    const data = await res.json();
    const products = data.products || [];

    // Select 4 varied seasonal picks
    const seasonalPicks = products.slice(0, 4);

    if (seasonalPicks.length === 0) {
      container.innerHTML = `<div style="grid-column:1/-1; color:#94a3b8; font-size:0.85rem; text-align:center;">No seasonal opportunities at this time.</div>`;
      return;
    }

    container.innerHTML = seasonalPicks.map((p, idx) => {
      const occasion = idx === 0 ? "☀️ Summer Tech & Hydration" : idx === 1 ? "🏃 Health & Fitness Cycle" : idx === 2 ? "💼 Workstation Efficiency" : "🏡 Home Comfort Upgrade";
      return `
        <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; display:flex; flex-direction:column; justify-content:space-between; position:relative;" id="seasonalCard-${p.id}">
          <button onclick="dismissSeasonalCard(${p.id})" style="position:absolute; top:8px; right:8px; background:rgba(15,23,42,0.6); border:none; color:#94a3b8; width:24px; height:24px; border-radius:50%; font-size:12px; cursor:pointer;" title="Dismiss">✕</button>

          <div>
            <div style="font-size:0.75rem; color:#f59e0b; font-weight:700; margin-bottom:6px;">
              ${occasion}
            </div>
            <div style="height:100px; background:#fff; border-radius:6px; overflow:hidden; display:flex; align-items:center; justify-content:center; margin-bottom:10px;">
              <img src="${p.image_url || '/static/images/placeholder.png'}" alt="${p.name}" style="max-height:100%; max-width:100%; object-fit:contain;">
            </div>
            <div style="font-size:0.85rem; font-weight:600; color:#f1f5f9; height:34px; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">
              ${p.name}
            </div>
            <div style="font-size:1rem; font-weight:700; color:#38bdf8; margin:6px 0;">
              ₹${Math.round(p.price).toLocaleString('en-IN')}
            </div>
          </div>

          <div style="display:flex; gap:8px; margin-top:8px;">
            <button onclick="addToCartById(${p.id})" style="flex:1; background:linear-gradient(135deg, #6366f1, #a855f7); color:#fff; border:none; padding:7px; border-radius:6px; font-size:0.75rem; font-weight:600; cursor:pointer;">
              🛒 Quick Add
            </button>
            <button onclick="toggleWishlistById(${p.id})" style="background:#0f172a; border:1px solid #475569; color:#f87171; padding:7px 10px; border-radius:6px; cursor:pointer; font-size:0.8rem;">
              ❤️
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div style="grid-column:1/-1; color:#ef4444; font-size:0.85rem;">Failed to load seasonal picks: ${e.message}</div>`;
  }
}

function dismissSeasonalCard(id) {
  const card = document.getElementById(`seasonalCard-${id}`);
  if (card) {
    card.style.opacity = '0';
    setTimeout(() => card.remove(), 200);
  }
  showToast('Seasonal suggestion dismissed', 'info');
}

/**
 * Replenishment Reminders
 */
async function loadReminders() {
  const container = document.getElementById("remindersContainer");
  if (!container) return;

  try {
    const res = await fetch("/api/predictions/reminders");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const items = data.reminders || [];
    if (items.length === 0) {
      container.innerHTML = `<div style="grid-column:1/-1; color:#94a3b8; font-size:0.85rem;">No active replenishment schedules. Add a recurring schedule above!</div>`;
      return;
    }

    container.innerHTML = items.map(r => {
      let badgeBg = "rgba(16, 185, 129, 0.2)";
      let badgeColor = "#10b981";
      if (r.urgency === "overdue") {
        badgeBg = "rgba(239, 68, 68, 0.2)";
        badgeColor = "#ef4444";
      } else if (r.urgency === "urgent") {
        badgeBg = "rgba(245, 158, 11, 0.2)";
        badgeColor = "#f59e0b";
      }

      return `
        <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-weight:600; color:#f1f5f9; font-size:0.9rem;">${r.title}</div>
            <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">
              ${r.category} • Every ${r.estimated_cycle_days} days
            </div>
            <div style="font-size:0.75rem; font-weight:700; color:${badgeColor}; margin-top:4px;">
              ${r.urgency_label} (${r.next_reminder_date})
            </div>
          </div>
          <div style="display:flex; flex-direction:column; gap:4px;">
            <button onclick="updateReminderStatus(${r.id}, 'completed')" style="background:#10b981; color:#fff; border:none; padding:4px 8px; border-radius:4px; font-size:0.75rem; font-weight:600; cursor:pointer;">
              ✓ Reordered
            </button>
            <button onclick="updateReminderStatus(${r.id}, 'snoozed')" style="background:transparent; color:#94a3b8; border:1px solid #475569; padding:3px 8px; border-radius:4px; font-size:0.7rem; cursor:pointer;">
              Snooze 7d
            </button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div style="grid-column:1/-1; color:#ef4444; font-size:0.85rem;">Failed to load reminders: ${err.message}</div>`;
  }
}

async function updateReminderStatus(id, status) {
  try {
    const res = await fetch(`/api/predictions/reminders/${id}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: status, snooze_days: 7 })
    });
    if (res.ok) {
      if (typeof showToast === "function") {
        showToast(status === 'completed' ? 'Replenishment marked as reordered!' : 'Reminder snoozed 7 days', 'success');
      }
      loadReminders();
    }
  } catch (err) {
    alert("Error updating reminder: " + err.message);
  }
}

function openAddReminderPrompt() {
  const title = prompt("Reminder Title (e.g. Arabica Coffee Beans, Vitamin D Capsules, Hair Serum):");
  if (!title) return;
  const cycle = prompt("Replenishment cycle in days (e.g. 15, 30, 45):", "30");
  if (!cycle) return;

  fetch("/api/predictions/reminders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: title,
      category: "Everyday Consumables",
      estimated_cycle_days: parseInt(cycle) || 30
    })
  }).then(r => r.json()).then(data => {
    loadReminders();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadPredictions();
  loadReminders();
});
