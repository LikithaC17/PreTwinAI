/**
 * PreTwin AI - For You & Smart Recommendations Controller
 * Displays complete product catalog + AI Spotlight recommendations
 */

let forYouCurrentPage = 1;
const forYouPageLimit = 24;
let forYouTotalPages = 1;
let forYouActiveCategory = 'all';
let forYouSearchTerm = '';
let forYouActiveSort = 'featured';
let forYouSearchTimer = null;

// Registry map of products for instant cart & wishlist actions
if (!window.catalogMap) window.catalogMap = {};

// Fallback images map for categories
const CATEGORY_IMAGE_FALLBACKS = {
  Fashion: '/static/images/fashion-tshirt.svg',
  Mobiles: '/static/images/mobile-phone.svg',
  Electronics: '/static/images/electronics-headphones.svg',
  'Home & Kitchen': '/static/images/home-decor.svg',
  Appliances: '/static/images/appliances-microwave.svg',
  Groceries: '/static/images/grocery-basket.svg',
  'Books & Media': '/static/images/book-cover.svg'
};

function getSafeProductImage(product) {
  if (product.image_url && product.image_url.trim()) return product.image_url;
  return CATEGORY_IMAGE_FALLBACKS[product.category] || '/static/images/placeholder.svg';
}

/**
 * Initialize For You page on load
 */
document.addEventListener('DOMContentLoaded', () => {
  loadForYouSpotlight();
  loadForYouProducts();
});

/**
 * 1. Load AI Spotlight Recommendations (Agent F Top Picks)
 */
async function loadForYouSpotlight() {
  const spotlightContainer = document.getElementById('spotlightRow');
  const budgetNote = document.getElementById('spotlightBudgetNote');

  try {
    const [recRes, profRes] = await Promise.all([
      fetch('/api/recommendations').then(r => r.json()).catch(() => ({})),
      fetch('/api/profile').then(r => r.json()).catch(() => ({}))
    ]);

    const recs = recRes.recommendations || [];
    const budgetMax = (profRes.preferences && profRes.preferences.budget_max) || 5000;

    if (budgetNote) {
      budgetNote.textContent = `Within your ₹${budgetMax.toLocaleString('en-IN')} budget bounds`;
    }

    if (!spotlightContainer) return;

    if (!recs || recs.length === 0) {
      spotlightContainer.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding: 20px; color: #64748b; font-size: 13.5px;">
          ✨ Exploring your Twin taste profile. Browse all available catalog products below!
        </div>
      `;
      return;
    }

    // Register recs in window.catalogMap
    recs.forEach(p => { window.catalogMap[p.id] = p; });

    spotlightContainer.innerHTML = recs.slice(0, 4).map(p => `
      <div class="card" style="border: 1px solid #e0e7ff; border-radius: 10px; padding: 14px; background: #ffffff; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s;">
        <div>
          <div style="position: relative; height: 140px; background: #f8fafc; border-radius: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden; margin-bottom: 10px;">
            <img src="${getSafeProductImage(p)}" alt="${p.title}" style="max-height: 120px; max-width: 90%; object-fit: contain;">
            <span style="position: absolute; top: 6px; left: 6px; background: #7c3aed; color: #ffffff; font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">
              ✦ Top Pick
            </span>
            <button type="button" onclick="handleWishlistClick(${p.id}, event)" style="position: absolute; top: 6px; right: 6px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #ef4444;" title="Add to Wishlist">
              ♥
            </button>
          </div>
          <div style="font-size: 11px; font-weight: 700; color: #7c3aed; text-transform: uppercase;">${p.category}</div>
          <h4 style="font-size: 13.5px; font-weight: 700; color: #1e293b; margin: 4px 0 6px; line-height: 1.3; height: 36px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
            ${p.title}
          </h4>
          <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 8px;">
            <span style="font-size: 16px; font-weight: 800; color: #0f172a;">₹${Math.round(p.price).toLocaleString('en-IN')}</span>
            <span style="font-size: 11.5px; color: #94a3b8; text-decoration: line-through;">₹${Math.round(p.price * 1.25).toLocaleString('en-IN')}</span>
          </div>
        </div>
        <button class="btn btn-primary" onclick="handleAddToCartClick(${p.id}, event)" style="width: 100%; padding: 7px; font-size: 12.5px; font-weight: 700;">
          + Add to Cart
        </button>
      </div>
    `).join('');

  } catch (err) {
    console.warn('Spotlight fetch error:', err);
    if (spotlightContainer) {
      spotlightContainer.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding: 16px; color: #64748b; font-size: 13px;">
          Personalized picks loaded. Browse the complete catalog below.
        </div>
      `;
    }
  }
}

