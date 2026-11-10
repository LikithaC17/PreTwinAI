/**
 * static/js/comparison.js
 * =======================
 * PreTwin AI - Product Comparison & Decision Support Controller (Feature 5)
 * Coordinates the Seven Dedicated Sections:
 * 1. Product Selection & Validation
 * 2. Side-by-Side Comparison Matrix
 * 3. Feature and Specification Analysis
 * 4. Price and Value Comparison
 * 5. Fact-Based Pros and Cons
 * 6. Smart Decision Assistant
 * 7. Final Decision & Product Actions
 */

let selectedProductIds = [];
let comparisonPayload = null;
let showDifferencesOnly = false;
let currentWeights = {
  price: 35,
  specs: 25,
  value: 20,
  rating: 15,
  brand: 5
};
let debounceTimer = null;
let allCatalogueCache = [];

// =============================================================================
// Helper Utilities
// =============================================================================

function formatCurrency(val) {
  const num = Number(val) || 0;
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getStoredComparisonIds() {
  // 1. Check URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const urlIds = urlParams.get('ids') || urlParams.get('product_ids');
  if (urlIds) {
    const parsed = urlIds.split(',').map(x => parseInt(x.trim(), 10)).filter(x => !isNaN(x) && x > 0);
    if (parsed.length > 0) return parsed.slice(0, 4);
  }

  // 2. Check global getComparisonIds from main.js if available
  if (typeof window.getComparisonIds === 'function') {
    try {
      const gIds = window.getComparisonIds();
      if (Array.isArray(gIds) && gIds.length > 0) return gIds.slice(0, 4);
    } catch (e) {}
  }

  // 3. Check localStorage
  try {
    const raw = localStorage.getItem('pretwin_comparison_ids');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.slice(0, 4);
    }
  } catch (e) {}

  return [];
}

function persistComparisonIds(ids) {
  const clean = (ids || []).slice(0, 4);
  localStorage.setItem('pretwin_comparison_ids', JSON.stringify(clean));
  if (typeof window.saveComparisonIds === 'function') {
    try { window.saveComparisonIds(clean); } catch (e) {}
  }
  // Sync with backend
  fetch('/api/comparison/saved', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_ids: clean })
  }).catch(() => {});
}

function notifyToast(msg, type = 'info') {
  if (typeof window.showToast === 'function') {
    window.showToast(msg, type);
  } else {
    alert(msg);
  }
}

// =============================================================================
// Page Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  initComparisonPage();
});

async function initComparisonPage() {
  selectedProductIds = getStoredComparisonIds();

  // Load Presets first so empty state has instant cards
  await loadPresets();

  // Pre-load catalogue products for search / modal
  loadCatalogueCache();

  // Render selection indicators
  renderSelectedPills();

  if (selectedProductIds.length >= 2) {
    await fetchFullComparison();
  } else {
    // If empty or only 1, check server saved session
    try {
      const sRes = await fetch('/api/comparison/saved');
      if (sRes.ok) {
        const sData = await sRes.json();
        if (sData.saved_ids && sData.saved_ids.length >= 2 && selectedProductIds.length === 0) {
          selectedProductIds = sData.saved_ids.slice(0, 4);
          persistComparisonIds(selectedProductIds);
          renderSelectedPills();
          await fetchFullComparison();
          return;
        }
      }
    } catch (e) {}

    renderEmptyComparisonState();
  }
}

// =============================================================================
// SECTION 1: Product Selection & Presets
// =============================================================================

