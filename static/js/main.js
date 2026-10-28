/**
 * PRETWIN — MASTER CLIENT JAVASCRIPT
 * Complete interactions for PreTwin Predictive Shopping Twin:
 * - Search autocomplete & keyword filtering
 * - 2-Pane Authentication Modal (Sign In & Register with password hashing & session management)
 * - Shopping Cart Modal with item quantity management, MRP strikethrough, savings calculation, and Proceed to Checkout
 * - Product Quick View Modal with image, ratings, PreTwin Assured badge, bank offers, specs, ADD TO CART & BUY NOW
 * - Wishlist drawer & heart icon states
 * - Banner carousel controls
 * - Horizontal deal carousels smooth scroll
 */

const API_BASE = '';

// Local Storage Keys (with migration fallback)
const CART_KEY = 'pretwin_cart';
const WISHLIST_KEY = 'pretwin_wishlist';
const USER_KEY = 'pretwin_user';

let currentBannerIndex = 0;
let bannerTimer = null;
let allCatalogProducts = [];
let currentUser = null;

// ---------------------------------------------------------------------------
// Currency Formatting (PreTwin INR Style)
// ---------------------------------------------------------------------------
function formatPrice(val) {
  const f = parseFloat(val) || 0;
  if (Math.abs(f % 1) > 0.001 || (Math.abs(f) > 0 && Math.abs(f) < 1)) {
    return '₹' + f.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return '₹' + Math.round(f).toLocaleString('en-IN');
}

// ---------------------------------------------------------------------------
// Toast Notification
// ---------------------------------------------------------------------------
function showToast(message) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ---------------------------------------------------------------------------
// API Helpers
// ---------------------------------------------------------------------------
async function apiGet(endpoint) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`GET ${endpoint} failed:`, err);
    throw err;
  }
}

async function apiPost(endpoint, data) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const json = await res.json();
    if (!res.ok) {
      throw new Error(json.error || `HTTP ${res.status}`);
    }
    return json;
  } catch (err) {
    console.error(`POST ${endpoint} failed:`, err);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// 1. PreTwin Search & Autocomplete
// ---------------------------------------------------------------------------
function handlePreTwinSearch(e) {
  e.preventDefault();
  const input = document.getElementById('fkSearchInput');
  const query = input ? input.value.trim() : '';
  if (query) {
    window.location.href = `/discovery?search=${encodeURIComponent(query)}`;
  }
}

// Keep alias for backwards compatibility
const handleFlipkartSearch = handlePreTwinSearch;

function handleSearchType(val) {
  const dropdown = document.getElementById('fkSearchDropdown');
  if (!dropdown) return;

  const query = val.trim().toLowerCase();
  if (!query || allCatalogProducts.length === 0) {
    dropdown.style.display = 'none';
    return;
  }

  const matches = allCatalogProducts
    .filter((p) => p.name.toLowerCase().includes(query) || (p.brand && p.brand.toLowerCase().includes(query)))
    .slice(0, 6);

  if (matches.length === 0) {
    dropdown.style.display = 'none';
    return;
  }

  dropdown.innerHTML = matches.map((p) => `
    <div class="fk-search-item" onclick="openProductDetail(${p.id}); document.getElementById('fkSearchDropdown').style.display='none';">
      <span style="color:#2874f0; font-size:14px;">🔍</span>
      <div style="flex:1;">
        <span style="font-weight:500;">${p.name}</span>
        <span style="color:#878787; font-size:12px; margin-left:6px;">in ${p.category}</span>
      </div>
      <span style="font-weight:700; color:#212121;">${formatPrice(p.price)}</span>
    </div>
  `).join('');

  dropdown.style.display = 'block';
}

// Close dropdown on click outside
document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('fkSearchDropdown');
  const searchBox = document.querySelector('.fk-search-box');
  if (dropdown && searchBox && !searchBox.contains(e.target)) {
    dropdown.style.display = 'none';
  }
});

// ---------------------------------------------------------------------------
// 2. PreTwin Authentication (Sign In, Register, Session)
// ---------------------------------------------------------------------------

function openLoginModal(tab = 'login') {
  const currentPath = window.location.pathname + window.location.search;
  window.location.href = '/login?next=' + encodeURIComponent(currentPath);
}

function closeLoginModal() {
  const modal = document.getElementById('fkLoginModal');
  if (modal) modal.classList.remove('open');
}