/**
 * 2. Load Full Catalog Products with Pagination, Filters, and Search
 */
async function loadForYouProducts() {
  const grid = document.getElementById('forYouProductGrid');
  const countEl = document.getElementById('forYouProductCount');
  const pageInfo = document.getElementById('forYouPageInfo');
  const currPageEl = document.getElementById('currentPageNum');
  const totalPagesEl = document.getElementById('totalPagesNum');
  const prevBtn = document.getElementById('btnPrevPage');
  const nextBtn = document.getElementById('btnNextPage');
  const totalCatalogStat = document.getElementById('statTotalCatalog');

  if (grid) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: #64748b;">
        <div class="spinner"></div>
        <p style="margin-top: 12px; font-size: 14px;">Loading catalog products...</p>
      </div>
    `;
  }

  try {
    const params = new URLSearchParams({
      page: forYouCurrentPage,
      limit: forYouPageLimit
    });

    if (forYouActiveCategory && forYouActiveCategory !== 'all') {
      params.append('category', forYouActiveCategory);
    }
    if (forYouSearchTerm && forYouSearchTerm.trim()) {
      params.append('search', forYouSearchTerm.trim());
    }
    if (forYouActiveSort) {
      params.append('sort', forYouActiveSort);
    }

    const res = await fetch(`/api/products?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const products = data.products || [];
    const total = data.total || 0;
    forYouTotalPages = data.pages || Math.ceil(total / forYouPageLimit) || 1;

    // Register all fetched products into window.catalogMap
    products.forEach(p => { window.catalogMap[p.id] = p; });

    // Update counters and pagination indicators
    if (countEl) countEl.textContent = total.toLocaleString('en-IN');
    if (totalCatalogStat) totalCatalogStat.textContent = total.toLocaleString('en-IN');
    if (pageInfo) pageInfo.textContent = `Showing Page ${forYouCurrentPage} of ${forYouTotalPages}`;
    if (currPageEl) currPageEl.textContent = forYouCurrentPage;
    if (totalPagesEl) totalPagesEl.textContent = forYouTotalPages;

    if (prevBtn) prevBtn.disabled = forYouCurrentPage <= 1;
    if (nextBtn) nextBtn.disabled = forYouCurrentPage >= forYouTotalPages;

    if (!grid) return;

    if (products.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 64px 20px; background: #ffffff; border-radius: 12px; border: 1px dashed #cbd5e1;">
          <span style="font-size: 36px;">🔍</span>
          <h3 style="font-size: 18px; font-weight: 700; color: #1e293b; margin: 12px 0 6px;">No products match your search</h3>
          <p style="font-size: 13.5px; color: #64748b; margin: 0 0 16px 0;">Try adjusting your keywords or clearing the category filter.</p>
          <button class="btn btn-outline" onclick="resetForYouFilters()">Reset Filters</button>
        </div>
      `;
      return;
    }

    // Render Product Cards
    grid.innerHTML = products.map(p => `
      <div class="card fk-product-card" id="productCard_${p.id}" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s;">
        <div>
          <!-- Thumbnail & Wishlist Button -->
          <div style="position: relative; height: 160px; background: #f8fafc; border-radius: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden; margin-bottom: 10px;">
            <img src="${getSafeProductImage(p)}" alt="${p.title}" style="max-height: 140px; max-width: 90%; object-fit: contain; cursor: pointer;" onclick="openProductDetail(${p.id})">
            
            <button type="button" onclick="handleWishlistClick(${p.id}, event)" style="position: absolute; top: 8px; right: 8px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #ef4444; box-shadow: 0 2px 6px rgba(0,0,0,0.06);" title="Save to Wishlist">
              ♥
            </button>
            ${p.brand ? `<span style="position: absolute; bottom: 8px; left: 8px; background: rgba(255,255,255,0.9); font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; color: #475569;">${p.brand}</span>` : ''}
          </div>

          <!-- Product Details -->
          <div style="font-size: 11.5px; font-weight: 700; color: #7c3aed; text-transform: uppercase;">
            ${p.category} ${p.subcategory ? `&bull; ${p.subcategory}` : ''}
          </div>

          <h3 style="font-size: 14px; font-weight: 700; color: #1e293b; margin: 4px 0 8px; line-height: 1.35; height: 38px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; cursor: pointer;" onclick="openProductDetail(${p.id})" title="${p.title}">
            ${p.title}
          </h3>

          <!-- Price & Discount -->
          <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 17px; font-weight: 800; color: #0f172a;">₹${Math.round(p.price).toLocaleString('en-IN')}</span>
            <span style="font-size: 12px; color: #94a3b8; text-decoration: line-through;">₹${Math.round(p.price * 1.25).toLocaleString('en-IN')}</span>
            <span style="font-size: 11.5px; color: #15803d; font-weight: 700;">20% off</span>
          </div>

          <!-- Rating -->
          <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 12px; font-size: 12px; color: #64748b;">
            <span style="background: #15803d; color: #ffffff; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 11px;">
              ${p.rating ? parseFloat(p.rating).toFixed(1) : '4.3'} ★
            </span>
            <span>(${p.stock_quantity ? p.stock_quantity * 7 : '142'} ratings)</span>
          </div>
        </div>

        <!-- Action Button -->
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-primary" onclick="handleAddToCartClick(${p.id}, event)" style="flex: 1; padding: 8px; font-size: 13px; font-weight: 700;">
            + Add to Cart
          </button>
        </div>
      </div>
    `).join('');

  } catch (err) {
    console.error('Failed to load products:', err);
    if (grid) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: #ef4444;">
          <p>Failed to load products from database: ${err.message}</p>
          <button class="btn btn-primary mt-2" onclick="loadForYouProducts()">Retry</button>
        </div>
      `;
    }
  }
}

