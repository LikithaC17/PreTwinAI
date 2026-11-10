/**
 * static/js/budget.js
 * ====================
 * PreTwin AI Budget and Price Intelligence Controller
 * Powers the 7 Main Sections:
 * 1. My Shopping Budget (Creation, Periods, Categories, Reset, History)
 * 2. My Spending Overview (Eligible Purchases, AOV, Date Filters, Monthly Trend)
 * 3. Category-wise Budget Tracking (Allocations, Real Spend, Progress, Overspending Alerts)
 * 4. Price Intelligence (Selling Price, MRP, Unit Economics, 60-day Chart, Alternatives, Drop Tracking)
 * 5. Smart Savings Planner (Integration with Savings Plans, Contributions, Cadence, Estimated Completion)
 * 6. Purchase Affordability (Pre-checkout Simulator, Cart Impact, Non-blocking Advice)
 * 7. Budget Insights & Alerts (Pace, Limit Warnings, Savings Opportunities)
 */

let priceChart = null;
let currentSelectedProductId = 1;
let currentActiveBudget = null;
let affordabilityDebounceTimer = null;

const CATALOGUE_CATEGORIES = [
  "Fashion", "Mobiles", "Electronics", "Laptops & Computers", "Home & Kitchen",
  "Appliances", "Beauty, Toys & More", "Toys & Baby Products", "Food & Grocery",
  "Sports & Fitness", "Books & Stationery", "Furniture", "Footwear",
  "Watches & Accessories", "TVs & Home Entertainment", "Personal Care",
  "Automotive Accessories", "Health & Wellness", "Pet Supplies", "Travel & Luggage"
];

document.addEventListener("DOMContentLoaded", () => {
  initBudgetDashboard();
});

async function initBudgetDashboard() {
  await loadBudgetOverview();
  await populateProductSelect();
  await loadProductPriceHistory(currentSelectedProductId);
  await loadCategoryTracking();
  await loadSavingsPlans();
  await syncLiveCartAffordability();
  await loadBudgetInsights();
  await loadBudgetHistory();
}

// =========================================================================
// SECTION NAVIGATION CONTROLLER
// =========================================================================

function switchBudgetSection(sectionId, btnEl) {
  document.querySelectorAll(".budget-section-panel").forEach(p => {
    p.style.display = "none";
  });
  document.querySelectorAll(".budget-nav-btn").forEach(b => {
    b.classList.remove("active");
  });

  const target = document.getElementById(sectionId);
  if (target) {
    target.style.display = "block";
  }
  if (btnEl) {
    btnEl.classList.add("active");
  }

  // If opening Price Intelligence and chart exists, trigger resize
  if (sectionId === "budget-section-pricing" && priceChart) {
    setTimeout(() => { priceChart.resize(); }, 150);
  }
}

// =========================================================================
// SECTION 1: MY SHOPPING BUDGET
// =========================================================================

