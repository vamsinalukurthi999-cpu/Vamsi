/**
 * Flower Shop Management System - Single Page Application Controller
 * High-performance, clean vanilla JS client interacting with Python REST API.
 */

// Application State
const state = {
  token: localStorage.getItem('flowershop_token') || null,
  user: null,
  activeView: 'catalog',
  flowers: [],
  categories: [],
  cart: JSON.parse(localStorage.getItem('flowershop_cart') || '[]'),
  currentFilters: {
    category: '',
    color: '',
    occasion: '',
    search: '',
    sort: 'name_asc',
    in_stock: false
  },
  activeCoupon: null,
  activeAdminTab: 'flowers'
};

// Flower SVG placeholders with colors for 100% offline visual presentation
const FLOWER_SVGS = {
  Red: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#ff4d4f" opacity="0.15"/><path d="M50 20 C60 10, 80 20, 75 40 C85 50, 75 75, 50 80 C25 75, 15 50, 25 40 C20 20, 40 10, 50 20 Z" fill="#e03131"/><circle cx="50" cy="50" r="14" fill="#c92a2a"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`,
  Pink: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#f783ac" opacity="0.15"/><path d="M50 20 C65 15, 80 30, 75 50 C80 70, 65 80, 50 80 C35 80, 20 70, 25 50 C20 30, 35 15, 50 20 Z" fill="#f06595"/><circle cx="50" cy="50" r="14" fill="#d6336c"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`,
  Purple: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#da77f2" opacity="0.15"/><path d="M50 15 C70 15, 85 35, 75 55 C85 75, 60 85, 50 80 C40 85, 15 75, 25 55 C15 35, 30 15, 50 15 Z" fill="#ae3ec9"/><circle cx="50" cy="50" r="14" fill="#862e9c"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`,
  White: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#e9ecef" opacity="0.5"/><path d="M50 20 C60 10, 80 20, 75 40 C85 50, 75 75, 50 80 C25 75, 15 50, 25 40 C20 20, 40 10, 50 20 Z" fill="#f8f9fa" stroke="#ced4da" stroke-width="2"/><circle cx="50" cy="50" r="14" fill="#ffd43b"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`,
  Yellow: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#ffe066" opacity="0.25"/><path d="M50 20 C65 15, 80 30, 75 50 C80 70, 65 80, 50 80 C35 80, 20 70, 25 50 C20 30, 35 15, 50 20 Z" fill="#fcc419"/><circle cx="50" cy="50" r="14" fill="#e8590c"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`,
  Blue: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#74c0fc" opacity="0.2"/><path d="M50 20 C65 15, 80 30, 75 50 C80 70, 65 80, 50 80 C35 80, 20 70, 25 50 C20 30, 35 15, 50 20 Z" fill="#339af0"/><circle cx="50" cy="50" r="14" fill="#1c7ed6"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`,
  Mixed: `<svg viewBox="0 0 100 100" width="120" height="120"><circle cx="50" cy="50" r="40" fill="#ffdeeb" opacity="0.3"/><path d="M35 35 C45 20, 60 25, 55 45 C45 55, 30 50, 35 35 Z" fill="#f06595"/><path d="M65 40 C75 25, 90 35, 80 55 C70 65, 55 55, 65 40 Z" fill="#ae3ec9"/><path d="M45 65 C35 80, 55 90, 65 75 C75 60, 55 55, 45 65 Z" fill="#ff922b"/><circle cx="50" cy="50" r="10" fill="#ffd43b"/><path d="M50 80 Q50 95 45 100" stroke="#2b8a3e" stroke-width="4" fill="none"/></svg>`
};

// ==================== API UTILITIES ====================

