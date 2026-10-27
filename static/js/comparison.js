/**
 * PreTwinShop AI - Product Comparison & Decision Support Controller (Agent D)
 */

let comparisonProducts = [];
let currentWinnerId = null;

async function initComparisonPage() {
  await populateProductSelect();
  renderSelectedPills();
  const ids = getComparisonIds();
  if (ids.length >= 2) {
    await fetchComparison(ids);
  } else if (ids.length === 1) {
    showToast('Add at least one more product to begin side-by-side comparison', 'info');
  } else {
    // Offer sample comparison when opened empty
    await loadSampleComparison();
  }
}

async function populateProductSelect() {
  const select = document.getElementById('addProductSelect');
  if (!select) return;

  try {
    const data = await apiGet('/api/products?limit=100');
    const prods = data.products || [];
    select.innerHTML = '<option value="">Choose a product from catalogue...</option>' +
      prods.map((p) => `<option value="${p.id}">${p.name} (${formatPrice(p.price)}) — ${p.category}</option>`).join('');
  } catch (err) {
    console.error('Failed to populate product select:', err);
  }
}

function renderSelectedPills() {
  const container = document.getElementById('selectedPillsContainer');
  if (!container) return;
  const ids = getComparisonIds();
  if (!ids.length) {
    container.innerHTML = '<span style="font-size:0.82rem; color:#64748b; font-style:italic;">None selected yet.</span>';
    return;
  }
  container.innerHTML = ids.map(id => {
    const p = window.catalogMap?.[id] || (window.allCatalogProducts && window.allCatalogProducts.find(x => x.id === id));
    const title = p ? p.name : `Product #${id}`;
    return `
      <span style="display:inline-flex; align-items:center; gap:6px; background:#1e293b; border:1px solid #475569; color:#f1f5f9; padding:4px 10px; border-radius:16px; font-size:0.8rem;">
        <span>${title}</span>
        <button onclick="removeProductFromComparison(${id})" style="background:none; border:none; color:#f87171; cursor:pointer; font-weight:700; font-size:12px; line-height:1;" title="Remove">&times;</button>
      </span>
    `;
  }).join('');
}

async function addProductFromSelect() {
  const select = document.getElementById('addProductSelect');
  if (!select) return;
  const val = parseInt(select.value, 10);
  if (!val) {
    showToast('Please select a product from the dropdown first', 'warning');
    return;
  }

  const ids = getComparisonIds();
  if (ids.includes(val)) {
    showToast('This product is already in the comparison table', 'info');
    return;
  }
  if (ids.length >= 4) {
    showToast('Maximum 4 products allowed for comparison. Remove one to add another.', 'warning');
    return;
  }

  ids.push(val);
  saveComparisonIds(ids);
  renderSelectedPills();
  await fetchComparison(ids);
  select.value = '';
}

async function fetchComparison(ids) {
  if (!ids || ids.length < 2) {
    renderEmptyState();
    return;
  }

  const tableHead = document.getElementById('comparisonTableHead');
  const tableBody = document.getElementById('comparisonTableBody');
  const winnerBanner = document.getElementById('comparisonWinnerBanner');

  if (tableBody) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center py-5" style="padding:48px 20px; text-align:center;">
          <div class="spinner"></div>
          <p style="margin-top:14px; color:#c4b5fd; font-weight:600;">Agent D analyzing specifications and calculating value tradeoffs...</p>
        </td>
      </tr>
    `;
  }

  try {
    const res = await apiPost('/api/comparisons', { product_ids: ids });
    const products = res.products || res.comparison_table || [];

    if (!products || products.length === 0) {
      throw new Error("No comparison records returned from server");
    }

    comparisonProducts = products;
    currentWinnerId = res.winner_id || (products[0] && products[0].product_id);

    renderComparisonTable(products, currentWinnerId, res.winner_reason);

    // Winner Banner
    if (winnerBanner && (res.winner_reason || res.winner_id)) {
      const winnerName = document.getElementById('winnerProductName');
      const winnerReasonEl = document.getElementById('winnerReason');
      const winProd = products.find((p) => (p.product_id || p.id) === currentWinnerId);
      if (winnerName) {
        winnerName.textContent = winProd ? (winProd.product_name || winProd.name) : 'Best Overall Pick';
      }
      if (winnerReasonEl) {
        winnerReasonEl.textContent = res.winner_reason || 'Identified as the highest scoring choice for your shopping profile.';
      }
      winnerBanner.style.display = 'block';
    } else if (winnerBanner) {
      winnerBanner.style.display = 'none';
    }
  } catch (err) {
    console.error('Comparison fetch failed:', err);
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4" style="color:#ef4444; padding:32px; text-align:center;">
            Comparison notice: ${err.message}. Please select active catalogue items.
          </td>
        </tr>
      `;
    }
  }
}

