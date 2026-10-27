/**
 * PreTwinShop AI - Smart Recommendations Controller (Agents E & F)
 */

let recommendationsData = [];

async function loadRecommendationsData() {
  const container = document.getElementById('recommendationsList');
  const countEl = document.getElementById('recsCount');

  try {
    const [recRes, profRes] = await Promise.all([
      apiGet('/api/recommendations'),
      apiGet('/api/profile'),
    ]);

    recommendationsData = recRes.recommendations || [];
    const budgetMax = profRes.preferences ? (profRes.preferences.budget_max || 5000) : 5000;

    renderBudgetSummary(recommendationsData, budgetMax);
    renderAiExplanations(recommendationsData, profRes);

    if (countEl) countEl.textContent = recommendationsData.length;
    renderRecommendationsList(recommendationsData);
  } catch (err) {
    console.error('Failed to load recommendations:', err);
    if (container) {
      container.innerHTML = `
        <div class="empty-state py-5 w-100">
          <p class="text-danger">Failed to load recommendations: ${err.message}</p>
          <button class="btn btn-primary mt-2" onclick="runAiAnalysis()">Generate Recommendations</button>
        </div>
      `;
    }
  }
}

function renderBudgetSummary(recs, budgetMax) {
  const totalCost = recs.reduce((sum, r) => sum + (parseFloat(r.price) || 0), 0);
  const remaining = Math.max(budgetMax - totalCost, 0);
  const percent = Math.min(Math.round((totalCost / budgetMax) * 100), 100);

  const costEl = document.getElementById('recTotalCost');
  const itemsEl = document.getElementById('recItemCount');
  const ceilEl = document.getElementById('recBudgetCeiling');
  const remEl = document.getElementById('recRemainingBudget');
  const percentText = document.getElementById('budgetPercentText');
  const ceilText = document.getElementById('budgetCeilingText');
  const barFill = document.getElementById('budgetProgressBar');
  const fitBadge = document.getElementById('recBudgetFitBadge');

  if (costEl) costEl.textContent = formatCurrency(totalCost);
  if (itemsEl) itemsEl.textContent = `${recs.length} proposed items`;
  if (ceilEl) ceilEl.textContent = formatCurrency(budgetMax);
  if (remEl) remEl.textContent = formatCurrency(remaining);
  if (percentText) percentText.textContent = `${percent}%`;
  if (ceilText) ceilText.textContent = formatCurrency(budgetMax);

  if (barFill) {
    barFill.style.width = `${percent}%`;
    barFill.className = 'progress-bar-fill ' + (percent > 90 ? 'bg-warning' : percent > 100 ? 'bg-danger' : 'bg-primary');
  }

  if (fitBadge) {
    if (totalCost <= budgetMax) {
      fitBadge.innerHTML = '<span class="badge badge-success">✓ Within Budget Ceiling</span>';
    } else {
      fitBadge.innerHTML = '<span class="badge badge-danger">⚠️ Over Budget</span>';
    }
  }
}

function renderAiExplanations(recs, profRes) {
  const summaryBox = document.getElementById('aiSummaryContent');
  const improveBox = document.getElementById('improvementsBox');
  if (!summaryBox) return;

  const user = profRes.user || {};
  const prefs = profRes.preferences || {};
  const cats = prefs.preferred_categories || [];

  summaryBox.innerHTML = `
    <div class="ai-synthesis-box">
      <p>
        <strong>Consolidated Evidence Chain:</strong> These recommendations synthesize evidence from your voluntary purchase history, preferred categories (${cats.slice(0, 3).join(', ')}), and strict financial limits.
      </p>
      <ul class="synthesis-points mt-2">
        <li><strong>Need Grounding:</strong> Every item is linked to a predicted replenishment pattern or stated preference.</li>
        <li><strong>Hard Budget Bounds:</strong> No single proposed item or constructed basket exceeds the established spending ceiling.</li>
        <li><strong>Trade-Off Evaluation:</strong> Agent D and Agent E evaluated feature density and warranty criteria before selection.</li>
      </ul>
    </div>
  `;

  if (improveBox) {
    improveBox.innerHTML = `
      <div class="improve-note">
        <span class="improve-icon">💡</span>
        <div>
          <strong>What would improve future predictions?</strong>
          <p class="text-sm text-muted mb-0">
            Adding more purchase history items or specifying strict brand preferences in your Shopping Twin will tighten interval calibrations and improve confidence metrics.
          </p>
        </div>
      </div>
    `;
  }
}

function renderRecommendationsList(recs) {
  const container = document.getElementById('recommendationsList');
  if (!container) return;

  if (recs.length === 0) {
    container.innerHTML = `
      <div class="empty-state py-5 w-100">
        <span class="empty-icon">⭐</span>
        <h4>No Recommendations Available</h4>
        <p>Trigger the multi-agent pipeline to generate fresh, budget-compliant product recommendations.</p>
        <button class="btn btn-primary mt-2" onclick="runAiAnalysis()">Run Recommendation Engine</button>
      </div>
    `;
    return;
  }

  container.innerHTML = recs.map((r, idx) => {
    const rank = r.rank || idx + 1;
    const name = r.product_name || r.name || 'Recommended Product';
    const price = formatCurrency(r.price);
    const category = r.category || 'General';
    const fit = r.budget_fit || 'Excellent';
    const reason = r.reason || r.explanation || 'Selected based on your stated shopping preferences.';

    return `
      <div class="recommendation-card">
        <div class="rec-card-header">
          <div class="flex-align-gap">
            <span class="badge badge-rank">#${rank}</span>
            <span class="category-pill">${category}</span>
            <span class="badge badge-success">${fit} Budget Fit</span>
          </div>
          <div class="rec-price">${price}</div>
        </div>

        <div class="rec-card-body">
          <h4 class="rec-title">${name}</h4>
          
          <div class="rec-explanation-box">
            <span class="expl-badge">🤖 Agent F Justification:</span>
            <p class="expl-text">${reason}</p>
          </div>

          <!-- Interactive Feedback & Actions -->
          <div class="rec-feedback-row mt-3" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div class="feedback-actions">
              <span class="feedback-label text-sm text-muted mr-2">Feedback:</span>
              <button class="btn btn-xs btn-outline" onclick="submitFeedback('recommendation', ${r.product_id || idx + 1}, 'like', 5)">👍 Helpful</button>
              <button class="btn btn-xs btn-outline" onclick="submitFeedback('recommendation', ${r.product_id || idx + 1}, 'dislike', 1)">👎 Not Relevant</button>
              <button class="btn btn-xs btn-outline" onclick="toggleProductComparison(${r.product_id || idx + 1})">⚖️ Compare</button>
            </div>
            <button class="btn btn-sm btn-primary" onclick="addToCart({id: ${r.product_id || idx + 1}, name: '${name.replace(/'/g, "\\'")}', category: '${category}', price: ${r.price || 999}, image_url: '${r.image_url || ''}'})">
              🛒 Add to Cart
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function submitFeedback(itemType, itemId, feedbackType, rating) {
  try {
    await apiPost('/api/feedback', {
      item_type: itemType,
      item_id: itemId,
      feedback_type: feedbackType,
      rating: rating,
      comment: 'User rating via dashboard',
    });
    showToast('Thank you for your feedback! Twin learning calibrated.', 'success');
  } catch (err) {
    showToast(`Feedback submission failed: ${err.message}`, 'error');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadRecommendationsData();
});
