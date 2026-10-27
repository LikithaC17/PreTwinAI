/**
 * FLIPKART HOMEPAGE CONTROLLER
 * Loads product data into horizontal deal carousels for all 20 categories and featured shelf
 */

async function loadHomepage() {
  try {
    // Fetch products catalogue (covers all 20 categories)
    const res = await apiGet('/api/products?limit=1100');
    const products = res.products || [];
    allCatalogProducts = products;

    // Register all products into the global catalog map for modal and cart actions
    window.catalogMap = window.catalogMap || {};
    products.forEach((p) => {
      window.catalogMap[p.id] = p;
    });

    // Configuration of tracks for all categories with custom deal badges
    const categoryTrackConfigs = [
      {
        trackId: 'mobilesTrack',
        category: 'Mobiles',
        offers: ['Min. ₹3,000 Off', 'Top Rated 5G', 'Best Seller', 'Exchange Offer', 'No Cost EMI']
      },
      {
        trackId: 'electronicsTrack',
        category: 'Electronics',
        offers: ['Up to 70% Off', 'Special Deal', 'Min. 40% Off', 'Trending Choice', 'Best Audio']
      },
      {
        trackId: 'laptopsTrack',
        category: 'Laptops & Computers',
        offers: ['From ₹29,990', 'Intel Core i5/i7', 'Gaming Deals', 'Thin & Light', 'Extra ₹2000 Off']
      },
      {
        trackId: 'tvsTrack',
        category: 'TVs & Home Entertainment',
        offers: ['4K Smart TVs', 'From ₹12,999', 'Dolby Audio', 'Min. 45% Off', 'Free Installation']
      },
      {
        trackId: 'fashionTrack',
        category: 'Fashion',
        offers: ['Min. 60% Off', 'Under ₹999', 'Trending Now', 'Fresh Season', 'Hot Styles']
      },
      {
        trackId: 'footwearTrack',
        category: 'Footwear',
        offers: ['Under ₹1,499', 'Min. 50% Off', 'Running & Casual', 'Puma, Nike & more', 'Best Picks']
      },
      {
        trackId: 'watchesTrack',
        category: 'Watches & Accessories',
        offers: ['Min. 40% Off', 'Smart & Analog', 'Starting ₹799', 'Premium Picks', 'Water Resistant']
      },
      {
        trackId: 'homeTrack',
        category: 'Home & Kitchen',
        offers: ['Starting ₹299', 'Min. 50% Off', 'Top Kitchenware', 'Best Deals', '100% Cotton']
      },
      {
        trackId: 'furnitureTrack',
        category: 'Furniture',
        offers: ['Min. 40% Off', 'Solid Wood', 'Free Assembly', 'Trending Sofas', 'Ergonomic']
      },
      {
        trackId: 'appliancesTrack',
        category: 'Appliances',
        offers: ['Energy Efficient', 'Up to 55% Off', 'Exchange Offer', 'Top Brands', '5-Star Rated']
      },
      {
        trackId: 'beautyTrack',
        category: 'Beauty, Toys & More',
        offers: ['Buy 1 Get 1', 'Min. 35% Off', 'Top Rated', 'From ₹199', 'Dermat Tested']
      },
      {
        trackId: 'personalCareTrack',
        category: 'Personal Care',
        offers: ['Dermatologist Pick', 'Min. 40% Off', 'Grooming Essentials', 'Daily Care', 'Salon Finish']
      },
      {
        trackId: 'toysTrack',
        category: 'Toys & Baby Products',
        offers: ['Age 0-12 yrs', 'Min. 45% Off', 'Safe & Non-Toxic', 'Creative Play', 'STEM Toys']
      },
      {
        trackId: 'groceryTrack',
        category: 'Food & Grocery',
        offers: ['Daily Staples', 'Min. 25% Off', 'Farm Fresh', 'Combo Packs', 'Organic']
      },
      {
        trackId: 'sportsTrack',
        category: 'Sports & Fitness',
        offers: ['Fitness Special', 'Min. 35% Off', 'Gym Gear', 'Starting ₹299', 'Heavy Duty']
      },
      {
        trackId: 'booksTrack',
        category: 'Books & Stationery',
        offers: ['Bestsellers', 'Min. 30% Off', 'Starting ₹99', 'School & Office', 'Editor Choice']
      },
      {
        trackId: 'healthTrack',
        category: 'Health & Wellness',
        offers: ['AYUSH Certified', 'Min. 30% Off', 'Daily Vitamins', 'Healthy Living', 'Pure Extracts']
      },
      {
        trackId: 'travelTrack',
        category: 'Travel & Luggage',
        offers: ['Hard & Soft Trolleys', 'Min. 60% Off', 'Starting ₹1,299', 'Cabin Bags', 'TSA Lock']
      },
      {
        trackId: 'automotiveTrack',
        category: 'Automotive Accessories',
        offers: ['Car Care', 'Starting ₹199', 'Min. 40% Off', 'Helmet & Bike', 'High Durability']
      },
      {
        trackId: 'petsTrack',
        category: 'Pet Supplies',
        offers: ['Nutritious Food', 'Min. 30% Off', 'Toys & Grooming', 'Pet Parent Choice', 'Vet Recommended']
      }
    ];

    // Populate each category deal track
    categoryTrackConfigs.forEach((cfg) => {
      const catProducts = products.filter((p) => p.category === cfg.category);
      renderTrack(cfg.trackId, catProducts.length > 0 ? catProducts : products.slice(0, 10), cfg.offers);
    });

    // Render Featured Shelf (24 top picks across entire catalogue)
    renderFeaturedGrid('featuredGrid', products.slice(0, 24));

    updateWishlistIcons();
  } catch (err) {
    console.error('Failed to load homepage products:', err);
  }
}

function renderTrack(containerId, items, offerLabels) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = '<p style="padding:20px; color:#878787;">Loading PreTwin deals...</p>';
    return;
  }

  container.innerHTML = items.map((p, idx) => {
    const offer = offerLabels[idx % offerLabels.length];
    return createFlipkartCardHtml(p, offer);
  }).join('');
}

function renderFeaturedGrid(containerId, items) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = items.map((p) => {
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
          <span class="fk-rating-badge">${(p.rating || 4.3).toFixed(1)} ★</span>
          <span style="color:#2874f0; font-size:11px; font-weight:700; margin-left:6px;">PreTwin Assured</span>
        </div>

        <div class="fk-card-price-row">
          <span class="fk-card-curr-price">${formatPrice(p.price)}</span>
          <span class="fk-card-mrp">${formatPrice(originalMrp)}</span>
          <span style="color:var(--fk-green); font-size:12px; font-weight:600;">${discPct}% off</span>
        </div>

        <div class="fk-card-sub">
          ${p.brand ? p.brand + ' • ' : ''}${p.category}
        </div>

        <div class="fk-card-quick-add" onclick="event.stopPropagation()">
          <button class="fk-btn-add" onclick="addToCartById(${p.id})">
            ADD TO CART
          </button>
        </div>
      </div>
    `;
  }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  loadHomepage();
});