async function loadPresets() {
  const container = document.getElementById('presetsGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/comparison/presets');
    if (!res.ok) return;
    const data = await res.json();
    const presets = data.presets || [];

    if (presets.length === 0) {
      container.parentElement.style.display = 'none';
      return;
    }

    container.innerHTML = presets.map((p, idx) => `
      <div style="background:#FFFDF9; border:1px solid var(--pt-border); border-radius:12px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; transition:all 0.2s ease; box-shadow:0 2px 8px rgba(64,54,83,0.03);"
           onclick="applyPreset([${p.product_ids.join(',')}])"
           onmouseover="this.style.borderColor='var(--pt-primary)'; this.style.transform='translateY(-2px)';"
           onmouseout="this.style.borderColor='var(--pt-border)'; this.style.transform='none';">
        <div style="display:flex; align-items:center; gap:10px;">
          <div style="display:flex; margin-right:4px;">
            ${(p.preview_images || []).map(img => `
              <img src="${img || '/static/images/placeholder.png'}" style="width:36px; height:36px; object-fit:contain; border-radius:6px; background:#F7F3FF; border:1px solid var(--pt-border); margin-left:-8px; first-child:margin-left:0;" onerror="this.src='/static/images/placeholder.png'">
            `).join('')}
          </div>
          <div>
            <strong style="display:block; font-size:0.85rem; color:var(--pt-text);">${p.title}</strong>
            <span style="font-size:0.75rem; color:var(--pt-text-muted);">${p.category}</span>
          </div>
        </div>
        <button class="btn-outline-pt" style="font-size:0.75rem; padding:4px 10px; border-radius:6px;">Compare ⚡</button>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load presets:', err);
  }
}

function applyPreset(ids) {
  selectedProductIds = ids.slice(0, 4);
  persistComparisonIds(selectedProductIds);
  renderSelectedPills();
  fetchFullComparison();
  notifyToast('Loaded preset comparison', 'success');
}

function renderSelectedPills() {
  const container = document.getElementById('selectedPillsContainer');
  const countBadge = document.getElementById('selectedCountBadge');
  const instr = document.getElementById('selectionInstruction');

  if (countBadge) {
    countBadge.textContent = `${selectedProductIds.length} / 4`;
  }

  if (instr) {
    if (selectedProductIds.length >= 2) {
      instr.textContent = `Comparing ${selectedProductIds.length} products.`;
    } else {
      instr.textContent = `Select at least two products to begin side-by-side comparison.`;
    }
  }

  if (!container) return;

  if (selectedProductIds.length === 0) {
    container.innerHTML = `<span style="font-size:0.85rem; color:var(--pt-text-muted); font-style:italic;">No products selected yet. Pick from above or try a quick preset below.</span>`;
    return;
  }

  container.innerHTML = selectedProductIds.map(id => {
    // Look up product title in cached list or window.catalogMap
    const p = (window.catalogMap && window.catalogMap[id]) || allCatalogueCache.find(x => x.id === id);
    const title = p ? p.name : `Product #${id}`;
    const price = p ? formatCurrency(p.price) : '';

    return `
      <span style="display:inline-flex; align-items:center; gap:8px; background:var(--pt-secondary); border:1px solid var(--pt-primary); color:var(--pt-text); padding:6px 12px; border-radius:20px; font-size:0.82rem; font-weight:700;">
        <span>${title} ${price ? `(${price})` : ''}</span>
        <button onclick="removeProductFromComparison(${id})" style="background:rgba(239,68,68,0.15); border:none; color:#DC2626; border-radius:50%; width:18px; height:18px; cursor:pointer; font-weight:800; font-size:12px; line-height:1; display:flex; align-items:center; justify-content:center;" title="Remove this product">&times;</button>
      </span>
    `;
  }).join('');
}

async function addProductToComparison(productId) {
  const pid = parseInt(productId, 10);
  if (!pid || isNaN(pid)) return;

  if (selectedProductIds.includes(pid)) {
    notifyToast('This product is already selected in your comparison.', 'info');
    return;
  }

  if (selectedProductIds.length >= 4) {
    notifyToast('Maximum 4 products allowed for comparison. Remove one to add another.', 'warning');
    return;
  }

  selectedProductIds.push(pid);
  persistComparisonIds(selectedProductIds);
  renderSelectedPills();

  // Hide search tray if visible
  hideSearchTray();
  const sInput = document.getElementById('compSearchInput');
  if (sInput) sInput.value = '';

  if (selectedProductIds.length >= 2) {
    await fetchFullComparison();
  } else {
    notifyToast('Add at least one more product to begin comparison.', 'info');
    renderEmptyComparisonState();
  }
}

function removeProductFromComparison(productId) {
  const pid = parseInt(productId, 10);
  selectedProductIds = selectedProductIds.filter(id => id !== pid);
  persistComparisonIds(selectedProductIds);
  renderSelectedPills();

  if (selectedProductIds.length >= 2) {
    fetchFullComparison();
  } else {
    renderEmptyComparisonState();
  }
  notifyToast('Product removed from comparison', 'info');
}

function promptClearAllComparison() {
  if (selectedProductIds.length === 0) {
    notifyToast('Comparison is already empty.', 'info');
    return;
  }
  if (confirm('Clear all products from comparison?')) {
    selectedProductIds = [];
    persistComparisonIds([]);
    renderSelectedPills();
    renderEmptyComparisonState();
    notifyToast('Comparison cleared', 'info');
  }
}

// =============================================================================
// Live Catalogue Search & Picker
// =============================================================================

function showSearchTray() {
  const tray = document.getElementById('compSearchTray');
  if (tray) tray.style.display = 'block';
}

function hideSearchTray() {
  setTimeout(() => {
    const tray = document.getElementById('compSearchTray');
    if (tray) tray.style.display = 'none';
  }, 250);
}