function switchAuthTab(tab) {
  const tabLogin = document.getElementById('authTabLogin');
  const tabRegister = document.getElementById('authTabRegister');
  const signInForm = document.getElementById('signInForm');
  const registerForm = document.getElementById('registerForm');
  const leftTitle = document.getElementById('authModalLeftTitle');
  const leftDesc = document.getElementById('authModalLeftDesc');

  clearAuthErrors();

  if (tab === 'register') {
    if (tabLogin) {
      tabLogin.style.color = '#878787';
      tabLogin.style.borderBottom = '2px solid transparent';
      tabLogin.style.fontWeight = '600';
    }
    if (tabRegister) {
      tabRegister.style.color = '#2874f0';
      tabRegister.style.borderBottom = '2px solid #2874f0';
      tabRegister.style.fontWeight = '700';
    }
    if (signInForm) signInForm.style.display = 'none';
    if (registerForm) registerForm.style.display = 'block';
    if (leftTitle) leftTitle.textContent = 'Create Account';
    if (leftDesc) leftDesc.textContent = 'Sign up to build your personalized AI Shopping Twin and unlock tailored offers';
  } else {
    if (tabLogin) {
      tabLogin.style.color = '#2874f0';
      tabLogin.style.borderBottom = '2px solid #2874f0';
      tabLogin.style.fontWeight = '700';
    }
    if (tabRegister) {
      tabRegister.style.color = '#878787';
      tabRegister.style.borderBottom = '2px solid transparent';
      tabRegister.style.fontWeight = '600';
    }
    if (signInForm) signInForm.style.display = 'block';
    if (registerForm) registerForm.style.display = 'none';
    if (leftTitle) leftTitle.textContent = 'Sign In';
    if (leftDesc) leftDesc.textContent = 'Get access to your Orders, Wishlist, and AI Personal Shopping Twin';
  }
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = 'HIDE';
  } else {
    input.type = 'password';
    btn.textContent = 'SHOW';
  }
}

function fillDemoCredentials() {
  const emailInput = document.getElementById('loginEmailInput');
  const passInput = document.getElementById('loginPasswordInput');
  if (emailInput) emailInput.value = 'alex@demo.pretwinshop.ai';
  if (passInput) passInput.value = 'password123';
}

function showAuthError(msg) {
  const errBox = document.getElementById('authErrorMessage');
  if (errBox) {
    errBox.textContent = msg;
    errBox.style.display = 'block';
  }
}

function clearAuthErrors() {
  const errBox = document.getElementById('authErrorMessage');
  if (errBox) errBox.style.display = 'none';
}