/**
 * Filter handling
 */
function filterForYouCategory(category) {
  forYouActiveCategory = category;
  forYouCurrentPage = 1;

  document.querySelectorAll('#forYouCategoryPills .for-you-cat-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  if (event && event.target) event.target.classList.add('active');

  loadForYouProducts();
}

function handleForYouSearch(query) {
  clearTimeout(forYouSearchTimer);
  forYouSearchTimer = setTimeout(() => {
    forYouSearchTerm = query;
    forYouCurrentPage = 1;
    loadForYouProducts();
  }, 250);
}

function handleForYouSort(sortValue) {
  forYouActiveSort = sortValue;
  forYouCurrentPage = 1;
  loadForYouProducts();
}

function changeForYouPage(delta) {
  const newPage = forYouCurrentPage + delta;
  if (newPage >= 1 && newPage <= forYouTotalPages) {
    forYouCurrentPage = newPage;
    loadForYouProducts();
    window.scrollTo({ top: 350, behavior: 'smooth' });
  }
}

function resetForYouFilters() {
  forYouActiveCategory = 'all';
  forYouSearchTerm = '';
  forYouCurrentPage = 1;
  const searchInput = document.getElementById('forYouSearchInput');
  if (searchInput) searchInput.value = '';
  document.querySelectorAll('#forYouCategoryPills .for-you-cat-btn').forEach((btn, idx) => {
    if (idx === 0) btn.classList.add('active');
    else btn.classList.remove('active');
  });
  loadForYouProducts();
}

/**
 * Cart and Wishlist helpers
 */
function handleAddToCartClick(productId, e) {
  if (e) e.stopPropagation();
  if (typeof addToCartById === 'function') {
    addToCartById(productId);
  } else if (window.catalogMap && window.catalogMap[productId] && typeof addToCart === 'function') {
    addToCart(window.catalogMap[productId]);
  }
  showFloatingNotice('Added to Cart! ✨');
}

function handleWishlistClick(productId, e) {
  if (e) e.stopPropagation();
  if (typeof toggleWishlistById === 'function') {
    toggleWishlistById(productId, e);
  } else if (typeof toggleWishlist === 'function') {
    toggleWishlist(productId, e);
  }
}

function openProductDetail(productId) {
  if (typeof openProductModal === 'function') {
    openProductModal(productId);
  }
}

function showFloatingNotice(text) {
  let notice = document.getElementById('forYouFloatingNotice');
  if (!notice) {
    notice = document.createElement('div');
    notice.id = 'forYouFloatingNotice';
    notice.style.position = 'fixed';
    notice.style.bottom = '24px';
    notice.style.right = '24px';
    notice.style.background = '#1e293b';
    notice.style.color = '#ffffff';
    notice.style.padding = '10px 18px';
    notice.style.borderRadius = '8px';
    notice.style.fontSize = '13.5px';
    notice.style.fontWeight = '600';
    notice.style.boxShadow = '0 10px 25px rgba(0,0,0,0.2)';
    notice.style.zIndex = '99999';
    notice.style.transition = 'opacity 0.2s';
    document.body.appendChild(notice);
  }
  notice.textContent = text;
  notice.style.opacity = '1';
  notice.style.display = 'block';
  setTimeout(() => {
    notice.style.opacity = '0';
    setTimeout(() => { notice.style.display = 'none'; }, 200);
  }, 2200);
}