async function handleLiveSearch(query) {
  const tray = document.getElementById('compSearchTray');
  const cat = document.getElementById('compCategorySelect') ? document.getElementById('compCategorySelect').value : '';
  if (!tray) return;

  tray.style.display = 'block';

  try {
    const res = await fetch(`/api/comparison/search?q=${encodeURIComponent(query)}&category=${encodeURIComponent(cat)}&limit=15`);
    if (!res.ok) throw new Error('Search failed');
    const data = await res.json();
    const products = data.products || [];

    if (products.length === 0) {
      tray.innerHTML = `<div style="padding:14px; text-align:center; color:var(--pt-text-muted); font-size:0.88rem;">No catalogue products matched "${query}".</div>`;
      return;
    }

    // Cache products for catalogMap
    products.forEach(p => {
      if (!window.catalogMap) window.catalogMap = {};
      window.catalogMap[p.id] = p;
    });

    tray.innerHTML = products.map(p => {
      const isSelected = selectedProductIds.includes(p.id);
      return `
        <div class="search-result-item" onclick="addProductToComparison(${p.id})">
          <img src="${p.image_url || '/static/images/placeholder.png'}" style="width:40px; height:40px; object-fit:contain; border-radius:6px; background:#F7F3FF; border:1px solid var(--pt-border);" onerror="this.src='/static/images/placeholder.png'">
          <div style="flex:1;">
            <div style="font-weight:700; font-size:0.88rem; color:var(--pt-text);">${p.name}</div>
            <div style="font-size:0.75rem; color:var(--pt-text-muted);">${p.brand || 'Generic'} • ${p.category}</div>
          </div>
          <div style="text-align:right;">
            <strong style="color:#7C3AED; font-size:0.9rem;">${formatCurrency(p.price)}</strong>
            <div>${isSelected ? '<span style="font-size:0.75rem; color:#10B981; font-weight:700;">✓ Added</span>' : '<button class="btn-outline-pt" style="font-size:0.72rem; padding:3px 8px;">+ Compare</button>'}</div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    tray.innerHTML = `<div style="padding:12px; color:#DC2626; font-size:0.85rem;">Error searching catalogue.</div>`;
  }
}

function handleCategoryFilter(category) {
  const query = document.getElementById('compSearchInput') ? document.getElementById('compSearchInput').value : '';
  handleLiveSearch(query);
}

// Catalogue Modal
function openProductSelectorModal() {
  const modal = document.getElementById('cataloguePickerModal');
  if (!modal) return;
  modal.style.display = 'flex';
  renderModalProducts(allCatalogueCache);
}

function closeProductSelectorModal() {
  const modal = document.getElementById('cataloguePickerModal');
  if (modal) modal.style.display = 'none';
}

async function loadCatalogueCache() {
  try {
    const res = await fetch('/api/comparison/search?limit=50');
    if (res.ok) {
      const data = await res.json();
      allCatalogueCache = data.products || [];
      allCatalogueCache.forEach(p => {
        if (!window.catalogMap) window.catalogMap = {};
        window.catalogMap[p.id] = p;
      });
    }
  } catch (e) {}
}

function filterModalProducts(query) {
  const q = (query || '').toLowerCase().trim();
  const filtered = allCatalogueCache.filter(p =>
    (p.name && p.name.toLowerCase().includes(q)) ||
    (p.brand && p.brand.toLowerCase().includes(q)) ||
    (p.category && p.category.toLowerCase().includes(q))
  );
  renderModalProducts(filtered);
}

function renderModalProducts(products) {
  const grid = document.getElementById('modalProductsGrid');
  if (!grid) return;

  if (products.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:32px; color:var(--pt-text-muted);">No products found.</div>`;
    return;
  }

  grid.innerHTML = products.map(p => {
    const isSelected = selectedProductIds.includes(p.id);
    return `
      <div style="background:#FFFDF9; border:1px solid var(--pt-border); border-radius:10px; padding:12px; text-align:center; display:flex; flex-direction:column; justify-content:space-between;">
        <img src="${p.image_url || '/static/images/placeholder.png'}" style="width:100%; height:110px; object-fit:contain; border-radius:8px; margin-bottom:8px;" onerror="this.src='/static/images/placeholder.png'">
        <div style="font-weight:700; font-size:0.85rem; color:var(--pt-text); margin-bottom:4px; line-height:1.2; height:34px; overflow:hidden;">${p.name}</div>
        <div style="font-size:0.75rem; color:var(--pt-text-muted); margin-bottom:6px;">${p.brand || 'Generic'}</div>
        <div style="font-weight:800; color:#7C3AED; font-size:0.92rem; margin-bottom:8px;">${formatCurrency(p.price)}</div>
        <button class="btn-primary-pt" style="font-size:0.78rem; padding:6px 12px; width:100%;" onclick="addProductToComparison(${p.id}); closeProductSelectorModal();" ${isSelected ? 'disabled style="opacity:0.6;"' : ''}>
          ${isSelected ? 'Already Added' : '+ Add to Compare'}
        </button>
      </div>
    `;
  }).join('');
}

// =============================================================================
// Comprehensive 7-Section Fetch & Dispatch
// =============================================================================

async function fetchFullComparison() {
  if (selectedProductIds.length < 2) {
    renderEmptyComparisonState();
    return;
  }

  const tbody = document.getElementById('comparisonTableBody');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center; padding:48px 20px;">
          <div class="spinner" style="margin:0 auto 12px;"></div>
          <strong style="color:var(--pt-text);">Analyzing catalogue specifications and calculating multi-attribute tradeoffs...</strong>
        </td>
      </tr>
    `;
  }

  try {
    const res = await fetch('/api/comparison/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_ids: selectedProductIds,
        weights: currentWeights,
        show_differences_only: showDifferencesOnly
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Comparison calculation failed');
    }

    const data = await res.json();
    comparisonPayload = data;

    // Cache in window.catalogMap for global cart/wishlist handlers
    if (data.products && Array.isArray(data.products)) {
      data.products.forEach(p => {
        if (!window.catalogMap) window.catalogMap = {};
        window.catalogMap[p.id] = p;
      });
    }

    // Render all 6 dynamic comparison sections
    renderSection2SideBySide(data.side_by_side, data.winner);
    renderSection3FeatureAnalysis(data.spec_analysis);
    renderSection4PriceValue(data.price_value);
    renderSection5ProsCons(data.pros_cons, data.products);
    renderSection6DecisionAssistant(data.decision);
    renderSection7FinalActions(data.products);

    // Hide empty state
    const emptyState = document.getElementById('comparisonEmptyState');
    const tableContainer = document.getElementById('sideBySideTableContainer');
    if (emptyState) emptyState.style.display = 'none';
    if (tableContainer) tableContainer.style.display = 'block';

  } catch (err) {
    console.error('fetchFullComparison failed:', err);
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center; padding:36px; color:#DC2626;">
            Error loading comparison: ${err.message}. Please select active catalogue items.
          </td>
        </tr>
      `;
    }
  }
}

