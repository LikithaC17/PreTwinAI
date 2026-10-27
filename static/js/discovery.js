/**
 * FLIPKART PRODUCT DISCOVERY & SEARCH CONTROLLER
 * Full support for 20 Categories, 128+ Subcategories, Brands, Pricing, Sorting & Pagination
 */

let allDiscoveryProducts = [];
let currentFiltered = [];
let currentSort = 'featured';
let currentPage = 1;
let totalPages = 1;
let totalCount = 0;
let availableSubcategories = [];
let availableBrands = [];
let selectedBrands = new Set();

async function initDiscovery() {
  const params = new URLSearchParams(window.location.search);
  const searchParam = params.get('search');
  const catParam = params.get('category');
  const subcatParam = params.get('subcategory');
  const sortParam = params.get('sort');
  const pageParam = parseInt(params.get('page')) || 1;
  const minP = params.get('min_price');
  const maxP = params.get('max_price');

  if (searchParam) {
    const input = document.getElementById('fkSearchInput');
    if (input) input.value = searchParam;
  }

  if (catParam) {
    const select = document.getElementById('categorySelect');
    if (select) select.value = catParam;
  }

  if (minP) {
    const el = document.getElementById('minPriceInput');
    if (el) el.value = minP;
  }

  if (maxP) {
    const el = document.getElementById('maxPriceInput');
    if (el) el.value = maxP;
  }

  if (sortParam) {
    currentSort = sortParam;
    updateSortTabsUI();
  }

  currentPage = pageParam;

  // Load subcategories for category if present
  if (catParam) {
    await loadSubcategories(catParam, subcatParam);
  }

  await applyFilters(currentPage);
}

async function onCategoryChange() {
  const cat = document.getElementById('categorySelect')?.value || '';
  await loadSubcategories(cat);
  selectedBrands.clear();
  await applyFilters(1);
}

async function loadSubcategories(category, defaultSelect = '') {
  const subcatSelect = document.getElementById('subcategorySelect');
  if (!subcatSelect) return;

  if (!category) {
    subcatSelect.innerHTML = '<option value="">All Subcategories</option>';
    return;
  }

  try {
    const res = await apiGet(`/api/subcategories?category=${encodeURIComponent(category)}`);
    const subcats = res.subcategories || [];
    availableSubcategories = subcats;

    let opts = '<option value="">All Subcategories</option>';
    subcats.forEach((s) => {
      const isSel = (defaultSelect && defaultSelect.toLowerCase() === s.toLowerCase()) ? 'selected' : '';
      opts += `<option value="${s}" ${isSel}>${s}</option>`;
    });
    subcatSelect.innerHTML = opts;
  } catch (err) {
    console.error('Failed to load subcategories:', err);
  }
}

function setPriceRange(min, max) {
  const minEl = document.getElementById('minPriceInput');
  const maxEl = document.getElementById('maxPriceInput');
  if (minEl) minEl.value = min;
  if (maxEl) maxEl.value = max >= 150000 ? '' : max;
  applyFilters(1);
}

function updateSortTabsUI() {
  document.querySelectorAll('.fk-sort-tab').forEach((t) => {
    t.style.color = '#212121';
    t.style.borderBottom = 'none';
    t.style.fontWeight = 'normal';
  });
  const activeTab = document.querySelector(`.fk-sort-tab[onclick*="'${currentSort}'"]`);
  if (activeTab) {
    activeTab.style.color = '#2874f0';
    activeTab.style.borderBottom = '2px solid #2874f0';
    activeTab.style.fontWeight = '600';
  }
}

function setSort(sortType, tabEl) {
  currentSort = sortType;
  updateSortTabsUI();
  applyFilters(1);
}

