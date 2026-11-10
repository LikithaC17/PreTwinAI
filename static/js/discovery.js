/**
 * static/js/discovery.js
 * =======================
 * PreTwin AI Smart Product Discovery (Feature 3)
 * Full 7-Section Architecture:
 * 1. Search Products (Natural-Language & Keyword Intent Parser)
 * 2. Explore Categories (All 20 Categories with Live Counts & Subcategories)
 * 3. Filter & Sort Products (Simultaneous Multi-Dimensional Filtering & Sorting)
 * 4. Smart Search Suggestions (Real-time Autocomplete, Typos & Zero-Result Fallbacks)
 * 5. Discover Products (Curated Catalogue Collections)
 * 6. Related Products & Alternatives (Budget-Friendly, Premium & Similar Alternatives)
 * 7. Product Details & Shopping Actions (Immediate Add to Cart & Wishlist Sync)
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
let allCategoriesSummary = [];
let isCategoriesExpanded = false;
let searchDebounceTimer = null;
let currentDidYouMean = null;

// =========================================================================
// INITIALIZATION
// =========================================================================

async function initDiscovery() {
  const params = new URLSearchParams(window.location.search);
  const searchParam = params.get('search') || '';
  const catParam = params.get('category') || '';
  const subcatParam = params.get('subcategory') || '';
  const sortParam = params.get('sort') || 'featured';
  const pageParam = parseInt(params.get('page')) || 1;
  const minP = params.get('min_price');
  const maxP = params.get('max_price');
  const brandParam = params.get('brand');

  const searchInput = document.getElementById('aiNlSearchInput');
  const fkInput = document.getElementById('fkSearchInput');
  if (searchParam) {
    if (searchInput) searchInput.value = searchParam;
    if (fkInput) fkInput.value = searchParam;
    const clearBtn = document.getElementById('searchClearBtn');
    if (clearBtn) clearBtn.style.display = 'block';
  }

  const catSelect = document.getElementById('categorySelect');
  if (catSelect && catParam) catSelect.value = catParam;

  if (minP && document.getElementById('minPriceInput')) {
    document.getElementById('minPriceInput').value = minP;
  }
  if (maxP && document.getElementById('maxPriceInput')) {
    document.getElementById('maxPriceInput').value = maxP;
  }

  if (brandParam) {
    brandParam.split(',').forEach(b => {
      if (b.trim()) selectedBrands.add(b.trim());
    });
  }

  currentSort = sortParam;
  currentPage = pageParam;
  updateSortTabsUI();

  // 1. Fetch categories summary (Section 2)
  await loadCategoriesSummary();

  // 2. Load subcategories if category active
  if (catParam) {
    await loadSubcategories(catParam, subcatParam);
  }

  // 3. Initial catalogue load
  await applyFilters(currentPage);

  // Setup click outside to close suggestions dropdown
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('searchSuggestionsDropdown');
    const searchContainer = document.getElementById('aiNlSearchInput');
    if (dropdown && !dropdown.contains(e.target) && e.target !== searchContainer) {
      dropdown.style.display = 'none';
    }
  });
}

// =========================================================================
// SECTION 2: EXPLORE CATEGORIES
// =========================================================================

async function loadCategoriesSummary() {
  const container = document.getElementById('categoryBrowseStrip');
  if (!container) return;

  try {
    const res = await fetch('/api/discovery/categories');
    const data = await res.json();
    if (data.categories) {
      allCategoriesSummary = data.categories;
      renderCategoriesStrip();
    }
  } catch (err) {
    console.warn('Failed to fetch categories summary:', err);
  }
}

function renderCategoriesStrip() {
  const container = document.getElementById('categoryBrowseStrip');
  if (!container || !allCategoriesSummary.length) return;

  const currentCat = document.getElementById('categorySelect')?.value || '';

  container.innerHTML = allCategoriesSummary.map(cat => {
    const isActive = (cat.name.toLowerCase() === currentCat.toLowerCase());
    const activeStyle = isActive ? 'background: #E9DDFB; border-color: #C4A6F5; font-weight: 700;' : '';
    return `
      <div 
        class="cat-browse-card ${isActive ? 'active' : ''}" 
        style="${activeStyle}"
        onclick="selectCategoryFromBrowse('${cat.name.replace(/'/g, "\\'")}')"
        title="${cat.name} (${cat.product_count} products, ${cat.subcategory_count} subcategories)"
      >
        <div style="font-size: 1.4rem; margin-bottom: 4px;">${cat.icon || '🛍️'}</div>
        <div style="font-size: 0.8rem; color: #403653; line-height: 1.2; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
          ${cat.name}
        </div>
        <div style="font-size: 0.72rem; color: #81778E; margin-top: 2px;">
          ${cat.product_count} items
        </div>
      </div>
    `;
  }).join('');
}

function toggleCategoriesExpansion() {
  const strip = document.getElementById('categoryBrowseStrip');
  const btn = document.getElementById('toggleCategoriesViewBtn');
  if (!strip || !btn) return;

  isCategoriesExpanded = !isCategoriesExpanded;
  if (isCategoriesExpanded) {
    strip.style.maxHeight = '800px';
    btn.innerHTML = 'Collapse Categories ▲';
  } else {
    strip.style.maxHeight = '140px';
    btn.innerHTML = 'View All Categories ▼';
  }
}

async function selectCategoryFromBrowse(catName) {
  const select = document.getElementById('categorySelect');
  if (select) {
    select.value = (select.value === catName) ? '' : catName;
    await onCategoryChange();
  }
}

async function onCategoryChange() {
  const cat = document.getElementById('categorySelect')?.value || '';
  await loadSubcategories(cat);
  selectedBrands.clear();
  renderCategoriesStrip();
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
    const res = await fetch(`/api/subcategories?category=${encodeURIComponent(category)}`);
    const data = await res.json();
    const subcats = data.subcategories || [];
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

// =========================================================================
// SECTION 1 & 4: SEARCH PRODUCTS, AUTOCOMPLETE & TYPOS
// =========================================================================

function handleSearchFocus() {
  const input = document.getElementById('aiNlSearchInput');
  const val = (input?.value || '').trim();
  fetchSearchSuggestions(val);
}

function handleSearchInput(val) {
  const clearBtn = document.getElementById('searchClearBtn');
  if (clearBtn) clearBtn.style.display = val.length > 0 ? 'block' : 'none';

  // Sync alias input
  const fkInput = document.getElementById('fkSearchInput');
  if (fkInput) fkInput.value = val;

  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    fetchSearchSuggestions(val);
  }, 220);
}

function clearSearchInput() {
  const input = document.getElementById('aiNlSearchInput');
  const fkInput = document.getElementById('fkSearchInput');
  if (input) input.value = '';
  if (fkInput) fkInput.value = '';

  const clearBtn = document.getElementById('searchClearBtn');
  if (clearBtn) clearBtn.style.display = 'none';

  const dropdown = document.getElementById('searchSuggestionsDropdown');
  if (dropdown) dropdown.style.display = 'none';

  const didYouMean = document.getElementById('didYouMeanNotice');
  if (didYouMean) didYouMean.style.display = 'none';

  const feedback = document.getElementById('nlSearchFeedback');
  if (feedback) feedback.style.display = 'none';

  applyFilters(1);
}

async function fetchSearchSuggestions(query) {
  const dropdown = document.getElementById('searchSuggestionsDropdown');
  const content = document.getElementById('suggestionsContent');
  const didYouMeanBox = document.getElementById('didYouMeanNotice');
  const didYouMeanQuery = document.getElementById('didYouMeanQuery');
  if (!dropdown || !content) return;

  try {
    const res = await fetch(`/api/discovery/suggestions?q=${encodeURIComponent(query)}&limit=8`);
    const data = await res.json();
    const suggestions = data.suggestions || [];

    // Handle "Did You Mean?"
    if (data.did_you_mean && data.did_you_mean.toLowerCase() !== query.toLowerCase()) {
      currentDidYouMean = data.did_you_mean;
      if (didYouMeanBox && didYouMeanQuery) {
        didYouMeanQuery.textContent = data.did_you_mean;
        didYouMeanBox.style.display = 'block';
      }
    } else {
      currentDidYouMean = null;
      if (didYouMeanBox) didYouMeanBox.style.display = 'none';
    }

    if (!suggestions.length) {
      dropdown.style.display = 'none';
      return;
    }

    content.innerHTML = suggestions.map(s => {
      let icon = '🔍';
      let badge = '';
      if (s.type === 'category') {
        icon = '📂';
        badge = '<span style="font-size:0.7rem; background:#E9DDFB; color:#403653; padding:2px 6px; border-radius:4px; margin-left:6px;">Category</span>';
      } else if (s.type === 'brand') {
        icon = '🏷️';
        badge = '<span style="font-size:0.7rem; background:#F7F3FF; color:#81778E; padding:2px 6px; border-radius:4px; margin-left:6px;">Brand</span>';
      } else if (s.type === 'popular') {
        icon = '🔥';
        badge = '<span style="font-size:0.7rem; background:#FFFDF9; color:#D6B875; border:1px solid #D6B875; padding:1px 6px; border-radius:4px; margin-left:6px;">Popular</span>';
      }

      return `
        <div class="suggestion-row" onclick="applySuggestion('${encodeURIComponent(JSON.stringify(s))}')">
          <div style="display:flex; align-items:center; gap:8px;">
            <span>${icon}</span>
            <span>${s.text}</span>
            ${badge}
          </div>
          <span style="color:#C4A6F5; font-size:0.78rem;">Explore &rarr;</span>
        </div>
      `;
    }).join('');

    dropdown.style.display = 'block';
  } catch (err) {
    console.warn('Suggestions failed:', err);
    dropdown.style.display = 'none';
  }
}

function applySuggestion(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  const dropdown = document.getElementById('searchSuggestionsDropdown');
  if (dropdown) dropdown.style.display = 'none';

  const input = document.getElementById('aiNlSearchInput');
  const fkInput = document.getElementById('fkSearchInput');

  if (item.type === 'category' && item.category) {
    const catSelect = document.getElementById('categorySelect');
    if (catSelect) catSelect.value = item.category;
    if (input) input.value = '';
    if (fkInput) fkInput.value = '';
    onCategoryChange();
  } else if (item.type === 'brand' && item.brand) {
    selectedBrands.clear();
    selectedBrands.add(item.brand);
    if (input) input.value = item.brand;
    if (fkInput) fkInput.value = item.brand;
    applyFilters(1);
  } else {
    const q = item.query || item.text;
    if (input) input.value = q;
    if (fkInput) fkInput.value = q;
    executeSmartSearch();
  }
}

function applyDidYouMean() {
  if (!currentDidYouMean) return;
  const input = document.getElementById('aiNlSearchInput');
  const fkInput = document.getElementById('fkSearchInput');
  if (input) input.value = currentDidYouMean;
  if (fkInput) fkInput.value = currentDidYouMean;

  const didYouMeanBox = document.getElementById('didYouMeanNotice');
  if (didYouMeanBox) didYouMeanBox.style.display = 'none';

  executeSmartSearch();
}

async function executeSmartSearch() {
  const dropdown = document.getElementById('searchSuggestionsDropdown');
  if (dropdown) dropdown.style.display = 'none';

  const input = document.getElementById('aiNlSearchInput');
  const query = (input?.value || '').trim();
  const feedback = document.getElementById('nlSearchFeedback');

  if (!query) {
    if (feedback) feedback.style.display = 'none';
    return applyFilters(1);
  }

  // Check if natural-language tokens present
  const isConversational = /(?:under|below|less than|above|<|>|between|for|budget of|best|cheap|\d+)/i.test(query);

  if (isConversational) {
    if (feedback) {
      feedback.style.display = 'block';
      feedback.innerHTML = '<em>⚡ Parsing natural-language shopping intent across catalogue...</em>';
    }

    try {
      const res = await fetch('/api/discovery/nl-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      const intent = data.parsed_intent || {};
      if (feedback) {
        feedback.innerHTML = `
          <strong>AI Intent Parsed:</strong>
          ${intent.category ? `Category: <strong>${intent.category}</strong> • ` : ''}
          ${intent.brand ? `Brand: <strong>${intent.brand}</strong> • ` : ''}
          ${intent.max_price ? `Budget Cap: <strong>₹${intent.max_price.toLocaleString('en-IN')}</strong> • ` : ''}
          Keywords: <em>${(intent.extracted_keywords || []).join(', ') || 'relevance'}</em>
          <span style="color:#7B4EB5; margin-left:8px;">(${data.total_matches} high-confidence matches)</span>
        `;
      }

      // If category or max_price were parsed, sync sidebar filters
      if (intent.category) {
        const catSelect = document.getElementById('categorySelect');
        if (catSelect) catSelect.value = intent.category;
      }
      if (intent.max_price) {
        const maxInput = document.getElementById('maxPriceInput');
        if (maxInput) maxInput.value = intent.max_price;
      }

      currentFiltered = data.products || [];
      totalCount = data.total_matches || currentFiltered.length;
      totalPages = 1;
      currentPage = 1;

      renderGrid();
      renderBreadcrumb(intent.category || query);

      const titleEl = document.getElementById('resultsTitle');
      const countEl = document.getElementById('resultsCount');
      if (titleEl) titleEl.textContent = `Smart Results for "${query}"`;
      if (countEl) countEl.textContent = `(${totalCount} products found)`;

      return;
    } catch (err) {
      console.warn('NL Search error, falling back to standard search:', err);
    }
  }

  // Standard keyword search
  if (feedback) feedback.style.display = 'none';
  await applyFilters(1);
}

// =========================================================================
// SECTION 5: DISCOVER PRODUCTS (CURATED COLLECTIONS)
// =========================================================================

async function loadCuratedCollection(type, btnEl) {
  // Update collection pill styles
  document.querySelectorAll('.collection-pill').forEach(b => {
    b.classList.remove('active');
    b.style.background = '#FFFDF9';
    b.style.color = '#81778E';
    b.style.borderColor = '#EAE1F4';
  });
  if (btnEl) {
    btnEl.classList.add('active');
    btnEl.style.background = '#E9DDFB';
    btnEl.style.color = '#403653';
    btnEl.style.borderColor = '#C4A6F5';
  }

  const grid = document.getElementById('productsGrid');
  const titleEl = document.getElementById('resultsTitle');
  const countEl = document.getElementById('resultsCount');

  if (grid) {
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:36px; color:#81778E;">Loading curated collection...</div>';
  }

  try {
    const res = await fetch(`/api/discovery/collections?type=${encodeURIComponent(type)}&limit=24`);
    const data = await res.json();
    currentFiltered = data.products || [];
    totalCount = data.total || currentFiltered.length;
    totalPages = 1;
    currentPage = 1;

    if (titleEl) titleEl.textContent = data.title || 'Curated Collection';
    if (countEl) countEl.textContent = `(${totalCount} products)`;

    renderGrid();
    renderBreadcrumb(data.title);

    const pag = document.getElementById('paginationContainer');
    if (pag) pag.style.display = 'none';
  } catch (err) {
    console.error('Failed to load collection:', err);
  }
}

// =========================================================================
// SECTION 3: FILTER AND SORT PRODUCTS
// =========================================================================

function setPriceRange(min, max) {
  const minEl = document.getElementById('minPriceInput');
  const maxEl = document.getElementById('maxPriceInput');
  if (minEl) minEl.value = min;
  if (maxEl) maxEl.value = max >= 150000 ? '' : max;
  applyFilters(1);
}

function updateSortTabsUI() {
  document.querySelectorAll('.fk-sort-tab').forEach((t) => {
    t.style.color = '#403653';
    t.style.borderBottom = 'none';
    t.style.fontWeight = 'normal';
    t.classList.remove('active');
  });
  const activeTab = document.querySelector(`.fk-sort-tab[onclick*="'${currentSort}'"]`);
  if (activeTab) {
    activeTab.style.color = '#6B34A6';
    activeTab.style.borderBottom = '2px solid #C4A6F5';
    activeTab.style.fontWeight = '700';
    activeTab.classList.add('active');
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

  const searchInput = document.getElementById('aiNlSearchInput');
  const search = (searchInput?.value || '').trim();

  const category = document.getElementById('categorySelect')?.value || '';
  const subcategory = document.getElementById('subcategorySelect')?.value || '';
  const minPrice = parseFloat(document.getElementById('minPriceInput')?.value);
  const maxPrice = parseFloat(document.getElementById('maxPriceInput')?.value);
  const rating4 = document.getElementById('rating4Check')?.checked;
  const rating3 = document.getElementById('rating3Check')?.checked;
  const inStockOnly = document.getElementById('inStockCheck')?.checked;

  const discountRadio = document.querySelector('input[name="discountFilter"]:checked');
  const minDiscount = parseInt(discountRadio ? discountRadio.value : '0') || 0;

  // Build query parameters
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

  // Update browser URL silently
  const newUrl = `/discovery?${query.toString()}`;
  window.history.replaceState({}, '', newUrl);

  try {
    if (grid) {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:48px; color:#81778E;"><p>Loading PreTwin catalogue...</p></div>';
    }

    const res = await fetch(`/api/products?${query.toString()}`);
    const data = await res.json();
    let products = data.products || [];
    totalCount = data.total || products.length;
    totalPages = data.pages || Math.ceil(totalCount / 24) || 1;

    // Client-side discount & in-stock filters if required
    if (minDiscount > 0) {
      products = products.filter(p => (p.discount_percentage || 15) >= minDiscount);
    }
    if (inStockOnly) {
      products = products.filter(p => (p.stock === undefined || p.stock > 0));
    }

    allDiscoveryProducts = products;
    currentFiltered = products;

    // Update brands in sidebar
    if (data.brands && data.brands.length) {
      availableBrands = data.brands;
      renderBrandFilters(data.brands);
    }

    // Update title, counts & breadcrumb
    if (titleEl) {
      if (search) titleEl.textContent = `Results for "${search}"`;
      else if (subcategory) titleEl.textContent = `${subcategory} (${category || 'Catalogue'})`;
      else if (category) titleEl.textContent = `${category}`;
      else titleEl.textContent = 'All Products Catalogue';
    }

    if (countEl) {
      countEl.textContent = `(Showing ${products.length} of ${totalCount} products — Page ${currentPage} of ${totalPages})`;
    }

    renderBreadcrumb(category || search);
    renderAppliedTags(category, subcategory, search, minPrice, maxPrice, selectedBrands);
    renderGrid();
    renderPagination();
  } catch (err) {
    console.error('Failed to discover products:', err);
    if (grid) {
      grid.innerHTML = '<p style="grid-column: 1/-1; text-align:center; padding:32px; color:#d32f2f;">Failed to load products. Please check connection.</p>';
    }
  }
}

function renderBrandFilters(brands) {
  const brandList = document.getElementById('brandList');
  const countLabel = document.getElementById('brandCountLabel');
  if (!brandList) return;

  if (countLabel) countLabel.textContent = `(${brands.length})`;

  const topBrands = brands.slice(0, 20);
  brandList.innerHTML = topBrands.map(b => {
    const isChecked = selectedBrands.has(b) ? 'checked' : '';
    const safeBrand = b.replace(/"/g, '&quot;');
    return `
      <label style="display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: #403653; cursor: pointer;">
        <input type="checkbox" value="${safeBrand}" ${isChecked} onchange="toggleBrand('${safeBrand}')" style="accent-color: #C4A6F5;">
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

function renderBreadcrumb(activeName) {
  const sep = document.getElementById('breadcrumbSeparator');
  const cur = document.getElementById('breadcrumbCurrent');
  if (!sep || !cur) return;

  if (activeName) {
    sep.style.display = 'inline';
    cur.style.display = 'inline';
    cur.textContent = activeName;
  } else {
    sep.style.display = 'none';
    cur.style.display = 'none';
  }
}

function renderAppliedTags(category, subcategory, search, minP, maxP, brands) {
  const container = document.getElementById('appliedFilterTags');
  if (!container) return;

  let tags = [];
  if (category) {
    tags.push(`<span class="fk-filter-tag">Category: ${category} <b onclick="removeFilter('category')">&times;</b></span>`);
  }
  if (subcategory) {
    tags.push(`<span class="fk-filter-tag">Subcategory: ${subcategory} <b onclick="removeFilter('subcategory')">&times;</b></span>`);
  }
  if (search) {
    tags.push(`<span class="fk-filter-tag">"${search}" <b onclick="removeFilter('search')">&times;</b></span>`);
  }
  if (!isNaN(minP) || !isNaN(maxP)) {
    const label = `Price: ₹${minP || 0} - ₹${maxP || 'Above'}`;
    tags.push(`<span class="fk-filter-tag">${label} <b onclick="removeFilter('price')">&times;</b></span>`);
  }
  brands.forEach(b => {
    tags.push(`<span class="fk-filter-tag">Brand: ${b} <b onclick="toggleBrand('${b}')">&times;</b></span>`);
  });

  if (tags.length > 0) {
    tags.push(`<span style="color:#7B4EB5; font-size:0.78rem; font-weight:700; cursor:pointer; align-self:center; margin-left:4px;" onclick="clearFilters()">Clear All</span>`);
  }

  container.innerHTML = tags.join('');
}

function removeFilter(type) {
  if (type === 'category') {
    const cat = document.getElementById('categorySelect');
    if (cat) cat.value = '';
    const subcat = document.getElementById('subcategorySelect');
    if (subcat) subcat.innerHTML = '<option value="">All Subcategories</option>';
    renderCategoriesStrip();
  } else if (type === 'subcategory') {
    const subcat = document.getElementById('subcategorySelect');
    if (subcat) subcat.value = '';
  } else if (type === 'search') {
    const s = document.getElementById('aiNlSearchInput');
    if (s) s.value = '';
    const fk = document.getElementById('fkSearchInput');
    if (fk) fk.value = '';
    const clearBtn = document.getElementById('searchClearBtn');
    if (clearBtn) clearBtn.style.display = 'none';
  } else if (type === 'price') {
    const minP = document.getElementById('minPriceInput');
    const maxP = document.getElementById('maxPriceInput');
    if (minP) minP.value = '';
    if (maxP) maxP.value = '';
  }
  applyFilters(1);
}

function clearFilters() {
  const cat = document.getElementById('categorySelect');
  const subcat = document.getElementById('subcategorySelect');
  const minP = document.getElementById('minPriceInput');
  const maxP = document.getElementById('maxPriceInput');
  const r4 = document.getElementById('rating4Check');
  const r3 = document.getElementById('rating3Check');
  const inStock = document.getElementById('inStockCheck');
  const searchInput = document.getElementById('aiNlSearchInput');
  const fkInput = document.getElementById('fkSearchInput');
  const allDiscount = document.querySelector('input[name="discountFilter"][value="0"]');

  if (cat) cat.value = '';
  if (subcat) subcat.innerHTML = '<option value="">All Subcategories</option>';
  if (minP) minP.value = '';
  if (maxP) maxP.value = '';
  if (r4) r4.checked = false;
  if (r3) r3.checked = false;
  if (inStock) inStock.checked = false;
  if (searchInput) searchInput.value = '';
  if (fkInput) fkInput.value = '';
  if (allDiscount) allDiscount.checked = true;
  selectedBrands.clear();

  const clearBtn = document.getElementById('searchClearBtn');
  if (clearBtn) clearBtn.style.display = 'none';

  const feedback = document.getElementById('nlSearchFeedback');
  if (feedback) feedback.style.display = 'none';

  renderCategoriesStrip();
  window.history.pushState({}, '', '/discovery');
  applyFilters(1);
}

function clearAllSearchAndFilters() {
  clearFilters();
}

// =========================================================================
// SECTION 7: PRODUCT DETAILS & SHOPPING ACTIONS
// =========================================================================

function renderGrid() {
  const grid = document.getElementById('productsGrid');
  if (!grid) return;

  if (currentFiltered.length === 0) {
    // Intelligent zero-result fallback (Section 4)
    renderZeroResultsView(grid);
    return;
  }

  grid.innerHTML = currentFiltered.map(p => {
    window.catalogMap = window.catalogMap || {};
    window.catalogMap[p.id] = p;

    const originalMrp = p.mrp || Math.round(p.price * 1.35);
    const discPct = p.discount_percentage || Math.round(((originalMrp - p.price) / originalMrp) * 100);
    const fallbackImg = (typeof getCategoryFallbackImg === 'function') 
      ? getCategoryFallbackImg(p.category) 
      : 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200&q=80';
    const displayImg = p.image_url || fallbackImg;
    const rating = parseFloat(p.rating || 4.2).toFixed(1);
    const stockCount = p.stock !== undefined ? p.stock : 18;
    const stockBadge = stockCount < 5 
      ? `<span style="color:#d97706; font-size:0.72rem; font-weight:700;">Only ${stockCount} left!</span>`
      : `<span style="color:#10b981; font-size:0.72rem; font-weight:600;">In Stock</span>`;

    return `
      <div class="fk-product-card-v3" onclick="openProductModal(${p.id})">
        <!-- Wishlist Heart Button -->
        <button 
          class="fk-card-wish" 
          data-product-id="${p.id}" 
          onclick="event.stopPropagation(); toggleWishlistById(${p.id});" 
          title="Add to Wishlist"
          style="position: absolute; right: 10px; top: 10px; background: #FFFDF9; border: 1px solid #EAE1F4; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #81778E; font-size: 1rem; z-index: 2; transition: all 0.2s ease;"
        >
          ♥
        </button>

        <!-- Product Image -->
        <div style="height: 160px; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; overflow: hidden; border-radius: 8px; background: #fafafa;">
          <img src="${displayImg}" alt="${p.name}" loading="lazy" onerror="this.onerror=null;this.src='${fallbackImg}'" style="max-height: 100%; max-width: 100%; object-fit: contain;">
        </div>

        <!-- PreTwin Assured / Match Reason -->
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
          <span style="font-size: 0.72rem; font-weight: 700; color: #6B34A6;">✓ PreTwin Assured</span>
          ${stockBadge}
        </div>

        <!-- Product Title -->
        <h3 style="font-size: 0.88rem; font-weight: 600; color: #403653; margin: 0 0 6px 0; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;" title="${p.name}">
          ${p.name}
        </h3>

        <!-- Brand & Subcategory -->
        <div style="font-size: 0.75rem; color: #81778E; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          ${p.brand ? `<strong>${p.brand}</strong> • ` : ''}${p.subcategory || p.category}
        </div>

        <!-- Rating & Reviews -->
        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
          <span style="background: #10b981; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-size: 0.74rem; font-weight: 700;">
            ${rating} ★
          </span>
          <span style="font-size: 0.74rem; color: #81778E;">
            (${p.review_count_demo || 120})
          </span>
        </div>

        <!-- Price, MRP & Discount Row -->
        <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 12px; flex-wrap: wrap;">
          <span style="font-size: 1.05rem; font-weight: 800; color: #403653;">
            ₹${Math.round(p.price).toLocaleString('en-IN')}
          </span>
          <span style="font-size: 0.78rem; color: #81778E; text-decoration: line-through;">
            ₹${Math.round(originalMrp).toLocaleString('en-IN')}
          </span>
          <span style="font-size: 0.78rem; font-weight: 700; color: #10b981;">
            ${discPct}% off
          </span>
        </div>

        <!-- Actions Row: Add to Cart & View Alternatives -->
        <div style="display: flex; gap: 6px;" onclick="event.stopPropagation()">
          <button 
            onclick="addToCartById(${p.id})" 
            style="flex: 1; background: linear-gradient(135deg, #C4A6F5 0%, #A78BFA 100%); color: #ffffff; border: none; padding: 8px 10px; border-radius: 8px; font-size: 0.78rem; font-weight: 700; cursor: pointer; transition: opacity 0.2s ease; display: flex; align-items: center; justify-content: center; gap: 4px;"
            title="Add to Shopping Cart"
          >
            <span>🛒</span> Add to Cart
          </button>
          <button 
            onclick="openAlternativesModal(${p.id})" 
            style="background: #E9DDFB; color: #403653; border: 1px solid #C4A6F5; padding: 8px 10px; border-radius: 8px; font-size: 0.78rem; font-weight: 700; cursor: pointer; transition: all 0.2s ease;"
            title="View Similar &amp; Budget Alternatives"
          >
            🔄
          </button>
        </div>
      </div>
    `;
  }).join('');

  if (typeof updateWishlistIcons === 'function') {
    updateWishlistIcons();
  }
}

async function renderZeroResultsView(grid) {
  const searchInput = document.getElementById('aiNlSearchInput');
  const q = (searchInput?.value || '').trim();

  let fallbackHtml = `
    <div style="grid-column: 1/-1; text-align: center; padding: 40px 20px; background: #FFFDF9; border: 1.5px dashed #EAE1F4; border-radius: 16px;">
      <div style="font-size: 2.4rem; margin-bottom: 10px;">🔍</div>
      <h3 style="font-size: 1.15rem; color: #403653; font-weight: 700; margin: 0 0 6px 0;">No matching products found</h3>
      <p style="font-size: 0.85rem; color: #81778E; max-width: 460px; margin: 0 auto 16px auto;">
        We couldn't find any catalogue items matching your exact filters. Try broadening your price range, clearing brand selections, or exploring popular categories below.
      </p>
      <button onclick="clearFilters()" style="background: #C4A6F5; color: #ffffff; border: none; padding: 9px 20px; border-radius: 8px; font-weight: 700; font-size: 0.85rem; cursor: pointer; margin-bottom: 24px;">
        Clear All Filters
      </button>
      <div id="zeroResultRecommendations" style="margin-top: 16px;"></div>
    </div>
  `;
  grid.innerHTML = fallbackHtml;

  try {
    const res = await fetch(`/api/discovery/zero-results?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const target = document.getElementById('zeroResultRecommendations');
    if (!target) return;

    let recHtml = '<div style="font-size:0.85rem; font-weight:700; color:#403653; margin-bottom:10px;">Suggested Categories to Explore:</div>';
    recHtml += '<div style="display:flex; flex-wrap:wrap; gap:8px; justify-content:center;">';
    (data.popular_categories || []).forEach(cat => {
      recHtml += `
        <span 
          onclick="selectCategoryFromBrowse('${cat}')" 
          style="background:#E9DDFB; color:#403653; border:1px solid #C4A6F5; padding:6px 12px; border-radius:16px; font-size:0.8rem; font-weight:600; cursor:pointer;"
        >
          ${cat}
        </span>
      `;
    });
    recHtml += '</div>';
    target.innerHTML = recHtml;
  } catch (e) {
    // Graceful silent fallback
  }
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
  if (currentPage > 1) {
    html += `<button class="fk-page-btn" onclick="applyFilters(${currentPage - 1})">PREVIOUS</button>`;
  }

  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, start + 4);

  for (let i = start; i <= end; i++) {
    const activeClass = (i === currentPage) ? 'active' : '';
    html += `<button class="fk-page-btn ${activeClass}" onclick="applyFilters(${i})">${i}</button>`;
  }

  if (currentPage < totalPages) {
    html += `<button class="fk-page-btn" onclick="applyFilters(${currentPage + 1})">NEXT</button>`;
  }

  btns.innerHTML = html;
}

// =========================================================================
// SECTION 6: RELATED PRODUCTS & ALTERNATIVES
// =========================================================================

async function openAlternativesModal(productId) {
  const modal = document.getElementById('alternativesModal');
  const sourceCard = document.getElementById('altSourceProductCard');
  const altList = document.getElementById('alternativesList');

  if (!modal || !sourceCard || !altList) return;

  sourceCard.innerHTML = '<div style="color:#81778E; font-size:0.85rem;">Analyzing catalogue alternatives...</div>';
  altList.innerHTML = '<div style="color:#81778E; font-size:0.85rem; text-align:center; padding:20px;">Fetching comparison items...</div>';
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/discovery/products/${productId}/alternatives?limit=4`);
    const data = await res.json();
    const source = data.source_product;
    const alternatives = data.alternatives || [];

    if (source) {
      sourceCard.innerHTML = `
        <img src="${source.image_url || '/static/images/pretwin-icon.svg'}" alt="${source.name}" style="width:60px; height:60px; object-fit:contain; border-radius:8px; background:#fff; padding:4px;">
        <div style="flex:1;">
          <div style="font-size:0.75rem; color:#81778E;">COMPARING FOR:</div>
          <strong style="font-size:0.92rem; color:#403653;">${source.name}</strong>
          <div style="font-size:0.85rem; color:#403653; margin-top:2px;">
            ₹${Math.round(source.price).toLocaleString('en-IN')} • ${source.rating} ★ • ${source.category}
          </div>
        </div>
      `;
    }

    if (!alternatives.length) {
      altList.innerHTML = '<p style="color:#81778E; font-size:0.85rem; text-align:center; padding:16px;">No closer alternatives found in this exact category bracket.</p>';
      return;
    }

    altList.innerHTML = alternatives.map(alt => {
      let badgeColor = '#6B34A6';
      let badgeBg = '#E9DDFB';
      if (alt.alternative_type === 'budget') {
        badgeColor = '#059669';
        badgeBg = '#D1FAE5';
      } else if (alt.alternative_type === 'premium') {
        badgeColor = '#B45309';
        badgeBg = '#FEF3C7';
      }

      return `
        <div style="background:#ffffff; border:1px solid #EAE1F4; border-radius:12px; padding:14px; display:flex; gap:14px; align-items:center; justify-content:space-between; flex-wrap:wrap;">
          <div style="display:flex; gap:12px; align-items:center; flex:1; min-width:240px;">
            <img src="${alt.image_url || '/static/images/pretwin-icon.svg'}" alt="${alt.name}" style="width:54px; height:54px; object-fit:contain; border-radius:6px; background:#fafafa;">
            <div>
              <span style="background:${badgeBg}; color:${badgeColor}; font-size:0.7rem; font-weight:700; padding:2px 8px; border-radius:10px;">
                ${alt.alternative_badge || 'Alternative'}
              </span>
              <h5 style="font-size:0.88rem; font-weight:600; color:#403653; margin:4px 0 2px 0;">${alt.name}</h5>
              <div style="font-size:0.78rem; color:#81778E;">
                ${alt.explanation || 'Comparable specs and customer rating'}
              </div>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:12px;">
            <div style="text-align:right;">
              <strong style="font-size:1rem; color:#403653;">₹${Math.round(alt.price).toLocaleString('en-IN')}</strong>
              <div style="font-size:0.74rem; color:#10b981; font-weight:600;">${alt.rating} ★ Rating</div>
            </div>
            <button onclick="addToCartById(${alt.id})" style="background:#C4A6F5; color:#ffffff; border:none; padding:7px 14px; border-radius:8px; font-size:0.78rem; font-weight:700; cursor:pointer;">
              Add to Cart
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    altList.innerHTML = '<p style="color:#d32f2f; font-size:0.85rem; text-align:center;">Failed to fetch alternatives.</p>';
  }
}

function closeAlternativesModal() {
  const modal = document.getElementById('alternativesModal');
  if (modal) modal.style.display = 'none';
}

// Close alternatives modal on background click
document.addEventListener('click', (e) => {
  const modal = document.getElementById('alternativesModal');
  if (modal && e.target === modal) {
    modal.style.display = 'none';
  }
});

// =========================================================================
// VISUAL SEARCH INTEGRATION
// =========================================================================

async function triggerVisualSearchModal() {
  const cat = prompt("Select style hint for visual product search (e.g. Shoes, Watch, Headphone, Dress, Laptop):", "Shoes");
  if (!cat) return;

  const grid = document.getElementById('productsGrid');
  const title = document.getElementById('resultsTitle');
  if (grid) {
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:36px; color:#81778E;">Analyzing visual patterns &amp; finding matches...</div>';
  }

  try {
    const res = await fetch('/api/discovery/visual-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category_hint: cat, style_tag: 'Casual' })
    });
    const data = await res.json();
    if (data.products) {
      currentFiltered = data.products;
      totalCount = data.products.length;
      totalPages = 1;
      currentPage = 1;

      renderGrid();
      if (title) title.innerText = `Visual Matches for "${cat}" (${Math.round(data.confidence * 100)}% Confidence)`;
    }
  } catch (e) {
    alert('Visual search failed: ' + e.message);
  }
}

// Product detail modal integration
function openProductModal(productId) {
  if (typeof openProductDetail === 'function') {
    openProductDetail(productId);
  } else {
    window.location.href = `/product/${productId}`;
  }
}

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initDiscovery();
});
