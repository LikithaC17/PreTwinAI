/**
 * PreTwin Reward Points Controller
 */

async function loadRewardsDashboard() {
  const balanceEl = document.getElementById("pointsBalance");
  const rupeeEl = document.getElementById("rupeeEquivalence");
  const earnedEl = document.getElementById("lifetimeEarned");
  const redeemedEl = document.getElementById("lifetimeRedeemed");
  const tableBody = document.getElementById("rewardLedgerBody");

  try {
    // 1. Fetch Balance & Stats
    const balRes = await apiGet("/api/rewards/balance");
    if (balanceEl) balanceEl.textContent = balRes.balance_points.toLocaleString('en-IN');
    if (rupeeEl) rupeeEl.textContent = `₹${balRes.rupee_value.toFixed(2)}`;
    if (earnedEl) earnedEl.textContent = balRes.lifetime_earned.toLocaleString('en-IN');
    if (redeemedEl) redeemedEl.textContent = balRes.lifetime_redeemed.toLocaleString('en-IN');

    // 2. Fetch Ledger Transactions
    const histRes = await apiGet("/api/rewards/history");
    const txs = histRes.transactions || [];

    if (tableBody) {
      if (txs.length === 0) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="5" style="padding: 36px; text-align: center; color: #64748b;">
              No reward transactions yet. Complete an order to earn your first 5 points!
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

document.addEventListener("DOMContentLoaded", () => {
  loadRewardsDashboard();
});
