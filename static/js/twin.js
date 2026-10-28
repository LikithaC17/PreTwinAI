/**
 * PreTwinShop AI - Twin Profile & Personalization Controller
 */

let currentCategories = [];
let currentBrands = [];

function switchTwinTab(tabKey) {
  const tabs = ['tech', 'fashion', 'home', 'budget', 'priorities'];
  tabs.forEach(t => {
    const content = document.getElementById(`tabContent-${t}`);
    const btn = document.getElementById(`tabBtn-${t}`);
    if (content) content.style.display = t === tabKey ? 'block' : 'none';
    if (btn) {
      if (t === tabKey) {
        btn.style.borderColor = '#6366f1';
        btn.style.background = 'rgba(99, 102, 241, 0.2)';
        btn.style.color = '#c4b5fd';
      } else {
        btn.style.borderColor = '#334155';
        btn.style.background = '#1e293b';
        btn.style.color = '#94a3b8';
      }
    }
  });
}

function updateOverviewChips() {
  const catWrap = document.getElementById('overviewCategoryChips');
  if (catWrap) {
    if (currentCategories.length === 0) {
      catWrap.innerHTML = '<span style="color:#64748b; font-size:0.8rem;">No categories selected</span>';
    } else {
      catWrap.innerHTML = currentCategories.slice(0, 6).map(c => `
        <span style="font-size:0.75rem; background:rgba(168, 85, 247, 0.15); border:1px solid rgba(168, 85, 247, 0.35); color:#c084fc; padding:2px 8px; border-radius:12px; font-weight:600;">
          ${c}
        </span>
      `).join('');
    }
  }

  const brandWrap = document.getElementById('overviewBrandChips');
  if (brandWrap) {
    if (currentBrands.length === 0) {
      brandWrap.innerHTML = '<span style="color:#64748b; font-size:0.8rem;">No brands specified</span>';
    } else {
      brandWrap.innerHTML = currentBrands.slice(0, 6).map(b => `
        <span style="font-size:0.75rem; background:rgba(56, 189, 248, 0.15); border:1px solid rgba(56, 189, 248, 0.35); color:#38bdf8; padding:2px 8px; border-radius:12px; font-weight:600;">
          ${b}
        </span>
      `).join('');
    }
  }
}

function updateOverviewCadence() {
  const freqEl = document.getElementById('twinShoppingFreq');
  const cadenceEl = document.getElementById('overviewFreqDisplay');
  if (freqEl && cadenceEl) {
    cadenceEl.textContent = freqEl.options[freqEl.selectedIndex].text.split(' ')[0];
  }
}

async function loadTwinProfile() {
  try {
    const data = await apiGet('/api/profile');
    const user = data.user || data || {};
    const prefs = data.preferences || {};
    const goals = data.shopping_goals || data.goals || [];

    // Header info
    const nameEl = document.getElementById('twinFullName');
    const emailEl = document.getElementById('twinEmail');
    const avatarEl = document.getElementById('twinAvatarLarge');
    if (nameEl) nameEl.textContent = user.username || 'PreTwin Shopper';
    if (emailEl) emailEl.textContent = user.email || 'shopper@pretwin.ai';
    if (avatarEl) {
      avatarEl.textContent = (user.username || 'AJ')
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }

    // Categories
    currentCategories = Array.isArray(prefs.preferred_categories)
      ? prefs.preferred_categories
      : ['Electronics', 'Computer Accessories', 'Home Essentials'];
    renderCategoryTags();

    // Brands
    currentBrands = Array.isArray(prefs.preferred_brands)
      ? prefs.preferred_brands
      : ['Sony', 'Logitech', 'Philips'];
    renderBrandTags();

    // Shopping frequency & notes
    const freqEl = document.getElementById('twinShoppingFreq');
    const notesEl = document.getElementById('twinNotes');
    if (freqEl) freqEl.value = prefs.shopping_frequency || 'monthly';
    if (notesEl) notesEl.value = prefs.notes || '';
    updateOverviewCadence();

    // Budget
    const bMinEl = document.getElementById('budgetMinInput');
    const bMaxEl = document.getElementById('budgetMaxInput');
    if (bMinEl) bMinEl.value = prefs.budget_min !== undefined ? prefs.budget_min : 500;
    if (bMaxEl) bMaxEl.value = prefs.budget_max !== undefined ? prefs.budget_max : 5000;
    updateBudgetDisplay();

    // Shopping Goals
    renderGoalsList(goals);

    // Purchase History
    await loadPurchaseHistory();

    // Autonomous Twin Matches
    await loadTwinRecommendations();
  } catch (err) {
    console.error('Failed to load twin profile:', err);
    showToast('Failed to load profile settings', 'error');
  }
}

