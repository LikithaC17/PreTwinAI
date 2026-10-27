/**
 * smart_cart.js
 * Handles Smart Cart and Shopping Automation:
 * 1. Duplicate & Recent Purchase Warning
 * 2. Missing Companion Essentials
 * 3. Combo Bundle Discounts
 * 4. Twin Budget Ceiling Checks
 */

document.addEventListener("DOMContentLoaded", () => {
  initSmartCart();
});

function getLocalCart() {
  try {
    const raw = localStorage.getItem("pretwin_cart");
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveLocalCart(cart) {
  localStorage.setItem("pretwin_cart", JSON.stringify(cart));
  if (typeof updateCartCount === "function") {
    updateCartCount();
  }
}

async function initSmartCart() {
  let cart = getLocalCart();

  // If cart is empty, add sample demo products for rich exploration
  if (!cart || cart.length === 0) {
    cart = [
      { id: 1, name: "Wireless Over-Ear ANC Headphones", price: 3499, quantity: 1, category: "Electronics", image_url: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&q=80" },
      { id: 4, name: "Men's Breathable Running Shoes", price: 2199, quantity: 1, category: "Fashion", image_url: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&q=80" }
    ];
    saveLocalCart(cart);
  }

  renderCartItems(cart);
  loadDigitalShoppingCard();
  await runCartAIAnalysis();
}

async function loadDigitalShoppingCard() {
  // 1. Load User Profile
  try {
    const res = await fetch("/api/profile");
    if (res.ok) {
      const data = await res.json();
      const userName = data.username || data.name || "PreTwin Shopper";
      const elName = document.getElementById("dscUserName");
      if (elName) elName.innerText = userName;

      const rawId = data.id || 1;
      const maskedId = `#PRE-${10000 + parseInt(rawId, 10)}`;
      const elId = document.getElementById("dscMaskedId");
      if (elId) elId.innerText = maskedId;
    }
  } catch (e) {
    console.debug("Digital card profile load fallback", e);
  }

  // 2. Load Rewards Balance
  try {
    const res = await fetch("/api/rewards/balance");
    if (res.ok) {
      const data = await res.json();
      const pts = data.balance_points || 0;
      const rupees = (data.rupee_value || (pts / 100.0)).toFixed(2);
      const elPts = document.getElementById("dscRewardPoints");
      const elRupees = document.getElementById("dscRewardRupees");
      if (elPts) elPts.innerText = Math.round(pts).toLocaleString("en-IN");
      if (elRupees) elRupees.innerText = rupees;
    }
  } catch (e) {
    console.debug("Digital card rewards load fallback", e);
  }

  // 3. Load Savings Plan
  try {
    const res = await fetch("/api/savings/plans");
    if (res.ok) {
      const data = await res.json();
      const plans = data.plans || (Array.isArray(data) ? data : []);
      if (plans.length > 0) {
        const activePlan = plans.find(p => (p.status || "").toLowerCase() === "active") || plans[0];
        const title = activePlan.goal_title || activePlan.title || "Shopping Goal";
        const saved = Math.round(activePlan.current_saved || activePlan.saved_amount || 0);
        const target = Math.round(activePlan.target_amount || 0);
        const pct = Math.min(100, Math.round(activePlan.progress_percentage || (target > 0 ? (saved / target * 100) : 0)));

        const elTitle = document.getElementById("dscSavingsTitle");
        const elPct = document.getElementById("dscSavingsPct");
        const elSaved = document.getElementById("dscSavedAmount");
        const elTarget = document.getElementById("dscTargetAmount");
        const elBar = document.getElementById("dscSavingsBar");
        const elStatus = document.getElementById("dscSavingsStatus");

        if (elTitle) elTitle.innerText = title;
        if (elPct) elPct.innerText = `${pct}%`;
        if (elSaved) elSaved.innerText = saved.toLocaleString("en-IN");
        if (elTarget) elTarget.innerText = target.toLocaleString("en-IN");
        if (elBar) elBar.style.width = `${pct}%`;
        if (elStatus) elStatus.innerText = pct >= 100 ? "Goal Reached 🎉" : "Target in progress";
      }
    }
  } catch (e) {
    console.debug("Digital card savings load fallback", e);
  }
}

function renderCartItems(cart) {
  const container = document.getElementById("smartCartItemsList");
  if (!container) return;

  if (cart.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:48px 16px; color:#64748b;">
        <span style="font-size:2.5rem; display:block; margin-bottom:12px;">🛒</span>
        Your basket is empty. Browse items to trigger AI basket optimization.
        <div style="margin-top:16px;">
          <a href="/discovery" style="background:#6366f1; color:#fff; text-decoration:none; padding:8px 16px; border-radius:6px; font-weight:600; font-size:0.85rem;">Discover Products</a>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = cart.map((item, idx) => `
    <div style="display:flex; justify-content:space-between; align-items:center; padding:14px 0; border-bottom:1px solid #1e293b; gap:14px;">
      <div style="display:flex; align-items:center; gap:14px;">
        ${item.image_url ? `<img src="${item.image_url}" style="width:54px; height:54px; object-fit:contain; border-radius:8px; background:#fff; padding:4px;">` : ""}
        <div>
          <div style="font-weight:600; color:#f1f5f9; font-size:0.95rem;">${item.name}</div>
          <div style="font-size:0.8rem; color:#94a3b8; margin-top:2px;">
            ${item.category || "General"} • ₹${Math.round(item.price).toLocaleString("en-IN")} each
          </div>
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:16px;">
        <div style="display:flex; align-items:center; background:#1e293b; border-radius:6px; border:1px solid #334155;">
          <button onclick="changeQty(${idx}, -1)" style="background:transparent; border:none; color:#cbd5e1; padding:4px 10px; cursor:pointer; font-weight:700;">-</button>
          <span style="color:#f1f5f9; font-size:0.85rem; padding:0 6px;">${item.quantity || 1}</span>
          <button onclick="changeQty(${idx}, 1)" style="background:transparent; border:none; color:#cbd5e1; padding:4px 10px; cursor:pointer; font-weight:700;">+</button>
        </div>
        <div style="font-weight:700; color:#f1f5f9; min-width:80px; text-align:right;">
          ₹${Math.round(item.price * (item.quantity || 1)).toLocaleString("en-IN")}
        </div>
        <button onclick="removeItem(${idx})" style="background:transparent; border:none; color:#ef4444; cursor:pointer; font-size:1.1rem; padding:4px;" title="Remove Item">×</button>
      </div>
    </div>
  `).join("");
}

function changeQty(index, delta) {
  let cart = getLocalCart();
  if (cart[index]) {
    cart[index].quantity = (cart[index].quantity || 1) + delta;
    if (cart[index].quantity <= 0) {
      cart.splice(index, 1);
    }
    saveLocalCart(cart);
    renderCartItems(cart);
    runCartAIAnalysis();
  }
}

function removeItem(index) {
  let cart = getLocalCart();
  cart.splice(index, 1);
  saveLocalCart(cart);
  renderCartItems(cart);
  runCartAIAnalysis();
}

async function runCartAIAnalysis() {
  const cart = getLocalCart();
  try {
    const res = await fetch("/api/smart-cart/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cart_items: cart })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Analysis failed");

    // Stats
    const subtotal = data.subtotal || 0;
    document.getElementById("statCartSubtotal").innerText = Math.round(subtotal).toLocaleString("en-IN");
    document.getElementById("statCartCount").innerText = data.item_count || 0;
    document.getElementById("summarySubtotal").innerText = Math.round(subtotal).toLocaleString("en-IN");

    // Bundle Discount
    let discount = 0;
    if (data.eligible_bundles && data.eligible_bundles.length > 0) {
      discount = data.eligible_bundles[0].savings_amount || 0;
      document.getElementById("statBundleSavings").innerText = Math.round(discount).toLocaleString("en-IN");
      document.getElementById("summaryDiscount").innerText = Math.round(discount).toLocaleString("en-IN");
      document.getElementById("statBundleBadge").innerText = "8% Multi-Item Combo Applied";
    } else {
      document.getElementById("statBundleSavings").innerText = "0";
      document.getElementById("summaryDiscount").innerText = "0";
      document.getElementById("statBundleBadge").innerText = "Add 2+ items to unlock";
    }

    const total = Math.max(0, subtotal - discount);
    document.getElementById("summaryTotal").innerText = Math.round(total).toLocaleString("en-IN");

    // Update Digital Shopping Card cart totals
    const dscTotal = document.getElementById("dscCartTotal");
    const dscBadge = document.getElementById("dscCartCountBadge");
    if (dscTotal) dscTotal.innerText = Math.round(total).toLocaleString("en-IN");
    if (dscBadge) dscBadge.innerText = `${data.item_count || 0} item${(data.item_count || 0) === 1 ? '' : 's'}`;

    // Duplicates
    const dupBox = document.getElementById("duplicateAlertBox");
    const dupList = document.getElementById("duplicateAlertList");
    const dupCount = document.getElementById("statDupCount");
    if (data.duplicates_detected && data.duplicates_detected.length > 0) {
      dupCount.innerText = data.duplicates_detected.length;
      dupBox.style.display = "block";
      dupList.innerHTML = data.duplicates_detected.map(d => `
        <div style="margin-top:4px;">
          • <strong>${d.cart_item}</strong>: ${d.warning}
        </div>
      `).join("");
    } else {
      dupCount.innerText = "0";
      dupBox.style.display = "none";
    }

    // Budget Ceiling
    const bCheck = data.budget_check;
    const overBox = document.getElementById("overBudgetAlertBox");
    const bStatus = document.getElementById("statBudgetStatus");
    const bRem = document.getElementById("statBudgetRemaining");
    const dscCeilingDot = document.getElementById("dscCeilingDot");
    const dscCeilingText = document.getElementById("dscCeilingText");

    if (bCheck && bCheck.is_over_budget) {
      bStatus.innerText = "Exceeded";
      bStatus.style.color = "#ef4444";
      bRem.innerText = `₹${Math.round(bCheck.overage)} over monthly cap`;
      overBox.style.display = "block";
      document.getElementById("overBudgetMessage").innerText = bCheck.message;

      if (dscCeilingDot) dscCeilingDot.style.background = "#ef4444";
      if (dscCeilingText) {
        dscCeilingText.innerText = `Ceiling Exceeded by ₹${Math.round(bCheck.overage)}`;
        dscCeilingText.style.color = "#ef4444";
      }
    } else {
      bStatus.innerText = "Within Budget";
      bStatus.style.color = "#10b981";
      bRem.innerText = `Monthly ceiling: ₹${Math.round(bCheck.budget_limit || 15000).toLocaleString("en-IN")}`;
      overBox.style.display = "none";

      if (dscCeilingDot) dscCeilingDot.style.background = "#10b981";
      if (dscCeilingText) {
        dscCeilingText.innerText = "Within Monthly Budget Ceiling";
        dscCeilingText.style.color = "#10b981";
      }
    }

    // Companion items
    renderCompanionItems(data.missing_essentials || []);
  } catch (err) {
    console.error("Cart analysis error:", err);
  }
}

function renderCompanionItems(items) {
  const container = document.getElementById("missingEssentialsContainer");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `
      <div style="font-size:0.85rem; color:#94a3b8; background:rgba(255,255,255,0.03); padding:10px; border-radius:8px;">
        ✨ Great basket composition! No critical companion accessories missing.
      </div>
    `;
    return;
  }

  container.innerHTML = items.map(item => `
    <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center; gap:10px;">
      <div>
        <div style="font-size:0.9rem; font-weight:600; color:#f1f5f9;">${item.name}</div>
        <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">${item.reason}</div>
        <div style="font-size:0.85rem; font-weight:700; color:#22d3ee; margin-top:4px;">₹${item.price}</div>
      </div>
      <button onclick="addCompanionToCart('${item.name.replace(/'/g, "\\'")}', ${item.price}, '${item.category}')" style="background:#6366f1; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-size:0.8rem; font-weight:600; cursor:pointer; white-space:nowrap;">
        + Add
      </button>
    </div>
  `).join("");
}

function addCompanionToCart(name, price, category) {
  let cart = getLocalCart();
  cart.push({
    id: Date.now(),
    name: name,
    price: price,
    quantity: 1,
    category: category,
    image_url: "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?w=400&q=80"
  });
  saveLocalCart(cart);
  renderCartItems(cart);
  runCartAIAnalysis();
}
