/**
 * static/js/smart_card.js
 * =======================
 * PreTwin AI — Feature 6: Smart Shopping Card
 *
 * Implements client-side dynamic rendering, live data fetching,
 * quick action navigation, section tabs, and privacy-safe card tools.
 */

document.addEventListener("DOMContentLoaded", function () {
  initSmartCard();
});

let currentCardData = null;

/**
 * Initialize and load full 7-section card data
 */
async function initSmartCard() {
  try {
    const res = await fetch("/api/shopping-card/data");
    if (!res.ok) {
      console.warn("Smart Shopping Card data endpoint returned", res.status);
      return;
    }
    const data = await res.json();
    currentCardData = data;
    renderSmartCard(data);
  } catch (err) {
    console.error("Failed to load Smart Shopping Card data:", err);
  }
}

/**
 * Render all 7 sections with retrieved data
 */
function renderSmartCard(data) {
  if (!data || !data.success) return;

  const idn = data.identity || {};
  const ovw = data.overview || {};
  const rwd = data.rewards || {};
  const bgt = data.budget_savings || {};
  const ord = data.orders || {};
  const ins = data.insights || {};
  const act = data.quick_actions || {};

  // =========================================================================
  // HERO DIGITAL MEMBERSHIP CARD
  // =========================================================================
  setElementText("dscUserName", idn.display_name || "PreTwin Shopper");
  setElementText("dscMaskedId", idn.masked_account_id || "#PRE-10001");
  setElementText("dscMemberSince", idn.member_since ? `Member since ${idn.member_since}` : "Verified Member");
  setElementText("dscPersonality", idn.shopping_personality || "Practical Smart Shopper");

  // Avatar / Monogram rendering
  const avatarContainer = document.getElementById("avatarContainer");
  if (avatarContainer) {
    if (idn.avatar_url && idn.avatar_url.trim()) {
      avatarContainer.innerHTML = `<img src="${escapeHtml(idn.avatar_url)}" alt="${escapeHtml(idn.display_name)}" class="card-avatar-img" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'card-avatar-monogram\\'>${escapeHtml(idn.monogram || 'PT')}</div>';">`;
    } else {
      avatarContainer.innerHTML = `<div class="card-avatar-monogram" id="dscMonogram">${escapeHtml(idn.monogram || 'PT')}</div>`;
    }
  }

  // Categories chips
  const catRow = document.getElementById("dscCategoriesRow");
  if (catRow) {
    const cats = idn.preferred_categories || [];
    if (cats.length > 0) {
      catRow.innerHTML = cats.map(c => `<span class="card-pref-chip">${escapeHtml(c)}</span>`).join("");
    } else {
      catRow.innerHTML = `<span class="card-pref-chip">Curated Essentials</span>`;
    }
  }

  // Financial metrics (Rewards & Rupee value)
  const balancePts = Math.round(rwd.balance_points || 0);
  setElementText("dscRewardPoints", balancePts.toLocaleString("en-IN"));
  const rupeeVal = (rwd.rupee_value || (balancePts / 100.0)).toFixed(2);
  setElementText("dscRewardRupees", rupeeVal);

  const totalSpent = ovw.total_completed_spent_formatted || `₹${Math.round(ovw.total_completed_spent || 0).toLocaleString('en-IN')}`;
  setElementText("dscSavedAmount", totalSpent);

  // Fallback notice for zero credits
  const zeroNotice = document.getElementById("dscZeroCreditsNotice");
  if (zeroNotice) {
    if (balancePts === 0) {
      zeroNotice.style.display = "block";
    } else {
      zeroNotice.style.display = "none";
    }
  }

  // =========================================================================
  // SECTION 1: MY SMART SHOPPING IDENTITY
  // =========================================================================
  setElementText("identDisplayName", idn.display_name || "—");
  setElementText("identAccountId", idn.masked_account_id || "—");
  setElementText("identCardTier", idn.card_tier || "PreTwin Classic");
  setElementText("identMemberSince", idn.created_at_formatted || idn.member_since || "—");
  setElementText("identPersonality", idn.shopping_personality || "—");
  setElementText("identFrequency", idn.shopping_frequency || "Regular");

  const identCatRow = document.getElementById("identCategoriesRow");
  if (identCatRow) {
    const cats = idn.preferred_categories || [];
    if (cats.length > 0) {
      identCatRow.innerHTML = cats.map(c => `<span class="card-pref-chip">${escapeHtml(c)}</span>`).join("");
    } else {
      identCatRow.innerHTML = `<span class="card-pref-chip">General Catalog</span>`;
    }
  }

  const identBrandsRow = document.getElementById("identBrandsRow");
  if (identBrandsRow) {
    const brands = (idn.preferred_brands || []).concat(idn.preferred_styles || []);
    if (brands.length > 0) {
      identBrandsRow.innerHTML = brands.map(b => `<span class="card-pref-chip">${escapeHtml(b)}</span>`).join("");
    } else {
      identBrandsRow.innerHTML = `<span class="card-pref-chip">Verified Brands</span>`;
    }
  }

  // =========================================================================
  // SECTION 2: MY SHOPPING OVERVIEW
  // =========================================================================
  setElementText("statCompletedOrders", ovw.completed_orders_count != null ? ovw.completed_orders_count : 0);
  setElementText("statActiveOrders", ovw.active_orders_count != null ? ovw.active_orders_count : 0);
  setElementText("statWishlistCount", ovw.wishlist_count != null ? ovw.wishlist_count : 0);
  setElementText("statCartCount", ovw.cart_count != null ? ovw.cart_count : 0);
  setElementText("overviewSummaryText", ovw.summary_text || "Live shopping identity verified.");

  // =========================================================================
  // SECTION 3: MY REWARDS AND BENEFITS
  // =========================================================================
  setElementText("rwBalancePoints", (rwd.balance_points || 0).toLocaleString("en-IN"));
  setElementText("rwRupeeValue", rwd.rupee_value_formatted || `₹${(rwd.rupee_value || 0).toFixed(2)}`);
  setElementText("rwLifetimeEarned", (rwd.lifetime_earned || 0).toLocaleString("en-IN"));
  setElementText("rwLifetimeRedeemed", (rwd.lifetime_redeemed || 0).toLocaleString("en-IN"));

  const rwTable = document.getElementById("rewardTransactionsBody");
  if (rwTable) {
    const txs = rwd.recent_transactions || [];
    if (txs.length > 0) {
      rwTable.innerHTML = txs.map(t => {
        const isPos = t.points > 0;
        const color = isPos ? "#10B981" : "#EF4444";
        return `
          <tr>
            <td>${escapeHtml(t.date || '—')}</td>
            <td><strong>${escapeHtml(t.description || 'Shopping Reward')}</strong></td>
            <td><span class="card-pref-chip">${escapeHtml(t.transaction_type || 'reward')}</span></td>
            <td style="color:${color}; font-weight:700;">${escapeHtml(t.points_formatted || t.points)}</td>
            <td style="font-weight:700;">₹${(t.rupee_value || 0).toFixed(2)}</td>
          </tr>
        `;
      }).join("");
    } else {
      rwTable.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#81778E; padding:16px;">No reward transactions yet. Complete purchases to earn 5 points per order.</td></tr>`;
    }
  }

  // =========================================================================
  // SECTION 4: MY BUDGET AND SAVINGS SNAPSHOT
  // =========================================================================
  setElementText("bsOverallBudget", bgt.overall_budget_formatted || "Not Set");
  setElementText("bsRemainingBudget", bgt.remaining_budget_formatted || "—");
  setElementText("bsCurrentSpent", bgt.current_spent_formatted || "₹0.00");
  setElementText("bsUtilizationText", `${bgt.utilization_pct || 0}% utilized (${bgt.budget_status || 'Active'})`);

  const bsBar = document.getElementById("bsProgressBar");
  if (bsBar) {
    const pct = Math.min(100, Math.max(0, bgt.utilization_pct || 0));
    bsBar.style.width = `${pct}%`;
    if (pct >= 100) {
      bsBar.style.background = "#EF4444";
    } else if (pct >= 80) {
      bsBar.style.background = "#F59E0B";
    } else {
      bsBar.style.background = "linear-gradient(90deg, #10B981, #C4A6F5)";
    }
  }

  const unconfMsg = document.getElementById("bsUnconfiguredMsg");
  if (unconfMsg) {
    unconfMsg.style.display = bgt.budget_configured ? "none" : "block";
  }

  // Savings goals
  const goalsContainer = document.getElementById("savingsGoalsList");
  if (goalsContainer) {
    const goals = bgt.active_savings_goals || [];
    if (goals.length > 0) {
      goalsContainer.innerHTML = goals.map(g => `
        <div class="savings-goal-card">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h6 style="margin:0; font-size:0.92rem; font-weight:700; color:#403653;">${escapeHtml(g.goal_title)}</h6>
            <span class="card-pref-chip">${escapeHtml(g.status)}</span>
          </div>
          <div style="font-size:0.82rem; color:#81778E; margin:6px 0;">
            Target: <strong>${escapeHtml(g.target_amount_formatted)}</strong> · Saved: <strong style="color:#10B981;">${escapeHtml(g.current_saved_formatted)}</strong>
          </div>
          <div class="budget-progress-bar-wrap" style="height:8px; margin:4px 0;">
            <div class="budget-progress-bar-fill" style="width:${g.progress_pct}%; background:#10B981;"></div>
          </div>
          <div style="font-size:0.75rem; color:#81778E; text-align:right;">${g.progress_pct}% completed</div>
        </div>
      `).join("");
    } else {
      goalsContainer.innerHTML = `<div style="color:#81778E; font-size:0.86rem; padding:10px;">No active savings goals found. Start a goal in Savings Planner to track dedicated funds.</div>`;
    }
  }

  // =========================================================================
  // SECTION 5: MY ORDERS AND SHOPPING ACTIVITY
  // =========================================================================
  const activeOrdersBody = document.getElementById("activeOrdersTableBody");
  if (activeOrdersBody) {
    const active = ord.active_orders || [];
    if (active.length > 0) {
      activeOrdersBody.innerHTML = active.map(o => `
        <tr>
          <td><strong>${escapeHtml(o.order_number)}</strong></td>
          <td>${escapeHtml(o.created_at_formatted)}</td>
          <td>${escapeHtml(o.items_summary)}</td>
          <td style="font-weight:700;">${escapeHtml(o.total_amount_formatted)}</td>
          <td><span class="card-pref-chip" style="background:#FFF3E0; color:#E65100;">${escapeHtml(o.status)}</span></td>
          <td><a href="${escapeHtml(o.tracking_url)}" class="overview-nav-btn" style="padding:4px 10px; font-size:0.78rem;">Track</a></td>
        </tr>
      `).join("");
    } else {
      activeOrdersBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#81778E; padding:16px;">No active shipments in transit right now.</td></tr>`;
    }
  }

  const completedOrdersBody = document.getElementById("completedOrdersTableBody");
  if (completedOrdersBody) {
    const completed = ord.recently_completed_orders || [];
    if (completed.length > 0) {
      completedOrdersBody.innerHTML = completed.map(o => `
        <tr>
          <td><strong>${escapeHtml(o.order_number)}</strong></td>
          <td>${escapeHtml(o.created_at_formatted)}</td>
          <td>${escapeHtml(o.items_summary)}</td>
          <td style="font-weight:700;">${escapeHtml(o.total_amount_formatted)}</td>
          <td><span class="card-pref-chip" style="background:#E8F5E9; color:#1B5E20;">${escapeHtml(o.status)}</span></td>
          <td><a href="${escapeHtml(o.view_url)}" class="overview-nav-btn" style="padding:4px 10px; font-size:0.78rem;">Details</a></td>
        </tr>
      `).join("");
    } else {
      completedOrdersBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#81778E; padding:16px;">No completed purchases yet.</td></tr>`;
    }
  }

  // =========================================================================
  // SECTION 6: MY PERSONALISED SHOPPING INSIGHTS
  // =========================================================================
  const insightsGrid = document.getElementById("insightsGrid");
  if (insightsGrid) {
    const insList = ins.insights || [];
    if (insList.length > 0) {
      insightsGrid.innerHTML = insList.map(item => `
        <div class="insight-card">
          <div>
            <span class="insight-badge">${escapeHtml(item.badge || 'Insight')}</span>
            <h5>${escapeHtml(item.title)}</h5>
            <p>${escapeHtml(item.message)}</p>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px dashed #EAE1F4; padding-top:10px; margin-top:8px;">
            <span style="font-size:0.75rem; color:#81778E;">${escapeHtml(item.source)}</span>
            <a href="${escapeHtml(item.link)}" class="insight-link">${escapeHtml(item.action_text || 'View')} <i class="bi bi-chevron-right"></i></a>
          </div>
        </div>
      `).join("");
    } else {
      insightsGrid.innerHTML = `<div style="color:#81778E; padding:12px;">No automated insights generated at this time.</div>`;
    }
  }

  // Populate safe share text snippet
  const safeTextEl = document.getElementById("safeShareText");
  if (safeTextEl && act.safe_export_text) {
    safeTextEl.innerText = act.safe_export_text;
  }
}