async function loadBudgetOverview() {
  try {
    const res = await fetch("/api/budget/overview");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to load budget data");

    currentActiveBudget = data;

    // Top summary
    const remaining = Math.round(data.budget_remaining || 0);
    const spent = Math.round(data.monthly_spent || 0);
    const maxB = Math.round(data.budget_max || 0);
    const percent = Math.min(100, Math.round(data.budget_used_percentage || 0));

    const remEl = document.getElementById("budgetRemaining");
    if (remEl) remEl.innerText = remaining.toLocaleString("en-IN");

    const remCardEl = document.getElementById("budgetRemainingCard");
    if (remCardEl) remCardEl.innerText = remaining.toLocaleString("en-IN");

    const spentEl = document.getElementById("monthlySpent");
    if (spentEl) spentEl.innerText = spent.toLocaleString("en-IN");

    const maxEl = document.getElementById("budgetMax");
    if (maxEl) maxEl.innerText = maxB.toLocaleString("en-IN");

    const pctEl = document.getElementById("budgetSpentPercent");
    if (pctEl) pctEl.innerText = `${percent}%`;

    const targetEl = document.getElementById("budgetProgressTarget");
    if (targetEl) targetEl.innerText = maxB.toLocaleString("en-IN");

    const bar = document.getElementById("budgetProgressBar");
    if (bar) bar.style.width = `${percent}%`;

    // Health Badge
    const healthBadge = document.getElementById("budgetHealthBadge");
    const healthStatus = document.getElementById("budgetHealthStatus");
    if (data.budget_health === "Healthy") {
      if (healthBadge) {
        healthBadge.innerText = "Healthy";
        healthBadge.style.background = "#D1FAE5";
        healthBadge.style.color = "#065F46";
        healthBadge.style.borderColor = "#A7F3D0";
      }
      if (healthStatus) {
        healthStatus.innerText = "Healthy Pace";
        healthStatus.style.color = "#10b981";
      }
    } else if (data.budget_health === "Attention") {
      if (healthBadge) {
        healthBadge.innerText = "Attention Needed";
        healthBadge.style.background = "#FEF3C7";
        healthBadge.style.color = "#92400E";
        healthBadge.style.borderColor = "#FDE68A";
      }
      if (healthStatus) {
        healthStatus.innerText = "Approaching Limit";
        healthStatus.color = "#f59e0b";
      }
    } else {
      if (healthBadge) {
        healthBadge.innerText = "Limit Reached";
        healthBadge.style.background = "#FEE2E2";
        healthBadge.style.color = "#991B1B";
        healthBadge.style.borderColor = "#FECACA";
      }
      if (healthStatus) {
        healthStatus.innerText = "Budget Exceeded";
        healthStatus.style.color = "#ef4444";
      }
    }

    // Period dates
    const datesEl = document.getElementById("budgetPeriodDates");
    if (datesEl && data.period_start && data.period_end) {
      datesEl.innerText = `Period: ${data.period_start} to ${data.period_end}`;
    }

    const periodBadge = document.getElementById("budgetPeriodBadge");
    if (periodBadge) {
      const pType = (data.budget_period || "Monthly").toUpperCase();
      periodBadge.innerText = `Period: ${pType}`;
    }

    // First time setup banner check
    const banner = document.getElementById("firstTimeBudgetBanner");
    if (banner) {
      banner.style.display = data.has_budget ? "none" : "block";
    }

    // Counts for price drops
    const totalTracked = document.getElementById("totalTrackedCount");
    if (totalTracked) totalTracked.innerText = data.total_tracked || 0;

    const activeDrops = document.getElementById("activeDropsCount");
    if (activeDrops) activeDrops.innerText = `${data.active_price_drops || 0} drops reached`;

    // Calculate total unlocked savings
    let totalSavings = 0;
    if (data.tracked_items && data.tracked_items.length > 0) {
      data.tracked_items.forEach(item => {
        if (item.savings_amount) totalSavings += item.savings_amount;
      });
    }
    const savingsEl = document.getElementById("unlockedSavings");
    if (savingsEl) savingsEl.innerText = Math.round(totalSavings).toLocaleString("en-IN");

    renderTrackedTable(data.tracked_items || []);
  } catch (err) {
    console.warn("Failed to load budget overview:", err);
  }
}