function renderCategoryTags() {
  const container = document.getElementById('categoryTagsContainer');
  if (container) {
    container.innerHTML = currentCategories.map((cat, idx) => `
      <span class="tag-pill">
        ${cat}
        <button type="button" class="tag-remove-btn" onclick="removeCategoryTag(${idx})">&times;</button>
      </span>
    `).join('');
  }
  updateOverviewChips();
}

function addCategoryTag() {
  const input = document.getElementById('newCategoryInput');
  if (!input) return;
  const val = input.value.trim();
  if (val && !currentCategories.includes(val)) {
    currentCategories.push(val);
    renderCategoryTags();
    input.value = '';
  }
}

function quickAddCategory(cat) {
  if (cat && !currentCategories.includes(cat)) {
    currentCategories.push(cat);
    renderCategoryTags();
    showToast(`Added ${cat} to preferences`, 'info');
  }
}

function removeCategoryTag(idx) {
  currentCategories.splice(idx, 1);
  renderCategoryTags();
}

function renderBrandTags() {
  const container = document.getElementById('brandTagsContainer');
  if (container) {
    container.innerHTML = currentBrands.map((b, idx) => `
      <span class="tag-pill">
        ${b}
        <button type="button" class="tag-remove-btn" onclick="removeBrandTag(${idx})">&times;</button>
      </span>
    `).join('');
  }
  updateOverviewChips();
}

function addBrandTag() {
  const input = document.getElementById('newBrandInput');
  if (!input) return;
  const val = input.value.trim();
  if (val && !currentBrands.includes(val)) {
    currentBrands.push(val);
    renderBrandTags();
    input.value = '';
  }
}

function quickAddBrand(brand) {
  if (brand && !currentBrands.includes(brand)) {
    currentBrands.push(brand);
    renderBrandTags();
    showToast(`Added ${brand} to affinities`, 'info');
  }
}

function removeBrandTag(idx) {
  currentBrands.splice(idx, 1);
  renderBrandTags();
}

function updateBudgetDisplay() {
  const minVal = parseFloat(document.getElementById('budgetMinInput').value) || 0;
  const maxVal = parseFloat(document.getElementById('budgetMaxInput').value) || 0;
  const display = document.getElementById('budgetRangeDisplay');
  const overviewDisplay = document.getElementById('overviewBudgetDisplay');
  const text = `${formatCurrency(minVal)} — ${formatCurrency(maxVal)}`;
  if (display) display.textContent = text;
  if (overviewDisplay) overviewDisplay.textContent = text;
}

async function saveTwinProfile() {
  const bMin = parseFloat(document.getElementById('budgetMinInput').value) || 0;
  const bMax = parseFloat(document.getElementById('budgetMaxInput').value) || 0;

  if (bMax < bMin) {
    showToast('Maximum budget ceiling cannot be less than minimum budget', 'error');
    return;
  }

  const payload = {
    preferred_categories: currentCategories,
    preferred_brands: currentBrands,
    budget_min: bMin,
    budget_max: bMax,
    shopping_frequency: document.getElementById('twinShoppingFreq').value,
    notes: document.getElementById('twinNotes').value,
  };

  try {
    await apiPut('/api/profile', payload);
    showToast('Twin preferences saved successfully!', 'success');
    await loadTwinRecommendations();
  } catch (err) {
    showToast(`Failed to save preferences: ${err.message}`, 'error');
  }
}

/**
 * Load Personalized Recommendations Grid
 */