function renderEmptyComparisonState() {
  const emptyState = document.getElementById('comparisonEmptyState');
  const tableContainer = document.getElementById('sideBySideTableContainer');
  const specSummary = document.getElementById('specMetricsSummary');
  const specGroups = document.getElementById('specGroupsContainer');
  const priceGrid = document.getElementById('priceValueCardsGrid');
  const prosGrid = document.getElementById('prosConsCardsGrid');
  const finalGrid = document.getElementById('finalActionCardsGrid');
  const decisionCard = document.getElementById('decisionBannerCard');

  if (emptyState) emptyState.style.display = 'block';
  if (tableContainer) tableContainer.style.display = 'none';

  if (specSummary) specSummary.innerHTML = '';
  if (specGroups) specGroups.innerHTML = `<div style="text-align:center; padding:24px; color:var(--pt-text-muted); font-size:0.9rem;">Select at least two products to inspect specification comparisons.</div>`;
  if (priceGrid) priceGrid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:24px; color:var(--pt-text-muted); font-size:0.9rem;">Financial price differences and value ratings will appear here.</div>`;
  if (prosGrid) prosGrid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:24px; color:var(--pt-text-muted); font-size:0.9rem;">Factual advantages and limitations will appear here.</div>`;
  if (finalGrid) finalGrid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:24px; color:var(--pt-text-muted); font-size:0.9rem;">Select products to take purchasing actions.</div>`;
  if (decisionCard) {
    const reason = document.getElementById('decisionReasonText');
    if (reason) reason.textContent = 'Please select at least two products to enable Smart Decision Assistant.';
  }
}

// =============================================================================
// SECTION 2: Side-by-Side Table Renderer
// =============================================================================