async function api(path, method = 'GET', data = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  const opts = { method, headers };
  if (data !== null) {
    opts.body = JSON.stringify(data);
  }

  try {
    const res = await fetch(path, opts);
    const json = await res.json();
    if (!res.ok) {
      throw new Error(json.error || `Error ${res.status}: ${res.statusText}`);
    }
    return json;
  } catch (err) {
    console.error(`API Error on ${method} ${path}:`, err);
    throw err;
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '❌';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function saveCart() {
  localStorage.setItem('flowershop_cart', JSON.stringify(state.cart));
  updateCartBadge();
}

function updateCartBadge() {
  const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  const badge = document.getElementById('cartBadge');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-block' : 'none';
  }
}

// ==================== AUTHENTICATION ====================

async function checkAuth() {
  if (!state.token) {
    updateAuthUI();
    return;
  }
  try {
    const res = await api('/api/auth/me');
    if (res.success && res.user) {
      state.user = res.user;
    } else {
      state.token = null;
      state.user = null;
      localStorage.removeItem('flowershop_token');
    }
  } catch (e) {
    state.token = null;
    state.user = null;
    localStorage.removeItem('flowershop_token');
  }
  updateAuthUI();
}

async function loginUser(email, password, role = '') {
  try {
    const res = await api('/api/auth/login', 'POST', { email, password, role });
    if (res.success) {
      state.token = res.token;
      state.user = res.user;
      localStorage.setItem('flowershop_token', res.token);
      showToast(`Welcome back, ${res.user.name}! (${res.user.role})`, 'success');
      closeModal('authModal');
      updateAuthUI();
      if (res.user.role === 'Admin') switchView('admin-portal');
      else if (res.user.role === 'Florist') switchView('staff-portal');
      else if (res.user.role === 'Delivery') switchView('delivery-portal');
      else switchView('catalog');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function registerCustomer(name, email, password, phone, address) {
  try {
    const res = await api('/api/auth/register', 'POST', { name, email, password, phone, address });
    if (res.success) {
      state.token = res.token;
      state.user = res.user;
      localStorage.setItem('flowershop_token', res.token);
      showToast(res.message, 'success');
      closeModal('authModal');
      updateAuthUI();
      switchView('catalog');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function logoutUser() {
  try {
    await api('/api/auth/logout', 'POST');
  } catch (e) {}
  state.token = null;
  state.user = null;
  localStorage.removeItem('flowershop_token');
  showToast('Logged out successfully', 'info');
  updateAuthUI();
  switchView('catalog');
}

async function quickLogin(role) {
  const credentials = {
    admin: { email: 'admin@flowershop.com', pass: 'admin123', role: 'Admin' },
    florist: { email: 'florist@flowershop.com', pass: 'staff123', role: 'Florist' },
    delivery: { email: 'delivery@flowershop.com', pass: 'delivery123', role: 'Delivery' },
    customer: { email: 'ananya@example.com', pass: 'customer123', role: 'Customer' }
  };
  const cred = credentials[role.toLowerCase()];
  if (cred) {
    await loginUser(cred.email, cred.pass, cred.role);
  }
}

function updateAuthUI() {
  const user = state.user;
  const userGreeting = document.getElementById('userGreeting');
  const loginBtn = document.getElementById('loginNavBtn');
  const logoutBtn = document.getElementById('logoutNavBtn');
  const staffPortalLink = document.getElementById('navStaffPortal');
  const deliveryPortalLink = document.getElementById('navDeliveryPortal');
  const adminPortalLink = document.getElementById('navAdminPortal');
  const myOrdersLink = document.getElementById('navMyOrders');
  const loyaltyBadge = document.getElementById('loyaltyBadge');

  if (user) {
    userGreeting.innerHTML = `<strong>${user.name}</strong> <span class="badge badge-primary">${user.role}</span>`;
    userGreeting.style.display = 'inline-flex';
    loginBtn.style.display = 'none';
    logoutBtn.style.display = 'inline-flex';

    if (user.role === 'Customer') {
      myOrdersLink.style.display = 'inline-flex';
      loyaltyBadge.style.display = 'inline-flex';
      loyaltyBadge.textContent = `⭐ ${user.loyalty_points || 0} pts`;
      staffPortalLink.style.display = 'none';
      deliveryPortalLink.style.display = 'none';
      adminPortalLink.style.display = 'none';
    } else {
      loyaltyBadge.style.display = 'none';
      myOrdersLink.style.display = 'none';
      staffPortalLink.style.display = (user.role === 'Florist' || user.role === 'Admin') ? 'inline-flex' : 'none';
      deliveryPortalLink.style.display = (user.role === 'Delivery' || user.role === 'Admin') ? 'inline-flex' : 'none';
      adminPortalLink.style.display = (user.role === 'Admin') ? 'inline-flex' : 'none';
    }
  } else {
    userGreeting.style.display = 'none';
    loyaltyBadge.style.display = 'none';
    loginBtn.style.display = 'inline-flex';
    logoutBtn.style.display = 'none';
    myOrdersLink.style.display = 'none';
    staffPortalLink.style.display = 'none';
    deliveryPortalLink.style.display = 'none';
    adminPortalLink.style.display = 'none';
  }

  document.querySelectorAll('.demo-pill').forEach(pill => {
    pill.classList.remove('active');
    if (user && pill.dataset.role && pill.dataset.role.toLowerCase() === user.role.toLowerCase()) {
      pill.classList.add('active');
    }
  });
}

// ==================== VIEW ROUTER ====================

function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll('.view-section').forEach(sec => sec.style.display = 'none');
  document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));

  const activeSec = document.getElementById(`view-${viewName}`);
  if (activeSec) activeSec.style.display = 'block';

  const navLink = document.querySelector(`[data-view="${viewName}"]`);
  if (navLink) navLink.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (viewName === 'catalog') {
    loadCatalog();
  } else if (viewName === 'my-orders') {
    loadCustomerOrders();
  } else if (viewName === 'staff-portal') {
    loadStaffPortal();
  } else if (viewName === 'delivery-portal') {
    loadDeliveryPortal();
  } else if (viewName === 'admin-portal') {
    loadAdminDashboard();
  }
}

// ==================== CATALOG & FLOWERS ====================

async function loadCategories() {
  try {
    const res = await api('/api/categories');
    if (res.success) {
      state.categories = res.categories;
      renderCategoryChips();
      populateCategoryDropdowns();
    }
  } catch (e) {
    console.error('Failed to load categories', e);
  }
}

function renderCategoryChips() {
  const container = document.getElementById('categoryChips');
  if (!container) return;

  let html = `<button class="category-chip ${state.currentFilters.category === '' ? 'active' : ''}" onclick="filterByCategory('')">All Flowers</button>`;
  state.categories.forEach(cat => {
    const isActive = state.currentFilters.category === cat.category_name;
    html += `<button class="category-chip ${isActive ? 'active' : ''}" onclick="filterByCategory('${cat.category_name}')">${cat.category_name} (${cat.flower_count})</button>`;
  });
  container.innerHTML = html;
}

function populateCategoryDropdowns() {
  const selects = document.querySelectorAll('.category-select');
  selects.forEach(select => {
    let html = select.dataset.allowAll ? '<option value="">All Categories</option>' : '';
    state.categories.forEach(c => {
      html += `<option value="${c.category_id}">${c.category_name}</option>`;
    });
    select.innerHTML = html;
  });
}

async function loadCatalog() {
  const params = new URLSearchParams();
  if (state.currentFilters.category) params.append('category', state.currentFilters.category);
  if (state.currentFilters.color) params.append('color', state.currentFilters.color);
  if (state.currentFilters.occasion) params.append('occasion', state.currentFilters.occasion);
  if (state.currentFilters.search) params.append('search', state.currentFilters.search);
  if (state.currentFilters.sort) params.append('sort', state.currentFilters.sort);
  if (state.currentFilters.in_stock) params.append('in_stock', '1');

  try {
    const res = await api(`/api/flowers?${params.toString()}`);
    if (res.success) {
      state.flowers = res.flowers;
      renderFlowerGrid(res.flowers);
    }
  } catch (err) {
    showToast('Failed to load flower catalog', 'error');
  }
}

function renderFlowerGrid(flowers) {
  const grid = document.getElementById('flowerGrid');
  if (!grid) return;

  if (flowers.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3rem 1rem; background: #fff; border-radius: 12px; border: 1px dashed #ced4da;">
        <span style="font-size: 3rem;">🥀</span>
        <h3 style="margin-top: 0.5rem; color: #495057;">No flowers found</h3>
        <p style="color: #868e96;">Try adjusting your filters or search keywords.</p>
        <button class="btn btn-outline-primary" style="margin-top: 1rem;" onclick="resetFilters()">Reset All Filters</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = flowers.map(f => {
    const isLowStock = f.stock_qty > 0 && f.stock_qty < 10;
    const isOutOfStock = f.stock_qty <= 0;
    let stockBadge = `<span class="flower-badge-stock badge-success">✓ In Stock (${f.stock_qty})</span>`;
    if (isLowStock) {
      stockBadge = `<span class="flower-badge-stock badge-warning">⚠️ Low Stock (${f.stock_qty} left)</span>`;
    } else if (isOutOfStock) {
      stockBadge = `<span class="flower-badge-stock badge-danger">Out of Stock</span>`;
    }

    const svgIcon = FLOWER_SVGS[f.color] || FLOWER_SVGS['Mixed'];

    return `
      <div class="flower-card">
        <div class="flower-image-box">
          ${svgIcon}
          ${stockBadge}
          <span class="flower-badge-category">${f.category_name}</span>
        </div>
        <div class="flower-body">
          <div class="flower-title">${f.name}</div>
          <div class="flower-meta">
            <span class="color-dot" style="background: ${getColorHex(f.color)};"></span>
            <span>${f.color}</span> • <span>${f.occasion}</span>
          </div>
          <div class="flower-description">${f.description || 'Fresh premium flower arrangement carefully arranged by expert florists.'}</div>
          <div class="flower-footer">
            <div class="flower-price">₹${f.price.toFixed(2)}</div>
            <div style="display: flex; gap: 0.4rem;">
              <button class="btn btn-sm btn-secondary" onclick="openFlowerDetail(${f.flower_id})">Details</button>
              <button class="btn btn-sm btn-primary" ${isOutOfStock ? 'disabled' : ''} onclick="addToCart(${f.flower_id})">
                ${isOutOfStock ? 'Sold Out' : '🛒 Add'}
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function getColorHex(color) {
  const map = {
    Red: '#e03131',
    Pink: '#f06595',
    Purple: '#ae3ec9',
    White: '#e9ecef',
    Yellow: '#fcc419',
    Blue: '#339af0',
    Mixed: '#ff922b'
  };
  return map[color] || '#ced4da';
}

function filterByCategory(catName) {
  state.currentFilters.category = catName;
  renderCategoryChips();
  loadCatalog();
}

function resetFilters() {
  state.currentFilters = {
    category: '',
    color: '',
    occasion: '',
    search: '',
    sort: 'name_asc',
    in_stock: false
  };
  document.getElementById('searchInput').value = '';
  document.getElementById('colorFilter').value = '';
  document.getElementById('occasionFilter').value = '';
  document.getElementById('sortSelect').value = 'name_asc';
  document.getElementById('inStockFilter').checked = false;
  renderCategoryChips();
  loadCatalog();
}

function openFlowerDetail(flowerId) {
  const flower = state.flowers.find(f => f.flower_id === flowerId);
  if (!flower) return;

  const content = document.getElementById('flowerModalContent');
  content.innerHTML = `
    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
      <div style="flex: 1; min-width: 200px; text-align: center; background: #fff0f6; border-radius: 12px; padding: 1.5rem;">
        ${FLOWER_SVGS[flower.color] || FLOWER_SVGS['Mixed']}
      </div>
      <div style="flex: 1.5; min-width: 250px;">
        <span class="badge badge-primary">${flower.category_name}</span>
        <h2 style="margin: 0.5rem 0; color: #212529;">${flower.name}</h2>
        <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary-dark); margin-bottom: 0.75rem;">₹${flower.price.toFixed(2)}</div>
        <p style="color: #495057; margin-bottom: 1rem;">${flower.description}</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; background: #f8f9fa; padding: 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1rem;">
          <div><strong>Color:</strong> ${flower.color}</div>
          <div><strong>Occasion:</strong> ${flower.occasion}</div>
          <div><strong>Stock Quantity:</strong> ${flower.stock_qty} available</div>
          <div><strong>Supplier:</strong> ${flower.supplier_name || 'Bloomfield Flora'}</div>
        </div>
        <button class="btn btn-primary btn-lg" style="width: 100%;" ${flower.stock_qty <= 0 ? 'disabled' : ''} onclick="addToCart(${flower.flower_id}); closeModal('flowerModal');">
          ${flower.stock_qty <= 0 ? 'Out of Stock' : '🛒 Add to Basket'}
        </button>
      </div>
    </div>
  `;
  openModal('flowerModal');
}

// ==================== CART & CHECKOUT ====================

function addToCart(flowerId) {
  const flower = state.flowers.find(f => f.flower_id === flowerId);
  if (!flower) return;

  const existing = state.cart.find(item => item.flower_id === flowerId);
  const currentInCart = existing ? existing.quantity : 0;

  if (currentInCart + 1 > flower.stock_qty) {
    showToast(`Sorry, only ${flower.stock_qty} available in stock!`, 'error');
    return;
  }

  if (existing) {
    existing.quantity += 1;
  } else {
    state.cart.push({
      flower_id: flower.flower_id,
      name: flower.name,
      price: flower.price,
      quantity: 1,
      stock_qty: flower.stock_qty,
      color: flower.color,
      category_name: flower.category_name
    });
  }

  saveCart();
  showToast(`Added '${flower.name}' to cart!`, 'success');
}

function updateCartQuantity(flowerId, change) {
  const item = state.cart.find(i => i.flower_id === flowerId);
  if (!item) return;

  const newQty = item.quantity + change;
  if (newQty <= 0) {
    state.cart = state.cart.filter(i => i.flower_id !== flowerId);
  } else {
    if (newQty > item.stock_qty) {
      showToast(`Cannot order more than available stock (${item.stock_qty})`, 'error');
      return;
    }
    item.quantity = newQty;
  }
  saveCart();
  renderCartModal();
}

function openCartModal() {
  renderCartModal();
  openModal('cartModal');
}

function renderCartModal() {
  const container = document.getElementById('cartItemsList');
  const subtotalEl = document.getElementById('cartSubtotal');
  const deliveryEl = document.getElementById('cartDelivery');
  const discountEl = document.getElementById('cartDiscount');
  const totalEl = document.getElementById('cartTotal');
  const checkoutBtn = document.getElementById('checkoutBtn');

  if (state.cart.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem 1rem;">
        <span style="font-size: 2.5rem;">🛒</span>
        <h4 style="margin-top: 0.5rem; color: #495057;">Your Cart is Empty</h4>
        <p style="color: #868e96; font-size: 0.9rem;">Browse our collection of fresh floral blossoms to add items.</p>
        <button class="btn btn-outline-primary" style="margin-top: 1rem;" onclick="closeModal('cartModal'); switchView('catalog');">Start Shopping</button>
      </div>
    `;
    subtotalEl.textContent = '₹0.00';
    deliveryEl.textContent = '₹0.00';
    discountEl.textContent = '₹0.00';
    totalEl.textContent = '₹0.00';
    if (checkoutBtn) checkoutBtn.disabled = true;
    return;
  }

  if (checkoutBtn) checkoutBtn.disabled = false;

  let subtotal = 0;
  container.innerHTML = state.cart.map(item => {
    const itemSubtotal = item.price * item.quantity;
    subtotal += itemSubtotal;
    return `
      <div class="cart-item">
        <div class="cart-item-info">
          <div class="cart-item-name">${item.name}</div>
          <div class="cart-item-price">₹${item.price.toFixed(2)} each</div>
        </div>
        <div class="cart-qty-ctrl">
          <button class="qty-btn" onclick="updateCartQuantity(${item.flower_id}, -1)">-</button>
          <span style="font-weight: 700; min-width: 24px; text-align: center;">${item.quantity}</span>
          <button class="qty-btn" onclick="updateCartQuantity(${item.flower_id}, 1)">+</button>
        </div>
        <div style="font-weight: 700; min-width: 80px; text-align: right;">₹${itemSubtotal.toFixed(2)}</div>
        <button class="btn btn-sm btn-icon btn-secondary" onclick="updateCartQuantity(${item.flower_id}, -${item.quantity})">✕</button>
      </div>
    `;
  }).join('');

  const deliveryCharge = 50.0;
  let discount = 0.0;

  if (state.activeCoupon === 'FLOWER100') {
    discount = 100.0;
  } else if (state.activeCoupon === 'WELCOME20') {
    discount = Math.round(subtotal * 0.20);
  } else if (state.activeCoupon === 'FREESHIP') {
    discount = 50.0;
  }

  const grandTotal = Math.max(0, subtotal + deliveryCharge - discount);

  subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
  deliveryEl.textContent = `₹${deliveryCharge.toFixed(2)}`;
  discountEl.textContent = `-₹${discount.toFixed(2)}`;
  totalEl.textContent = `₹${grandTotal.toFixed(2)}`;
}

function applyCoupon() {
  const input = document.getElementById('couponCodeInput');
  const code = input.value.trim().toUpperCase();
  if (code === 'FLOWER100') {
    state.activeCoupon = code;
    showToast('Coupon FLOWER100 applied: ₹100 discount!', 'success');
  } else if (code === 'WELCOME20') {
    state.activeCoupon = code;
    showToast('Coupon WELCOME20 applied: 20% off!', 'success');
  } else if (code === 'FREESHIP') {
    state.activeCoupon = code;
    showToast('Coupon FREESHIP applied: Free Delivery!', 'success');
  } else {
    showToast('Invalid coupon code. Try FLOWER100 or WELCOME20', 'error');
    state.activeCoupon = null;
  }
  renderCartModal();
}

function proceedToCheckout() {
  if (!state.user) {
    showToast('Please login or register to complete your order', 'info');
    closeModal('cartModal');
    openModal('authModal');
    return;
  }

  document.getElementById('checkoutAddress').value = state.user.address || '';
  document.getElementById('checkoutRecipientName').value = state.user.name || '';
  document.getElementById('checkoutRecipientPhone').value = state.user.phone || '';

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('checkoutDate').value = tomorrow.toISOString().split('T')[0];

  closeModal('cartModal');
  openModal('checkoutModal');
}

async function placeOrder() {
  const address = document.getElementById('checkoutAddress').value.trim();
  const date = document.getElementById('checkoutDate').value;
  const timeSlot = document.getElementById('checkoutTimeSlot').value;
  const recipientName = document.getElementById('checkoutRecipientName').value.trim();
  const recipientPhone = document.getElementById('checkoutRecipientPhone').value.trim();
  const greeting = document.getElementById('checkoutGreeting').value.trim();
  const paymentMethod = document.getElementById('checkoutPaymentMethod').value;

  if (!address) {
    showToast('Please enter delivery address', 'error');
    return;
  }

  const payload = {
    items: state.cart.map(item => ({ flower_id: item.flower_id, quantity: item.quantity })),
    delivery_address: address,
    delivery_date: date,
    delivery_time_slot: timeSlot,
    recipient_name: recipientName,
    recipient_phone: recipientPhone,
    greeting_message: greeting,
    payment_method: paymentMethod,
    coupon_code: state.activeCoupon || ''
  };

  try {
    const res = await api('/api/orders', 'POST', payload);
    if (res.success) {
      showToast(res.message, 'success');
      state.cart = [];
      state.activeCoupon = null;
      saveCart();
      closeModal('checkoutModal');
      showInvoiceModal(res.order_id);
      loadCatalog();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== INVOICE & ORDER STATUS ====================

async function showInvoiceModal(orderId) {
  try {
    const res = await api(`/api/orders/${orderId}/invoice`);
    if (res.success) {
      renderInvoice(res.order);
      openModal('invoiceModal');
    }
  } catch (err) {
    showToast('Could not load invoice', 'error');
  }
}

function renderInvoice(order) {
  const container = document.getElementById('invoiceContent');
  container.innerHTML = `
    <div class="invoice-box">
      <div class="invoice-header">
        <div>
          <div class="invoice-title">🌸 BloomCraft Florals</div>
          <div style="font-size: 0.85rem; color: #6c757d;">Automated Flower Shop Management System</div>
          <div style="font-size: 0.85rem; color: #6c757d;">GSTIN: 29AAAAA0000A1Z5 | Ph: +91 98765 43210</div>
        </div>
        <div style="text-align: right;">
          <h2 style="color: var(--primary); margin: 0;">TAX INVOICE</h2>
          <div style="font-weight: 700; font-size: 1.1rem;">Order No: #${order.order_id}</div>
          <div style="font-size: 0.85rem; color: #6c757d;">Date: ${order.order_date}</div>
        </div>
      </div>

      <div class="invoice-details-grid">
        <div>
          <h4 style="color: #495057; margin-bottom: 0.3rem;">Billed & Delivered To:</h4>
          <div style="font-weight: 700;">${order.recipient_name || order.customer_name}</div>
          <div>${order.delivery_address}</div>
          <div>Phone: ${order.recipient_phone || order.customer_phone || 'N/A'}</div>
          <div>Email: ${order.customer_email || 'N/A'}</div>
        </div>
        <div style="text-align: right;">
          <h4 style="color: #495057; margin-bottom: 0.3rem;">Delivery & Payment Info:</h4>
          <div><strong>Delivery Date:</strong> ${order.delivery_date}</div>
          <div><strong>Time Slot:</strong> ${order.delivery_time_slot || 'Standard'}</div>
          <div><strong>Payment Method:</strong> ${order.payment_method}</div>
          <div><strong>Payment Status:</strong> <span class="badge ${order.payment_status === 'Paid' ? 'badge-success' : 'badge-warning'}">${order.payment_status}</span></div>
          <div><strong>Order Status:</strong> <span class="badge badge-primary">${order.status}</span></div>
        </div>
      </div>

      ${order.greeting_message ? `
        <div style="background: #fff0f6; border-left: 4px solid var(--primary); padding: 0.6rem 1rem; border-radius: 4px; margin-bottom: 1.2rem; font-style: italic;">
          💌 <strong>Gift Card Message:</strong> "${order.greeting_message}"
        </div>
      ` : ''}

      <table class="invoice-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Item Description</th>
            <th style="text-align: right;">Unit Price</th>
            <th style="text-align: center;">Qty</th>
            <th style="text-align: right;">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          ${order.items.map((item, idx) => `
            <tr>
              <td>${idx + 1}</td>
              <td><strong>${item.flower_name}</strong> <span style="font-size: 0.8rem; color: #868e96;">(${item.color})</span></td>
              <td style="text-align: right;">₹${item.unit_price.toFixed(2)}</td>
              <td style="text-align: center;">${item.quantity}</td>
              <td style="text-align: right;">₹${item.subtotal.toFixed(2)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>

      <div class="invoice-summary-box">
        <table class="invoice-summary-table">
          <tr>
            <td>Items Subtotal:</td>
            <td style="text-align: right; font-weight: 600;">₹${order.subtotal.toFixed(2)}</td>
          </tr>
          <tr>
            <td>Delivery Charge:</td>
            <td style="text-align: right; font-weight: 600;">₹${order.delivery_charge.toFixed(2)}</td>
          </tr>
          ${order.discount > 0 ? `
            <tr>
              <td>Discount Applied:</td>
              <td style="text-align: right; color: #2b8a3e; font-weight: 600;">-₹${order.discount.toFixed(2)}</td>
            </tr>
          ` : ''}
          <tr class="total-row">
            <td>Total Amount:</td>
            <td style="text-align: right;">₹${order.total_amount.toFixed(2)}</td>
          </tr>
        </table>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed #dee2e6; padding-top: 1rem; font-size: 0.85rem; color: #868e96;">
        <div>Thank you for choosing BloomCraft! Handcrafted with love & fresh dew.</div>
        <div style="font-family: monospace;">Ref: ${order.transaction_ref || 'TXN-GEN-' + order.order_id}</div>
      </div>
    </div>
  `;
}

// ==================== CUSTOMER ORDERS & LIVE TRACKING ====================

async function loadCustomerOrders() {
  if (!state.user) {
    switchView('catalog');
    return;
  }
  try {
    const res = await api('/api/orders');
    if (res.success) {
      renderCustomerOrders(res.orders);
    }
  } catch (err) {
    showToast('Failed to load orders', 'error');
  }
}

function renderCustomerOrders(orders) {
  const container = document.getElementById('customerOrdersList');
  if (!container) return;

  if (orders.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem; background: #fff; border-radius: 12px; border: 1px solid #dee2e6;">
        <span style="font-size: 3rem;">📦</span>
        <h3 style="margin-top: 0.5rem;">No orders placed yet</h3>
        <p style="color: #868e96;">Place your first flower order from our fresh catalog!</p>
        <button class="btn btn-primary" style="margin-top: 1rem;" onclick="switchView('catalog')">Explore Catalog</button>
      </div>
    `;
    return;
  }

  container.innerHTML = orders.map(ord => {
    return `
      <div style="background: #fff; border-radius: 12px; border: 1px solid #dee2e6; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; border-bottom: 1px solid #e9ecef; padding-bottom: 0.75rem;">
          <div>
            <span style="font-weight: 800; font-size: 1.15rem; color: var(--primary-dark);">Order #${ord.order_id}</span>
            <span style="font-size: 0.85rem; color: #6c757d; margin-left: 0.75rem;">Placed on: ${ord.order_date}</span>
          </div>
          <div>
            <span class="badge ${getStatusBadgeClass(ord.status)}">${ord.status}</span>
            <span class="badge ${ord.payment_status === 'Paid' ? 'badge-success' : 'badge-warning'}" style="margin-left: 0.4rem;">${ord.payment_status}</span>
          </div>
        </div>

        ${renderOrderPipeline(ord.status)}

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; margin: 1.2rem 0; flex-wrap: wrap;">
          <div>
            <h5 style="color: #495057; margin-bottom: 0.5rem;">Items:</h5>
            <ul style="list-style: none;">
              ${ord.items.map(it => `
                <li style="display: flex; justify-content: space-between; padding: 0.35rem 0; font-size: 0.9rem; border-bottom: 1px dotted #f1f3f5;">
                  <span>${it.quantity}x ${it.flower_name} (${it.color})</span>
                  <span style="font-weight: 600;">₹${it.subtotal.toFixed(2)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
          <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; font-size: 0.85rem;">
            <div><strong>Deliver to:</strong> ${ord.recipient_name || ord.customer_name}</div>
            <div><strong>Address:</strong> ${ord.delivery_address}</div>
            <div><strong>Scheduled:</strong> ${ord.delivery_date} (${ord.delivery_time_slot || 'Standard'})</div>
            ${ord.delivery_person_name ? `<div><strong>Delivery Agent:</strong> 🛵 ${ord.delivery_person_name}</div>` : ''}
            <div style="margin-top: 0.5rem; font-size: 1.05rem; font-weight: 800; color: var(--primary-dark);">Total: ₹${ord.total_amount.toFixed(2)}</div>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
          <button class="btn btn-outline-primary btn-sm" onclick="showInvoiceModal(${ord.order_id})">📄 View Invoice</button>
          ${(ord.status === 'Order Placed' || ord.status === 'Payment Confirmed') ? `
            <button class="btn btn-danger btn-sm" onclick="cancelOrder(${ord.order_id})">Cancel Order</button>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function renderOrderPipeline(currentStatus) {
  const steps = [
    { key: 'Order Placed', label: 'Order Placed', icon: '📝' },
    { key: 'Payment Confirmed', label: 'Payment Confirmed', icon: '💳' },
    { key: 'Preparing', label: 'Florist Preparing', icon: '💐' },
    { key: 'Out for Delivery', label: 'Out for Delivery', icon: '🛵' },
    { key: 'Delivered', label: 'Delivered', icon: '🎉' }
  ];

  if (currentStatus === 'Cancelled') {
    return `
      <div style="background: #ffe3e3; color: #c92a2a; padding: 0.75rem 1rem; border-radius: 8px; font-weight: 600; text-align: center; margin: 1rem 0;">
        ❌ This order was cancelled. Flower stock has been returned to inventory.
      </div>
    `;
  }

  const orderStateIndex = {
    'Order Placed': 0,
    'Payment Confirmed': 1,
    'Preparing': 2,
    'Ready': 2,
    'Out for Delivery': 3,
    'Delivered': 4
  }[currentStatus] ?? 0;

  return `
    <div class="order-pipeline">
      ${steps.map((st, idx) => {
        let cls = '';
        if (idx < orderStateIndex) cls = 'completed';
        else if (idx === orderStateIndex) cls = 'current';
        return `
          <div class="pipeline-step ${cls}">
            <div class="step-icon">${st.icon}</div>
            <div>${st.label}</div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function getStatusBadgeClass(status) {
  const map = {
    'Order Placed': 'badge-info',
    'Payment Confirmed': 'badge-info',
    'Preparing': 'badge-warning',
    'Ready': 'badge-warning',
    'Out for Delivery': 'badge-primary',
    'Delivered': 'badge-success',
    'Cancelled': 'badge-danger'
  };
  return map[status] || 'badge-primary';
}

async function cancelOrder(orderId) {
  if (!confirm(`Are you sure you want to cancel Order #${orderId}?`)) return;
  try {
    const res = await api(`/api/orders/${orderId}/status`, 'PUT', { status: 'Cancelled' });
    if (res.success) {
      showToast(res.message, 'info');
      loadCustomerOrders();
      loadCatalog();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== FLORIST / STAFF PORTAL ====================

async function loadStaffPortal() {
  try {
    const [ordersRes, flowersRes, staffRes] = await Promise.all([
      api('/api/orders'),
      api('/api/flowers'),
      api('/api/staff')
    ]);

    if (ordersRes.success) renderStaffOrders(ordersRes.orders, staffRes.staff || []);
    if (flowersRes.success) renderStaffInventory(flowersRes.flowers);
  } catch (err) {
    showToast('Failed to load staff portal data', 'error');
  }
}

function renderStaffOrders(orders, staffList) {
  const tbody = document.getElementById('staffOrdersTbody');
  if (!tbody) return;

  const deliveryStaff = staffList.filter(s => s.role === 'Delivery');

  tbody.innerHTML = orders.map(ord => {
    return `
      <tr>
        <td><strong>#${ord.order_id}</strong></td>
        <td>
          <div style="font-weight: 600;">${ord.customer_name}</div>
          <div style="font-size: 0.8rem; color: #868e96;">${ord.customer_phone || ''}</div>
        </td>
        <td>
          <span style="font-size: 0.85rem;">
            ${ord.items.map(i => `${i.quantity}x ${i.flower_name}`).join(', ')}
          </span>
        </td>
        <td>
          <div style="font-size: 0.85rem;">${ord.delivery_address}</div>
          <div style="font-size: 0.75rem; color: #868e96;">📅 ${ord.delivery_date}</div>
        </td>
        <td><span class="badge ${getStatusBadgeClass(ord.status)}">${ord.status}</span></td>
        <td>
          <select class="form-control" style="font-size: 0.8rem; padding: 0.2rem 0.4rem; width: 140px;" onchange="assignDeliveryStaff(${ord.order_id}, this.value)">
            <option value="">Select Rider</option>
            ${deliveryStaff.map(s => `
              <option value="${s.staff_id}" ${ord.delivery_staff_id == s.staff_id ? 'selected' : ''}>${s.name}</option>
            `).join('')}
          </select>
        </td>
        <td>
          <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
            ${ord.status === 'Order Placed' || ord.status === 'Payment Confirmed' ? `
              <button class="btn btn-sm btn-warning" onclick="updateOrderStatus(${ord.order_id}, 'Preparing')">Start Preparing</button>
            ` : ''}
            ${ord.status === 'Preparing' ? `
              <button class="btn btn-sm btn-primary" onclick="updateOrderStatus(${ord.order_id}, 'Ready')">Mark Ready</button>
            ` : ''}
            ${ord.status === 'Ready' ? `
              <button class="btn btn-sm btn-success" onclick="updateOrderStatus(${ord.order_id}, 'Out for Delivery')">Dispatch 🛵</button>
            ` : ''}
            <button class="btn btn-sm btn-secondary" onclick="showInvoiceModal(${ord.order_id})">Invoice</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderStaffInventory(flowers) {
  const tbody = document.getElementById('staffInventoryTbody');
  if (!tbody) return;

  tbody.innerHTML = flowers.map(f => {
    const isLow = f.stock_qty < 10;
    return `
      <tr style="${isLow ? 'background: #fff9db;' : ''}">
        <td><strong>${f.name}</strong></td>
        <td>${f.category_name}</td>
        <td>₹${f.price.toFixed(2)}</td>
        <td>
          <span style="font-weight: 700; color: ${isLow ? '#d9480f' : '#2b8a3e'};">
            ${f.stock_qty} ${isLow ? '⚠️ LOW' : ''}
          </span>
        </td>
        <td>
          <div style="display: flex; gap: 0.3rem;">
            <button class="btn btn-sm btn-secondary" onclick="quickRestock(${f.flower_id}, 10)">+10</button>
            <button class="btn btn-sm btn-secondary" onclick="quickRestock(${f.flower_id}, 25)">+25</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function updateOrderStatus(orderId, newStatus) {
  try {
    const res = await api(`/api/orders/${orderId}/status`, 'PUT', { status: newStatus });
    if (res.success) {
      showToast(res.message, 'success');
      loadStaffPortal();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function assignDeliveryStaff(orderId, staffId) {
  if (!staffId) return;
  try {
    const res = await api(`/api/orders/${orderId}/assign-delivery`, 'POST', { staff_id: staffId });
    if (res.success) {
      showToast('Delivery rider assigned!', 'success');
      loadStaffPortal();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function quickRestock(flowerId, addQty) {
  const flower = state.flowers.find(f => f.flower_id === flowerId);
  const current = flower ? flower.stock_qty : 0;
  try {
    const res = await api(`/api/flowers/${flowerId}`, 'PUT', { stock_qty: current + addQty });
    if (res.success) {
      showToast(`Restocked ${flower ? flower.name : 'item'} with +${addQty} flowers!`, 'success');
      loadStaffPortal();
      loadCatalog();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== DELIVERY PERSON PORTAL ====================

async function loadDeliveryPortal() {
  try {
    const res = await api('/api/orders');
    if (res.success) {
      renderDeliveryPortal(res.orders);
    }
  } catch (err) {
    showToast('Failed to load delivery runs', 'error');
  }
}

function renderDeliveryPortal(orders) {
  const container = document.getElementById('deliveryCardsList');
  if (!container) return;

  const activeDeliveries = orders.filter(o => o.status !== 'Cancelled');

  if (activeDeliveries.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem; background: #fff; border-radius: 12px; border: 1px solid #dee2e6;">
        <span style="font-size: 3rem;">🛵</span>
        <h3 style="margin-top: 0.5rem;">No active deliveries assigned</h3>
        <p style="color: #868e96;">Check back when orders are prepared and ready for dispatch.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = activeDeliveries.map(ord => {
    const isDone = ord.status === 'Delivered';
    return `
      <div style="background: #fff; border-radius: 12px; border: 1px solid #dee2e6; padding: 1.5rem; margin-bottom: 1.2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); ${isDone ? 'opacity: 0.8;' : ''}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
          <span style="font-weight: 800; font-size: 1.15rem;">Order #${ord.order_id}</span>
          <span class="badge ${getStatusBadgeClass(ord.status)}">${ord.status}</span>
        </div>
        <div style="margin-bottom: 0.75rem;">
          <div><strong>Recipient:</strong> ${ord.recipient_name || ord.customer_name} (${ord.recipient_phone || ord.customer_phone || 'No phone'})</div>
          <div><strong>Address:</strong> 📍 ${ord.delivery_address}</div>
          <div><strong>Scheduled Date:</strong> 📅 ${ord.delivery_date} (${ord.delivery_time_slot || 'Standard'})</div>
          ${ord.greeting_message ? `<div style="font-style: italic; color: #495057; margin-top: 0.3rem;">💌 "${ord.greeting_message}"</div>` : ''}
        </div>
        <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
          <a class="btn btn-sm btn-secondary" href="tel:${ord.recipient_phone || ord.customer_phone}">📞 Call Customer</a>
          ${ord.status !== 'Delivered' && ord.status !== 'Out for Delivery' ? `
            <button class="btn btn-sm btn-primary" onclick="updateOrderStatusDelivery(${ord.order_id}, 'Out for Delivery')">Start Delivery 🛵</button>
          ` : ''}
          ${ord.status === 'Out for Delivery' ? `
            <button class="btn btn-sm btn-success" onclick="updateOrderStatusDelivery(${ord.order_id}, 'Delivered')">Mark Delivered ✅</button>
          ` : ''}
          <button class="btn btn-sm btn-outline-primary" onclick="showInvoiceModal(${ord.order_id})">Invoice</button>
        </div>
      </div>
    `;
  }).join('');
}

async function updateOrderStatusDelivery(orderId, newStatus) {
  try {
    const res = await api(`/api/orders/${orderId}/status`, 'PUT', { status: newStatus });
    if (res.success) {
      showToast(res.message, 'success');
      loadDeliveryPortal();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== ADMINISTRATOR DASHBOARD ====================

async function loadAdminDashboard() {
  try {
    const res = await api('/api/reports/dashboard');
    if (res.success) {
      renderAdminMetrics(res.metrics);
      renderAdminReportCharts(res);
    }
    switchAdminTab(state.activeAdminTab);
  } catch (err) {
    showToast('Failed to load admin dashboard', 'error');
  }
}

function renderAdminMetrics(m) {
  document.getElementById('metricRevenue').textContent = `₹${m.total_revenue.toLocaleString('en-IN')}`;
  document.getElementById('metricOrders').textContent = m.total_orders;
  document.getElementById('metricPending').textContent = m.pending_orders;
  document.getElementById('metricLowStock').textContent = m.low_stock_count;
  document.getElementById('metricCustomers').textContent = m.total_customers;
}

function renderAdminReportCharts(data) {
  const catSalesBox = document.getElementById('adminCategorySales');
  if (catSalesBox) {
    catSalesBox.innerHTML = data.category_sales.map(cs => `
      <div style="margin-bottom: 0.6rem;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.2rem;">
          <span><strong>${cs.category_name}</strong> (${cs.items_sold} items)</span>
          <span>₹${cs.total_sales.toFixed(2)}</span>
        </div>
        <div style="background: #e9ecef; height: 8px; border-radius: 4px; overflow: hidden;">
          <div style="background: var(--primary); height: 100%; width: ${Math.min(100, (cs.total_sales / Math.max(1, data.metrics.total_revenue)) * 100)}%;"></div>
        </div>
      </div>
    `).join('') || '<div style="color: #868e96;">No sales data available yet.</div>';
  }

  const statusBox = document.getElementById('adminStatusDistribution');
  if (statusBox) {
    statusBox.innerHTML = data.status_breakdown.map(sb => `
      <div style="display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px dotted #e9ecef; font-size: 0.9rem;">
        <span><span class="badge ${getStatusBadgeClass(sb.status)}">${sb.status}</span></span>
        <strong>${sb.count} orders</strong>
      </div>
    `).join('');
  }
}

function switchAdminTab(tabName) {
  state.activeAdminTab = tabName;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.admin-tab-pane').forEach(p => p.style.display = 'none');

  const btn = document.querySelector(`[data-tab="${tabName}"]`);
  if (btn) btn.classList.add('active');

  const pane = document.getElementById(`admin-tab-${tabName}`);
  if (pane) pane.style.display = 'block';

  if (tabName === 'flowers') loadAdminFlowers();
  else if (tabName === 'categories') loadAdminCategories();
  else if (tabName === 'suppliers') loadAdminSuppliers();
  else if (tabName === 'staff') loadAdminStaff();
  else if (tabName === 'customers') loadAdminCustomers();
}

async function loadAdminFlowers() {
  try {
    const res = await api('/api/flowers');
    if (res.success) {
      const tbody = document.getElementById('adminFlowersTbody');
      tbody.innerHTML = res.flowers.map(f => `
        <tr>
          <td>#${f.flower_id}</td>
          <td><strong>${f.name}</strong></td>
          <td>${f.category_name}</td>
          <td>${f.color}</td>
          <td>₹${f.price.toFixed(2)}</td>
          <td><span style="font-weight: 700; color: ${f.stock_qty < 10 ? '#d9480f' : '#2b8a3e'}">${f.stock_qty}</span></td>
          <td>
            <div style="display: flex; gap: 0.35rem;">
              <button class="btn btn-sm btn-secondary" onclick="editFlowerPrompt(${f.flower_id}, '${encodeURIComponent(f.name)}', ${f.price}, ${f.stock_qty})">Edit</button>
              <button class="btn btn-sm btn-danger" onclick="deleteFlower(${f.flower_id}, '${encodeURIComponent(f.name)}')">Delete</button>
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (e) {
    showToast('Failed to load flowers for management', 'error');
  }
}

async function deleteFlower(flowerId, nameEnc) {
  const name = decodeURIComponent(nameEnc);
  if (!confirm(`Are you sure you want to delete flower '${name}'?`)) return;
  try {
    const res = await api(`/api/flowers/${flowerId}`, 'DELETE');
    if (res.success) {
      showToast(res.message, 'success');
      loadAdminFlowers();
      loadCatalog();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function editFlowerPrompt(flowerId, nameEnc, price, stock) {
  const name = decodeURIComponent(nameEnc);
  const newPrice = prompt(`Update price for ${name} (₹):`, price);
  if (newPrice === null) return;
  const newStock = prompt(`Update stock count for ${name}:`, stock);
  if (newStock === null) return;

  try {
    const res = await api(`/api/flowers/${flowerId}`, 'PUT', {
      price: parseFloat(newPrice),
      stock_qty: parseInt(newStock)
    });
    if (res.success) {
      showToast('Flower updated!', 'success');
      loadAdminFlowers();
      loadCatalog();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadAdminCategories() {
  try {
    const res = await api('/api/categories');
    if (res.success) {
      const tbody = document.getElementById('adminCategoriesTbody');
      tbody.innerHTML = res.categories.map(c => `
        <tr>
          <td>#${c.category_id}</td>
          <td><strong>${c.category_name}</strong></td>
          <td>${c.description || '-'}</td>
          <td><span class="badge badge-primary">${c.flower_count} items</span></td>
          <td>
            <button class="btn btn-sm btn-danger" onclick="deleteCategory(${c.category_id})">Delete</button>
          </td>
        </tr>
      `).join('');
    }
  } catch (e) {
    showToast('Failed to load categories', 'error');
  }
}

async function deleteCategory(catId) {
  if (!confirm('Are you sure you want to delete this category? Associated flowers will also be affected.')) return;
  try {
    const res = await api(`/api/categories/${catId}`, 'DELETE');
    if (res.success) {
      showToast(res.message, 'success');
      loadAdminCategories();
      loadCategories();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadAdminSuppliers() {
  try {
    const res = await api('/api/suppliers');
    if (res.success) {
      const tbody = document.getElementById('adminSuppliersTbody');
      tbody.innerHTML = res.suppliers.map(s => `
        <tr>
          <td>#${s.supplier_id}</td>
          <td><strong>${s.name}</strong></td>
          <td>${s.contact}</td>
          <td>${s.email}</td>
          <td>${s.address}</td>
        </tr>
      `).join('');
    }
  } catch (e) {
    showToast('Failed to load suppliers', 'error');
  }
}

async function loadAdminStaff() {
  try {
    const res = await api('/api/staff');
    if (res.success) {
      const tbody = document.getElementById('adminStaffTbody');
      tbody.innerHTML = res.staff.map(s => `
        <tr>
          <td>#${s.staff_id}</td>
          <td><strong>${s.name}</strong></td>
          <td><span class="badge ${s.role === 'Admin' ? 'badge-primary' : (s.role === 'Florist' ? 'badge-warning' : 'badge-info')}">${s.role}</span></td>
          <td>${s.email}</td>
          <td>${s.phone || '-'}</td>
          <td>
            ${s.role !== 'Admin' ? `<button class="btn btn-sm btn-danger" onclick="deleteStaff(${s.staff_id})">Remove</button>` : '<span style="color: #868e96; font-size: 0.8rem;">Superuser</span>'}
          </td>
        </tr>
      `).join('');
    }
  } catch (e) {
    showToast('Failed to load staff list', 'error');
  }
}

async function deleteStaff(staffId) {
  if (!confirm('Are you sure you want to remove this staff member?')) return;
  try {
    const res = await api(`/api/staff/${staffId}`, 'DELETE');
    if (res.success) {
      showToast(res.message, 'success');
      loadAdminStaff();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadAdminCustomers() {
  try {
    const res = await api('/api/customers');
    if (res.success) {
      const tbody = document.getElementById('adminCustomersTbody');
      tbody.innerHTML = res.customers.map(c => `
        <tr>
          <td>#${c.customer_id}</td>
          <td><strong>${c.name}</strong></td>
          <td>${c.email}</td>
          <td>${c.phone || '-'}</td>
          <td><span class="badge badge-success">${c.total_orders} orders</span></td>
          <td><strong>₹${c.total_spent.toFixed(2)}</strong></td>
          <td>⭐ ${c.loyalty_points}</td>
        </tr>
      `).join('');
    }
  } catch (e) {
    showToast('Failed to load customers', 'error');
  }
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

// ==================== EVENT LISTENERS & INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', async () => {
  await checkAuth();
  await loadCategories();
  await loadCatalog();
  updateCartBadge();

  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.currentFilters.search = e.target.value.trim();
        loadCatalog();
      }, 300);
    });
  }

  document.getElementById('colorFilter')?.addEventListener('change', (e) => {
    state.currentFilters.color = e.target.value;
    loadCatalog();
  });

  document.getElementById('occasionFilter')?.addEventListener('change', (e) => {
    state.currentFilters.occasion = e.target.value;
    loadCatalog();
  });

  document.getElementById('sortSelect')?.addEventListener('change', (e) => {
    state.currentFilters.sort = e.target.value;
    loadCatalog();
  });

  document.getElementById('inStockFilter')?.addEventListener('change', (e) => {
    state.currentFilters.in_stock = e.target.checked;
    loadCatalog();
  });

  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('active');
      }
    });
  });

  document.getElementById('loginForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const pass = document.getElementById('loginPassword').value;
    const role = document.getElementById('loginRole').value;
    loginUser(email, pass, role);
  });

  document.getElementById('registerForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('regName').value;
    const email = document.getElementById('regEmail').value;
    const pass = document.getElementById('regPassword').value;
    const phone = document.getElementById('regPhone').value;
    const address = document.getElementById('regAddress').value;
    registerCustomer(name, email, pass, phone, address);
  });

  document.getElementById('addFlowerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      name: document.getElementById('flowerName').value.trim(),
      category_id: parseInt(document.getElementById('flowerCat').value),
      price: parseFloat(document.getElementById('flowerPrice').value),
      stock_qty: parseInt(document.getElementById('flowerStock').value),
      color: document.getElementById('flowerColor').value,
      occasion: document.getElementById('flowerOccasion').value.trim(),
      description: document.getElementById('flowerDesc').value.trim()
    };
    try {
      const res = await api('/api/flowers', 'POST', data);
      if (res.success) {
        showToast(res.message, 'success');
        closeModal('addFlowerModal');
        loadAdminFlowers();
        loadCatalog();
        e.target.reset();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('addCategoryForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      category_name: document.getElementById('newCategoryName').value.trim(),
      description: document.getElementById('newCategoryDesc').value.trim()
    };
    try {
      const res = await api('/api/categories', 'POST', data);
      if (res.success) {
        showToast(res.message, 'success');
        closeModal('addCategoryModal');
        loadAdminCategories();
        loadCategories();
        e.target.reset();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('addStaffForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      name: document.getElementById('staffName').value.trim(),
      role: document.getElementById('staffRole').value,
      email: document.getElementById('staffEmail').value.trim(),
      password: document.getElementById('staffPassword').value,
      phone: document.getElementById('staffPhone').value.trim()
    };
    try {
      const res = await api('/api/staff', 'POST', data);
      if (res.success) {
        showToast(res.message, 'success');
        closeModal('addStaffModal');
        loadAdminStaff();
        e.target.reset();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('addSupplierForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      name: document.getElementById('suppName').value.trim(),
      contact: document.getElementById('suppContact').value.trim(),
      email: document.getElementById('suppEmail').value.trim(),
      address: document.getElementById('suppAddress').value.trim()
    };
    try {
      const res = await api('/api/suppliers', 'POST', data);
      if (res.success) {
        showToast(res.message, 'success');
        closeModal('addSupplierModal');
        loadAdminSuppliers();
        e.target.reset();
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
});