async function loadTwinRecommendations() {
  const grid = document.getElementById('twinRecsGrid');
  if (!grid) return;

  grid.innerHTML = `
    <div style="text-align:center; padding:36px; color:#64748b; grid-column:1 / -1;">
      <div class="spinner"></div>
      <p style="margin-top:10px;">Finding tailored products matching your Twin...</p>
    </div>
  `;

  try {
    const res = await fetch('/api/products?limit=24');
    const data = await res.json();
    const products = data.products || [];

    const bMax = parseFloat(document.getElementById('budgetMaxInput')?.value) || 5000;

    // Score and rank products based on twin preferences
    const scored = products.map(p => {
      let score = 0;
      let reason = "Aligns with your shopping goals";

      const catMatch = currentCategories.some(c => c.toLowerCase() === (p.category || '').toLowerCase());
      const brandMatch = currentBrands.some(b => b.toLowerCase() === (p.brand || '').toLowerCase());

      if (catMatch && brandMatch) {
        score += 10;
        reason = `Direct match: ${p.brand} in ${p.category} within budget`;
      } else if (brandMatch) {
        score += 7;
        reason = `Preferred brand affinity: ${p.brand}`;
      } else if (catMatch) {
        score += 5;
        reason = `Category match: ${p.category}`;
      } else {
        score += 1;
      }

      if (p.price <= bMax) {
        score += 2;
      } else {
        score -= 5;
      }

      return { ...p, twin_score: score, match_reason: reason };
    });

    // Filter to top 8 items
    scored.sort((a, b) => b.twin_score - a.twin_score);
    const topRecs = scored.slice(0, 8);

    if (topRecs.length === 0) {
      grid.innerHTML = `
        <div style="text-align:center; padding:36px; color:#64748b; grid-column:1 / -1;">
          No direct recommendations found matching your current filters. Try expanding your categories or budget.
        </div>
      `;
      return;
    }

    grid.innerHTML = topRecs.map(p => `
      <div class="card" style="background:#1e293b; border:1px solid #334155; border-radius:12px; overflow:hidden; display:flex; flex-direction:column; justify-content:space-between; position:relative; transition:transform 0.2s, border-color 0.2s;" id="recCard-${p.id}">
        <!-- Dismiss Action -->
        <button onclick="dismissRecommendation(${p.id})" style="position:absolute; top:8px; right:8px; background:rgba(15,23,42,0.7); border:none; color:#94a3b8; width:26px; height:26px; border-radius:50%; font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center; z-index:2;" title="Dismiss recommendation">
          &times;
        </button>

        <div style="padding:14px;">
          <!-- Image -->
          <div style="height:140px; background:#fff; border-radius:8px; overflow:hidden; display:flex; align-items:center; justify-content:center; margin-bottom:12px;">
            <img src="${p.image_url || '/static/images/placeholder.png'}" alt="${p.name}" style="max-height:100%; max-width:100%; object-fit:contain;">
          </div>

          <!-- Category & Brand -->
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">${p.brand || 'PreTwin'}</span>
            <span style="font-size:0.7rem; background:rgba(99,102,241,0.2); color:#c4b5fd; padding:1px 6px; border-radius:4px;">${p.category}</span>
          </div>

          <!-- Product Name -->
          <h4 style="margin:0 0 8px 0; color:#f1f5f9; font-size:0.9rem; font-weight:600; line-height:1.3; height:38px; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">
            ${p.name}
          </h4>

          <!-- Price & Rating -->
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:1.15rem; font-weight:700; color:#f8fafc;">₹${Math.round(p.price).toLocaleString('en-IN')}</span>
            <span style="font-size:0.8rem; color:#fbbf24; font-weight:600;">⭐ ${p.rating ? p.rating.toFixed(1) : '4.5'}</span>
          </div>

          <!-- Why Matches Your Twin -->
          <div style="background:rgba(168,85,247,0.1); border-left:3px solid #a855f7; padding:6px 8px; border-radius:0 6px 6px 0; font-size:0.75rem; color:#d8b4fe; margin-bottom:12px; line-height:1.3;">
            <strong style="color:#e9d5ff;">Twin Match:</strong> ${p.match_reason}
          </div>
        </div>

        <!-- Action Buttons -->
        <div style="padding:12px 14px; background:#0f172a; border-top:1px solid #334155; display:flex; gap:8px;">
          <button onclick="addToCartById(${p.id})" style="flex:1; background:linear-gradient(135deg, #6366f1, #a855f7); color:#fff; border:none; padding:8px 10px; border-radius:6px; font-weight:600; font-size:0.8rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;">
            <span>🛒</span> Add to Cart
          </button>
          <button onclick="toggleWishlistById(${p.id})" style="background:#1e293b; border:1px solid #475569; color:#f87171; width:34px; height:34px; border-radius:6px; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:14px;" title="Save to Wishlist">
            ❤️
          </button>
          <button onclick="likeRecommendation(${p.id})" style="background:#1e293b; border:1px solid #475569; color:#38bdf8; width:34px; height:34px; border-radius:6px; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:14px;" title="Helpful match">
            👍
          </button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    grid.innerHTML = `
      <div style="text-align:center; padding:36px; color:#ef4444; grid-column:1 / -1;">
        Failed to load twin recommendations: ${e.message}
      </div>
    `;
  }
}

function dismissRecommendation(productId) {
  const card = document.getElementById(`recCard-${productId}`);
  if (card) {
    card.style.transition = 'opacity 0.3s, transform 0.3s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.9)';
    setTimeout(() => card.remove(), 300);
  }
  showToast('Recommendation dismissed', 'info');
  apiPost('/api/feedback', {
    item_type: 'product',
    item_id: productId,
    feedback_type: 'dismiss',
    rating: 1
  }).catch(() => {});
}

function likeRecommendation(productId) {
  showToast('Saved to Twin preferences! 👍', 'success');
  apiPost('/api/feedback', {
    item_type: 'product',
    item_id: productId,
    feedback_type: 'like',
    rating: 5
  }).catch(() => {});
}

function renderGoalsList(goals) {
  const container = document.getElementById('twinGoalsList');
  if (!container) return;

  if (!goals || goals.length === 0) {
    container.innerHTML = '<p class="text-muted text-sm">No active shopping goals. Click "+ New Goal" to add one.</p>';
    return;
  }

  container.innerHTML = goals.map((g) => `
    <div class="goal-item-card" style="background:#1e293b; padding:12px; border-radius:8px; margin-bottom:10px; border:1px solid #334155;">
      <div class="flex-between">
        <strong class="goal-title" style="color:#f1f5f9;">${g.goal_title}</strong>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteGoal(${g.id})">Delete</button>
      </div>
      <p class="goal-desc text-muted text-sm mt-1" style="color:#94a3b8; font-size:0.85rem;">${g.goal_description || ''}</p>
      <div class="goal-meta mt-2" style="display:flex; justify-content:space-between; align-items:center;">
        <span class="badge badge-outline" style="color:#38bdf8; border:1px solid #38bdf8; font-size:0.75rem; padding:2px 6px; border-radius:4px;">Budget: ${formatCurrency(g.budget || 0)}</span>
        <span class="text-xs text-muted" style="color:#64748b; font-size:0.75rem;">Target: ${formatDate(g.target_date)}</span>
      </div>
    </div>
  `).join('');
}

function openAddGoalModal() {
  const bodyHtml = `
    <div class="form-group">
      <label class="form-label">Goal Title *</label>
      <input type="text" id="goalTitleInput" class="form-control" placeholder="e.g. Ergonomic Home Office Setup" required>
    </div>
    <div class="form-group mt-3">
      <label class="form-label">Description / Details</label>
      <textarea id="goalDescInput" class="form-control" rows="2" placeholder="Specific requirements or context..."></textarea>
    </div>
    <div class="form-group mt-3">
      <label class="form-label">Target Budget (₹)</label>
      <input type="number" id="goalBudgetInput" class="form-control" value="2500" min="0" step="100">
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitNewGoal()">Create Goal</button>
  `;

  openModal('Add New Shopping Goal', bodyHtml, footerHtml);
}

async function submitNewGoal() {
  const title = document.getElementById('goalTitleInput').value.trim();
  const desc = document.getElementById('goalDescInput').value.trim();
  const budget = parseFloat(document.getElementById('goalBudgetInput').value) || 0;

  if (!title) {
    showToast('Please provide a goal title', 'warning');
    return;
  }

  try {
    await apiPost('/api/shopping-goals', {
      goal_title: title,
      goal_description: desc,
      budget: budget,
    });
    showToast('Shopping goal created!', 'success');
    closeModal();
    const profile = await apiGet('/api/profile');
    renderGoalsList(profile.shopping_goals || profile.goals || []);
  } catch (err) {
    showToast(`Failed to add goal: ${err.message}`, 'error');
  }
}

async function deleteGoal(goalId) {
  if (!confirm('Are you sure you want to delete this shopping goal?')) return;
  try {
    await apiDelete(`/api/shopping-goals/${goalId}`);
    showToast('Shopping goal removed', 'info');
    const profile = await apiGet('/api/profile');
    renderGoalsList(profile.shopping_goals || profile.goals || []);
  } catch (err) {
    showToast(`Failed to delete goal: ${err.message}`, 'error');
  }
}

async function loadPurchaseHistory() {
  const tbody = document.getElementById('purchaseHistoryBody');
  if (!tbody) return;

  try {
    const data = await apiGet('/api/purchase-history');
    const history = data.history || [];

    if (history.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center py-4 text-muted">
            No voluntary purchase history provided yet. Add past orders to empower proactive replenishment predictions.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = history.map((item) => {
      const orderRef = item.order_number ? `#${item.order_number}` : (item.order_id ? `#${item.order_id}` : 'Direct');
      const isVerified = item.is_verified_purchase === 1 || item.is_verified_purchase === null;
      const statusBadge = isVerified
        ? `<span class="badge badge-success" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); font-size:0.7rem; padding:2px 6px; border-radius:4px;">Verified Completed</span>`
        : `<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3); font-size:0.7rem; padding:2px 6px; border-radius:4px;">Disqualified</span>`;

      return `
        <tr>
          <td>${formatDate(item.purchase_date)}</td>
          <td><span style="font-family:monospace; color:#38bdf8;">${orderRef}</span></td>
          <td><strong>${item.product_name}</strong></td>
          <td><span class="badge badge-outline">${item.category || 'General'}</span></td>
          <td>${item.brand || '--'}</td>
          <td>${formatCurrency(item.price)}</td>
          <td>${item.quantity || 1}</td>
          <td>
            <div style="display:flex; flex-direction:column; gap:2px;">
              ${statusBadge}
              <span style="font-size:0.7rem; color:#94a3b8;">${item.payment_method || 'Online'} (${item.payment_status || 'Paid'})</span>
            </div>
          </td>
          <td>
            <button class="btn btn-sm btn-outline-danger" onclick="deletePurchaseItem(${item.id})">Delete</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load purchase history:', err);
  }
}

function openAddPurchaseModal() {
  const bodyHtml = `
    <div class="form-group">
      <label class="form-label">Product Name *</label>
      <input type="text" id="purchProdName" class="form-control" placeholder="e.g. Logitech Wireless Mouse" required>
    </div>
    <div class="grid-2-col mt-3">
      <div class="form-group">
        <label class="form-label">Category *</label>
        <select id="purchCategory" class="form-control">
          <option value="Electronics">Electronics</option>
          <option value="Computer Accessories">Computer Accessories</option>
          <option value="Home Essentials">Home Essentials</option>
          <option value="Kitchen Products">Kitchen Products</option>
          <option value="Personal Care">Personal Care</option>
          <option value="Stationery">Stationery</option>
          <option value="Everyday Consumables">Everyday Consumables</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Brand</label>
        <input type="text" id="purchBrand" class="form-control" placeholder="e.g. Logitech">
      </div>
    </div>
    <div class="grid-2-col mt-3">
      <div class="form-group">
        <label class="form-label">Price (₹) *</label>
        <input type="number" id="purchPrice" class="form-control" step="1" value="1299">
      </div>
      <div class="form-group">
        <label class="form-label">Quantity</label>
        <input type="number" id="purchQty" class="form-control" value="1" min="1">
      </div>
    </div>
    <div class="form-group mt-3">
      <label class="form-label">Notes</label>
      <input type="text" id="purchNotes" class="form-control" placeholder="Optional notes or replenishment frequency...">
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitNewPurchase()">Add to History</button>
  `;

  openModal('Add Voluntary Purchase Record', bodyHtml, footerHtml);
}

async function submitNewPurchase() {
  const name = document.getElementById('purchProdName').value.trim();
  const category = document.getElementById('purchCategory').value;
  const brand = document.getElementById('purchBrand').value.trim();
  const price = parseFloat(document.getElementById('purchPrice').value) || 0;
  const qty = parseInt(document.getElementById('purchQty').value, 10) || 1;
  const notes = document.getElementById('purchNotes').value.trim();

  if (!name) {
    showToast('Product name is required', 'warning');
    return;
  }

  try {
    await apiPost('/api/purchase-history', {
      product_name: name,
      category: category,
      brand: brand,
      price: price,
      quantity: qty,
      notes: notes,
      purchase_date: new Date().toISOString().split('T')[0],
    });
    showToast('Purchase record added!', 'success');
    closeModal();
    await loadPurchaseHistory();
  } catch (err) {
    showToast(`Failed to add purchase: ${err.message}`, 'error');
  }
}

async function deletePurchaseItem(id) {
  if (!confirm('Remove this past purchase record from your history?')) return;
  try {
    await apiDelete(`/api/purchase-history/${id}`);
    showToast('Purchase record deleted', 'info');
    await loadPurchaseHistory();
  } catch (err) {
    showToast(`Failed to delete record: ${err.message}`, 'error');
  }
}

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
        <button onclick="switchHouseholdProfile(${p.id})" style="display:flex; align-items:center; gap:8px; padding:6px 14px; border-radius:20px; border:1px solid ${isActive ? '#a855f7' : '#334155'}; background:${isActive ? 'rgba(168, 85, 247, 0.2)' : '#1e293b'}; color:${isActive ? '#fff' : '#94a3b8'}; cursor:pointer; font-size:0.85rem; font-weight:${isActive ? '700' : '500'};">
          <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${p.avatar_color || '#8b5cf6'};"></span>
          <span>${p.profile_name} (${p.relationship || 'Self'})</span>
          ${isActive ? '<span style="font-size:0.7rem; background:#10b981; color:#fff; padding:1px 5px; border-radius:10px;">ACTIVE</span>' : ''}
        </button>
      `;
    }).join("");
  } catch (err) {
    strip.innerHTML = `<span style="font-size:0.8rem; color:#ef4444;">Failed to load personas</span>`;
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
      loadTwinProfile();
    }
  } catch (err) {
    alert("Switch failed: " + err.message);
  }
}

