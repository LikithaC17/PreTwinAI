/**
 * budget.js
 * Handles Budget & Price Intelligence dashboard, interactive 60-day price history chart,
 * price drop alert management, and AI buy vs wait recommendations.
 */

let priceChart = null;
let currentSelectedProductId = 1;

document.addEventListener("DOMContentLoaded", () => {
  loadBudgetOverview();
  loadProductPriceHistory(currentSelectedProductId);
});

async function loadBudgetOverview() {
  try {
    const res = await fetch("/api/budget/overview");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load budget data");

    // Monthly budget stats
    document.getElementById("monthlySpent").innerText = Math.round(data.monthly_spent).toLocaleString("en-IN");
    document.getElementById("budgetMax").innerText = Math.round(data.budget_max).toLocaleString("en-IN");
    document.getElementById("budgetRemaining").innerText = Math.round(data.budget_remaining).toLocaleString("en-IN");

    const percent = Math.min(100, Math.round(data.budget_used_percentage));
    document.getElementById("budgetSpentPercent").innerText = `${percent}%`;
    const bar = document.getElementById("budgetProgressBar");
    bar.style.width = `${percent}%`;

    const badge = document.getElementById("budgetHealthBadge");
    if (percent < 75) {
      badge.innerText = "Healthy";
      badge.style.background = "#10b981";
      bar.style.background = "linear-gradient(90deg, #6366f1, #10b981)";
    } else if (percent < 90) {
      badge.innerText = "Attention";
      badge.style.background = "#f59e0b";
      bar.style.background = "linear-gradient(90deg, #6366f1, #f59e0b)";
    } else {
      badge.innerText = "Limit Reached";
      badge.style.background = "#ef4444";
      bar.style.background = "linear-gradient(90deg, #f59e0b, #ef4444)";
    }

    // Counts
    document.getElementById("totalTrackedCount").innerText = data.total_tracked || 0;
    document.getElementById("activeDropsCount").innerText = `${data.active_price_drops || 0} drops reached`;

    // Calculate total savings
    let totalSavings = 0;
    if (data.tracked_items && data.tracked_items.length > 0) {
      data.tracked_items.forEach(item => {
        if (item.savings_amount) totalSavings += item.savings_amount;
      });
    }
    document.getElementById("unlockedSavings").innerText = Math.round(totalSavings).toLocaleString("en-IN");

    // Render tracked table
    renderTrackedTable(data.tracked_items || []);
  } catch (err) {
    console.error("Budget overview error:", err);
  }
}

function renderTrackedTable(items) {
  const tbody = document.getElementById("trackedTableBody");
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="padding:28px; text-align:center; color:#94a3b8;">
          No products currently tracked. Select any product above to start monitoring price drops!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const isReached = item.is_drop_reached;
    return `
      <tr style="border-bottom:1px solid #1e293b; transition:background 0.2s ease;">
        <td style="padding:12px 14px; font-weight:600; color:#f1f5f9;">
          <div style="display:flex; align-items:center; gap:10px;">
            ${item.image_url ? `<img src="${item.image_url}" style="width:36px; height:36px; object-fit:contain; border-radius:6px; background:#fff; padding:2px;">` : ""}
            <span>${item.name || "Product #" + item.product_id}</span>
          </div>
        </td>
        <td style="padding:12px 14px; color:#94a3b8;">${item.category || "General"}</td>
        <td style="padding:12px 14px; color:#22d3ee; font-weight:600;">₹${Math.round(item.target_price).toLocaleString("en-IN")}</td>
        <td style="padding:12px 14px; color:#f1f5f9; font-weight:600;">₹${Math.round(item.current_price).toLocaleString("en-IN")}</td>
        <td style="padding:12px 14px;">
          ${isReached
            ? `<span style="background:rgba(16, 185, 129, 0.2); color:#10b981; border:1px solid #10b981; padding:3px 8px; border-radius:6px; font-size:0.75rem; font-weight:700;">🎯 TARGET REACHED (-₹${Math.round(item.savings_amount)})</span>`
            : `<span style="background:rgba(148, 163, 184, 0.15); color:#94a3b8; padding:3px 8px; border-radius:6px; font-size:0.75rem;">Monitoring</span>`
          }
        </td>
        <td style="padding:12px 14px;">
          <div style="display:flex; gap:8px;">
            <button onclick="untrackProduct(${item.product_id})" style="background:transparent; border:1px solid #475569; color:#94a3b8; padding:4px 8px; border-radius:6px; cursor:pointer; font-size:0.8rem;">
              Remove
            </button>
            ${isReached ? `<a href="/discovery" style="background:#10b981; color:#fff; text-decoration:none; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:600;">Buy</a>` : ""}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

async function loadProductPriceHistory(productId) {
  try {
    currentSelectedProductId = productId;
    const res = await fetch(`/api/products/${productId}/price-history`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load price history");

    // Populate Stats
    document.getElementById("statLowest").innerText = Math.round(data.lowest_price).toLocaleString("en-IN");
    document.getElementById("statAverage").innerText = Math.round(data.average_price).toLocaleString("en-IN");
    document.getElementById("statHighest").innerText = Math.round(data.highest_price).toLocaleString("en-IN");

    // Populate Advisor
    const badge = document.getElementById("advisorBadge");
    badge.innerText = data.decision;
    if (data.decision === "BUY NOW") {
      badge.style.background = "#10b981";
    } else if (data.decision === "FAIR DEAL") {
      badge.style.background = "#6366f1";
    } else {
      badge.style.background = "#f59e0b";
    }

    document.getElementById("advisorTitle").innerText = `Recommendation: ${data.decision}`;
    document.getElementById("advisorReason").innerText = data.advice;

    // Render Chart
    renderPriceChart(data.history);
  } catch (err) {
    console.error("Price history load error:", err);
  }
}

function renderPriceChart(history) {
  const ctx = document.getElementById("priceHistoryChart");
  if (!ctx) return;

  const labels = history.map(h => h.date);
  const dataPoints = history.map(h => h.price);

  if (priceChart) {
    priceChart.destroy();
  }

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Price (₹)",
        data: dataPoints,
        borderColor: "#a855f7",
        backgroundColor: "rgba(168, 85, 247, 0.12)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: "#c084fc",
        pointBorderColor: "#fff",
        pointRadius: 3,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f172a",
          titleColor: "#f1f5f9",
          bodyColor: "#c084fc",
          callbacks: {
            label: function(context) {
              return ` Price: ₹${context.parsed.y.toLocaleString("en-IN")}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", maxTicksLimit: 8 }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            callback: function(val) { return `₹${val.toLocaleString("en-IN")}`; }
          }
        }
      }
    }
  });
}

async function trackCurrentProduct() {
  const select = document.getElementById("priceHistoryProductSelect");
  const pid = select.value;
  try {
    const res = await fetch("/api/budget/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: pid })
    });
    const data = await res.json();
    if (res.ok) {
      if (typeof showToast === "function") {
        showToast(data.message, "success");
      } else {
        alert(data.message);
      }
      loadBudgetOverview();
    } else {
      alert(data.error || "Failed to track product");
    }
  } catch (err) {
    alert("Tracking failed: " + err.message);
  }
}

async function untrackProduct(productId) {
  try {
    const res = await fetch(`/api/budget/track/${productId}`, { method: "DELETE" });
    if (res.ok) {
      loadBudgetOverview();
    }
  } catch (err) {
    console.error("Untrack error:", err);
  }
}