async function handleSignInSubmit(e) {
  e.preventDefault();
  clearAuthErrors();

  const emailInput = document.getElementById('loginEmailInput');
  const passInput = document.getElementById('loginPasswordInput');
  const submitBtn = document.getElementById('signInSubmitBtn');

  const email = emailInput ? emailInput.value.trim() : '';
  const password = passInput ? passInput.value : '';

  if (!email || !password) {
    showAuthError('Please enter both email and password.');
    return;
  }

  const originalBtnText = submitBtn ? submitBtn.textContent : 'Sign In';
  if (submitBtn) {
    submitBtn.textContent = 'Signing in...';
    submitBtn.disabled = true;
  }

  try {
    const res = await apiPost('/api/auth/login', { email, password });
    currentUser = res.user;
    localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    updateAuthUI();
    closeLoginModal();
    showToast(`Welcome back, ${currentUser.username}!`);
  } catch (err) {
    showAuthError(err.message || 'Sign in failed. Please verify credentials.');
  } finally {
    if (submitBtn) {
      submitBtn.textContent = originalBtnText;
      submitBtn.disabled = false;
    }
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  clearAuthErrors();

  const nameInput = document.getElementById('regNameInput');
  const emailInput = document.getElementById('regEmailInput');
  const passInput = document.getElementById('regPasswordInput');
  const confirmPassInput = document.getElementById('regConfirmPasswordInput');
  const submitBtn = document.getElementById('registerSubmitBtn');

  const name = nameInput ? nameInput.value.trim() : '';
  const email = emailInput ? emailInput.value.trim() : '';
  const password = passInput ? passInput.value : '';
  const confirmPassword = confirmPassInput ? confirmPassInput.value : '';

  if (!name || !email || !password) {
    showAuthError('Please complete all required fields.');
    return;
  }
  if (password.length < 6) {
    showAuthError('Password must be at least 6 characters long.');
    return;
  }
  if (password !== confirmPassword) {
    showAuthError('Passwords do not match. Please re-enter.');
    return;
  }

  const originalBtnText = submitBtn ? submitBtn.textContent : 'Create PreTwin Account';
  if (submitBtn) {
    submitBtn.textContent = 'Creating account...';
    submitBtn.disabled = true;
  }

  try {
    const res = await apiPost('/api/auth/register', {
      name,
      email,
      password,
      confirm_password: confirmPassword
    });
    currentUser = res.user;
    localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    updateAuthUI();
    closeLoginModal();
    showToast(`Account created! Welcome to PreTwin, ${currentUser.username}.`);
  } catch (err) {
    showAuthError(err.message || 'Registration failed. Please try a different email.');
  } finally {
    if (submitBtn) {
      submitBtn.textContent = originalBtnText;
      submitBtn.disabled = false;
    }
  }
}

// ---------------------------------------------------------------------------
// PreTwin Account Dropdown & Authentication Navigation
// ---------------------------------------------------------------------------
function togglePreTwinAccountDropdown(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const dropdown = document.getElementById('pretwinAccountDropdown');
  const btn = document.getElementById('pretwinProfileBtn');
  if (!dropdown) return;
  const isOpen = dropdown.classList.contains('is-open');
  if (isOpen) {
    dropdown.classList.remove('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  } else {
    dropdown.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

async function handlePreTwinLogout(e) {
  if (e) e.preventDefault();
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (err) {
    console.warn('Logout API error:', err);
  }
  currentUser = null;
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem('flipkart_user');
  window.location.href = '/login?logged_out=1';
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
  const accountItem = document.getElementById('pretwinAccountItem');
  const dropdown = document.getElementById('pretwinAccountDropdown');
  if (dropdown && dropdown.classList.contains('is-open')) {
    if (!accountItem || !accountItem.contains(e.target)) {
      dropdown.classList.remove('is-open');
      const btn = document.getElementById('pretwinProfileBtn');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
  }
});

async function handleUserLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {
    console.warn('Logout API warning:', e);
  }
  currentUser = null;
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem('flipkart_user');
  updateAuthUI();
  showToast('Signed out successfully.');
}

async function checkAuthStatus() {
  try {
    const res = await apiGet('/api/auth/me');
    if (res.authenticated && res.user && res.user.email !== 'alex@demo.pretwinshop.ai' && res.user.username !== 'Alex Johnson') {
      currentUser = res.user;
      localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    } else {
      currentUser = null;
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem('flipkart_user');
    }
  } catch (e) {
    // If backend offline or error, check cached localStorage
    try {
      const cached = localStorage.getItem(USER_KEY) || localStorage.getItem('flipkart_user');
      if (cached) {
        const parsed = typeof cached === 'string' && cached.startsWith('{') ? JSON.parse(cached) : { username: cached };
        if (parsed.email === 'alex@demo.pretwinshop.ai' || parsed.username === 'Alex Johnson') {
          currentUser = null;
          localStorage.removeItem(USER_KEY);
          localStorage.removeItem('flipkart_user');
        } else {
          currentUser = parsed;
        }
      }
    } catch (ignore) {}
  }
  updateAuthUI();
}

function updateAuthUI() {
  // Sync global authentication status
  if (currentUser && currentUser.username && currentUser.username !== 'Alex Johnson' && currentUser.email !== 'alex@demo.pretwinshop.ai') {
    window.PRETWIN_IS_AUTHENTICATED = true;
    window.PRETWIN_CURRENT_USER = currentUser;
  } else {
    window.PRETWIN_IS_AUTHENTICATED = false;
    window.PRETWIN_CURRENT_USER = null;
  }
}

function navigateOrLogin(targetUrl) {
  window.location.href = targetUrl;
}

function showSellerNotice() {
  showToast('PreTwin AI Merchant Hub: Sell smarter with predictive customer insights!');
}

// ---------------------------------------------------------------------------
// 3. Cart Management System (PreTwin Cart Modal & Persistence)
// ---------------------------------------------------------------------------
function getCart() {
  try {
    const data = localStorage.getItem(CART_KEY) || localStorage.getItem('flipkart_cart');
    return JSON.parse(data || '[]');
  } catch (e) {
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartBadge();
  renderCartModal();
}

function updateCartBadge() {
  const badge = document.getElementById('fkCartBadge');
  const cart = getCart();
  const count = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);
  if (badge) {
    badge.textContent = count;
    badge.classList.remove('cart-badge-bounce');
    // Trigger CSS reflow to re-trigger bounce animation
    void badge.offsetWidth;
    badge.classList.add('cart-badge-bounce');
  }
}

function addToCart(product) {
  if (!product) return;
  let cart = getCart();
  const existing = cart.find((i) => i.id === product.id);

  if (existing) {
    existing.quantity = (existing.quantity || 1) + 1;
  } else {
    cart.push({ ...product, quantity: 1 });
  }

  saveCart(cart);
  showToast(`Added "${product.name.slice(0, 28)}..." to Cart!`);
}

function removeFromCart(productId) {
  let cart = getCart();
  cart = cart.filter((i) => i.id !== productId);
  saveCart(cart);
  showToast('Item removed from Cart');
}

function updateCartQty(productId, delta) {
  let cart = getCart();
  const item = cart.find((i) => i.id === productId);
  if (!item) return;

  item.quantity = (item.quantity || 1) + delta;
  if (item.quantity <= 0) {
    removeFromCart(productId);
  } else {
    saveCart(cart);
  }
}

function openCartModal() {
  renderCartModal();
  const modal = document.getElementById('fkCartModal');
  if (modal) modal.classList.add('open');
}

function closeCartModal() {
  const modal = document.getElementById('fkCartModal');
  if (modal) modal.classList.remove('open');
}

function renderCartModal() {
  const cart = getCart();
  const container = document.getElementById('fkCartItemsContainer');
  const countTitle = document.getElementById('cartCountTitle');
  const summaryCount = document.getElementById('summaryItemCount');
  const origPriceEl = document.getElementById('summaryOriginalPrice');
  const discountEl = document.getElementById('summaryDiscount');
  const deliveryFeeEl = document.getElementById('summaryDeliveryFee');
  const totalAmountEl = document.getElementById('summaryTotalAmount');
  const savingsNotice = document.getElementById('summarySavingsNotice');

  const totalQty = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);
  if (countTitle) countTitle.textContent = totalQty;
  if (summaryCount) summaryCount.textContent = totalQty;

  let totalPayable = 0;
  let totalMrp = 0;

  if (!container) return;

  if (cart.length === 0) {
    container.innerHTML = `
      <div class="fk-cart-empty">
        <img src="https://rukminim1.flixcart.com/www/800/800/promos/16/05/2019/d438a32e-765a-4d8b-b4a6-520b560971e8.png?q=90" alt="Empty Cart">
        <h3>Your PreTwin cart is empty!</h3>
        <p>Explore top deals, trending categories, and AI Twin recommendations.</p>
        <button class="fk-btn-orange" style="width:180px;" onclick="closeCartModal(); window.location.href='/discovery';">Shop Now</button>
      </div>
    `;
  } else {
    container.innerHTML = cart.map((item) => {
      const price = parseFloat(item.price) || 0;
      const mrp = item.mrp || Math.round(price * 1.35);
      const qty = item.quantity || 1;

      totalPayable += price * qty;
      totalMrp += mrp * qty;

      const fallbackImg = getCategoryFallbackImg(item.category);

      return `
        <div class="fk-cart-item-card">
          <img src="${item.image_url || fallbackImg}" alt="${item.name}" class="fk-cart-item-img" onerror="this.src='${fallbackImg}'">
          <div class="fk-cart-item-details">
            <h4 class="fk-cart-item-title">${item.name}</h4>
            <div style="font-size:12px; color:#878787; margin-bottom:8px;">Seller: PreTwin Retail • <span style="color:#2874f0; font-weight:700;">PreTwin Assured</span></div>
            <div class="fk-cart-item-price-row">
              <span class="fk-cart-item-price">${formatPrice(price)}</span>
              <span class="fk-cart-item-mrp">${formatPrice(mrp)}</span>
              <span class="fk-cart-item-disc">${Math.round(((mrp - price) / mrp) * 100)}% Off</span>
            </div>
            <div class="fk-cart-qty-row">
              <button class="fk-qty-btn" onclick="updateCartQty(${item.id}, -1)">−</button>
              <span class="fk-qty-num">${qty}</span>
              <button class="fk-qty-btn" onclick="updateCartQty(${item.id}, 1)">+</button>
              <span class="fk-cart-action-link" onclick="removeFromCart(${item.id})">REMOVE</span>
              <span class="fk-cart-action-link" onclick="toggleWishlistById(${item.id}); removeFromCart(${item.id});">SAVE FOR LATER</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  const totalDiscount = totalMrp - totalPayable;
  const isFreeDelivery = totalPayable >= 500 || totalPayable === 0;
  const deliveryFee = isFreeDelivery ? 0 : 40;
  const finalTotal = totalPayable + deliveryFee;

  if (origPriceEl) origPriceEl.textContent = formatPrice(totalMrp);
  if (discountEl) discountEl.textContent = '−' + formatPrice(totalDiscount);
  if (deliveryFeeEl) deliveryFeeEl.textContent = isFreeDelivery ? 'FREE' : formatPrice(deliveryFee);
  if (totalAmountEl) totalAmountEl.textContent = formatPrice(finalTotal);
  if (savingsNotice) savingsNotice.textContent = `You will save ${formatPrice(totalDiscount)} on this order`;
}

function proceedToCheckout() {
  const cart = getCart();
  if (cart.length === 0) {
    showToast('Your cart is empty. Add products before proceeding.');
    return;
  }
  closeCartModal();
  window.location.href = '/checkout';
}

// Keep legacy alias for backward compatibility
const handlePlaceOrder = proceedToCheckout;

// ---------------------------------------------------------------------------
// 4. Wishlist Management System
// ---------------------------------------------------------------------------
function getWishlist() {
  try {
    const data = localStorage.getItem(WISHLIST_KEY) || localStorage.getItem('flipkart_wishlist');
    return JSON.parse(data || '[]');
  } catch (e) {
    return [];
  }
}

function saveWishlist(list) {
  localStorage.setItem(WISHLIST_KEY, JSON.stringify(list));
  const countEl = document.getElementById('menuWishlistCount');
  if (countEl) countEl.textContent = list.length;
}

function toggleWishlist(product) {
  let list = getWishlist();
  const idx = list.findIndex((i) => i.id === product.id);

  if (idx > -1) {
    list.splice(idx, 1);
    saveWishlist(list);
    showToast('Removed from Wishlist');
  } else {
    list.push(product);
    saveWishlist(list);
    showToast('Added to Wishlist ❤️');
  }

  updateWishlistIcons();
}

function updateWishlistIcons() {
  const list = getWishlist();
  const ids = new Set(list.map((i) => i.id));

  document.querySelectorAll('.fk-card-wish').forEach((btn) => {
    const pid = parseInt(btn.getAttribute('data-product-id'));
    if (ids.has(pid)) {
      if (!btn.classList.contains('active')) {
        btn.classList.add('active');
        btn.classList.add('wishlist-pop');
        setTimeout(() => btn.classList.remove('wishlist-pop'), 450);
      }
    } else {
      btn.classList.remove('active');
      btn.classList.remove('wishlist-pop');
    }
  });
}

function openWishlistModal() {
  const list = getWishlist();
  if (list.length === 0) {
    showToast('Your wishlist is empty');
    return;
  }
  // Open cart modal with wishlist items or navigate to discovery
  window.location.href = '/discovery';
}

// ---------------------------------------------------------------------------
// 5. Product Quick View Detail Modal
// ---------------------------------------------------------------------------
async function openProductDetail(productId) {
  try {
    const modal = document.getElementById('fkDetailModal');
    if (!modal) return;

    let p = window.catalogMap[productId] || (allCatalogProducts && allCatalogProducts.find(x => x.id === productId));
    if (!p) {
      const res = await apiGet(`/api/products/${productId}`);
      p = res.product || res;
    }
    if (!p) return;

    const imgEl = document.getElementById('detailImg');
    const titleEl = document.getElementById('detailTitle');
    const ratingEl = document.getElementById('detailRating');
    const reviewsEl = document.getElementById('detailReviews');
    const priceEl = document.getElementById('detailPrice');
    const mrpEl = document.getElementById('detailMrp');
    const discEl = document.getElementById('detailDiscount');
    const descEl = document.getElementById('detailDescription');
    const specsEl = document.getElementById('detailSpecsTable');
    const addBtn = document.getElementById('detailAddToCartBtn');
    const buyBtn = document.getElementById('detailBuyNowBtn');

    const originalMrp = p.mrp || Math.round(p.price * 1.35);
    const discPct = p.discount_percentage || Math.round(((originalMrp - p.price) / originalMrp) * 100);
    const fallbackImg = getCategoryFallbackImg(p.category);

    if (imgEl) {
      imgEl.src = p.image_url || fallbackImg;
      imgEl.onerror = () => { imgEl.src = fallbackImg; };
    }
    if (titleEl) titleEl.textContent = p.name;
    if (ratingEl) ratingEl.textContent = `${(p.rating || 4.4).toFixed(1)} ★`;
    if (reviewsEl) reviewsEl.textContent = `(${p.review_count_demo || 120} Ratings & Customer Reviews)`;
    if (priceEl) priceEl.textContent = formatPrice(p.price);
    if (mrpEl) mrpEl.textContent = formatPrice(originalMrp);
    if (discEl) discEl.textContent = `${discPct}% off`;
    if (descEl) descEl.textContent = p.description || 'Experience cutting-edge performance and quality crafted for everyday convenience.';

    if (specsEl) {
      let specs = p.specifications;
      if (typeof specs === 'string') {
        try { specs = JSON.parse(specs); } catch (e) { specs = {}; }
      }
      specs = specs || {};

      const rows = Object.entries(specs).map(([k, v]) => `
        <tr>
          <td class="fk-spec-key">${k.replace(/_/g, ' ')}</td>
          <td class="fk-spec-val">${v}</td>
        </tr>
      `);

      rows.push(`
        <tr>
          <td class="fk-spec-key">Category</td>
          <td class="fk-spec-val">${p.category}</td>
        </tr>
      `);
      if (p.brand) {
        rows.push(`
          <tr>
            <td class="fk-spec-key">Brand</td>
            <td class="fk-spec-val">${p.brand}</td>
          </tr>
        `);
      }

      specsEl.innerHTML = rows.join('');
    }

    if (addBtn) {
      addBtn.onclick = () => {
        addToCart(p);
      };
    }

    if (buyBtn) {
      buyBtn.onclick = () => {
        addToCart(p);
        closeDetailModal();
        window.location.href = '/checkout';
      };
    }

    const compareBtn = document.getElementById('detailCompareBtn');
    if (compareBtn) {
      const isComp = getComparisonIds().includes(p.id);
      compareBtn.innerHTML = isComp ? '<span>✓</span> IN COMPARISON' : '<span>⚖️</span> COMPARE';
      compareBtn.style.background = isComp ? '#7c3aed' : '#ffffff';
      compareBtn.style.color = isComp ? '#ffffff' : '#7c3aed';
      compareBtn.onclick = () => {
        toggleProductComparison(p.id, p.name);
        const nowComp = getComparisonIds().includes(p.id);
        compareBtn.innerHTML = nowComp ? '<span>✓</span> IN COMPARISON' : '<span>⚖️</span> COMPARE';
        compareBtn.style.background = nowComp ? '#7c3aed' : '#ffffff';
        compareBtn.style.color = nowComp ? '#ffffff' : '#7c3aed';
      };
    }

    modal.classList.add('open');
  } catch (err) {
    console.error('Failed to load product detail:', err);
  }
}

function closeDetailModal() {
  const modal = document.getElementById('fkDetailModal');
  if (modal) modal.classList.remove('open');
}

// ---------------------------------------------------------------------------
// 6. Homepage Banner Carousel Controls
// ---------------------------------------------------------------------------
function initBannerCarousel() {
  const viewport = document.getElementById('fkBannerViewport');
  if (!viewport) return;

  const slides = viewport.querySelectorAll('.fk-banner-slide');
  if (slides.length <= 1) return;

  if (bannerTimer) clearInterval(bannerTimer);
  bannerTimer = setInterval(() => {
    moveBannerSlide(1);
  }, 4500);
}

function moveBannerSlide(direction) {
  const viewport = document.getElementById('fkBannerViewport');
  if (!viewport) return;

  const slides = viewport.querySelectorAll('.fk-banner-slide');
  const dots = document.querySelectorAll('#bannerDots .fk-dot');
  if (slides.length === 0) return;

  slides[currentBannerIndex].classList.remove('active');
  if (dots[currentBannerIndex]) dots[currentBannerIndex].classList.remove('active');

  currentBannerIndex = (currentBannerIndex + direction + slides.length) % slides.length;

  slides[currentBannerIndex].classList.add('active');
  if (dots[currentBannerIndex]) dots[currentBannerIndex].classList.add('active');
}

function goToBannerSlide(index) {
  const viewport = document.getElementById('fkBannerViewport');
  if (!viewport) return;

  const slides = viewport.querySelectorAll('.fk-banner-slide');
  const dots = document.querySelectorAll('#bannerDots .fk-dot');

  slides[currentBannerIndex].classList.remove('active');
  if (dots[currentBannerIndex]) dots[currentBannerIndex].classList.remove('active');

  currentBannerIndex = index;

  slides[currentBannerIndex].classList.add('active');
  if (dots[currentBannerIndex]) dots[currentBannerIndex].classList.add('active');

  initBannerCarousel(); // reset timer
}

// ---------------------------------------------------------------------------
// 7. Horizontal Deal Carousel Smooth Scroll
// ---------------------------------------------------------------------------
function scrollTrack(trackId, offset) {
  const track = document.getElementById(trackId);
  if (track) {
    track.scrollBy({ left: offset, behavior: 'smooth' });
  }
}

function scrollCatBar(offset) {
  const bar = document.getElementById('categoryBar');
  if (bar) {
    bar.scrollBy({ left: offset, behavior: 'smooth' });
  }
}

// ---------------------------------------------------------------------------
// 8. Product Registry & PreTwin Product Card HTML
// ---------------------------------------------------------------------------
window.catalogMap = window.catalogMap || {};

function registerProduct(p) {
  if (p && p.id) {
    window.catalogMap[p.id] = p;
  }
}

function addToCartById(id) {
  const p = window.catalogMap[id] || (allCatalogProducts && allCatalogProducts.find(x => x.id === id));
  if (p) addToCart(p);
  else console.warn('Product not found in registry for id:', id);
}

function toggleWishlistById(id) {
  const p = window.catalogMap[id] || (allCatalogProducts && allCatalogProducts.find(x => x.id === id));
  if (p) toggleWishlist(p);
}

function getCategoryFallbackImg(category) {
  if (!category) return '/static/images/pretwin-icon.svg';
  const slug = category.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return `/static/images/placeholders/${slug}.svg`;
}

function createFlipkartCardHtml(p, offerLabel = 'Min. 50% Off') {
  if (!p) return '';
  registerProduct(p);

  const originalMrp = p.mrp || Math.round(p.price * 1.35);
  const discountText = p.discount_percentage ? `${p.discount_percentage}% off` : offerLabel;
  const fallbackSvg = getCategoryFallbackImg(p.category);
  const initialImg = p.image_url || fallbackSvg;

  return `
    <div class="fk-card" onclick="openProductDetail(${p.id})">
      <button 
        class="fk-card-wish" 
        data-product-id="${p.id}" 
        onclick="event.stopPropagation(); toggleWishlistById(${p.id});" 
        title="Add to Wishlist"
      >
        ♥
      </button>
      
      <div class="fk-card-img-box">
        <img 
          src="${initialImg}" 
          alt="${p.name}" 
          loading="lazy" 
          onerror="this.onerror=null; this.src='${fallbackSvg}';"
        />
      </div>

      <div class="fk-card-title" title="${p.name}">
        ${p.name}
      </div>

      <div class="fk-card-offer">
        ${discountText}
      </div>

      <div class="fk-card-price-row">
        <span class="fk-card-curr-price">${formatPrice(p.price)}</span>
        <span class="fk-card-mrp">${formatPrice(originalMrp)}</span>
      </div>

      <div class="fk-card-sub">
        ${p.brand ? p.brand + ' • ' : ''}${p.subcategory || p.category}
      </div>

      <div class="fk-card-quick-add" onclick="event.stopPropagation()" style="display:flex; gap:6px; margin-top:8px;">
        <button class="fk-btn-add" style="flex:1;" onclick="addToCartById(${p.id})">
          ADD TO CART
        </button>
        <button class="fk-btn-compare-card" 
                data-product-id="${p.id}"
                onclick="toggleProductComparison(${p.id}, '${(p.name || '').replace(/'/g, "\\'")}')" 
                title="Add to Comparison"
                style="padding:6px 10px; font-size:11px; font-weight:700; border-radius:3px; border:1px solid #7c3aed; background:${getComparisonIds().includes(p.id) ? '#7c3aed' : '#ffffff'}; color:${getComparisonIds().includes(p.id) ? '#ffffff' : '#7c3aed'}; cursor:pointer; transition:all 0.2s ease;">
          ⚖️ ${getComparisonIds().includes(p.id) ? 'Compared' : 'Compare'}
        </button>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 8. Product Comparison Management System (PreTwin Persistent Compare)
// ---------------------------------------------------------------------------
const COMPARISON_KEY = 'pretwin_comparison_ids';

function getComparisonIds() {
  try {
    const raw = localStorage.getItem(COMPARISON_KEY);
    const parsed = JSON.parse(raw || '[]');
    return Array.isArray(parsed) ? parsed.map(Number).filter(n => !isNaN(n) && n > 0) : [];
  } catch (e) {
    return [];
  }
}

function saveComparisonIds(ids) {
  try {
    const clean = Array.from(new Set(ids.map(Number).filter(n => !isNaN(n) && n > 0))).slice(0, 4);
    localStorage.setItem(COMPARISON_KEY, JSON.stringify(clean));
    updateComparisonUI();
  } catch (e) {
    console.warn('Failed to save comparison ids:', e);
  }
}

function toggleProductComparison(productId, productName) {
  const pid = parseInt(productId, 10);
  if (!pid) return;
  let ids = getComparisonIds();
  if (ids.includes(pid)) {
    ids = ids.filter(id => id !== pid);
    saveComparisonIds(ids);
    showToast(`Removed from comparison`, 'info');
  } else {
    if (ids.length >= 4) {
      showToast('Maximum 4 products allowed for comparison. Remove one to add another.', 'warning');
      return;
    }
    ids.push(pid);
    saveComparisonIds(ids);
    showToast(`Added ${productName || 'product'} to comparison (Total: ${ids.length})`, 'success');
  }
}

function clearAllComparisonGlobal() {
  saveComparisonIds([]);
  showToast('Comparison list cleared', 'info');
}

function updateComparisonUI() {
  const ids = getComparisonIds();

  // 1. Update all compare buttons on cards
  document.querySelectorAll('.fk-btn-compare-card').forEach(btn => {
    const pid = parseInt(btn.dataset.productId, 10);
    if (pid) {
      const active = ids.includes(pid);
      btn.style.background = active ? '#7c3aed' : '#ffffff';
      btn.style.color = active ? '#ffffff' : '#7c3aed';
      btn.innerHTML = `⚖️ ${active ? 'Compared' : 'Compare'}`;
    }
  });

  // 2. Manage floating compare widget
  let widget = document.getElementById('pretwinFloatingCompareBar');
  if (ids.length > 0) {
    if (!widget) {
      widget = document.createElement('div');
      widget.id = 'pretwinFloatingCompareBar';
      widget.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 24px;
        z-index: 9999;
        background: linear-gradient(135deg, #181438 0%, #2e1065 100%);
        border: 1.5px solid #a855f7;
        color: #ffffff;
        padding: 10px 18px;
        border-radius: 30px;
        box-shadow: 0 10px 30px rgba(124, 58, 237, 0.4);
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
        font-weight: 600;
        backdrop-filter: blur(8px);
      `;
      document.body.appendChild(widget);
    }
    widget.innerHTML = `
      <span>⚖️ <strong>${ids.length}</strong> product${ids.length > 1 ? 's' : ''} in comparison</span>
      <a href="/comparison" style="background:#7c3aed; color:#fff; padding:6px 14px; border-radius:20px; text-decoration:none; font-weight:700; font-size:12px; box-shadow:0 2px 8px rgba(0,0,0,0.2);">Compare Now ➔</a>
      <button onclick="clearAllComparisonGlobal()" style="background:none; border:none; color:#cbd5e1; cursor:pointer; font-size:12px; text-decoration:underline;">Clear</button>
    `;
    widget.style.display = 'flex';
  } else if (widget) {
    widget.style.display = 'none';
  }
}

// ---------------------------------------------------------------------------
// 9. Initialisation on Page Load
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  // Sync Saved User & Auth Status from Server
  await checkAuthStatus();

  updateCartBadge();
  updateComparisonUI();
  const list = getWishlist();
  const countEl = document.getElementById('menuWishlistCount');
  if (countEl) countEl.textContent = list.length;

  // Load products for search autocomplete and initial state
  try {
    const data = await apiGet('/api/products?limit=100');
    allCatalogProducts = data.products || [];
    allCatalogProducts.forEach(registerProduct);
  } catch (e) {
    console.error('Failed to pre-fetch products:', e);
  }

  initBannerCarousel();
});

// ===========================================================================
// PRETWIN LOCATION ACCESS & SELECTOR
// ===========================================================================
const PRETWIN_LOC_KEY = 'pretwin_delivery_location';

function loadSavedLocation() {
  const textEl = document.getElementById('pretwinNavLocationText');
  const stored = localStorage.getItem(PRETWIN_LOC_KEY);
  if (textEl) {
    textEl.textContent = stored ? stored : 'Select location';
  }
}

function toggleLocationModal(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const modal = document.getElementById('pretwinLocationModal');
  const backdrop = document.getElementById('pretwinLocationBackdrop');
  if (!modal) return;
  const isHidden = modal.style.display === 'none' || !modal.style.display;
  if (isHidden) {
    closeAllNavDropdowns();
    modal.style.display = 'block';
    if (backdrop) backdrop.style.display = 'block';
    const inp = document.getElementById('manualLocationInput');
    if (inp) inp.focus();
  } else {
    closeLocationModal();
  }
}

function closeLocationModal() {
  const modal = document.getElementById('pretwinLocationModal');
  const backdrop = document.getElementById('pretwinLocationBackdrop');
  if (modal) modal.style.display = 'none';
  if (backdrop) backdrop.style.display = 'none';
}

function applyManualLocation(e) {
  if (e) e.preventDefault();
  const inp = document.getElementById('manualLocationInput');
  if (!inp || !inp.value.trim()) return;
  const val = inp.value.trim();
  localStorage.setItem(PRETWIN_LOC_KEY, val);
  const textEl = document.getElementById('pretwinNavLocationText');
  if (textEl) textEl.textContent = val;
  if (typeof showToast === 'function') {
    showToast(`Delivery location set to ${val}`, 'success');
  }
  closeLocationModal();
}

function requestBrowserLocation() {
  const statusMsg = document.getElementById('locStatusMessage');
  if (!navigator.geolocation) {
    if (statusMsg) {
      statusMsg.style.display = 'block';
      statusMsg.style.background = '#fef2f2';
      statusMsg.style.color = '#991b1b';
      statusMsg.style.border = '1px solid #fecaca';
      statusMsg.textContent = 'Geolocation is not supported by your browser. Please enter your city or PIN code manually.';
    }
    return;
  }

  if (statusMsg) {
    statusMsg.style.display = 'block';
    statusMsg.style.background = '#eff6ff';
    statusMsg.style.color = '#1e40af';
    statusMsg.style.border = '1px solid #bfdbfe';
    statusMsg.textContent = 'Detecting location... Please confirm browser permission.';
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude.toFixed(2);
      const lon = position.coords.longitude.toFixed(2);
      const locLabel = `GPS (${lat}, ${lon})`;
      localStorage.setItem(PRETWIN_LOC_KEY, locLabel);
      const textEl = document.getElementById('pretwinNavLocationText');
      if (textEl) textEl.textContent = locLabel;
      if (statusMsg) {
        statusMsg.style.background = '#f0fdf4';
        statusMsg.style.color = '#166534';
        statusMsg.style.border = '1px solid #bbf7d0';
        statusMsg.textContent = `Location updated: ${locLabel}`;
      }
      if (typeof showToast === 'function') {
        showToast('Location updated via browser GPS', 'success');
      }
      setTimeout(closeLocationModal, 800);
    },
    (err) => {
      let errText = 'Location permission was denied or unavailable. Please enter your city or PIN code manually.';
      if (err.code === err.PERMISSION_DENIED) {
        errText = 'Location permission was denied. You can still enter your city or PIN code manually below.';
      }
      if (statusMsg) {
        statusMsg.style.display = 'block';
        statusMsg.style.background = '#fef2f2';
        statusMsg.style.color = '#991b1b';
        statusMsg.style.border = '1px solid #fecaca';
        statusMsg.textContent = errText;
      }
    },
    { timeout: 10000, enableHighAccuracy: false }
  );
}

// ===========================================================================
// PRETWIN NAVBAR DROPDOWNS (Features, Notifications, More)
// ===========================================================================
function closeAllNavDropdowns() {
  document.querySelectorAll('.pretwin-features-dropdown, .pretwin-notif-dropdown, .pretwin-more-dropdown, .pretwin-account-dropdown').forEach(el => {
    el.classList.remove('is-open');
  });
  document.querySelectorAll('[aria-expanded="true"]').forEach(el => {
    el.setAttribute('aria-expanded', 'false');
  });
}

function toggleFeaturesMenu(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const dropdown = document.getElementById('pretwinFeaturesDropdown');
  const btn = document.getElementById('pretwinFeaturesBtn');
  if (!dropdown) return;
  const isOpen = dropdown.classList.contains('is-open');
  closeAllNavDropdowns();
  if (!isOpen) {
    dropdown.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

function toggleNotificationsMenu(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const dropdown = document.getElementById('pretwinNotificationsDropdown');
  const btn = document.getElementById('pretwinNotificationsBtn');
  if (!dropdown) return;
  const isOpen = dropdown.classList.contains('is-open');
  closeAllNavDropdowns();
  if (!isOpen) {
    dropdown.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

function toggleMoreMenu(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const dropdown = document.getElementById('pretwinMoreDropdown');
  const btn = document.getElementById('pretwinMoreBtn');
  if (!dropdown) return;
  const isOpen = dropdown.classList.contains('is-open');
  closeAllNavDropdowns();
  if (!isOpen) {
    dropdown.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

function toggleNav2MoreMenu(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const dropdown = document.getElementById('nav2MoreDropdown');
  const btn = document.getElementById('nav2MoreBtn');
  if (!dropdown) return;
  const isOpen = dropdown.classList.contains('is-open');
  closeAllNavDropdowns();
  if (!isOpen) {
    dropdown.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

function toggleNav2AccountDropdown(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const dropdown = document.getElementById('nav2AccountDropdown');
  const btn = document.getElementById('nav2ProfileBtn');
  if (!dropdown) return;
  const isOpen = dropdown.classList.contains('is-open');
  closeAllNavDropdowns();
  if (!isOpen) {
    dropdown.classList.add('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
}

// Global outside-click listener for all dropdowns & location modal
document.addEventListener('click', (e) => {
  const containers = [
    document.getElementById('pretwinFeaturesContainer'),
    document.getElementById('pretwinNotificationsContainer'),
    document.getElementById('pretwinMoreContainer'),
    document.getElementById('pretwinAccountItem'),
    document.getElementById('pretwinLocationContainer'),
    document.getElementById('nav2MoreContainer'),
    document.getElementById('nav2AccountItem')
  ];

  const clickedInside = containers.some(c => c && c.contains(e.target));
  if (!clickedInside) {
    closeAllNavDropdowns();
  }
});

// Escape key listener
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' || e.key === 'Esc') {
    closeAllNavDropdowns();
    closeLocationModal();
  }
});

// Scroll reveal observer for subtle fade-up animations
function initScrollReveal() {
  const revealElements = document.querySelectorAll('.pretwin-reveal-on-scroll, .feature-card, .features-hero-header');
  if (!revealElements.length) return;

  if (typeof IntersectionObserver === 'undefined') {
    revealElements.forEach(el => el.classList.add('is-revealed'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -20px 0px' });

  revealElements.forEach(el => {
    if (!el.classList.contains('pretwin-reveal-on-scroll')) {
      el.classList.add('pretwin-reveal-on-scroll');
    }
    observer.observe(el);
  });
}

// Initialize Location and Animations on load
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    loadSavedLocation();
    initScrollReveal();
  });
}