function openAddHouseholdTwinModal() {
  const name = prompt("Enter Twin Name (e.g., Mom's Shopping Twin, Teenager Twin, Office Twin):");
  if (!name) return;
  const rel = prompt("Relationship (e.g., Mother, Partner, Teenager, Work):", "Family Member");
  if (!rel) return;

  fetch("/api/profiles/household", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile_name: name,
      relationship: rel,
      shopping_personality: "Savvy Trendsetter",
      lifestyle_type: "Active Urban",
      preferred_categories: ["Fashion", "Personal Care"],
      budget_max: 8000
    })
  }).then(r => r.json()).then(data => {
    loadHouseholdProfiles();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadTwinProfile();
  loadHouseholdProfiles();
  loadTwinPrivacySettings();
  loadTwinInsights();
});


/**
 * ---------------------------------------------------------------------------
 * Digital Twin Intelligence & Verified Purchase History Controller
 * ---------------------------------------------------------------------------
 */

async function loadTwinPrivacySettings() {
  const toggle = document.getElementById('twinHistoryPrivacyToggle');
  const badge = document.getElementById('privacyStatusBadge');
  if (!toggle) return;

  try {
    const res = await fetch('/api/twin/privacy-controls');
    const data = await res.json();
    const isOptedIn = data.use_purchase_history_for_twin !== false;
    toggle.checked = isOptedIn;
    if (badge) {
      if (isOptedIn) {
        badge.textContent = 'Active Learning';
        badge.style.background = 'rgba(16, 185, 129, 0.15)';
        badge.style.color = '#34d399';
        badge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      } else {
        badge.textContent = 'Paused (Private)';
        badge.style.background = 'rgba(239, 68, 68, 0.15)';
        badge.style.color = '#f87171';
        badge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
      }
    }
  } catch (err) {
    console.warn('Could not load privacy controls:', err);
  }
}