/**
 * Refresh card dynamic counters with feedback toast
 */
async function refreshCardData() {
  const btnTop = document.getElementById("btnRefreshTop");
  if (btnTop) {
    btnTop.innerHTML = `<i class="bi bi-arrow-repeat spin"></i> Refreshing...`;
    btnTop.disabled = true;
  }

  try {
    const res = await fetch("/api/shopping-card/refresh", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      currentCardData = data;
      renderSmartCard(data);
      showToast("Smart Shopping Card refreshed with latest live data.");
    } else {
      showToast("Unable to refresh card at this time.");
    }
  } catch (e) {
    console.error("Refresh error:", e);
    showToast("Network error while refreshing card.");
  } finally {
    if (btnTop) {
      btnTop.innerHTML = `<i class="bi bi-arrow-clockwise"></i> Refresh Card`;
      btnTop.disabled = false;
    }
  }
}

/**
 * Tab smooth scroll helper
 */
function scrollToSection(sectionId) {
  const sec = document.getElementById(sectionId);
  if (sec) {
    sec.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Update tab active class
  const tabs = document.querySelectorAll(".sc-tab-btn");
  tabs.forEach(t => t.classList.remove("active"));
  if (event && event.currentTarget) {
    event.currentTarget.classList.add("active");
  }
}

/**
 * Share modal open & close
 */
function openShareModal() {
  const m = document.getElementById("shareModal");
  if (m) m.style.display = "flex";
}

function closeShareModal() {
  const m = document.getElementById("shareModal");
  if (m) m.style.display = "none";
}

/**
 * Copy privacy-safe text to clipboard
 */
function copyShareText() {
  const txt = document.getElementById("safeShareText");
  if (txt && navigator.clipboard) {
    navigator.clipboard.writeText(txt.innerText).then(() => {
      showToast("Privacy-safe card details copied to clipboard!");
      closeShareModal();
    }).catch(() => {
      showToast("Could not copy automatically. Please copy the text manually.");
    });
  }
}

/**
 * Utility toast notification
 */
function showToast(msg) {
  const toast = document.createElement("div");
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.background = "#403653";
  toast.style.color = "#FFFFFF";
  toast.style.padding = "12px 20px";
  toast.style.borderRadius = "12px";
  toast.style.boxShadow = "0 8px 24px rgba(64,54,83,0.3)";
  toast.style.zIndex = "10000";
  toast.style.fontSize = "0.9rem";
  toast.style.fontWeight = "600";
  toast.style.transition = "opacity 0.3s ease";
  toast.innerText = msg;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 350);
  }, 2800);
}

function setElementText(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerText = text;
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