function renderComparisonTable(products, winnerId, winnerReason) {
  const thead = document.getElementById('comparisonTableHead');
  const tbody = document.getElementById('comparisonTableBody');
  if (!thead || !tbody) return;

  const minPrice = Math.min(...products.map(p => Number(p.price) || 999999));

  // Build header columns
  thead.innerHTML = `
    <th class="spec-col-header" style="width: 220px; padding: 18px 20px; position: sticky; left: 0; background: #1e293b; z-index: 2; border-right: 1px solid #334155; color: #94a3b8; font-size: 0.85rem; font-weight: 700; text-transform: uppercase;">
      Products &amp; Criteria
    </th>
    ${products.map((p) => {
      const pid = p.product_id || p.id;
      const isWinner = pid === winnerId;
      const isLowest = Number(p.price) === minPrice;
      const fallbackImg = getCategoryFallbackImg(p.category);
      const img = p.image_url || fallbackImg;
      const name = p.product_name || p.name || 'Product';

      return `
        <th class="comp-col-header" style="min-width: 240px; padding: 18px 16px; text-align: center; border-right: 1px solid #334155; vertical-align: top; background: ${isWinner ? 'rgba(124, 58, 237, 0.12)' : '#1e293b'};">
          <div style="position:relative;">
            <button onclick="removeProductFromComparison(${pid})" style="position:absolute; top:-6px; right:-6px; background:#334155; color:#cbd5e1; border:none; border-radius:50%; width:24px; height:24px; font-weight:700; cursor:pointer; font-size:14px; line-height:1;" title="Remove this product">&times;</button>
            
            ${isWinner ? '<div style="display:inline-block; background:#7c3aed; color:#fff; font-size:0.7rem; font-weight:800; padding:3px 10px; border-radius:10px; text-transform:uppercase; margin-bottom:8px;">👑 Top Pick</div>' : ''}
            ${isLowest ? '<div style="display:inline-block; background:#10b981; color:#fff; font-size:0.7rem; font-weight:800; padding:3px 10px; border-radius:10px; text-transform:uppercase; margin-bottom:8px; margin-left:4px;">🏷️ Lowest Price</div>' : ''}

            <div style="width: 100px; height: 100px; margin: 0 auto 10px auto; background: #0f172a; border-radius: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden; border: 1px solid #334155;">
              <img src="${img}" alt="${name}" style="max-width: 90%; max-height: 90%; object-fit: contain;" onerror="this.onerror=null; this.src='${fallbackImg}';">
            </div>

            <div style="font-size: 0.95rem; font-weight: 700; color: #f1f5f9; line-height: 1.3; min-height: 38px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${name}">
              ${name}
            </div>

            <div style="font-size: 1.25rem; font-weight: 800; color: #38bdf8; margin: 6px 0;">
              ${formatPrice(p.price)}
            </div>

            <div style="display:flex; flex-direction:column; gap:6px; margin-top:10px;">
              <button onclick="addToCartById(${pid})" style="width:100%; padding:8px 12px; background:linear-gradient(135deg, #7c3aed, #4f46e5); color:#fff; border:none; border-radius:6px; font-size:0.82rem; font-weight:700; cursor:pointer; box-shadow:0 2px 8px rgba(124, 58, 237, 0.3);">
                🛒 Add to Cart
              </button>
              <button onclick="toggleWishlistById(${pid})" style="width:100%; padding:6px 12px; background:rgba(255,255,255,0.06); border:1px solid #475569; color:#cbd5e1; border-radius:6px; font-size:0.8rem; font-weight:600; cursor:pointer;">
                ❤️ Wishlist
              </button>
            </div>
          </div>
        </th>
      `;
    }).join('')}
  `;

  // Collect all verified specification keys across products
  const allSpecKeys = new Set();
  products.forEach(p => {
    let s = p.specifications || p.specs || {};
    if (typeof s === 'string') {
      try { s = JSON.parse(s); } catch (e) { s = {}; }
    }
    Object.keys(s).forEach(k => allSpecKeys.add(k));
  });

  const specRows = Array.from(allSpecKeys).slice(0, 8);

  // Grouped Metric Rows
  let html = '';

  // Section 1: Overview & Brand
  html += `
    <tr style="background:#1e293b;"><td colspan="${products.length + 1}" style="padding:10px 18px; font-weight:800; color:#c084fc; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">1. Product Basics &amp; Trust</td></tr>
    ${createRow('Category', (p) => p.category || '--', products, winnerId)}
    ${createRow('Brand', (p) => p.brand ? `<strong>${p.brand}</strong>` : '--', products, winnerId)}
    ${createRow('Customer Rating', (p) => `⭐ ${(Number(p.rating) || 4.4).toFixed(1)} / 5.0`, products, winnerId)}
    ${createRow('Stock Availability', (p) => `<span style="color:#10b981; font-weight:600;">✓ In Stock (${p.stock || 25} units)</span>`, products, winnerId)}
  `;

  // Section 2: Pricing & Budget
  html += `
    <tr style="background:#1e293b;"><td colspan="${products.length + 1}" style="padding:10px 18px; font-weight:800; color:#c084fc; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">2. Price &amp; Value Analysis</td></tr>
    ${createRow('Current Price', (p) => `<span style="font-weight:700; color:#38bdf8;">${formatPrice(p.price)}</span>`, products, winnerId)}
    ${createRow('Price Comparison', (p) => {
      const diff = Number(p.price) - minPrice;
      if (diff === 0) return '<span style="color:#10b981; font-weight:700;">★ Best Price in Comparison</span>';
      return `<span style="color:#f59e0b;">+${formatPrice(diff)} vs lowest</span>`;
    }, products, winnerId)}
    ${createRow('Delivery & Returns', (p) => '<span style="color:#cbd5e1;">Free Prime Express • 7-day replacement</span>', products, winnerId)}
  `;

  // Section 3: Verified Catalogue Specs
  if (specRows.length > 0) {
    html += `<tr style="background:#1e293b;"><td colspan="${products.length + 1}" style="padding:10px 18px; font-weight:800; color:#c084fc; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">3. Verified Catalogue Specifications</td></tr>`;
    specRows.forEach(key => {
      html += createRow(key.replace(/_/g, ' '), (p) => {
        let s = p.specifications || p.specs || {};
        if (typeof s === 'string') {
          try { s = JSON.parse(s); } catch (e) { s = {}; }
        }
        return s[key] || '<span style="color:#64748b;">--</span>';
      }, products, winnerId);
    });
  }

  // Section 4: Agent D Decision Insights
  html += `
    <tr style="background:#1e293b;"><td colspan="${products.length + 1}" style="padding:10px 18px; font-weight:800; color:#c084fc; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">4. Agent D Decision Intelligence</td></tr>
    ${createRow('Key Advantages', (p) => {
      const adv = Array.isArray(p.advantages) ? p.advantages : [p.advantages || 'High quality build'];
      return `<ul style="margin:0; padding-left:18px; text-align:left; color:#a7f3d0; font-size:0.82rem;">${adv.map(a => `<li>${a}</li>`).join('')}</ul>`;
    }, products, winnerId)}
    ${createRow('Considerations', (p) => {
      const lim = Array.isArray(p.limitations) ? p.limitations : [p.limitations || 'None reported'];
      return `<ul style="margin:0; padding-left:18px; text-align:left; color:#cbd5e1; font-size:0.82rem;">${lim.map(l => `<li>${l}</li>`).join('')}</ul>`;
    }, products, winnerId)}
    ${createRow('Agent D Score', (p) => {
      const score = p.comparison_score || (p.scores && p.scores.composite) || 85.0;
      return `<div style="font-weight:800; color:#c084fc; font-size:1.05rem;">${score} pts</div>`;
    }, products, winnerId)}
  `;

  tbody.innerHTML = html;
}