async function toggleHistoryPrivacy(enabled) {
  const badge = document.getElementById('privacyStatusBadge');
  try {
    const res = await fetch('/api/twin/privacy-controls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ use_purchase_history_for_twin: enabled }),
    });
    const data = await res.json();
    if (badge) {
      if (enabled) {
        badge.textContent = 'Active Learning';
        badge.style.background = 'rgba(16, 185, 129, 0.15)';
        badge.style.color = '#34d399';
        badge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      } else {
        badge.textContent = 'Paused (Private)';
        badge.style.background = 'rgba(239, 68, 68, 0.15)';
        badge.style.color = '#f87171';
        badge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
      }
    }
    showToast(
      enabled
        ? 'Purchase history learning enabled for your Digital Twin.'
        : 'Purchase history learning paused. Your twin will use manual preferences only.',
      'info'
    );
    await loadTwinInsights();
  } catch (err) {
    showToast('Failed to update privacy preference: ' + err.message, 'error');
  }
}

async function loadTwinInsights() {
  try {
    const res = await fetch('/api/twin/insights');
    const data = await res.json();

    const history = data.history_summary || {};
    const profile = data.learned_profile || {};
    const predictions = data.predictions || [];
    const recommendations = data.recommendations || [];

    // 1. Metric Cards
    const totalOrdersEl = document.getElementById('insightTotalOrders');
    const totalItemsEl = document.getElementById('insightTotalItems');
    const totalSpendEl = document.getElementById('insightTotalSpend');
    const tierEl = document.getElementById('insightSpendingTier');
    const avgBasketEl = document.getElementById('insightAvgBasket');
    const avgItemEl = document.getElementById('insightAvgItem');
    const cadenceEl = document.getElementById('insightCadence');
    const cadenceDaysEl = document.getElementById('insightCadenceDays');

    if (totalOrdersEl) totalOrdersEl.textContent = history.total_orders ?? 0;
    if (totalItemsEl) totalItemsEl.textContent = `${history.total_items_count ?? 0} items delivered / recorded`;
    if (totalSpendEl) totalSpendEl.textContent = formatCurrency(history.total_spent ?? 0);
    if (tierEl) tierEl.textContent = `Tier: ${profile.spending_tier || 'Smart Value'}`;
    if (avgBasketEl) avgBasketEl.textContent = formatCurrency(history.average_order_value ?? 0);
    if (avgItemEl) avgItemEl.textContent = `Avg ${formatCurrency(history.average_item_price ?? 0)}/item`;
    if (cadenceEl) cadenceEl.textContent = profile.observed_frequency || 'Monthly';
    if (cadenceDaysEl) cadenceDaysEl.textContent = `Every ~${profile.cadence_days || 30} days`;

    // 2. Frequently Purchased Products
    renderFrequentlyPurchased(history.frequently_purchased || []);

    // 3. Replenishment Predictions
    renderReplenishmentPredictions(predictions);

    // 4. Personalized Recommendations
    renderCoordinatedRecommendations(recommendations);

  } catch (err) {
    console.error('Failed to load twin insights:', err);
  }
}

