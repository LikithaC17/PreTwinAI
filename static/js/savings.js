/**
 * PreTwin Smart Shopping Savings Plan Controller
 */

async function loadSavingsPlans() {
  const container = document.getElementById("savingsPlansGrid");
  if (!container) return;

  try {
    const res = await apiGet("/api/savings/plans");
    const plans = res.plans || [];

    if (plans.length === 0) {
      container.innerHTML = `
        <div style="background:#ffffff; padding:48px 24px; text-align:center; border-radius:8px; border:1px solid #e2e8f0; grid-column:1/-1;">
          <div style="font-size:40px; margin-bottom:12px;">🎯</div>
          <h3 style="font-size:18px; font-weight:700; color:#1e293b; margin-bottom:6px;">No Active Savings Goals Yet</h3>
          <p style="color:#64748b; font-size:13px; max-width:440px; margin:0 auto 20px;">
            Set a 30-day savings goal for a smartphone, pair of headphones, or wardrobe refresh. PreTwin will calculate your daily savings pace!
          </p>
          <button onclick="openCreatePlanModal()" class="fk-btn-orange" style="display:inline-block; padding:10px 24px; font-weight:700; border-radius:4px;">
            + Create Your First Goal
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = plans.map(p => {
      const isComplete = p.is_ready_to_shop || p.status === 'completed';
      const pct = Math.min(100, p.progress_percentage || 0);

      return `
        <div style="background:#ffffff; border-radius:10px; border:1px solid ${isComplete ? '#86efac' : '#e2e8f0'}; box-shadow:0 4px 12px rgba(0,0,0,0.04); padding:20px; display:flex; flex-direction:column; justify-content:space-between; position:relative; overflow:hidden;">
          ${isComplete ? `
            <div style="position:absolute; top:0; right:0; background:linear-gradient(135deg, #10b981, #059669); color:#fff; font-size:11px; font-weight:700; padding:4px 16px; border-bottom-left-radius:8px; letter-spacing:0.5px;">
              🎉 GOAL REACHED!
            </div>
          ` : `
            <div style="position:absolute; top:0; right:0; background:#f1f5f9; color:#64748b; font-size:11px; font-weight:600; padding:4px 12px; border-bottom-left-radius:8px;">
              ⏳ ${p.days_remaining} Days Left
            </div>
          `}

          <div>
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:14px; margin-top:4px;">
              ${p.product && p.product.image_url ? `
                <img src="${p.product.image_url}" alt="${escapeHtml(p.title)}" style="width:50px; height:50px; object-fit:contain; border-radius:4px; border:1px solid #f1f5f9; background:#f8fafc;" onerror="this.src='/static/images/placeholder.jpg'">
              ` : `
                <div style="width:50px; height:50px; border-radius:8px; background:linear-gradient(135deg, #ede9fe, #ddd6fe); display:flex; align-items:center; justify-content:center; font-size:24px;">
                  🛍️
                </div>
              `}
              <div style="flex:1;">
                <h3 style="font-size:16px; font-weight:700; color:#1e293b; margin:0 0 4px;">${escapeHtml(p.title)}</h3>
                <div style="font-size:12px; color:#64748b;">Target Date: ${p.target_date || 'In 30 days'}</div>
              </div>
            </div>

            <!-- Progress Bar -->
            <div style="margin:14px 0 10px;">
              <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:6px;">
                <span style="font-weight:700; color:#10b981;">Saved: ₹${Number(p.saved_amount).toLocaleString('en-IN')}</span>
                <span style="font-weight:700; color:#1e293b;">Goal: ₹${Number(p.target_amount).toLocaleString('en-IN')}</span>
              </div>
              <div class="pretwin-progress-outer">
                <div class="pretwin-progress-bar" style="width: ${pct}%;"></div>
              </div>
              <div style="display:flex; justify-content:space-between; font-size:11.5px; color:#64748b; margin-top:4px;">
                <span>${pct}% completed</span>
                <span>Remaining: ₹${Number(p.remaining_amount).toLocaleString('en-IN')}</span>
              </div>
            </div>

            <!-- Breakdown Milestones -->
            <div style="background:#f8fafc; border-radius:6px; padding:10px 12px; margin:12px 0; display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px;">
              <div>
                <span style="color:#64748b; display:block; font-size:10.5px;">Daily Target:</span>
                <strong style="color:#4f46e5; font-size:13px;">₹${Number(p.daily_savings_rate).toLocaleString('en-IN')}/day</strong>
              </div>
              <div>
                <span style="color:#64748b; display:block; font-size:10.5px;">Weekly Target:</span>
                <strong style="color:#4f46e5; font-size:13px;">₹${Number(p.weekly_savings_rate).toLocaleString('en-IN')}/week</strong>
              </div>
            </div>

            ${p.notes ? `
              <div style="font-size:11.5px; color:#64748b; font-style:italic; margin-bottom:12px;">
                "${escapeHtml(p.notes)}"
              </div>
            ` : ''}
          </div>

          <!-- Actions -->
          <div style="margin-top:14px; pt-2; border-top:1px solid #f1f5f9; display:flex; gap:8px; align-items:center;">
            ${isComplete ? `
              <button onclick="handleReadyToShop(${p.id}, ${p.product_id || 'null'}, '${escapeHtml(p.title).replace(/'/g, "\\'")}', ${p.target_amount})" class="fk-btn-orange" style="flex:1; padding:8px 0; font-size:13px; font-weight:700; border-radius:4px;">
                Ready to Shop — Buy Now ➔
              </button>
            ` : `
              <button onclick="openAddDepositModal(${p.id}, '${escapeHtml(p.title).replace(/'/g, "\\'")}')" class="fk-btn-primary" style="flex:1; background:#4f46e5; color:#fff; border:none; padding:8px 0; border-radius:4px; font-weight:600; font-size:12.5px; cursor:pointer;">
                + Add Deposit
              </button>
            `}
            <button onclick="viewPlanContributions(${p.id})" style="background:#f1f5f9; border:1px solid #cbd5e1; color:#475569; padding:8px 12px; border-radius:4px; font-size:12px; font-weight:600; cursor:pointer;" title="View past contributions">
              History
            </button>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error("Savings load error:", err);
    container.innerHTML = `<div style="background:#fee2e2; color:#b91c1c; padding:20px; border-radius:6px; grid-column:1/-1;">Failed to load savings plans.</div>`;
  }
}

function openCreatePlanModal() {
  const m = document.getElementById("createPlanModal");
  if (m) m.style.display = "flex";
  const dt = document.getElementById("planTargetDate");
  if (dt) {
    const nextMonth = new Date();
    nextMonth.setDate(nextMonth.getDate() + 30);
    dt.value = nextMonth.toISOString().split("T")[0];
  }
}

function closeCreatePlanModal() {
  const m = document.getElementById("createPlanModal");
  if (m) m.style.display = "none";
}

async function handleCreatePlanSubmit(e) {
  e.preventDefault();
  const title = document.getElementById("planTitle").value.trim();
  const targetAmount = parseFloat(document.getElementById("planTargetAmount").value);
  const targetDate = document.getElementById("planTargetDate").value;
  const notes = document.getElementById("planNotes").value.trim();

  try {
    const res = await apiPost("/api/savings/plans", {
      title,
      target_amount: targetAmount,
      target_date: targetDate,
      notes
    });

    if (res.success) {
      showToast("Savings plan created successfully!", "success");
      closeCreatePlanModal();
      loadSavingsPlans();
    } else {
      showToast(res.error || "Failed to create plan", "error");
    }
  } catch (err) {
    showToast(err.message || "Error creating plan", "error");
  }
}

function openAddDepositModal(planId, planTitle) {
  const m = document.getElementById("addDepositModal");
  if (!m) return;
  document.getElementById("depositPlanId").value = planId;
  const sub = document.getElementById("depositPlanTitleSubtitle");
  if (sub) sub.textContent = `Logging deposit toward "${planTitle}"`;
  document.getElementById("depositAmount").value = "";
  m.style.display = "flex";
}

function closeAddDepositModal() {
  const m = document.getElementById("addDepositModal");
  if (m) m.style.display = "none";
}

async function handleAddDepositSubmit(e) {
  e.preventDefault();
  const planId = document.getElementById("depositPlanId").value;
  const amount = parseFloat(document.getElementById("depositAmount").value);
  const method = document.getElementById("depositMethod").value;
  const notes = document.getElementById("depositNotes").value.trim();

  try {
    const res = await apiPost(`/api/savings/plans/${planId}/contributions`, {
      amount,
      payment_method: method,
      notes
    });

    if (res.success) {
      showToast(`Recorded ₹${amount.toLocaleString('en-IN')} savings deposit!`, "success");
      closeAddDepositModal();
      loadSavingsPlans();
    } else {
      showToast(res.error || "Failed to add deposit", "error");
    }
  } catch (err) {
    showToast(err.message || "Error adding deposit", "error");
  }
}

async function viewPlanContributions(planId) {
  try {
    const res = await apiGet(`/api/savings/plans/${planId}`);
    const plan = res.plan;
    const contribs = plan.contributions || [];

    let msg = `Savings History for "${plan.title}":\n\n`;
    if (contribs.length === 0) {
      msg += "No contributions logged yet.";
    } else {
      contribs.forEach((c, idx) => {
        msg += `${idx + 1}. ₹${c.amount} on ${c.contribution_date} via ${c.payment_method || 'PreTwin'}${c.notes ? ' (' + c.notes + ')' : ''}\n`;
      });
    }
    alert(msg);
  } catch (e) {
    showToast("Failed to fetch contribution history", "error");
  }
}

function handleReadyToShop(planId, productId, title, amount) {
  // Add item or simulated item to cart and direct to checkout
  if (productId) {
    addChatProductToCart(productId, title, amount, "");
  } else {
    // Add generic goal product to cart
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem("pretwin_cart") || "[]"); } catch (e) {}
    cart.push({
      product_id: 1, // default product ID for seamless server verification
      id: 1,
      name: title,
      price: amount,
      quantity: 1,
      image_url: ""
    });
    localStorage.setItem("pretwin_cart", JSON.stringify(cart));
  }
  showToast("Goal item added to cart! Redirecting to checkout...", "success");
  setTimeout(() => {
    window.location.href = "/checkout";
  }, 1000);
}

document.addEventListener("DOMContentLoaded", () => {
  loadSavingsPlans();
});