async function loadBudgetHistory() {
  const tbody = document.getElementById("budgetHistoryTableBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/budget/history");
    const data = await res.json();
    const history = data.history || [];

    if (!history.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="padding: 24px; text-align: center; color: #81778E;">
            No historical budget periods recorded yet. Save your first budget to begin tracking!
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = history.map(h => {
      const isOver = (h.actual_spent || 0) > (h.overall_budget || 0);
      const outcomeBadge = isOver 
        ? `<span style="background:#FEE2E2; color:#991B1B; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:700;">Exceeded</span>`
        : `<span style="background:#D1FAE5; color:#065F46; padding:3px 8px; border-radius:12px; font-size:0.75rem; font-weight:700;">Within Budget</span>`;

      return `
        <tr style="border-bottom: 1px solid #EAE1F4;">
          <td style="padding: 10px 12px; font-weight: 600; text-transform: capitalize;">${h.budget_period || 'Monthly'}</td>
          <td style="padding: 10px 12px; color: #81778E;">${h.period_start} to ${h.period_end}</td>
          <td style="padding: 10px 12px; font-weight: 700;">₹${Math.round(h.overall_budget).toLocaleString('en-IN')}</td>
          <td style="padding: 10px 12px; color: #6B34A6; font-weight: 700;">₹${Math.round(h.actual_spent || 0).toLocaleString('en-IN')}</td>
          <td style="padding: 10px 12px;">${h.utilization_percentage || 0}%</td>
          <td style="padding: 10px 12px;">${outcomeBadge}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.warn("Failed to load budget history:", err);
  }
}

function openBudgetModal() {
  const modal = document.getElementById("budgetManageModal");
  if (!modal) return;

  const overallInput = document.getElementById("modalOverallBudget");
  if (overallInput && currentActiveBudget) {
    overallInput.value = currentActiveBudget.budget_max || 10000;
  }

  // Render category allocation inputs
  const catContainer = document.getElementById("modalCategoryInputs");
  if (catContainer) {
    const existingAllocs = currentActiveBudget?.category_allocations || {};
    catContainer.innerHTML = CATALOGUE_CATEGORIES.map(cat => {
      const val = existingAllocs[cat] || "";
      return `
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px;">
          <span style="font-size: 0.8rem; color: #403653; flex: 1;">${cat}</span>
          <input 
            type="number" 
            name="cat_${cat}" 
            placeholder="No limit" 
            value="${val}" 
            min="0" 
            step="100" 
            style="width: 130px; padding: 6px 10px; border: 1px solid #EAE1F4; border-radius: 6px; font-size: 0.82rem;"
          >
        </div>
      `;
    }).join("");
  }

  modal.style.display = "flex";
}

function closeBudgetModal() {
  const modal = document.getElementById("budgetManageModal");
  if (modal) modal.style.display = "none";
}

function toggleCustomDates(val) {
  const customGroup = document.getElementById("modalCustomDatesGroup");
  if (customGroup) {
    customGroup.style.display = (val === "custom") ? "flex" : "none";
  }
}

async function submitBudgetForm(e) {
  e.preventDefault();
  const period = document.getElementById("modalBudgetPeriod").value;
  const overall = parseFloat(document.getElementById("modalOverallBudget").value) || 0;
  const pStart = document.getElementById("modalPeriodStart").value;
  const pEnd = document.getElementById("modalPeriodEnd").value;

  const categoryAllocations = {};
  CATALOGUE_CATEGORIES.forEach(cat => {
    const input = document.querySelector(`input[name="cat_${cat}"]`);
    if (input && input.value) {
      const amt = parseFloat(input.value);
      if (amt > 0) categoryAllocations[cat] = amt;
    }
  });

  try {
    const res = await fetch("/api/budget/manage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        budget_period: period,
        overall_budget: overall,
        period_start: pStart,
        period_end: pEnd,
        category_allocations: categoryAllocations,
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    closeBudgetModal();
    if (typeof showToast === "function") {
      showToast(data.message || "Budget saved successfully!", "success");
    } else {
      alert(data.message || "Budget saved successfully!");
    }
    await loadBudgetOverview();
    await loadCategoryTracking();
    await loadBudgetHistory();
  } catch (err) {
    alert("Failed to save budget: " + err.message);
  }
}

async function confirmResetBudget() {
  if (!confirm("Are you sure you want to reset your active budget? This will archive the current budget period.")) {
    return;
  }
  try {
    const res = await fetch("/api/budget/reset", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      alert(data.message || "Budget reset successfully.");
      await loadBudgetOverview();
      await loadBudgetHistory();
    }
  } catch (err) {
    alert("Reset failed: " + err.message);
  }
}

// =========================================================================
// SECTION 2: MY SPENDING OVERVIEW
// =========================================================================

async function loadSpendingOverview(dateFilter = "current_month", btnEl) {
  if (btnEl) {
    document.querySelectorAll(".budget-date-chip").forEach(b => b.classList.remove("active"));
    btnEl.classList.add("active");
  }

  try {
    const res = await fetch(`/api/budget/spending-overview?date_filter=${dateFilter}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const lbl = document.getElementById("spendingFilterLabel");
    if (lbl) lbl.innerText = `${data.filter_label} • Completed and paid purchases only`;

    document.getElementById("overviewTotalSpent").innerText = Math.round(data.total_spent).toLocaleString("en-IN");
    document.getElementById("overviewEligibleCount").innerText = data.eligible_purchases_count || 0;
    document.getElementById("overviewAov").innerText = Math.round(data.average_order_value).toLocaleString("en-IN");

    const maxBudget = currentActiveBudget ? (currentActiveBudget.budget_max || 0) : 0;
    const remaining = Math.max(0, maxBudget - data.total_spent);
    document.getElementById("overviewRemaining").innerText = Math.round(remaining).toLocaleString("en-IN");

    renderMonthlyTrendBars(data.monthly_trend || []);
    renderRecentPurchasesTable(data.recent_purchases || []);
  } catch (err) {
    console.warn("Failed to load spending overview:", err);
  }
}

function renderMonthlyTrendBars(trend) {
  const container = document.getElementById("monthlyTrendBars");
  if (!container) return;

  const maxSpent = Math.max(...trend.map(t => t.spent), 1000);

  container.innerHTML = trend.map(t => {
    const heightPct = Math.min(100, Math.max(8, Math.round((t.spent / maxSpent) * 100)));
    return `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 160px;">
        <div style="font-size: 0.72rem; font-weight: 700; color: #403653; margin-bottom: 6px;">
          ₹${Math.round(t.spent).toLocaleString('en-IN')}
        </div>
        <div style="width: 100%; max-width: 48px; background: #EAE1F4; border-radius: 8px 8px 0 0; height: 110px; display: flex; align-items: flex-end; overflow: hidden;">
          <div style="width: 100%; height: ${heightPct}%; background: linear-gradient(180deg, #C4A6F5 0%, #A78BFA 100%); border-radius: 8px 8px 0 0; transition: height 0.4s ease;"></div>
        </div>
        <div style="font-size: 0.75rem; color: #81778E; margin-top: 8px; font-weight: 600;">
          ${t.month_label}
        </div>
      </div>
    `;
  }).join("");
}

function renderRecentPurchasesTable(orders) {
  const tbody = document.getElementById("overviewRecentOrdersBody");
  if (!tbody) return;

  if (!orders.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="padding: 24px; text-align: center; color: #81778E;">
          No eligible purchases found in this date window.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = orders.map(o => {
    return `
      <tr style="border-bottom: 1px solid #EAE1F4;">
        <td style="padding: 10px 12px; font-weight: 700; color: #403653;">${o.order_number}</td>
        <td style="padding: 10px 12px; color: #81778E;">${o.date}</td>
        <td style="padding: 10px 12px;">${o.items_count} items</td>
        <td style="padding: 10px 12px; font-weight: 700; color: #403653;">₹${Math.round(o.total_amount).toLocaleString('en-IN')}</td>
        <td style="padding: 10px 12px; color: #81778E;">${o.payment_method || 'Verified'}</td>
        <td style="padding: 10px 12px;">
          <span style="background: #D1FAE5; color: #065F46; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 700;">
            ${o.status || 'Confirmed'}
          </span>
        </td>
      </tr>
    `;
  }).join("");
}

// =========================================================================
// SECTION 3: CATEGORY-WISE BUDGET TRACKING
// =========================================================================

async function loadCategoryTracking() {
  const grid = document.getElementById("categoryTrackingGrid");
  const alertsBox = document.getElementById("categoryAlertsContainer");
  if (!grid) return;

  try {
    const res = await fetch("/api/budget/categories");
    const data = await res.json();
    const categories = data.categories || [];

    // Render overspending alerts
    if (alertsBox) {
      if (data.category_alerts && data.category_alerts.length > 0) {
        alertsBox.innerHTML = data.category_alerts.map(a => `
          <div style="background: #FEE2E2; border: 1px solid #FECACA; color: #991B1B; padding: 10px 14px; border-radius: 10px; font-size: 0.82rem; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
            <span>⚠️</span>
            <div><strong>${a.title}:</strong> ${a.message}</div>
          </div>
        `).join("");
      } else {
        alertsBox.innerHTML = "";
      }
    }

    if (!categories.length) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 32px; color: #81778E; background: #ffffff; border: 1px dashed #EAE1F4; border-radius: 12px;">
          <div style="font-size: 1.8rem; margin-bottom: 6px;">🏷️</div>
          <div style="font-weight: 700; color: #403653; margin-bottom: 4px;">No Category Limits Set</div>
          <div style="font-size: 0.8rem; color: #81778E; margin-bottom: 12px;">Set specific limits for categories like Fashion, Mobiles, and Electronics to keep spending balanced.</div>
          <button onclick="openCategoryLimitsModal()" style="background: #C4A6F5; color: #ffffff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 0.82rem; font-weight: 700; cursor: pointer;">
            Allocate Category Limits
          </button>
        </div>
      `;
      return;
    }

    grid.innerHTML = categories.map(c => {
      const isOver = c.is_over_budget;
      const pct = Math.min(100, Math.round(c.utilization_percentage || 0));
      const barColor = isOver ? "#ef4444" : (pct >= 85 ? "#f59e0b" : "#10b981");

      return `
        <div style="background: #ffffff; border: 1.5px solid ${isOver ? '#fca5a5' : '#EAE1F4'}; border-radius: 12px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="font-size: 0.92rem; color: #403653;">${c.category}</strong>
            <span style="font-size: 0.74rem; font-weight: 700; color: ${barColor};">
              ${isOver ? 'Exceeded' : (pct >= 85 ? 'Warning' : 'On Track')}
            </span>
          </div>

          <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px;">
            <span style="color: #81778E;">Spent: <strong>₹${Math.round(c.spent).toLocaleString('en-IN')}</strong></span>
            <span style="color: #81778E;">Limit: ₹${Math.round(c.allocated).toLocaleString('en-IN')}</span>
          </div>

          <div class="custom-progress-bg" style="height: 6px; margin-bottom: 8px;">
            <div style="height: 100%; width: ${pct}%; background: ${barColor}; border-radius: 6px;"></div>
          </div>

          <div style="display: flex; justify-content: space-between; font-size: 0.74rem; color: #81778E;">
            <span>${c.utilization_percentage}% used</span>
            <span>${isOver ? `Over by ₹${Math.round(c.over_amount).toLocaleString('en-IN')}` : `₹${Math.round(c.remaining).toLocaleString('en-IN')} left`}</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.warn("Failed to load category tracking:", err);
  }
}

function openCategoryLimitsModal() {
  openBudgetModal();
}

// =========================================================================
// SECTION 4: PRICE INTELLIGENCE
// =========================================================================

async function populateProductSelect() {
  const select = document.getElementById("priceHistoryProductSelect");
  if (!select) return;

  try {
    const res = await fetch("/api/products?limit=25");
    const data = await res.json();
    const products = data.products || [];

    if (products.length > 0) {
      select.innerHTML = products.map(p => {
        return `<option value="${p.id}">${p.name} (₹${Math.round(p.price).toLocaleString('en-IN')})</option>`;
      }).join("");
      currentSelectedProductId = products[0].id;
    }
  } catch (err) {
    console.warn("Failed to load products for dropdown:", err);
  }
}

async function loadProductPriceHistory(productId) {
  currentSelectedProductId = productId;
  try {
    // 1. Fetch 60-day price history and recommendation
    const res = await fetch(`/api/products/${productId}/price-history`);
    const data = await res.json();

    document.getElementById("statLowest").innerText = Math.round(data.lowest_price || 0).toLocaleString("en-IN");
    document.getElementById("statAverage").innerText = Math.round(data.average_price || 0).toLocaleString("en-IN");
    document.getElementById("statHighest").innerText = Math.round(data.highest_price || 0).toLocaleString("en-IN");

    const badge = document.getElementById("advisorBadge");
    if (badge) {
      badge.innerText = data.decision || "BUY NOW";
      if (data.decision === "BUY NOW") {
        badge.style.background = "#10b981";
      } else if (data.decision === "FAIR DEAL") {
        badge.style.background = "#6366f1";
      } else {
        badge.style.background = "#f59e0b";
      }
    }

    const titleEl = document.getElementById("advisorTitle");
    if (titleEl) titleEl.innerText = `Timing Recommendation: ${data.decision || 'BUY NOW'}`;

    const reasonEl = document.getElementById("advisorReason");
    if (reasonEl) reasonEl.innerText = data.advice || "Price is currently at a competitive level.";

    renderPriceChart(data.history || []);

    // 2. Fetch price intelligence details & affordable alternatives
    const intelRes = await fetch(`/api/budget/price-intelligence?product_id=${productId}`);
    const intelData = await intelRes.json();

    document.getElementById("intelSellingPrice").innerText = `₹${Math.round(intelData.selling_price || 0).toLocaleString('en-IN')}`;
    document.getElementById("intelMrp").innerText = `₹${Math.round(intelData.mrp || 0).toLocaleString('en-IN')}`;
    document.getElementById("intelDiscountBadge").innerText = `${intelData.discount_percentage || 15}% off`;

    const unitEl = document.getElementById("intelUnitPrice");
    if (unitEl) {
      unitEl.innerText = intelData.unit_price_info ? intelData.unit_price_info.display : "Standard Unit";
    }

    const valLabel = document.getElementById("intelValueLabel");
    if (valLabel) valLabel.innerText = intelData.value_label || "Good Value";

    const valReason = document.getElementById("intelValueReason");
    if (valReason) valReason.innerText = intelData.value_reason || "vs. category average";

    renderAffordableAlternatives(intelData.affordable_alternatives || []);
  } catch (err) {
    console.warn("Price history load error:", err);
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

  if (typeof Chart === "undefined") {
    // If Chart.js CDN is unavailable, fail gracefully
    ctx.parentElement.innerHTML = `<div style="text-align:center; padding:32px; color:#81778E;">Historical price curve recorded across ${history.length} price checks.</div>`;
    return;
  }

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Price (₹)",
        data: dataPoints,
        borderColor: "#C4A6F5",
        backgroundColor: "rgba(196, 166, 245, 0.15)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: "#A78BFA",
        pointBorderColor: "#ffffff",
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
          backgroundColor: "#403653",
          titleColor: "#ffffff",
          bodyColor: "#E9DDFB",
          callbacks: {
            label: function(context) {
              return ` Price: ₹${context.parsed.y.toLocaleString("en-IN")}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(234, 225, 244, 0.4)" },
          ticks: { color: "#81778E", maxTicksLimit: 7 }
        },
        y: {
          grid: { color: "rgba(234, 225, 244, 0.4)" },
          ticks: {
            color: "#81778E",
            callback: function(val) { return `₹${val.toLocaleString("en-IN")}`; }
          }
        }
      }
    }
  });
}

function renderAffordableAlternatives(alternatives) {
  const grid = document.getElementById("affordableAlternativesGrid");
  if (!grid) return;

  if (!alternatives.length) {
    grid.innerHTML = '<div style="grid-column:1/-1; color:#81778E; font-size:0.82rem;">No lower-priced alternatives needed — current selection is in the top-value tier!</div>';
    return;
  }

  grid.innerHTML = alternatives.map(alt => `
    <div style="background: #ffffff; border: 1px solid #EAE1F4; border-radius: 10px; padding: 12px; display: flex; gap: 10px; align-items: center;">
      <img src="${alt.image_url || '/static/images/pretwin-icon.svg'}" alt="${alt.name}" style="width: 44px; height: 44px; object-fit: contain; border-radius: 6px; background: #fafafa;">
      <div style="flex: 1; min-width: 0;">
        <h4 style="font-size: 0.82rem; font-weight: 700; color: #403653; margin: 0 0 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${alt.name}</h4>
        <div style="font-size: 0.74rem; color: #10b981; font-weight: 700;">₹${Math.round(alt.price).toLocaleString('en-IN')} • Save ₹${Math.round(alt.savings).toLocaleString('en-IN')}</div>
        <div style="font-size: 0.7rem; color: #81778E;">${alt.rating} ★ Rating</div>
      </div>
    </div>
  `).join("");
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
      alert(data.message || "Price drop alert active!");
      loadBudgetOverview();
    } else {
      alert(data.error || "Failed to track product");
    }
  } catch (err) {
    alert("Tracking failed: " + err.message);
  }
}

function renderTrackedTable(items) {
  const tbody = document.getElementById("trackedTableBody");
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="padding:24px; text-align:center; color:#81778E;">
          No products currently tracked. Select any product above to monitor price drops!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const isReached = item.is_drop_reached;
    return `
      <tr style="border-bottom:1px solid #EAE1F4;">
        <td style="padding:10px 12px; font-weight:600; color:#403653;">
          <div style="display:flex; align-items:center; gap:8px;">
            ${item.image_url ? `<img src="${item.image_url}" style="width:32px; height:32px; object-fit:contain; border-radius:4px; background:#fff;">` : ""}
            <span>${item.name || "Product #" + item.product_id}</span>
          </div>
        </td>
        <td style="padding:10px 12px; color:#81778E;">${item.category || "General"}</td>
        <td style="padding:10px 12px; color:#6B34A6; font-weight:700;">₹${Math.round(item.target_price).toLocaleString("en-IN")}</td>
        <td style="padding:10px 12px; font-weight:700;">₹${Math.round(item.current_price).toLocaleString("en-IN")}</td>
        <td style="padding:10px 12px;">
          ${isReached
            ? `<span style="background:#D1FAE5; color:#065F46; padding:3px 8px; border-radius:12px; font-size:0.74rem; font-weight:700;">🎯 TARGET REACHED (-₹${Math.round(item.savings_amount)})</span>`
            : `<span style="background:#EAE1F4; color:#403653; padding:3px 8px; border-radius:12px; font-size:0.74rem;">Monitoring</span>`
          }
        </td>
        <td style="padding:10px 12px;">
          <button onclick="untrackProduct(${item.product_id})" style="background:transparent; border:1px solid #EAE1F4; color:#81778E; padding:4px 8px; border-radius:6px; cursor:pointer; font-size:0.76rem;">
            Remove
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

async function untrackProduct(productId) {
  try {
    const res = await fetch(`/api/budget/track/${productId}`, { method: "DELETE" });
    if (res.ok) {
      loadBudgetOverview();
    }
  } catch (err) {
    console.warn("Untrack error:", err);
  }
}

// =========================================================================
// SECTION 5: SMART SAVINGS PLANNER
// =========================================================================

async function loadSavingsPlans() {
  const container = document.getElementById("savingsGoalsContainer");
  if (!container) return;

  try {
    const res = await fetch("/api/budget/savings-summary");
    const data = await res.json();

    document.getElementById("savingsTotalSaved").innerText = Math.round(data.total_saved_amount || 0).toLocaleString("en-IN");
    document.getElementById("savingsTotalTarget").innerText = Math.round(data.total_target_amount || 0).toLocaleString("en-IN");
    document.getElementById("savingsActiveGoalsCount").innerText = data.active_plans || 0;
    document.getElementById("savingsOverallProgress").innerText = `${data.overall_savings_progress || 0}%`;

    const plans = data.plans || [];
    if (!plans.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 36px; background: #ffffff; border: 1.5px dashed #EAE1F4; border-radius: 14px;">
          <div style="font-size: 2rem; margin-bottom: 6px;">💰</div>
          <h4 style="margin: 0 0 4px 0; color: #403653; font-weight: 800;">No Savings Goals Created Yet</h4>
          <p style="margin: 0 0 16px 0; color: #81778E; font-size: 0.82rem;">Create a savings goal for a major upcoming gadget, apparel, or holiday purchase.</p>
          <button onclick="openNewSavingsGoalModal()" style="background: #C4A6F5; color: #ffffff; border: none; padding: 8px 18px; border-radius: 8px; font-weight: 700; font-size: 0.82rem; cursor: pointer;">
            + Create First Goal
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = plans.map(p => {
      const pct = p.progress_percentage || 0;
      const isComplete = pct >= 100;
      return `
        <div style="background: #ffffff; border: 1.5px solid #EAE1F4; border-radius: 12px; padding: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <h4 style="font-size: 0.95rem; font-weight: 800; color: #403653; margin: 0;">${p.goal_title}</h4>
                <span class="budget-pill" style="background:${isComplete ? '#D1FAE5' : '#E9DDFB'}; color:${isComplete ? '#065F46' : '#403653'};">
                  ${isComplete ? 'Goal Completed 🎉' : 'In Progress'}
                </span>
              </div>
              <span style="font-size: 0.76rem; color: #81778E;">Estimated Completion: <strong>${p.estimated_completion_date || 'In Progress'}</strong></span>
            </div>
            <div style="display: flex; gap: 8px;">
              ${!isComplete ? `
                <button onclick="openSavingsDepositModal(${p.id}, '${p.goal_title.replace(/'/g, "\\'")}')" style="background: #10b981; color: #ffffff; border: none; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; font-weight: 700; cursor: pointer;">
                  + Add Deposit
                </button>
              ` : ''}
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 6px;">
            <span>Saved: <strong style="color:#10b981;">₹${Math.round(p.current_saved).toLocaleString('en-IN')}</strong> / ₹${Math.round(p.target_amount).toLocaleString('en-IN')}</span>
            <span style="font-weight: 700;">${pct}%</span>
          </div>

          <div class="custom-progress-bg" style="height: 8px;">
            <div class="custom-progress-bar" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.warn("Failed to load savings plans:", err);
  }
}

function openNewSavingsGoalModal() {
  const modal = document.getElementById("newSavingsGoalModal");
  if (modal) modal.style.display = "flex";
}

function closeNewSavingsGoalModal() {
  const modal = document.getElementById("newSavingsGoalModal");
  if (modal) modal.style.display = "none";
}

async function submitNewSavingsGoal(e) {
  e.preventDefault();
  const title = document.getElementById("goalTitleInput").value;
  const target = parseFloat(document.getElementById("goalTargetInput").value) || 0;
  const targetDate = document.getElementById("goalTargetDateInput").value;
  const initialSaved = parseFloat(document.getElementById("goalInitialSavedInput").value) || 0;

  try {
    const res = await fetch("/api/savings/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        goal_title: title,
        target_amount: target,
        target_date: targetDate,
        initial_deposit: initialSaved
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    closeNewSavingsGoalModal();
    alert("Savings goal created successfully!");
    loadSavingsPlans();
  } catch (err) {
    alert("Failed to create goal: " + err.message);
  }
}

function openSavingsDepositModal(planId, goalTitle) {
  const modal = document.getElementById("savingsDepositModal");
  if (!modal) return;

  document.getElementById("depositPlanId").value = planId;
  document.getElementById("depositGoalTitle").innerText = `Contributing to: ${goalTitle}`;
  modal.style.display = "flex";
}

function closeSavingsDepositModal() {
  const modal = document.getElementById("savingsDepositModal");
  if (modal) modal.style.display = "none";
}

async function submitSavingsDeposit(e) {
  e.preventDefault();
  const planId = document.getElementById("depositPlanId").value;
  const amount = parseFloat(document.getElementById("depositAmountInput").value) || 0;
  const note = document.getElementById("depositNoteInput").value;

  try {
    const res = await fetch(`/api/savings/plans/${planId}/contributions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: amount, note: note })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    closeSavingsDepositModal();
    alert("Deposit recorded successfully!");
    loadSavingsPlans();
  } catch (err) {
    alert("Deposit failed: " + err.message);
  }
}

// =========================================================================
// SECTION 6: SMART PURCHASE AFFORDABILITY
// =========================================================================

function setAffordabilityPreset(val) {
  const input = document.getElementById("affordabilityCartInput");
  if (input) {
    input.value = val;
    recalculateAffordability(val);
  }
}

async function syncLiveCartAffordability() {
  let subtotal = 1500;
  if (typeof getCart === "function") {
    const cart = getCart();
    if (cart && cart.length > 0) {
      subtotal = cart.reduce((sum, item) => sum + (parseFloat(item.price || 0) * (item.quantity || 1)), 0);
    }
  }
  const input = document.getElementById("affordabilityCartInput");
  if (input) input.value = Math.round(subtotal);
  await recalculateAffordability(subtotal);
}

function recalculateAffordability(val) {
  clearTimeout(affordabilityDebounceTimer);
  affordabilityDebounceTimer = setTimeout(async () => {
    const cartVal = parseFloat(val) || 0;
    try {
      const res = await fetch("/api/budget/affordability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart_subtotal: cartVal })
      });
      const data = await res.json();

      document.getElementById("affordBudget").innerText = `₹${Math.round(data.overall_budget).toLocaleString('en-IN')}`;
      document.getElementById("affordSpent").innerText = `₹${Math.round(data.current_spent).toLocaleString('en-IN')}`;
      document.getElementById("affordRemainingBefore").innerText = `₹${Math.round(data.remaining_budget_before).toLocaleString('en-IN')}`;
      document.getElementById("affordCartSubtotal").innerText = `₹${Math.round(data.cart_subtotal).toLocaleString('en-IN')}`;
      document.getElementById("affordShipping").innerText = data.shipping_fee > 0 ? `₹${data.shipping_fee}` : "FREE";
      document.getElementById("affordFinalPayable").innerText = `₹${Math.round(data.final_payable).toLocaleString('en-IN')}`;
      
      const remAfter = document.getElementById("affordRemainingAfter");
      if (remAfter) {
        remAfter.innerText = `₹${Math.round(data.remaining_budget_after).toLocaleString('en-IN')}`;
        remAfter.style.color = data.is_over_budget ? "#ef4444" : "#10b981";
      }

      document.getElementById("affordUtilizationAfter").innerText = `${data.budget_utilization_after}%`;

      const alertBox = document.getElementById("affordabilityAlertBox");
      if (alertBox) {
        if (data.warning_level === "danger") {
          alertBox.style.background = "#FEE2E2";
          alertBox.style.color = "#991B1B";
          alertBox.style.border = "1px solid #FECACA";
        } else if (data.warning_level === "warning") {
          alertBox.style.background = "#FEF3C7";
          alertBox.style.color = "#92400E";
          alertBox.style.border = "1px solid #FDE68A";
        } else {
          alertBox.style.background = "#D1FAE5";
          alertBox.style.color = "#065F46";
          alertBox.style.border = "1px solid #A7F3D0";
        }
        alertBox.innerHTML = `<strong>${data.is_over_budget ? '⚠️ Budget Notice:' : '✓ Affordability Status:'}</strong> ${data.warning_message}`;
      }
    } catch (err) {
      console.warn("Affordability calculation failed:", err);
    }
  }, 180);
}

// =========================================================================
// SECTION 7: BUDGET INSIGHTS AND ALERTS
// =========================================================================

async function loadBudgetInsights() {
  const alertsList = document.getElementById("insightsAlertsList");
  const obsList = document.getElementById("insightsObservationsList");
  if (!alertsList || !obsList) return;

  try {
    const res = await fetch("/api/budget/insights");
    const data = await res.json();
    const alerts = data.alerts || [];
    const insights = data.insights || [];

    if (!alerts.length) {
      alertsList.innerHTML = `
        <div style="background: #D1FAE5; border: 1px solid #A7F3D0; color: #065F46; padding: 12px 16px; border-radius: 10px; font-size: 0.84rem; font-weight: 600;">
          ✓ All systems normal! Your expenditures are within established limits with zero overspending alerts.
        </div>
      `;
    } else {
      alertsList.innerHTML = alerts.map(a => `
        <div style="background: #FEE2E2; border: 1px solid #FECACA; color: #991B1B; padding: 12px 16px; border-radius: 10px; font-size: 0.84rem;">
          <strong style="display: block; margin-bottom: 2px;">⚠️ ${a.title}</strong>
          <span>${a.message}</span>
        </div>
      `).join("");
    }

    if (!insights.length) {
      obsList.innerHTML = `<div style="grid-column:1/-1; color:#81778E; font-size:0.82rem;">No additional spending observations recorded yet.</div>`;
    } else {
      obsList.innerHTML = insights.map(i => `
        <div style="background: #ffffff; border: 1.5px solid #EAE1F4; border-radius: 12px; padding: 16px;">
          <h4 style="font-size: 0.88rem; font-weight: 800; color: #403653; margin: 0 0 4px 0;">💡 ${i.title}</h4>
          <p style="margin: 0; font-size: 0.82rem; color: #81778E; line-height: 1.5;">${i.message}</p>
        </div>
      `).join("");
    }
  } catch (err) {
    console.warn("Failed to load budget insights:", err);
  }
}
