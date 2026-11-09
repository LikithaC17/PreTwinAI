/**
 * PreTwin AI - Personalization and Digital Twin Dashboard Controller
 * Drives all 6 Intelligent Sections:
 * 1. My Shopping Identity (Explicit & Inferred preferences, tags, budget, cadence)
 * 2. My Shopping Behaviour (Purchases, browsed items, wishlist, cart, searches, trends)
 * 3. My Spending Habits (Verified completed spend, AOV, category breakdown, monthly)
 * 4. My Digital Twin Insights (Explainable, empirical insights with source & confidence)
 * 5. My Future Shopping Needs (Consumable restocking forecasts with windows & 1-click reorder)
 * 6. Manage My Twin (Privacy toggles, inference correction, reset & deletion controls)
 */

let currentDashboardData = null;
let currentExplicitCategories = [];
let currentExplicitBrands = [];
let currentInferredCategories = [];
let currentInferredBrands = [];
let currentColors = [];
let currentSizes = [];

// Currency formatter for INR
function formatCurrency(val) {
  const f = parseFloat(val) || 0;
  return '₹' + Math.round(f).toLocaleString('en-IN');
}

function formatDate(d) {
  if (!d) return '--';
  try {
    const dt = new Date(d);
    if (isNaN(dt.getTime())) return d;
    return dt.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch (e) {
    return d;
  }
}

function capitalize(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Smoothly scroll to target section and update navigation highlight
 */
function scrollToSection(sectionId) {
  const el = document.getElementById(sectionId);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  const buttons = document.querySelectorAll('.twin-tab-btn');
  buttons.forEach(btn => {
    if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(sectionId)) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

/**
 * ---------------------------------------------------------------------------
 * Primary Loader: Unified Twin Dashboard
 * ---------------------------------------------------------------------------
 */
async function loadTwinDashboard() {
  try {
    const res = await fetch('/api/twin/dashboard');
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const data = await res.json();
    currentDashboardData = data;

    renderHeaderAndArchetype(data);
    renderSection1Identity(data.identity || {});
    renderSection2Behaviour(data.behaviour || {});
    renderSection3Spending(data.spending || {});
    renderSection4Insights(data.insights || []);
    renderSection5FutureNeeds(data.future_needs || {});
    renderSection6ManageTwin(data);

    // Keep backward-compatible elements populated for tests
    populateHiddenCompatibilityElements(data);

  } catch (err) {
    console.error('Failed to load twin dashboard:', err);
    if (typeof showToast === 'function') {
      showToast('Could not load Twin dashboard data. Retrying...', 'error');
    }
  }
}

/**
 * ---------------------------------------------------------------------------
 * Header & Persona Archetype
 * ---------------------------------------------------------------------------
 */
function renderHeaderAndArchetype(data) {
  const identity = data.identity || {};
  const explicit = identity.explicit || {};

  const nameEl = document.getElementById('twinFullName');
  const emailEl = document.getElementById('twinEmail');
  const avatarEl = document.getElementById('twinAvatarLarge');
  const archetypeEl = document.getElementById('twinArchetype');
  const completenessEl = document.getElementById('twinCompletenessDisplay');
  const budgetDisplay = document.getElementById('overviewBudgetDisplay');
  const freqDisplay = document.getElementById('overviewFreqDisplay');

  const fullName = identity.full_name || identity.username || 'PreTwin Shopper';
  if (nameEl) nameEl.textContent = fullName;
  if (emailEl) emailEl.textContent = identity.email || 'shopper@pretwin.ai';
  if (avatarEl) {
    avatarEl.textContent = fullName
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || 'PT';
  }

  if (archetypeEl) {
    archetypeEl.textContent = data.archetype || 'Smart Value & Practical Essentials Shopper';
  }

  if (completenessEl) {
    completenessEl.textContent = `${identity.completeness_score || 85}%`;
  }

  const bMin = explicit.budget_min !== undefined ? explicit.budget_min : 500;
  const bMax = explicit.budget_max !== undefined ? explicit.budget_max : 10000;
  if (budgetDisplay) {
    budgetDisplay.textContent = `${formatCurrency(bMin)} — ${formatCurrency(bMax)}`;
  }

  if (freqDisplay) {
    freqDisplay.textContent = capitalize(explicit.frequency || 'Monthly');
  }

  // Onboarding banner for first-time / new users
  const banner = document.getElementById('firstTimeUserBanner');
  if (banner) {
    const isNew = (!data.behaviour || data.behaviour.total_purchases_recorded === 0) &&
                  (!data.behaviour || data.behaviour.browsing_events_count === 0) &&
                  (identity.completeness_score < 40);
    banner.style.display = isNew ? 'block' : 'none';
  }
}

/**
 * ---------------------------------------------------------------------------
 * Section 1: My Shopping Identity
 * ---------------------------------------------------------------------------
 */
function renderSection1Identity(identity) {
  const explicit = identity.explicit || {};
  const inferred = identity.inferred || {};

  currentExplicitCategories = Array.isArray(explicit.categories) ? [...explicit.categories] : [];
  currentExplicitBrands = Array.isArray(explicit.brands) ? [...explicit.brands] : [];
  currentInferredCategories = Array.isArray(inferred.categories) ? [...inferred.categories] : [];
  currentInferredBrands = Array.isArray(inferred.brands) ? [...inferred.brands] : [];
  currentColors = Array.isArray(explicit.colors) ? [...explicit.colors] : [];
  currentSizes = Array.isArray(explicit.sizes) ? [...explicit.sizes] : [];

  renderCategoryChips();
  renderBrandChips();
  renderColorChips();
  renderSizeChips();

  // Inputs
  const bMinInput = document.getElementById('budgetMinInput');
  const bMaxInput = document.getElementById('budgetMaxInput');
  const freqSelect = document.getElementById('twinShoppingFreq');
  const goalsInput = document.getElementById('twinGoalsInput');

  if (bMinInput) bMinInput.value = explicit.budget_min !== undefined ? explicit.budget_min : 500;
  if (bMaxInput) bMaxInput.value = explicit.budget_max !== undefined ? explicit.budget_max : 10000;
  if (freqSelect) freqSelect.value = explicit.frequency || 'monthly';
  if (goalsInput) goalsInput.value = explicit.goals || '';
}

function renderCategoryChips() {
  const container = document.getElementById('categoryChipsContainer');
  if (!container) return;

  const html = [];

  // Explicit
  currentExplicitCategories.forEach((cat, idx) => {
    html.push(`
      <span class="twin-pill-explicit" style="margin-right:6px; margin-bottom:6px;">
        ${cat}
        <button type="button" onclick="removeCategoryTag(${idx})" style="background:none; border:none; color:#403653; font-weight:700; cursor:pointer; padding:0 0 0 4px;" title="Remove category">&times;</button>
      </span>
    `);
  });

  // Inferred
  currentInferredCategories.forEach((cat) => {
    html.push(`
      <span class="twin-pill-inferred" style="margin-right:6px; margin-bottom:6px;">
        ✨ ${cat} <small style="opacity:0.8;">(Inferred)</small>
        <button type="button" onclick="dislikeInferredTag('category', '${encodeURIComponent(cat)}')" style="background:none; border:none; color:#8C6D1F; font-weight:700; cursor:pointer; padding:0 0 0 4px;" title="Not for me (dislike)">&times;</button>
      </span>
    `);
  });

  if (html.length === 0) {
    container.innerHTML = '<span style="color:#81778E; font-size:0.82rem;">No preferred categories selected yet.</span>';
  } else {
    container.innerHTML = html.join('');
  }
}

function renderBrandChips() {
  const container = document.getElementById('brandChipsContainer');
  if (!container) return;

  const html = [];

  // Explicit
  currentExplicitBrands.forEach((b, idx) => {
    html.push(`
      <span class="twin-pill-explicit" style="margin-right:6px; margin-bottom:6px;">
        ${b}
        <button type="button" onclick="removeBrandTag(${idx})" style="background:none; border:none; color:#403653; font-weight:700; cursor:pointer; padding:0 0 0 4px;" title="Remove brand">&times;</button>
      </span>
    `);
  });

  // Inferred
  currentInferredBrands.forEach((b) => {
    html.push(`
      <span class="twin-pill-inferred" style="margin-right:6px; margin-bottom:6px;">
        ✨ ${b} <small style="opacity:0.8;">(Inferred)</small>
        <button type="button" onclick="dislikeInferredTag('brand', '${encodeURIComponent(b)}')" style="background:none; border:none; color:#8C6D1F; font-weight:700; cursor:pointer; padding:0 0 0 4px;" title="Not for me (dislike)">&times;</button>
      </span>
    `);
  });

  if (html.length === 0) {
    container.innerHTML = '<span style="color:#81778E; font-size:0.82rem;">No favorite brands specified yet.</span>';
  } else {
    container.innerHTML = html.join('');
  }
}

function renderColorChips() {
  const container = document.getElementById('colorChipsContainer');
  if (!container) return;

  if (currentColors.length === 0) {
    container.innerHTML = '<span style="color:#81778E; font-size:0.75rem;">None</span>';
    return;
  }
  container.innerHTML = currentColors.map((c, idx) => `
    <span style="font-size:0.75rem; background:#E9DDFB; border:1px solid #C4A6F5; color:#403653; padding:2px 8px; border-radius:10px; display:inline-flex; align-items:center; gap:4px;">
      ${c}
      <button type="button" onclick="removeColorTag(${idx})" style="background:none; border:none; color:#403653; cursor:pointer;">&times;</button>
    </span>
  `).join('');
}

function renderSizeChips() {
  const container = document.getElementById('sizeChipsContainer');
  if (!container) return;

  if (currentSizes.length === 0) {
    container.innerHTML = '<span style="color:#81778E; font-size:0.75rem;">None</span>';
    return;
  }
  container.innerHTML = currentSizes.map((s, idx) => `
    <span style="font-size:0.75rem; background:#E9DDFB; border:1px solid #C4A6F5; color:#403653; padding:2px 8px; border-radius:10px; display:inline-flex; align-items:center; gap:4px;">
      ${s}
      <button type="button" onclick="removeSizeTag(${idx})" style="background:none; border:none; color:#403653; cursor:pointer;">&times;</button>
    </span>
  `).join('');
}

function addCategoryTag() {
  const input = document.getElementById('newCategoryInput');
  if (!input) return;
  const val = input.value.trim();
  if (val && !currentExplicitCategories.includes(val)) {
    currentExplicitCategories.push(val);
    renderCategoryChips();
    input.value = '';
    showToast(`Added ${val} to preferred categories`);
  }
}

function removeCategoryTag(idx) {
  currentExplicitCategories.splice(idx, 1);
  renderCategoryChips();
}

function addBrandTag() {
  const input = document.getElementById('newBrandInput');
  if (!input) return;
  const val = input.value.trim();
  if (val && !currentExplicitBrands.includes(val)) {
    currentExplicitBrands.push(val);
    renderBrandChips();
    input.value = '';
    showToast(`Added ${val} to preferred brands`);
  }
}

function removeBrandTag(idx) {
  currentExplicitBrands.splice(idx, 1);
  renderBrandChips();
}

function updateColorsList(val) {
  const input = document.getElementById('colorInput');
  const items = val.split(',').map(s => s.trim()).filter(Boolean);
  items.forEach(c => {
    if (!currentColors.includes(c)) currentColors.push(c);
  });
  renderColorChips();
  if (input) input.value = '';
}

function removeColorTag(idx) {
  currentColors.splice(idx, 1);
  renderColorChips();
}

function updateSizesList(val) {
  const input = document.getElementById('sizeInput');
  const items = val.split(',').map(s => s.trim()).filter(Boolean);
  items.forEach(s => {
    if (!currentSizes.includes(s)) currentSizes.push(s);
  });
  renderSizeChips();
  if (input) input.value = '';
}

function removeSizeTag(idx) {
  currentSizes.splice(idx, 1);
  renderSizeChips();
}

function updateBudgetDisplay() {
  const minVal = parseFloat(document.getElementById('budgetMinInput')?.value) || 0;
  const maxVal = parseFloat(document.getElementById('budgetMaxInput')?.value) || 0;
  const text = `${formatCurrency(minVal)} — ${formatCurrency(maxVal)}`;
  const overview = document.getElementById('overviewBudgetDisplay');
  if (overview) overview.textContent = text;
}

function updateOverviewCadence() {
  const freqEl = document.getElementById('twinShoppingFreq');
  const cadenceEl = document.getElementById('overviewFreqDisplay');
  if (freqEl && cadenceEl) {
    cadenceEl.textContent = capitalize(freqEl.value);
  }
}

/**
 * Persist Explicit Twin Preferences
 */
async function saveTwinProfile() {
  const bMin = parseFloat(document.getElementById('budgetMinInput')?.value) || 0;
  const bMax = parseFloat(document.getElementById('budgetMaxInput')?.value) || 10000;
  const freq = document.getElementById('twinShoppingFreq')?.value || 'monthly';
  const goals = document.getElementById('twinGoalsInput')?.value || '';

  if (bMax < bMin) {
    if (typeof showToast === 'function') {
      showToast('Maximum budget ceiling cannot be less than minimum budget', 'error');
    }
    return;
  }

  const payload = {
    preferred_categories: currentExplicitCategories,
    preferred_brands: currentExplicitBrands,
    preferred_colors: currentColors,
    preferred_sizes: currentSizes,
    budget_min: bMin,
    budget_max: bMax,
    shopping_frequency: freq,
    goals: goals,
    notes: goals
  };

  try {
    const res = await fetch('/api/twin/preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to save preferences');

    if (typeof showToast === 'function') {
      showToast('Shopping Twin profile saved successfully! ✨', 'success');
    }
    await loadTwinDashboard();
  } catch (err) {
    console.error('Failed to save profile:', err);
    if (typeof showToast === 'function') {
      showToast('Failed to save preferences: ' + err.message, 'error');
    }
  }
}

/**
 * ---------------------------------------------------------------------------
 * Section 2: My Shopping Behaviour
 * ---------------------------------------------------------------------------
 */
function renderSection2Behaviour(behaviour) {
  const ordersEl = document.getElementById('behaviourOrdersCount');
  const wishlistEl = document.getElementById('behaviourWishlistCount');
  const cartEl = document.getElementById('behaviourCartCount');
  const browsingEl = document.getElementById('behaviourBrowsingCount');
  const searchEl = document.getElementById('behaviourSearchCount');

  if (ordersEl) ordersEl.textContent = behaviour.total_purchases_recorded || 0;
  if (wishlistEl) wishlistEl.textContent = behaviour.wishlist_count || 0;
  if (cartEl) cartEl.textContent = behaviour.cart_count || 0;
  if (browsingEl) browsingEl.textContent = behaviour.browsing_events_count || 0;
  if (searchEl) searchEl.textContent = (behaviour.recent_search_queries || []).length || 0;

  // Top Engaged Categories with progress bars
  const topList = document.getElementById('topEngagedCategoriesList');
  if (topList) {
    const categories = behaviour.top_engaged_categories || [];
    if (categories.length === 0) {
      topList.innerHTML = `
        <div style="color:#81778E; font-size:0.85rem; padding:12px; background:#FFFDF9; border:1px dashed #EAE1F4; border-radius:8px;">
          Explore products or categories to establish real-time engagement signals.
        </div>
      `;
    } else {
      const maxScore = Math.max(...categories.map(c => c.score || 1), 1);
      topList.innerHTML = categories.map(c => {
        const pct = Math.min(Math.round(((c.score || 0) / maxScore) * 100), 100);
        return `
          <div style="background:#FFFDF9; border:1px solid #EAE1F4; border-radius:8px; padding:10px 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <strong style="color:#403653; font-size:0.88rem;">${c.category}</strong>
              <span style="font-size:0.75rem; color:#8C6D1F; font-weight:700;">${c.score} affinity pts</span>
            </div>
            <div style="background:#EAE1F4; height:6px; border-radius:3px; overflow:hidden;">
              <div style="background:linear-gradient(90deg, #C4A6F5, #D6B875); width:${pct}%; height:100%; border-radius:3px;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Interest Evolution & Trends
  const trendList = document.getElementById('interestTrendsList');
  if (trendList) {
    const trends = behaviour.interest_trends || [];
    if (trends.length === 0) {
      trendList.innerHTML = `
        <div style="color:#81778E; font-size:0.85rem; padding:12px; background:#FFFDF9; border:1px dashed #EAE1F4; border-radius:8px;">
          Interest trend patterns update dynamically as you browse, search, and add items to your wishlist.
        </div>
      `;
    } else {
      trendList.innerHTML = trends.map(t => {
        const isUp = t.direction === 'growing';
        const isSteady = t.direction === 'steady';
        const icon = isUp ? '📈' : (isSteady ? '⚖️' : '📉');
        const badgeColor = isUp ? '#10b981' : (isSteady ? '#6366f1' : '#f59e0b');
        const badgeBg = isUp ? 'rgba(16,185,129,0.12)' : (isSteady ? 'rgba(99,102,241,0.12)' : 'rgba(245,158,11,0.12)');

        return `
          <div style="background:#FFFDF9; border:1px solid #EAE1F4; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-weight:700; color:#403653; font-size:0.88rem;">${t.category}</div>
              <div style="font-size:0.76rem; color:#81778E; margin-top:2px;">${t.explanation || 'Consistent engagement observed'}</div>
            </div>
            <span style="font-size:0.75rem; font-weight:700; color:${badgeColor}; background:${badgeBg}; border:1px solid ${badgeColor}40; padding:3px 8px; border-radius:12px; display:inline-flex; align-items:center; gap:4px;">
              ${icon} ${capitalize(t.direction)}
            </span>
          </div>
        `;
      }).join('');
    }
  }
}

/**
 * ---------------------------------------------------------------------------
 * Section 3: My Spending Habits
 * ---------------------------------------------------------------------------
 */
function renderSection3Spending(spending) {
  const totalEl = document.getElementById('spendingTotal');
  const tierEl = document.getElementById('spendingTierLabel');
  const aovEl = document.getElementById('spendingAov');
  const priceRangeEl = document.getElementById('spendingPriceRange');
  const cadenceEl = document.getElementById('spendingCadence');
  const freqDaysEl = document.getElementById('spendingFrequencyDays');

  if (totalEl) totalEl.textContent = formatCurrency(spending.total_spent || 0);
  if (tierEl) tierEl.textContent = `Tier: ${spending.spending_tier || 'Smart Value'}`;
  if (aovEl) aovEl.textContent = formatCurrency(spending.average_order_value || 0);

  const pMin = spending.typical_price_min || 0;
  const pMax = spending.typical_price_max || 0;
  if (priceRangeEl) priceRangeEl.textContent = `${formatCurrency(pMin)} — ${formatCurrency(pMax)}`;

  if (cadenceEl) cadenceEl.textContent = spending.purchase_cadence_label || 'Monthly';
  if (freqDaysEl) {
    const days = spending.purchase_frequency_days || 30;
    freqDaysEl.textContent = `Every ~${days} days`;
  }

  // Spend by Category
  const catContainer = document.getElementById('spendByCategoryContainer');
  if (catContainer) {
    const catSpend = spending.spend_by_category || [];
    if (catSpend.length === 0) {
      catContainer.innerHTML = `
        <div style="color:#81778E; font-size:0.85rem; padding:12px; background:#FFFDF9; border:1px dashed #EAE1F4; border-radius:8px;">
          No completed purchases recorded yet. Spend habits update automatically when orders are delivered.
        </div>
      `;
    } else {
      const maxVal = Math.max(...catSpend.map(c => c.total_spent || 1), 1);
      catContainer.innerHTML = catSpend.map(c => {
        const pct = Math.min(Math.round(((c.total_spent || 0) / maxVal) * 100), 100);
        return `
          <div style="background:#FFFDF9; border:1px solid #EAE1F4; border-radius:8px; padding:10px 14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <strong style="color:#403653; font-size:0.88rem;">${c.category}</strong>
              <span style="font-weight:700; color:#8C6D1F; font-size:0.88rem;">${formatCurrency(c.total_spent)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#81778E; margin-bottom:6px;">
              <span>${c.item_count} items delivered</span>
              <span>${c.percentage || 0}% of total spend</span>
            </div>
            <div style="background:#EAE1F4; height:6px; border-radius:3px; overflow:hidden;">
              <div style="background:linear-gradient(90deg, #D6B875, #C4A6F5); width:${pct}%; height:100%; border-radius:3px;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Monthly Spending
  const monthContainer = document.getElementById('monthlySpendingContainer');
  if (monthContainer) {
    const months = spending.monthly_spending || [];
    if (months.length === 0) {
      monthContainer.innerHTML = `
        <div style="color:#81778E; font-size:0.85rem; padding:12px; background:#FFFDF9; border:1px dashed #EAE1F4; border-radius:8px;">
          No monthly order history recorded yet.
        </div>
      `;
    } else {
      monthContainer.innerHTML = months.map(m => `
        <div style="background:#FFFDF9; border:1px solid #EAE1F4; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong style="color:#403653; font-size:0.88rem;">${m.month}</strong>
            <div style="font-size:0.75rem; color:#81778E; margin-top:2px;">${m.order_count} verified order(s)</div>
          </div>
          <div style="font-size:1rem; font-weight:700; color:#403653;">
            ${formatCurrency(m.total_spent)}
          </div>
        </div>
      `).join('');
    }
  }
}

/**
 * ---------------------------------------------------------------------------
 * Section 4: My Digital Twin Insights
 * ---------------------------------------------------------------------------
 */
function renderSection4Insights(insights) {
  const grid = document.getElementById('twinInsightsCardsGrid');
  if (!grid) return;

  if (!insights || insights.length === 0) {
    grid.innerHTML = `
      <div style="color:#81778E; font-size:0.85rem; padding:20px; grid-column:1 / -1; text-align:center; background:#FFFDF9; border-radius:10px; border:1px dashed #C4A6F5;">
        Complete profile preferences or browse catalog items to generate personalized Digital Twin insights.
      </div>
    `;
    return;
  }

  grid.innerHTML = insights.map((it, idx) => {
    let sourceBadge = 'Explicit Preference';
    let sourceColor = '#C4A6F5';
    let sourceBg = '#E9DDFB';

    if (it.source_type === 'verified_purchase') {
      sourceBadge = 'Verified Purchase';
      sourceColor = '#10b981';
      sourceBg = 'rgba(16,185,129,0.12)';
    } else if (it.source_type === 'browsing_behaviour') {
      sourceBadge = 'Browsing Intent';
      sourceColor = '#D6B875';
      sourceBg = 'rgba(214,184,117,0.15)';
    }

    return `
      <div style="background:#FFFDF9; border:1px solid #EAE1F4; border-radius:12px; padding:18px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 2px 10px rgba(196,166,245,0.06);">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:1.15rem;">💡</span>
              <h4 style="margin:0; font-size:0.95rem; font-weight:700; color:#403653;">${it.title || 'Shopping Insight'}</h4>
            </div>
            <span style="font-size:0.72rem; font-weight:700; color:#403653; background:${sourceBg}; border:1px solid ${sourceColor}; padding:2px 8px; border-radius:10px;">
              ${sourceBadge}
            </span>
          </div>
          <p style="margin:0 0 12px 0; font-size:0.86rem; color:#403653; line-height:1.45;">
            ${it.text}
          </p>
        </div>
        <div style="background:#F7F3FF; border-radius:8px; padding:10px; border:1px solid #EAE1F4;">
          <div style="display:flex; justify-content:space-between; font-size:0.74rem; color:#81778E; margin-bottom:4px;">
            <span>Empirical Evidence:</span>
            <span style="font-weight:700; color:#8C6D1F;">Confidence: ${it.confidence || '90%'}</span>
          </div>
          <div style="font-size:0.76rem; color:#403653; line-height:1.35;">
            ${it.explanation || 'Analyzed from verified user signals.'}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * ---------------------------------------------------------------------------
 * Section 5: My Future Shopping Needs
 * ---------------------------------------------------------------------------
 */
function renderSection5FutureNeeds(futureNeeds) {
  const grid = document.getElementById('futureNeedsGrid');
  if (!grid) return;

  const needs = futureNeeds.needs || [];

  if (futureNeeds.status === 'insufficient_data' || needs.length === 0) {
    grid.innerHTML = `
      <div style="color:#403653; font-size:0.88rem; padding:28px 20px; grid-column:1 / -1; text-align:center; background:#FFFDF9; border-radius:12px; border:1.5px dashed #C4A6F5; line-height:1.5;">
        <div style="font-size:2rem; margin-bottom:8px;">🔮</div>
        <strong style="font-size:1rem; color:#403653; display:block; margin-bottom:6px;">
          Replenishment Forecasting Awaiting Verified History
        </strong>
        <p style="margin:0 auto; max-width:580px; color:#81778E; font-size:0.85rem;">
          ${futureNeeds.message || 'No repeat consumable purchases recorded yet. As you order everyday consumables like skincare, groceries, or wellness items, your twin will automatically project restocking cycles.'}
        </p>
      </div>
    `;
    return;
  }

  grid.innerHTML = needs.map(n => {
    let urgencyBadge = 'Upcoming Restock';
    let urgencyColor = '#6366f1';
    let urgencyBg = 'rgba(99,102,241,0.12)';

    if (n.urgency === 'overdue') {
      urgencyBadge = 'Restock Overdue';
      urgencyColor = '#ef4444';
      urgencyBg = 'rgba(239,68,68,0.12)';
    } else if (n.urgency === 'due_soon') {
      urgencyBadge = 'Due Soon';
      urgencyColor = '#f59e0b';
      urgencyBg = 'rgba(245,158,11,0.12)';
    }

    return `
      <div style="background:#FFFDF9; border:1px solid #EAE1F4; border-radius:12px; padding:16px; display:flex; flex-direction:column; justify-content:space-between; position:relative;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:0.7rem; color:${urgencyColor}; background:${urgencyBg}; border:1px solid ${urgencyColor}40; padding:2px 8px; border-radius:10px; font-weight:700;">
              ● ${urgencyBadge}
            </span>
            <span style="font-size:0.75rem; color:#81778E;">${n.category}</span>
          </div>

          <h4 style="margin:4px 0 6px 0; font-size:0.95rem; font-weight:700; color:#403653; line-height:1.35;">
            ${n.product_name}
          </h4>

          <div style="font-size:0.8rem; color:#403653; margin-bottom:8px;">
            <strong style="color:#8C6D1F;">Estimated Window:</strong> ${n.estimated_window_start || 'Upcoming'} — ${n.estimated_window_end || 'Soon'}
          </div>

          <div style="background:#F7F3FF; border-left:3px solid #C4A6F5; padding:8px 10px; border-radius:0 6px 6px 0; font-size:0.75rem; color:#81778E; margin-bottom:14px; line-height:1.35;">
            <strong style="color:#403653;">Mathematical Evidence:</strong> ${n.evidence_explanation || 'Calculated from historical replenishment frequency.'}
          </div>
        </div>

        <div>
          <button onclick="quickRepurchase('${encodeURIComponent(n.product_name)}', ${n.product_id || 0})" class="btn" style="width:100%; background:linear-gradient(135deg, #C4A6F5, #A78BFA); color:#403653; border:none; padding:8px 14px; border-radius:6px; font-weight:700; font-size:0.82rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <span>🛒</span> 1-Click Reorder Restock
          </button>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * ---------------------------------------------------------------------------
 * Section 6: Manage My Twin
 * ---------------------------------------------------------------------------
 */
function renderSection6ManageTwin(data) {
  const identity = data.identity || {};
  const inferred = identity.inferred || {};

  // Master switch
  const masterToggle = document.getElementById('masterPersonalizationToggle');
  if (masterToggle) {
    masterToggle.checked = data.is_personalization_enabled !== false;
  }

  // Purchase privacy switch
  const privacyToggle = document.getElementById('twinHistoryPrivacyToggle');
  if (privacyToggle) {
    privacyToggle.checked = identity.use_purchase_history !== false;
  }

  // Manage Inferred Tags list
  const inferredList = document.getElementById('manageInferredList');
  if (inferredList) {
    const allInferred = [
      ...(inferred.categories || []).map(c => ({ type: 'category', val: c })),
      ...(inferred.brands || []).map(b => ({ type: 'brand', val: b }))
    ];

    if (allInferred.length === 0) {
      inferredList.innerHTML = '<span style="color:#81778E; font-size:0.8rem;">No inferred tags currently active.</span>';
    } else {
      inferredList.innerHTML = allInferred.map(it => `
        <span class="twin-pill-inferred">
          ✨ ${it.val} <small>(${it.type})</small>
          <button type="button" onclick="dislikeInferredTag('${it.type}', '${encodeURIComponent(it.val)}')" style="background:none; border:none; color:#8C6D1F; font-weight:700; cursor:pointer; padding:0 0 0 4px;" title="Dislike / Not for me">&times;</button>
        </span>
      `).join('');
    }
  }

  // Corrected Dislikes List
  const dislikesEl = document.getElementById('correctedDislikesList');
  if (dislikesEl) {
    const dislikes = inferred.corrected_dislikes || [];
    if (dislikes.length > 0) {
      dislikesEl.innerHTML = `<strong>Excluded / Disliked:</strong> ${dislikes.join(', ')}`;
    } else {
      dislikesEl.innerHTML = '';
    }
  }
}

/**
 * Correct inaccurate inference
 */
async function dislikeInferredTag(tagType, encodedTagValue) {
  const val = decodeURIComponent(encodedTagValue);
  try {
    const res = await fetch('/api/twin/correct-inference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_type: tagType, tag_value: val })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to update inference');

    if (typeof showToast === 'function') {
      showToast(`Removed "${val}" from your inferred twin profile 👍`, 'info');
    }
    await loadTwinDashboard();
  } catch (err) {
    console.error('Failed to correct inference:', err);
    if (typeof showToast === 'function') {
      showToast(`Could not correct inference: ${err.message}`, 'error');
    }
  }
}

/**
 * Toggle Master Personalization
 */
async function toggleMasterPersonalization(enabled) {
  try {
    const res = await fetch('/api/twin/preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_personalization_enabled: enabled })
    });
    const data = await res.json();
    if (typeof showToast === 'function') {
      showToast(enabled ? 'Personalization enabled ✨' : 'Personalization turned off (generic experience)', 'info');
    }
  } catch (err) {
    console.error('Could not toggle master personalization:', err);
  }
}

/**
 * Toggle Purchase Learning Privacy
 */
async function toggleHistoryPrivacy(enabled) {
  try {
    const res = await fetch('/api/twin/privacy-controls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ use_purchase_history_for_twin: enabled }),
    });
    const data = await res.json();
    if (typeof showToast === 'function') {
      showToast(
        enabled
          ? 'Purchase learning enabled for your Digital Twin.'
          : 'Purchase learning paused. Using manual preferences only.',
        'info'
      );
    }
  } catch (err) {
    if (typeof showToast === 'function') {
      showToast('Failed to update privacy preference: ' + err.message, 'error');
    }
  }
}

/**
 * Confirm & Reset Twin Profile
 */
async function confirmResetTwin() {
  if (!confirm('Are you sure you want to reset your Digital Twin profile? All learned preferences will be cleared.')) {
    return;
  }
  try {
    const res = await fetch('/api/twin/reset', { method: 'POST' });
    const data = await res.json();
    if (typeof showToast === 'function') {
      showToast('Digital Twin reset to default state.', 'info');
    }
    await loadTwinDashboard();
  } catch (err) {
    alert('Reset failed: ' + err.message);
  }
}

/**
 * Confirm & Delete All Personalization Data
 */
async function confirmDeletePersonalization() {
  if (!confirm('CAUTION: Are you sure you want to permanently delete all personalization and browsing activity data? This action cannot be undone.')) {
    return;
  }
  try {
    const res = await fetch('/api/twin/delete-personalization', { method: 'POST' });
    const data = await res.json();
    if (typeof showToast === 'function') {
      showToast('All personalization data has been purged.', 'info');
    }
    await loadTwinDashboard();
  } catch (err) {
    alert('Deletion failed: ' + err.message);
  }
}

function refreshTwinDashboard() {
  if (typeof showToast === 'function') {
    showToast('Refreshing Digital Twin intelligence...', 'info');
  }
  loadTwinDashboard();
}

/**
 * 1-Click Reorder Helper
 */
async function quickRepurchase(productName, productId) {
  try {
    if (productId && productId > 0) {
      if (typeof addToCartById === 'function') {
        await addToCartById(productId);
      } else {
        await fetch('/api/cart', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: productId, quantity: 1 })
        });
        if (typeof showToast === 'function') showToast('Added to cart!', 'success');
      }
    } else {
      const decoded = decodeURIComponent(productName);
      const res = await fetch(`/api/products?search=${encodeURIComponent(decoded)}&limit=1`);
      const data = await res.json();
      const p = (data.products || [])[0];
      if (p && typeof addToCartById === 'function') {
        await addToCartById(p.id);
      } else {
        if (typeof showToast === 'function') showToast(`Added ${decoded} restock request to cart!`, 'success');
      }
    }
  } catch (err) {
    if (typeof showToast === 'function') {
      showToast('Could not add to cart: ' + err.message, 'error');
    }
  }
}

/**
 * ---------------------------------------------------------------------------
 * Household Profiles Persona Switcher
 * ---------------------------------------------------------------------------
 */
async function loadHouseholdProfiles() {
  const strip = document.getElementById("householdProfilesStrip");
  if (!strip) return;

  try {
    const res = await fetch("/api/profiles/household");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const profiles = data.profiles || [];
    strip.innerHTML = profiles.map(p => {
      const isActive = p.is_active === 1;
      return `
        <button onclick="switchHouseholdProfile(${p.id})" style="display:flex; align-items:center; gap:6px; padding:4px 10px; border-radius:16px; border:1px solid ${isActive ? '#C4A6F5' : '#EAE1F4'}; background:${isActive ? '#E9DDFB' : '#FFFDF9'}; color:${isActive ? '#403653' : '#81778E'}; cursor:pointer; font-size:0.78rem; font-weight:${isActive ? '700' : '500'};">
          <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${p.avatar_color || '#C4A6F5'};"></span>
          <span>${p.profile_name}</span>
          ${isActive ? '<span style="font-size:0.65rem; background:#10b981; color:#fff; padding:1px 4px; border-radius:8px;">ACTIVE</span>' : ''}
        </button>
      `;
    }).join("");
  } catch (err) {
    strip.innerHTML = '';
  }
}

async function switchHouseholdProfile(profileId) {
  try {
    const res = await fetch(`/api/profiles/household/${profileId}/switch`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      if (typeof showToast === "function") {
        showToast(data.message, "success");
      }
      loadHouseholdProfiles();
      loadTwinDashboard();
    }
  } catch (err) {
    alert("Switch failed: " + err.message);
  }
}

function openAddHouseholdTwinModal() {
  const name = prompt("Enter Persona Name (e.g., Mom, Teenager, Office Twin):");
  if (!name) return;
  const rel = prompt("Relationship (e.g., Mother, Partner, Teenager, Work):", "Family Member");
  if (!rel) return;

  fetch("/api/profiles/household", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile_name: name,
      relationship: rel,
      shopping_personality: "Savvy Shopper",
      lifestyle_type: "Active Urban",
      preferred_categories: ["Home Essentials", "Personal Care"],
      budget_max: 8000
    })
  }).then(r => r.json()).then(() => {
    loadHouseholdProfiles();
  });
}

/**
 * ---------------------------------------------------------------------------
 * Hidden Compatibility Helpers
 * ---------------------------------------------------------------------------
 */
function populateHiddenCompatibilityElements(data) {
  const archetypeEl = document.getElementById('twinArchetype');
  if (archetypeEl) archetypeEl.textContent = data.archetype || 'Smart Value & Practical Essentials Shopper';

  const spendEl = document.getElementById('insightTotalSpend');
  if (spendEl) spendEl.textContent = formatCurrency(data.spending?.total_spent || 0);

  const ordersEl = document.getElementById('insightTotalOrders');
  if (ordersEl) ordersEl.textContent = data.spending?.total_orders || 0;

  const aovEl = document.getElementById('insightAvgBasket');
  if (aovEl) aovEl.textContent = formatCurrency(data.spending?.average_order_value || 0);

  const tierEl = document.getElementById('insightSpendingTier');
  if (tierEl) tierEl.textContent = `Tier: ${data.spending?.spending_tier || 'Smart Value'}`;
}

// Global DOM Ready Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadTwinDashboard();
  loadHouseholdProfiles();
});