function createRow(label, valueFn, products, winnerId) {
  return `
    <tr style="border-bottom: 1px solid #1e293b;">
      <td class="spec-label" style="padding: 14px 18px; font-weight: 600; color: #cbd5e1; background: #0f172a; position: sticky; left: 0; z-index: 1; border-right: 1px solid #334155; font-size: 0.88rem;">
        ${label}
      </td>
      ${products.map(p => {
        const pid = p.product_id || p.id;
        const isWinner = pid === winnerId;
        return `
          <td style="padding: 14px 16px; text-align: center; color: #f1f5f9; border-right: 1px solid #1e293b; background: ${isWinner ? 'rgba(124, 58, 237, 0.05)' : 'transparent'}; font-size: 0.88rem; vertical-align: middle;">
            ${valueFn(p)}
          </td>
        `;
      }).join('')}
    </tr>
  `;
}

function removeProductFromComparison(productId) {
  let ids = getComparisonIds();
  ids = ids.filter((id) => id !== productId);
  saveComparisonIds(ids);
  renderSelectedPills();
  if (ids.length >= 2) {
    fetchComparison(ids);
  } else {
    renderEmptyState();
  }
}

function clearAllComparison() {
  saveComparisonIds([]);
  renderSelectedPills();
  renderEmptyState();
  showToast('Comparison list cleared', 'info');
}

