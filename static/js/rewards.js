/**
 * PreTwin Reward Points Controller
 */

let currentPointsBalance = 0;

async function loadRewardsDashboard() {
  const balanceEl = document.getElementById("pointsBalance");
  const rupeeEl = document.getElementById("rupeeEquivalence");
  const earnedEl = document.getElementById("lifetimeEarned");
  const redeemedEl = document.getElementById("lifetimeRedeemed");
  const tableBody = document.getElementById("rewardLedgerBody");

  try {
    // 1. Fetch Balance & Stats
    const balRes = await apiGet("/api/rewards/balance");
    currentPointsBalance = balRes.balance_points || 0;
    if (balanceEl) balanceEl.textContent = currentPointsBalance.toLocaleString('en-IN');
    if (rupeeEl) rupeeEl.textContent = `₹${(balRes.rupee_value || 0).toFixed(2)}`;
    if (earnedEl) earnedEl.textContent = (balRes.lifetime_earned || 0).toLocaleString('en-IN');
    if (redeemedEl) redeemedEl.textContent = (balRes.lifetime_redeemed || 0).toLocaleString('en-IN');

    // 2. Check for active credit voucher in session
    checkActiveCredit();

    // 3. Fetch Ledger Transactions
    const histRes = await apiGet("/api/rewards/history");
    const txs = histRes.transactions || [];

    if (tableBody) {
      if (txs.length === 0) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="5" style="padding: 36px; text-align: center; color: #64748b;">
              No reward transactions yet. Complete an order to earn your first points!
            </td>
          </tr>
        `;
        return;
      }

      tableBody.innerHTML = txs.map(t => {
        const isPositive = t.points > 0;
        const ptsSign = isPositive ? `+${t.points}` : `${t.points}`;
        const ptsColor = isPositive ? '#15803d' : '#b91c1c';
        const dateStr = t.created_at ? new Date(t.created_at).toLocaleDateString('en-IN', {
          year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }) : 'Recent';

        return `
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 12px 14px; color: #64748b; white-space: nowrap;">${dateStr}</td>
            <td style="padding: 12px 14px;">
              <span style="background: ${isPositive ? '#dcfce7' : '#fee2e2'}; color: ${isPositive ? '#166534' : '#991b1b'}; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;">
                ${escapeHtml(t.transaction_type)}
              </span>
            </td>
            <td style="padding: 12px 14px; color: #1e293b;">${escapeHtml(t.description)}</td>
            <td style="padding: 12px 14px; text-align: right; font-weight: 700; color: ${ptsColor};">
              ${ptsSign} pts
            </td>
            <td style="padding: 12px 14px; text-align: right; font-weight: 600; color: #64748b;">
              ₹${t.rupee_value ? t.rupee_value.toFixed(2) : (Math.abs(t.points) / 100).toFixed(2)}
            </td>
          </tr>
        `;
      }).join('');
    }

  } catch (err) {
    console.error("Rewards load error:", err);
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" style="padding: 24px; text-align: center; color: #ef4444;">
            Failed to load rewards data.
          </td>
        </tr>
      `;
    }
  }
}

async function checkActiveCredit() {
  const banner = document.getElementById("activeVoucherBanner");
  const textEl = document.getElementById("activeVoucherText");
  if (!banner || !textEl) return;

  try {
    const res = await apiGet("/api/rewards/active-credit");
    if (res.has_active_credit && res.credit) {
      const cr = res.credit;
      textEl.innerHTML = `You have an active store discount of <strong>₹${Number(cr.rupee_discount).toFixed(2)}</strong> (${cr.points} pts, Voucher <code>${escapeHtml(cr.code)}</code>) ready at checkout!`;
      banner.style.display = "flex";
    } else {
      banner.style.display = "none";
    }
  } catch (e) {
    banner.style.display = "none";
  }
}

function updateRedeemEstimate() {
  const inp = document.getElementById("redeemInput");
  const est = document.getElementById("redeemEstimateText");
  if (!inp || !est) return;

  const pts = parseInt(inp.value, 10) || 0;
  if (pts <= 0) {
    est.textContent = "= ₹0.00 discount";
    est.style.color = "#64748b";
  } else {
    const val = (pts / 100.0).toFixed(2);
    est.textContent = `= ₹${val} discount`;
    est.style.color = "#15803d";
  }
}

function setRedeemPoints(pts) {
  const inp = document.getElementById("redeemInput");
  if (inp) {
    inp.value = pts;
    updateRedeemEstimate();
  }
}

function setRedeemMax() {
  const inp = document.getElementById("redeemInput");
  if (inp) {
    inp.value = currentPointsBalance > 0 ? currentPointsBalance : 100;
    updateRedeemEstimate();
  }
}

async function handleRedeemPoints() {
  const inp = document.getElementById("redeemInput");
  const fb = document.getElementById("redeemFeedback");
  const btn = document.getElementById("redeemBtn");

  const pts = parseInt(inp ? inp.value : 0, 10);
  if (!pts || pts <= 0) {
    showFeedback("Please enter a valid positive number of points to redeem.", "error");
    return;
  }

  if (pts > currentPointsBalance) {
    showFeedback(`You only have ${currentPointsBalance} points available to redeem.`, "error");
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = "Redeeming...";
  }

  try {
    const res = await apiPost("/api/rewards/redeem", { points: pts });
    if (res.success) {
      showFeedback(res.message, "success");
      if (typeof showToast === "function") {
        showToast(res.message, "success");
      }
      if (inp) inp.value = "";
      updateRedeemEstimate();
      await loadRewardsDashboard();
    } else {
      showFeedback(res.error || "Failed to redeem points.", "error");
    }
  } catch (e) {
    showFeedback(e.message || "Redemption request failed.", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Redeem Points Now ➔";
    }
  }
}

async function handleClaimBonus() {
  try {
    const res = await apiPost("/api/rewards/claim-bonus", {});
    if (res.success) {
      if (typeof showToast === "function") {
        showToast(res.message, "success");
      } else {
        alert(res.message);
      }
      await loadRewardsDashboard();
    } else {
      alert(res.error || "Could not claim bonus points.");
    }
  } catch (e) {
    alert(e.message || "Failed to claim bonus.");
  }
}

function showFeedback(msg, type) {
  const fb = document.getElementById("redeemFeedback");
  if (!fb) return;
  fb.style.display = "block";
  fb.textContent = msg;
  if (type === "success") {
    fb.style.color = "#15803d";
  } else {
    fb.style.color = "#b91c1c";
  }
  setTimeout(() => {
    if (fb) fb.style.display = "none";
  }, 6000);
}

document.addEventListener("DOMContentLoaded", () => {
  loadRewardsDashboard();
});