async function applyFilters(page = 1) {
  currentPage = page;
  const grid = document.getElementById('productsGrid');
  const countEl = document.getElementById('resultsCount');
  const titleEl = document.getElementById('resultsTitle');

  const params = new URLSearchParams(window.location.search);
  const search = (document.getElementById('fkSearchInput')?.value || params.get('search') || '').trim();
  const category = document.getElementById('categorySelect')?.value || '';
  const subcategory = document.getElementById('subcategorySelect')?.value || params.get('subcategory') || '';
  const minPrice = parseFloat(document.getElementById('minPriceInput')?.value);
  const maxPrice = parseFloat(document.getElementById('maxPriceInput')?.value);
  const rating4 = document.getElementById('rating4Check')?.checked;
  const rating3 = document.getElementById('rating3Check')?.checked;
  const assuredOnly = document.getElementById('assuredCheck')?.checked;

  const discountRadio = document.querySelector('input[name="discountFilter"]:checked');
  const minDiscount = parseInt(discountRadio ? discountRadio.value : '0') || 0;

  // Build query
  const query = new URLSearchParams();
  if (search) query.set('search', search);
  if (category) query.set('category', category);
  if (subcategory) query.set('subcategory', subcategory);
  if (!isNaN(minPrice)) query.set('min_price', minPrice);
  if (!isNaN(maxPrice)) query.set('max_price', maxPrice);
  if (rating4) query.set('min_rating', '4.0');
  else if (rating3) query.set('min_rating', '3.0');

  if (selectedBrands.size > 0) {
    query.set('brand', Array.from(selectedBrands).join(','));
  }

  query.set('sort', currentSort);
  query.set('page', currentPage);
  query.set('limit', '24');

  // Update browser URL without reloading
  const newUrl = `/discovery?${query.toString()}`;
  window.history.replaceState({}, '', newUrl);

  try {
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:48px; color:#878787;"><p>Loading products...</p></div>';

    const data = await apiGet(`/api/products?${query.toString()}`);
    let products = data.products || [];
    totalCount = data.total || products.length;
    totalPages = data.pages || Math.ceil(totalCount / 24) || 1;

    // Client-side discount and assured filter if needed
    if (minDiscount > 0) {
      products = products.filter((p) => (p.discount_percentage || 15) >= minDiscount);
    }

    allDiscoveryProducts = products;
    currentFiltered = products;

    // Update brands list in sidebar if available
    if (data.brands && data.brands.length) {
      renderBrandFilters(data.brands);
    }

    // Update title & counts
    if (titleEl) {
      if (search) titleEl.textContent = `Results for "${search}"`;
      else if (subcategory) titleEl.textContent = `${subcategory} (${category || 'Catalogue'})`;
      else if (category) titleEl.textContent = `${category}`;
      else titleEl.textContent = 'All Products Catalogue';
    }

    if (countEl) {
      countEl.textContent = `(Showing ${totalCount} products — Page ${currentPage} of ${totalPages})`;
    }

    renderAppliedTags(category, subcategory, search, minPrice, maxPrice, selectedBrands);
    renderGrid();
    renderPagination();
  } catch (err) {
    console.error('Failed to discover products:', err);
    if (grid) {
      grid.innerHTML = '<p style="grid-column: 1/-1; text-align:center; padding:32px; color:#d32f2f;">Failed to load products. Please try again.</p>';
    }
  }
}