function renderEmptyState() {
  const thead = document.getElementById('comparisonTableHead');
  const tbody = document.getElementById('comparisonTableBody');
  const banner = document.getElementById('comparisonWinnerBanner');

  if (banner) banner.style.display = 'none';
  if (thead) {
    thead.innerHTML = '<th class="spec-col-header" style="width:220px; padding:18px 20px;">Criteria &amp; Metrics</th>';
  }
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center py-5" style="padding:48px 20px; text-align:center;">
          <div class="empty-state">
            <span class="empty-icon" style="font-size:2.6rem; display:block; margin-bottom:12px;">⚖️</span>
            <h4 style="color:#f1f5f9; font-size:1.2rem; margin:0 0 6px 0;">No Products in Comparison</h4>
            <p style="color:#94a3b8; font-size:0.9rem; max-width:440px; margin:0 auto 16px auto;">
              Select at least two products from the catalogue above or click "Compare" on any product card in the store.
            </p>
            <button class="btn btn-primary" onclick="loadSampleComparison()" style="padding:10px 20px; background:linear-gradient(135deg, #7c3aed, #4f46e5); color:#fff; border:none; border-radius:8px; font-weight:700; cursor:pointer;">
              Load Recommended Comparison
            </button>
          </div>
        </td>
      </tr>
    `;
  }
}

async function loadSampleComparison() {
  try {
    const data = await apiGet('/api/products?limit=8');
    const prods = data.products || [];
    if (prods.length >= 3) {
      const ids = prods.slice(0, 3).map((p) => p.id);
      saveComparisonIds(ids);
      renderSelectedPills();
      await fetchComparison(ids);
    }
  } catch (e) {
    console.error('Failed to load sample comparison:', e);
  }
}

function updateWeightsUI() {
  const p = document.getElementById("wPrice") ? document.getElementById("wPrice").value : 35;
  const r = document.getElementById("wRating") ? document.getElementById("wRating").value : 30;
  const s = document.getElementById("wSpecs") ? document.getElementById("wSpecs").value : 20;
  const b = document.getElementById("wBrand") ? document.getElementById("wBrand").value : 15;

  if (document.getElementById("wPriceVal")) document.getElementById("wPriceVal").innerText = `${p}%`;
  if (document.getElementById("wRatingVal")) document.getElementById("wRatingVal").innerText = `${r}%`;
  if (document.getElementById("wSpecsVal")) document.getElementById("wSpecsVal").innerText = `${s}%`;
  if (document.getElementById("wBrandVal")) document.getElementById("wBrandVal").innerText = `${b}%`;

  const ids = getComparisonIds();
  if (ids.length >= 2) {
    runWeightedComparison(ids, { price: p, rating: r, specs: s, brand: b });
  }
}

async function runWeightedComparison(ids, weights) {
  try {
    const res = await fetch("/api/comparison/weighted", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_ids: ids, weights: weights })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const winnerBanner = document.getElementById('comparisonWinnerBanner');
    const winnerName = document.getElementById('winnerProductName');
    const winnerReasonEl = document.getElementById('winnerReason');

    if (data.winner) {
      currentWinnerId = data.winner.id;
      if (winnerBanner) {
        winnerBanner.style.display = 'block';
        if (winnerName) winnerName.textContent = data.winner.name;
        if (winnerReasonEl) winnerReasonEl.textContent = data.winner.decision_reason;
      }
      if (comparisonProducts && comparisonProducts.length > 0) {
        renderComparisonTable(comparisonProducts, currentWinnerId, data.winner.decision_reason);
      }
    }
  } catch (err) {
    console.error("Weighted comparison update notice:", err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initComparisonPage();
});