function renderSection2SideBySide(matrix, winner) {
  const thead = document.getElementById('comparisonTableHead');
  const tbody = document.getElementById('comparisonTableBody');
  if (!thead || !tbody || !matrix) return;

  const cols = matrix.columns || [];
  const rows = matrix.rows || [];
  const winnerId = winner ? winner.id : null;

  // Header row
  thead.innerHTML = `
    <th class="sticky-col" style="padding:18px 20px;">
      <span style="font-size:0.8rem; text-transform:uppercase; color:var(--pt-text-muted); letter-spacing:0.5px;">Products &amp; Criteria</span>
    </th>
    ${cols.map(col => {
      const isWinner = col.id === winnerId;
      return `
        <th style="min-width:240px; padding:18px 16px; text-align:center; background:${isWinner ? 'var(--pt-secondary)' : '#FFFDF9'};">
          <div style="position:relative;">
            <button onclick="removeProductFromComparison(${col.id})" style="position:absolute; top:-6px; right:-6px; background:#E2E8F0; color:#475569; border:none; border-radius:50%; width:24px; height:24px; font-weight:800; cursor:pointer; font-size:14px; line-height:1;" title="Remove">&times;</button>
            
            <div style="margin-bottom:8px; display:flex; justify-content:center; gap:6px; flex-wrap:wrap;">
              ${isWinner ? '<span class="badge-value">👑 Top Recommendation</span>' : ''}
              ${col.is_lowest_price ? '<span class="badge-lowest">🏷️ Lowest Price</span>' : ''}
              ${col.is_top_rated ? '<span class="badge-gold">★ Top Rated</span>' : ''}
            </div>

            <div style="width:110px; height:110px; margin:0 auto 10px; background:#F7F3FF; border-radius:10px; display:flex; align-items:center; justify-content:center; overflow:hidden; border:1px solid var(--pt-border);">
              <img src="${col.image_url || '/static/images/placeholder.png'}" alt="${col.name}" style="max-width:90%; max-height:90%; object-fit:contain;" onerror="this.src='/static/images/placeholder.png'">
            </div>

            <div style="font-size:0.92rem; font-weight:800; color:var(--pt-text); min-height:40px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.3;" title="${col.name}">
              ${col.name}
            </div>

            <div style="font-size:1.25rem; font-weight:800; color:#7C3AED; margin:8px 0 4px;">
              ${formatCurrency(col.price)}
            </div>
            ${col.discount_percentage ? `<div style="font-size:0.75rem; color:#B45309; font-weight:700;"><span style="text-decoration:line-through; color:var(--pt-text-muted);">${formatCurrency(col.original_price)}</span> (${col.discount_percentage}% OFF)</div>` : ''}

            <!-- Quick Action Buttons -->
            <div style="display:flex; flex-direction:column; gap:6px; margin-top:12px;">
              <button class="btn-primary-pt" style="font-size:0.8rem; padding:8px 12px; width:100%;" onclick="addToCartById(${col.id})">
                🛒 Add to Cart
              </button>
              <button class="btn-outline-pt" style="font-size:0.78rem; padding:6px 12px; width:100%; justify-content:center;" onclick="toggleWishlistById(${col.id})">
                ❤️ Add to Wishlist
              </button>
            </div>
          </div>
        </th>
      `;
    }).join('')}
  `;

  // Body rows grouped
  let currentGroup = '';
  let tbodyHtml = '';

  rows.forEach(r => {
    if (r.group !== currentGroup) {
      currentGroup = r.group;
      tbodyHtml += `
        <tr class="group-header">
          <td colspan="${cols.length + 1}">${currentGroup}</td>
        </tr>
      `;
    }

    const rowClass = r.is_different ? 'row-diff' : 'row-identical';
    const diffBadge = r.is_different ? '<span style="font-size:0.68rem; background:rgba(214, 184, 117, 0.25); color:#92400E; padding:1px 6px; border-radius:6px; margin-left:6px; font-weight:700;">Diff</span>' : '';

    tbodyHtml += `
      <tr class="${rowClass}">
        <td class="sticky-col">
          <div style="display:flex; align-items:center;">
            <span>${r.label}</span>
            ${diffBadge}
          </div>
        </td>
        ${r.values.map((val, idx) => {
          const isWinner = cols[idx] && cols[idx].id === winnerId;
          return `
            <td style="text-align:center; background:${isWinner ? 'rgba(196,166,245,0.06)' : 'transparent'};">
              ${val}
            </td>
          `;
        }).join('')}
      </tr>
    `;
  });

  tbody.innerHTML = tbodyHtml;
}

function toggleShowDifferences(checked) {
  showDifferencesOnly = checked;
  fetchFullComparison();
}

// =============================================================================
// SECTION 3: Feature and Specification Analysis
// =============================================================================