function renderBrandFilters(brands) {
  const brandList = document.getElementById('brandList');
  if (!brandList) return;

  const topBrands = brands.slice(0, 15);
  brandList.innerHTML = topBrands.map((b) => {
    const isChecked = selectedBrands.has(b) ? 'checked' : '';
    const safeBrand = b.replace(/"/g, '&quot;');
    return `
      <label style="display:flex; align-items:center; gap:8px; font-size:13px; color:#212121; cursor:pointer;">
        <input type="checkbox" value="${safeBrand}" ${isChecked} onchange="toggleBrand('${safeBrand}')">
        <span>${b}</span>
      </label>
    `;
  }).join('');
}

function toggleBrand(b) {
  if (selectedBrands.has(b)) selectedBrands.delete(b);
  else selectedBrands.add(b);
  applyFilters(1);
}

function renderAppliedTags(category, subcategory, search, minP, maxP, brands) {
  const container = document.getElementById('appliedFilterTags');
  if (!container) return;

  let tags = [];
  if (category) {
    tags.push(`<span class="fk-filter-tag">${category} <b onclick="removeFilter('category')">&times;</b></span>`);
  }
  if (subcategory) {
    tags.push(`<span class="fk-filter-tag">${subcategory} <b onclick="removeFilter('subcategory')">&times;</b></span>`);
  }
  if (search) {
    tags.push(`<span class="fk-filter-tag">"${search}" <b onclick="removeFilter('search')">&times;</b></span>`);
  }
  if (!isNaN(minP) || !isNaN(maxP)) {
    const label = `₹${minP || 0} - ₹${maxP || 'Above'}`;
    tags.push(`<span class="fk-filter-tag">${label} <b onclick="removeFilter('price')">&times;</b></span>`);
  }
  brands.forEach((b) => {
    tags.push(`<span class="fk-filter-tag">${b} <b onclick="toggleBrand('${b}')">&times;</b></span>`);
  });

  container.innerHTML = tags.join('');
}

function removeFilter(type) {
  if (type === 'category') {
    const cat = document.getElementById('categorySelect');
    if (cat) cat.value = '';
    const subcat = document.getElementById('subcategorySelect');
    if (subcat) subcat.innerHTML = '<option value="">All Subcategories</option>';
  } else if (type === 'subcategory') {
    const subcat = document.getElementById('subcategorySelect');
    if (subcat) subcat.value = '';
  } else if (type === 'search') {
    const s = document.getElementById('fkSearchInput');
    if (s) s.value = '';
  } else if (type === 'price') {
    const minP = document.getElementById('minPriceInput');
    const maxP = document.getElementById('maxPriceInput');
    if (minP) minP.value = '';
    if (maxP) maxP.value = '';
  }
  applyFilters(1);
}

function renderGrid() {
  const grid = document.getElementById('productsGrid');
  if (!grid) return;

  if (currentFiltered.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align:center; padding:48px; background:#fff;">
        <img src="https://rukminim1.flixcart.com/www/800/800/promos/16/05/2019/d438a32e-765a-4d8b-b4a6-520b560971e8.png?q=90" style="height:120px; margin-bottom:16px;" alt="No results">
        <h3 style="font-size:18px; color:#212121; margin-bottom:8px;">Sorry, no products found!</h3>
        <p style="color:#878787; font-size:13px; margin-bottom:16px;">Try clearing filters or selecting another category.</p>
        <button class="fk-btn-orange" style="display:inline-block; width:160px;" onclick="clearFilters()">Clear Filters</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = currentFiltered.map((p) => {
    window.catalogMap = window.catalogMap || {};
    window.catalogMap[p.id] = p;
    const originalMrp = p.mrp || Math.round(p.price * 1.35);
    const discPct = p.discount_percentage || Math.round(((originalMrp - p.price) / originalMrp) * 100);
    const fallbackImg = getCategoryFallbackImg ? getCategoryFallbackImg(p.category) : 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&q=80';
    const displayImg = p.image_url || fallbackImg;

    return `
      <div class="fk-grid-card" onclick="openProductDetail(${p.id})">
        <button 
          class="fk-card-wish" 
          data-product-id="${p.id}" 
          onclick="event.stopPropagation(); toggleWishlistById(${p.id});" 
          title="Add to Wishlist"
        >
          ♥
        </button>

        <div class="fk-grid-card-img">
          <img src="${displayImg}" alt="${p.name}" loading="lazy" onerror="this.src='${fallbackImg}'">
        </div>

        <div class="fk-card-title" title="${p.name}">
          ${p.name}
        </div>

        <div style="display:flex; align-items:center; margin:4px 0;">
          <span class="fk-rating-badge">${(p.rating || 4.4).toFixed(1)} ★</span>
          <span style="color:#878787; font-size:11px; margin-left:6px;">(${p.review_count_demo || 120})</span>
          <span style="color:#2874f0; font-size:11px; font-weight:700; margin-left:auto;">PreTwin Assured</span>
        </div>

        <div class="fk-card-price-row">
          <span class="fk-card-curr-price">${formatPrice(p.price)}</span>
          <span class="fk-card-mrp">${formatPrice(originalMrp)}</span>
          <span style="color:var(--fk-green); font-size:12px; font-weight:600;">${discPct}% off</span>
        </div>

        <div class="fk-card-sub">
          ${p.brand ? p.brand + ' • ' : ''}${p.subcategory || p.category}
        </div>

        <div class="fk-card-quick-add" onclick="event.stopPropagation()">
          <button class="fk-btn-add" onclick="addToCartById(${p.id})">
            ADD TO CART
          </button>
        </div>
      </div>
    `;
  }).join('');

  updateWishlistIcons();
}

function renderPagination() {
  const container = document.getElementById('paginationContainer');
  const info = document.getElementById('paginationInfo');
  const btns = document.getElementById('paginationButtons');

  if (!container || !btns) return;

  if (totalPages <= 1) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'flex';
  if (info) {
    info.textContent = `Page ${currentPage} of ${totalPages} (${totalCount} products)`;
  }

  let html = '';

  // Prev Button
  if (currentPage > 1) {
    html += `<button class="fk-page-btn" onclick="applyFilters(${currentPage - 1})">PREVIOUS</button>`;
  }

  // Page Numbers (up to 5 pages around current)
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, start + 4);

  for (let i = start; i <= end; i++) {
    const activeClass = (i === currentPage) ? 'active' : '';
    html += `<button class="fk-page-btn ${activeClass}" onclick="applyFilters(${i})">${i}</button>`;
  }

  // Next Button
  if (currentPage < totalPages) {
    html += `<button class="fk-page-btn" onclick="applyFilters(${currentPage + 1})">NEXT</button>`;
  }

  btns.innerHTML = html;
}

function clearFilters() {
  const cat = document.getElementById('categorySelect');
  const subcat = document.getElementById('subcategorySelect');
  const minP = document.getElementById('minPriceInput');
  const maxP = document.getElementById('maxPriceInput');
  const r4 = document.getElementById('rating4Check');
  const r3 = document.getElementById('rating3Check');
  const searchInput = document.getElementById('fkSearchInput');
  const allDiscount = document.querySelector('input[name="discountFilter"][value="0"]');

  if (cat) cat.value = '';
  if (subcat) subcat.innerHTML = '<option value="">All Subcategories</option>';
  if (minP) minP.value = '';
  if (maxP) maxP.value = '';
  if (r4) r4.checked = false;
  if (r3) r3.checked = false;
  if (searchInput) searchInput.value = '';
  if (allDiscount) allDiscount.checked = true;
  selectedBrands.clear();

  window.history.pushState({}, '', '/discovery');
  const title = document.getElementById('resultsTitle');
  if (title) title.textContent = 'All Products Catalogue';

  applyFilters(1);
}

async function executeNlSearch() {
  const input = document.getElementById("aiNlSearchInput");
  const query = (input ? input.value : "").trim();
  if (!query) return;

  const feedback = document.getElementById("nlSearchFeedback");
  if (feedback) {
    feedback.style.display = "block";
    feedback.innerText = "Parsing intent & evaluating catalogue relevance...";
  }

  try {
    const res = await fetch("/api/discovery/nl-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    if (feedback) {
      const intent = data.parsed_intent || {};
      feedback.innerHTML = `
        ✓ Identified intent: Category [<strong>${intent.category || 'All'}</strong>]
        ${intent.max_price ? `• Cap: ₹<strong>${intent.max_price}</strong>` : ''}
        • Found <strong>${data.total_matches}</strong> matching items.
      `;
    }

    // Render results
    const grid = document.getElementById("productsGrid");
    if (grid && data.products) {
      grid.innerHTML = data.products.map(p => {
        const rating = parseFloat(p.rating || 4.2).toFixed(1);
        const price = Math.round(p.price).toLocaleString("en-IN");
        return `
          <div class="fk-product-card" onclick="openProductModal(${p.id})">
            <div class="fk-card-image-wrap">
              <img src="${p.image_url}" alt="${p.name}" loading="lazy" onerror="this.onerror=null;this.src='/static/img/placeholder.svg';">
            </div>
            <div class="fk-card-body">
              <div style="font-size:0.75rem; color:#6366f1; font-weight:700; margin-bottom:2px;">${p.match_reason || 'AI Match'}</div>
              <h3 class="fk-card-title">${p.name}</h3>
              <div class="fk-rating-row">
                <span class="fk-rating-badge">${rating} ★</span>
                <span class="fk-rating-count">(PreTwin Verified)</span>
              </div>
              <div class="fk-price-row">
                <span class="fk-current-price">₹${price}</span>
              </div>
            </div>
          </div>
        `;
      }).join("");

      const title = document.getElementById("resultsTitle");
      if (title) title.innerText = `AI Results for "${query}"`;
    }
  } catch (err) {
    if (feedback) feedback.innerText = "Search error: " + err.message;
  }
}

async function triggerVisualSearchModal() {
  const cat = prompt("Select style hint for visual upload (e.g. Shoes, Watch, Headphone, Dress, Laptop):", "Shoes");
  if (!cat) return;

  try {
    const res = await fetch("/api/discovery/visual-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category_hint: cat, style_tag: "Casual" })
    });
    const data = await res.json();
    if (data.products) {
      const grid = document.getElementById("productsGrid");
      if (grid) {
        grid.innerHTML = data.products.map(p => {
          const rating = parseFloat(p.rating || 4.2).toFixed(1);
          const price = Math.round(p.price).toLocaleString("en-IN");
          return `
            <div class="fk-product-card" onclick="openProductModal(${p.id})">
              <div class="fk-card-image-wrap">
                <img src="${p.image_url}" alt="${p.name}" loading="lazy" onerror="this.onerror=null;this.src='/static/img/placeholder.svg';">
              </div>
              <div class="fk-card-body">
                <div style="font-size:0.75rem; color:#10b981; font-weight:700; margin-bottom:2px;">
                  Visual Similarity: ${Math.round(p.visual_similarity * 100)}%
                </div>
                <h3 class="fk-card-title">${p.name}</h3>
                <div class="fk-rating-row">
                  <span class="fk-rating-badge">${rating} ★</span>
                </div>
                <div class="fk-price-row">
                  <span class="fk-current-price">₹${price}</span>
                </div>
              </div>
            </div>
          `;
        }).join("");

        const title = document.getElementById("resultsTitle");
        if (title) title.innerText = `Visual Matches for "${cat}" (${data.confidence * 100}% Confidence)`;
      }
    }
  } catch (e) {
    alert("Visual search: " + e.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initDiscovery();
});