function renderFrequentlyPurchased(items) {
  const grid = document.getElementById('frequentlyPurchasedGrid');
  if (!grid) return;

  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div style="color:#64748b; font-size:0.85rem; padding:18px; grid-column:1 / -1; text-align:center; background:#1e293b; border-radius:10px; border:1px dashed #334155;">
        No repeat purchases observed yet. As you make purchases on PreTwin AI, your frequent items will appear here for 1-click replenishment.
      </div>
    `;
    return;
  }

  grid.innerHTML = items.slice(0, 6).map(it => `
    <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; display:flex; flex-direction:column; justify-content:space-between; transition:transform 0.2s;">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <span style="font-size:0.7rem; color:#38bdf8; background:rgba(56,189,248,0.1); padding:2px 6px; border-radius:4px; font-weight:600;">${it.category}</span>
          <span style="font-size:0.75rem; color:#a855f7; font-weight:700;">Ordered ${it.order_appearances}x (${it.total_quantity} pcs)</span>
        </div>
        <h4 style="margin:4px 0 6px; font-size:0.9rem; color:#f8fafc; font-weight:600; line-height:1.3; height:36px; overflow:hidden;">
          ${it.product_name}
        </h4>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <span style="font-size:1.05rem; font-weight:700; color:#34d399;">${formatCurrency(it.avg_price)}</span>
          <span style="font-size:0.75rem; color:#94a3b8;">Last: ${it.latest_purchase_date || '--'}</span>
        </div>
      </div>
      <div>
        <button onclick="quickRepurchase('${encodeURIComponent(it.product_name)}', ${it.product_id || 0})" style="width:100%; background:linear-gradient(135deg, #38bdf8, #6366f1); border:none; color:#fff; padding:7px 12px; border-radius:6px; font-weight:600; font-size:0.8rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
          <span>🔁</span> Reorder / Restock
        </button>
      </div>
    </div>
  `).join('');
}

async function quickRepurchase(productName, productId) {
  try {
    if (productId && productId > 0) {
      await addToCartById(productId);
    } else {
      // Find product in catalog
      const res = await fetch(`/api/products?search=${encodeURIComponent(decodeURIComponent(productName))}&limit=1`);
      const data = await res.json();
      const p = (data.products || [])[0];
      if (p) {
        await addToCartById(p.id);
      } else {
        showToast('Added request to shopping card!', 'success');
      }
    }
  } catch (err) {
    showToast('Could not add to cart: ' + err.message, 'error');
  }
}

function renderReplenishmentPredictions(predictions) {
  const grid = document.getElementById('replenishmentPredictionsGrid');
  if (!grid) return;

  if (!predictions || predictions.length === 0) {
    grid.innerHTML = `
      <div style="color:#64748b; font-size:0.85rem; padding:20px; grid-column:1 / -1; text-align:center; background:#1e293b; border-radius:10px; border:1px dashed #334155;">
        No repeat replenishment forecasts active yet. Predictions activate automatically as repeat orders or consumable goods are delivered.
      </div>
    `;
    return;
  }

  grid.innerHTML = predictions.map(pred => {
    const isDue = pred.is_due_soon;
    const isOver = pred.is_overdue;
    const statusColor = isOver ? '#ef4444' : (isDue ? '#f59e0b' : '#38bdf8');
    const statusText = isOver ? 'Restock Overdue' : (isDue ? 'Due Soon' : 'Upcoming');

    return `
      <div style="background:#1e293b; border:1px solid ${statusColor}44; border-radius:12px; padding:16px; display:flex; flex-direction:column; justify-content:space-between; position:relative;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:0.7rem; color:${statusColor}; background:${statusColor}18; border:1px solid ${statusColor}33; padding:2px 8px; border-radius:12px; font-weight:700;">
              ● ${statusText} (${pred.confidence_label})
            </span>
            <span style="font-size:0.75rem; color:#94a3b8;">Est. Interval: ~${pred.average_interval_days}d</span>
          </div>
          <h4 style="margin:4px 0 6px; font-size:0.95rem; color:#f8fafc; font-weight:600;">
            ${pred.product_name}
          </h4>
          <div style="font-size:0.8rem; color:#cbd5e1; margin-bottom:8px;">
            <strong style="color:#38bdf8;">Estimated Restock:</strong> ${pred.estimated_replenishment_date}
            <span style="color:#64748b; font-size:0.75rem;">(Window: ${pred.estimated_window_start} to ${pred.estimated_window_end})</span>
          </div>
          <div style="background:#0f172a; border-left:3px solid #38bdf8; padding:8px 10px; border-radius:0 6px 6px 0; font-size:0.75rem; color:#94a3b8; margin-bottom:12px; line-height:1.35;">
            <strong style="color:#cbd5e1;">Agent Evidence:</strong> ${pred.evidence_explanation}
          </div>
        </div>
        <div>
          <button onclick="quickRepurchase('${encodeURIComponent(pred.product_name)}', ${pred.product_id || 0})" style="width:100%; background:linear-gradient(135deg, #10b981, #059669); border:none; color:#fff; padding:8px 12px; border-radius:6px; font-weight:600; font-size:0.8rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <span>🛒</span> Restock This Item
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderCoordinatedRecommendations(recs) {
  const grid = document.getElementById('twinRecsGrid');
  if (!grid) return;

  if (!recs || recs.length === 0) {
    grid.innerHTML = `
      <div style="text-align:center; padding:36px; color:#64748b; grid-column:1 / -1;">
        No recommendations available matching current preferences and budget ceiling. Try adjusting your preferences.
      </div>
    `;
    return;
  }

  grid.innerHTML = recs.map(p => `
    <div class="card" style="background:#1e293b; border:1px solid #334155; border-radius:12px; overflow:hidden; display:flex; flex-direction:column; justify-content:space-between; position:relative; transition:transform 0.2s, border-color 0.2s;" id="recCard-${p.id}">
      <!-- Dismiss Action -->
      <button onclick="dismissRecommendation(${p.id})" style="position:absolute; top:8px; right:8px; background:rgba(15,23,42,0.8); border:1px solid #334155; color:#94a3b8; width:26px; height:26px; border-radius:50%; font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center; z-index:2;" title="Dismiss recommendation">
        &times;
      </button>

      <div style="padding:14px;">
        <!-- Image -->
        <div style="height:140px; background:#fff; border-radius:8px; overflow:hidden; display:flex; align-items:center; justify-content:center; margin-bottom:12px;">
          <img src="${p.image_url || '/static/images/placeholder.png'}" alt="${p.name}" style="max-height:100%; max-width:100%; object-fit:contain;">
        </div>

        <!-- Category & Brand -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <span style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; font-weight:600;">${p.brand || 'PreTwin'}</span>
          <span style="font-size:0.7rem; background:rgba(99,102,241,0.2); color:#c4b5fd; padding:1px 6px; border-radius:4px;">${p.category}</span>
        </div>

        <!-- Product Name -->
        <h4 style="margin:0 0 8px 0; color:#f1f5f9; font-size:0.9rem; font-weight:600; line-height:1.3; height:38px; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">
          ${p.name}
        </h4>

        <!-- Price & Rating -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <span style="font-size:1.15rem; font-weight:700; color:#f8fafc;">₹${Math.round(p.price).toLocaleString('en-IN')}</span>
          <span style="font-size:0.8rem; color:#fbbf24; font-weight:600;">⭐ ${p.rating ? Number(p.rating).toFixed(1) : '4.5'}</span>
        </div>

        <!-- Why Matches Your Twin -->
        <div style="background:rgba(168,85,247,0.1); border-left:3px solid #a855f7; padding:8px; border-radius:0 6px 6px 0; font-size:0.75rem; color:#d8b4fe; margin-bottom:12px; line-height:1.35;">
          <strong style="color:#e9d5ff;">${p.badge || 'AI Match'}:</strong> ${p.recommendation_reason || 'Aligns with your shopping goals and verified budget.'}
        </div>
      </div>

      <!-- Action Buttons -->
      <div style="padding:12px 14px; background:#0f172a; border-top:1px solid #334155; display:flex; gap:8px;">
        <button onclick="addToCartById(${p.id})" style="flex:1; background:linear-gradient(135deg, #6366f1, #a855f7); color:#fff; border:none; padding:8px 10px; border-radius:6px; font-weight:600; font-size:0.8rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;">
          <span>🛒</span> Add to Cart
        </button>
        <button onclick="toggleWishlistById(${p.id})" style="background:#1e293b; border:1px solid #475569; color:#f87171; width:34px; height:34px; border-radius:6px; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:14px;" title="Save to Wishlist">
          ❤️
        </button>
      </div>
    </div>
  `).join('');
}

async function dismissRecommendation(productId) {
  const card = document.getElementById(`recCard-${productId}`);
  if (card) {
    card.style.transition = 'opacity 0.3s, transform 0.3s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.9)';
    setTimeout(() => card.remove(), 300);
  }
  showToast('Recommendation dismissed', 'info');
  try {
    await fetch('/api/twin/dismiss-recommendation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: productId }),
    });
  } catch (err) {
    console.warn('Could not persist recommendation dismissal:', err);
  }
}