function renderSection3FeatureAnalysis(analysis) {
  const container = document.getElementById('specGroupsContainer');
  const summaryEl = document.getElementById('specMetricsSummary');
  if (!container || !analysis) return;

  const groups = analysis.groups || [];
  const sharedCount = (analysis.shared_keys || []).length;
  const uniqueCount = (analysis.unique_keys || []).length;

  if (summaryEl) {
    summaryEl.innerHTML = `
      <span style="background:var(--pt-secondary); padding:4px 10px; border-radius:12px; font-weight:700;">
        ${sharedCount} Shared Attributes • ${uniqueCount} Distinct Differences
      </span>
    `;
  }

  if (groups.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--pt-text-muted);">No specifications available across selected products.</div>`;
    return;
  }

  container.innerHTML = groups.map((g, gIdx) => `
    <div style="background:#FFFDF9; border:1px solid var(--pt-border); border-radius:12px; overflow:hidden;">
      <div style="padding:12px 18px; background:var(--pt-secondary); font-weight:800; font-size:0.88rem; color:var(--pt-text); display:flex; justify-content:space-between; align-items:center;">
        <span>${g.group_name}</span>
        <span style="font-size:0.75rem; color:var(--pt-text-muted); font-weight:600;">${g.rows.length} Specs</span>
      </div>
      <div style="padding:8px 0;">
        ${g.rows.map(row => `
          <div style="display:grid; grid-template-columns: 220px repeat(${row.values.length}, 1fr); padding:10px 18px; border-bottom:1px solid var(--pt-border); align-items:center; font-size:0.88rem;">
            <div style="font-weight:700; color:var(--pt-text); display:flex; align-items:center; gap:6px;">
              <span>${row.key}</span>
              ${row.is_shared ? '<span style="font-size:0.7rem; color:#10B981;">(Shared)</span>' : ''}
            </div>
            ${row.values.map((v, vIdx) => {
              const isBest = row.best_product_index === vIdx;
              const isMissing = !v || v === 'Not specified';
              return `
                <div style="text-align:center; ${isBest ? 'font-weight:800; color:#92400E;' : ''}">
                  ${isMissing ? '<span style="color:#81778E; font-style:italic;">Not specified</span>' : v}
                  ${isBest ? ' <span class="badge-gold">★ Best in Row</span>' : ''}
                </div>
              `;
            }).join('')}
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

// =============================================================================
// SECTION 4: Price and Value Comparison
// =============================================================================

function renderSection4PriceValue(priceValue) {
  const grid = document.getElementById('priceValueCardsGrid');
  const budgetNotice = document.getElementById('budgetAffordabilityNotice');
  if (!grid || !priceValue) return;

  const items = priceValue.items || [];
  grid.innerHTML = items.map(item => `
    <div style="background:#FFFDF9; border:1.5px solid ${item.is_best_value ? 'var(--pt-primary)' : 'var(--pt-border)'}; border-radius:14px; padding:20px; box-shadow:0 4px 16px rgba(64,54,83,0.04); position:relative;">
      <div style="margin-bottom:10px; display:flex; gap:6px; flex-wrap:wrap;">
        ${item.is_lowest_price ? '<span class="badge-lowest">🏷️ Lowest Price</span>' : ''}
        ${item.is_highest_discount ? '<span class="badge-discount">🔥 Top Discount</span>' : ''}
        ${item.is_best_value ? '<span class="badge-value">💎 Best Value Proposition</span>' : ''}
      </div>

      <h4 style="margin:0 0 8px 0; font-size:1rem; font-weight:800; color:var(--pt-text); line-height:1.3; height:42px; overflow:hidden;">
        ${item.product_name}
      </h4>

      <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:8px;">
        <span style="font-size:1.5rem; font-weight:800; color:#7C3AED;">${formatCurrency(item.price)}</span>
        ${item.discount_percentage ? `<span style="font-size:0.85rem; color:var(--pt-text-muted); text-decoration:line-through;">${formatCurrency(item.original_price)}</span>` : ''}
      </div>

      <div style="background:var(--pt-bg); border-radius:8px; padding:10px 12px; margin-bottom:12px; font-size:0.82rem; line-height:1.5;">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
          <span style="color:var(--pt-text-muted);">Savings:</span>
          <strong style="color:#10B981;">${item.discount_amount ? formatCurrency(item.discount_amount) : '₹0.00'} (${item.discount_percentage || 0}%)</strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
          <span style="color:var(--pt-text-muted);">Vs Lowest in Set:</span>
          <strong>${item.diff_from_lowest === 0 ? '<span style="color:#10B981;">Lowest Option</span>' : `+${formatCurrency(item.diff_from_lowest)}`}</strong>
        </div>
        ${item.unit_price_info ? `
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--pt-text-muted);">Unit Price:</span>
            <strong>${item.unit_price_info}</strong>
          </div>
        ` : ''}
      </div>

      <!-- Value Proposition Score Bar -->
      <div>
        <div style="display:flex; justify-content:space-between; font-size:0.78rem; font-weight:700; margin-bottom:4px;">
          <span style="color:var(--pt-text);">Value Rating</span>
          <span style="color:#7C3AED;">${item.value_score} / 100</span>
        </div>
        <div style="width:100%; height:8px; background:#EAE1F4; border-radius:4px; overflow:hidden;">
          <div style="width:${item.value_score}%; height:100%; background:linear-gradient(90deg, #C4A6F5, #7C3AED);"></div>
        </div>
      </div>
    </div>
  `).join('');

  // Budget Affordability Context
  if (budgetNotice) {
    if (priceValue.budget_context && priceValue.budget_context.user_monthly_budget) {
      const budget = priceValue.budget_context.user_monthly_budget;
      const affordableIds = priceValue.budget_context.affordable_products || [];
      budgetNotice.style.display = 'block';
      budgetNotice.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:1.3rem;">📊</span>
          <div style="font-size:0.88rem; color:var(--pt-text);">
            <strong>Feature 4 Budget Context:</strong> Your active monthly shopping budget is <strong>${formatCurrency(budget)}</strong>.
            ${affordableIds.length === items.length ? '<span style="color:#10B981; font-weight:700;"> All compared products fit comfortably within your monthly budget!</span>' : `<span style="color:#B45309; font-weight:700;"> ${affordableIds.length} of ${items.length} products fit within your monthly budget.</span>`}
          </div>
        </div>
      `;
    } else {
      budgetNotice.style.display = 'none';
    }
  }
}

// =============================================================================
// SECTION 5: Pros and Cons
// =============================================================================

function renderSection5ProsCons(prosCons, products) {
  const grid = document.getElementById('prosConsCardsGrid');
  if (!grid || !prosCons || !products) return;

  grid.innerHTML = products.map(p => {
    const data = prosCons[p.id] || { pros: [], cons: [] };
    const pros = data.pros || [];
    const cons = data.cons || [];

    return `
      <div style="background:#FFFDF9; border:1px solid var(--pt-border); border-radius:14px; padding:20px; box-shadow:0 4px 16px rgba(64,54,83,0.03); display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--pt-border);">
            <img src="${p.image_url || '/static/images/placeholder.png'}" style="width:40px; height:40px; object-fit:contain; border-radius:6px; background:#F7F3FF;" onerror="this.src='/static/images/placeholder.png'">
            <div>
              <h4 style="margin:0; font-size:0.92rem; font-weight:800; color:var(--pt-text); line-height:1.2;">${p.name}</h4>
              <span style="font-size:0.75rem; color:var(--pt-text-muted);">${formatCurrency(p.price)}</span>
            </div>
          </div>

          <!-- Verified Advantages (Pros) -->
          <div style="margin-bottom:14px;">
            <div style="font-size:0.8rem; font-weight:800; color:#15803D; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; display:flex; align-items:center; gap:4px;">
              <span>✓ Verified Advantages</span>
            </div>
            <ul style="margin:0; padding-left:18px; font-size:0.82rem; color:var(--pt-text); line-height:1.5;">
              ${pros.map(pr => `<li style="margin-bottom:4px;">${pr}</li>`).join('')}
            </ul>
          </div>

          <!-- Verified Limitations (Cons) -->
          <div>
            <div style="font-size:0.8rem; font-weight:800; color:#B45309; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; display:flex; align-items:center; gap:4px;">
              <span>⚠ Considerations &amp; Trade-offs</span>
            </div>
            <ul style="margin:0; padding-left:18px; font-size:0.82rem; color:var(--pt-text-muted); line-height:1.5;">
              ${cons.map(cn => `<li style="margin-bottom:4px;">${cn}</li>`).join('')}
            </ul>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// =============================================================================
// SECTION 6: Smart Decision Assistant
// =============================================================================

function onWeightSliderChange() {
  const p = parseInt(document.getElementById('wPrice').value, 10);
  const s = parseInt(document.getElementById('wSpecs').value, 10);
  const v = parseInt(document.getElementById('wValue').value, 10);
  const r = parseInt(document.getElementById('wRating').value, 10);
  const b = parseInt(document.getElementById('wBrand').value, 10);

  document.getElementById('wPriceVal').textContent = `${p}%`;
  document.getElementById('wSpecsVal').textContent = `${s}%`;
  document.getElementById('wValueVal').textContent = `${v}%`;
  document.getElementById('wRatingVal').textContent = `${r}%`;
  document.getElementById('wBrandVal').textContent = `${b}%`;

  currentWeights = { price: p, specs: s, value: v, rating: r, brand: b };

  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    fetchFullComparison();
  }, 300);
}

function resetDecisionWeights() {
  currentWeights = { price: 35, specs: 25, value: 20, rating: 15, brand: 5 };
  document.getElementById('wPrice').value = 35;
  document.getElementById('wSpecs').value = 25;
  document.getElementById('wValue').value = 20;
  document.getElementById('wRating').value = 15;
  document.getElementById('wBrand').value = 5;

  document.getElementById('wPriceVal').textContent = '35%';
  document.getElementById('wSpecsVal').textContent = '25%';
  document.getElementById('wValueVal').textContent = '20%';
  document.getElementById('wRatingVal').textContent = '15%';
  document.getElementById('wBrandVal').textContent = '5%';

  fetchFullComparison();
  notifyToast('Weights reset to default', 'info');
}

function renderSection6DecisionAssistant(decision) {
  if (!decision) return;

  const iconEl = document.getElementById('decisionIcon');
  const badgeEl = document.getElementById('decisionOutcomeBadge');
  const scorePill = document.getElementById('decisionScorePill');
  const titleEl = document.getElementById('decisionTitle');
  const reasonEl = document.getElementById('decisionReasonText');
  const tradeoffEl = document.getElementById('decisionTradeoffText');

  const winner = decision.winner;
  const isComparable = decision.is_comparable;

  if (isComparable) {
    if (iconEl) iconEl.textContent = '⚖️';
    if (badgeEl) {
      badgeEl.textContent = 'Comparable Options';
      badgeEl.style.background = '#D97706';
    }
    if (scorePill && winner) {
      scorePill.textContent = `Score Delta ≤ 3.0 pts`;
    }
  } else {
    if (iconEl) iconEl.textContent = '🏆';
    if (badgeEl) {
      badgeEl.textContent = 'Top Recommendation';
      badgeEl.style.background = '#7C3AED';
    }
    if (scorePill && winner) {
      scorePill.textContent = `Composite Score: ${winner.score} pts`;
    }
  }

  if (titleEl) titleEl.textContent = decision.decision_title || (winner ? `${winner.name} Recommended` : 'Decision Support');
  if (reasonEl && winner) reasonEl.textContent = winner.decision_reason;
  if (tradeoffEl) tradeoffEl.textContent = decision.tradeoff_explanation || 'Scores computed using normalized multi-attribute scoring.';
}

// =============================================================================
// SECTION 7: Final Decision and Product Actions
// =============================================================================

function renderSection7FinalActions(products) {
  const grid = document.getElementById('finalActionCardsGrid');
  if (!grid || !products) return;

  grid.innerHTML = products.map(p => `
    <div style="background:#FFFDF9; border:1px solid var(--pt-border); border-radius:14px; padding:18px; text-align:center; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 14px rgba(64,54,83,0.03);">
      <div>
        <div style="width:100px; height:100px; margin:0 auto 12px; background:#F7F3FF; border-radius:10px; display:flex; align-items:center; justify-content:center; overflow:hidden; border:1px solid var(--pt-border);">
          <img src="${p.image_url || '/static/images/placeholder.png'}" style="max-width:90%; max-height:90%; object-fit:contain;" onerror="this.src='/static/images/placeholder.png'">
        </div>
        <h4 style="margin:0 0 4px 0; font-size:0.95rem; font-weight:800; color:var(--pt-text); line-height:1.3; min-height:38px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
          ${p.name}
        </h4>
        <div style="font-size:0.8rem; color:var(--pt-text-muted); margin-bottom:8px;">${p.brand || 'Generic'}</div>
        <div style="font-size:1.25rem; font-weight:800; color:#7C3AED; margin-bottom:14px;">${formatCurrency(p.price)}</div>
      </div>

      <div style="display:flex; flex-direction:column; gap:8px;">
        <button class="btn-primary-pt" style="font-size:0.85rem; padding:9px 14px; width:100%;" onclick="addToCartById(${p.id})">
          🛒 Add to Cart
        </button>
        <button class="btn-outline-pt" style="font-size:0.8rem; padding:7px 12px; width:100%; justify-content:center;" onclick="toggleWishlistById(${p.id})">
          ❤️ Add to Wishlist
        </button>
        <div style="display:flex; gap:6px; margin-top:2px;">
          <a href="/product/${p.id}" class="btn-outline-pt" style="font-size:0.75rem; padding:5px 8px; flex:1; justify-content:center; text-decoration:none;">
            🔍 View Details
          </a>
          <button class="btn-outline-pt" style="font-size:0.75rem; padding:5px 8px; color:#DC2626; border-color:#FCA5A5;" onclick="removeProductFromComparison(${p.id})" title="Remove from comparison">
            Remove
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

// Sample Comparison Loader (fallback)
async function loadSampleComparison() {
  try {
    const res = await fetch('/api/comparison/search?limit=3');
    if (res.ok) {
      const data = await res.json();
      const ids = (data.products || []).slice(0, 3).map(p => p.id);
      if (ids.length >= 2) {
        applyPreset(ids);
      }
    }
  } catch (e) {
    console.error('Failed to load sample comparison:', e);
  }
}
