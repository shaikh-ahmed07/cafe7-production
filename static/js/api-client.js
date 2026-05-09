/**
 * ================================================================
 * CAFE 7 - API CLIENT (Frontend ↔ Backend bridge)
 * ================================================================
 * What is this file?
 *   This replaces your localStorage-based cart with REAL API calls.
 *   Include this in every HTML page:
 *     <script src="js/api-client.js"></script>
 *
 * What it does:
 *   - Sends HTTP requests to your Flask backend
 *   - Manages the JWT login token in localStorage
 *   - Provides easy functions: login(), addToCart(), placeOrder()
 *
 * How JWT works here:
 *   1. User logs in → we save the token to localStorage
 *   2. Every API call → we add the token to the request header
 *   3. Token expires → user gets redirected to login page
 * ================================================================
 */

// ── Configuration ────────────────────────────────────────────────
// Change this when you deploy! In production: "https://yourdomain.com"
const API_BASE_URL = "http://localhost:5000";

// ── Token Storage ─────────────────────────────────────────────────
const TOKEN_KEY = "cafe7_access_token";
const REFRESH_KEY = "cafe7_refresh_token";
const USER_KEY = "cafe7_user";


/**
 * CafeAPI — the main object with all API methods
 * Think of it as your backend's remote control
 */
const CafeAPI = {

  // ── Token Helpers ──────────────────────────────────────────────
  
  /**
   * Get the JWT token from localStorage
   * Returns null if user is not logged in
   */
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  
  /**
   * Save tokens after login/register
   */
  saveTokens(accessToken, refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
  },
  
  /**
   * Clear tokens on logout
   */
  clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },
  
  /**
   * Is the user currently logged in?
   */
  isLoggedIn() {
    return !!this.getToken();
  },

  // ── Core Request Method ────────────────────────────────────────
  
  /**
   * Make an HTTP request to the backend.
   * 
   * This is the engine under the hood — all other methods use this.
   * 
   * @param {string} endpoint   - URL path like "/api/menu/"
   * @param {string} method     - "GET", "POST", "PUT", "DELETE"
   * @param {object} body       - Data to send (for POST/PUT)
   * @param {boolean} requiresAuth - Should we send the JWT token?
   * @returns {object} - Response data from the server
   */
  async request(endpoint, method = "GET", body = null, requiresAuth = false) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Build the headers
    const headers = {
      "Content-Type": "application/json",  // We're sending JSON data
    };
    
    // If this endpoint requires login, add the JWT token to the headers
    if (requiresAuth) {
      const token = this.getToken();
      if (!token) {
        // Not logged in — redirect to login page
        window.location.href = "/login.html";
        return;
      }
      headers["Authorization"] = `Bearer ${token}`;
      // ↑ This is how the backend knows who you are
      // Flask's @jwt_required() checks this header
    }
    
    // Build the request options
    const options = {
      method,
      headers,
    };
    
    // Add body for POST/PUT requests
    if (body) {
      options.body = JSON.stringify(body);  // Convert JS object → JSON string
    }
    
    try {
      // Make the actual HTTP request
      const response = await fetch(url, options);
      
      // If token expired, try refreshing it automatically
      if (response.status === 401 && requiresAuth) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          // Retry the original request with the new token
          return this.request(endpoint, method, body, requiresAuth);
        } else {
          // Refresh failed — user must log in again
          this.clearTokens();
          window.location.href = "/login.html";
          return;
        }
      }
      
      // Parse the JSON response
      const data = await response.json();
      
      if (!response.ok) {
        // Server returned an error (400, 404, 500, etc.)
        throw new Error(data.error || data.message || "Something went wrong");
      }
      
      return data;
      
    } catch (error) {
      // Network error (no internet, server down, etc.)
      console.error(`API Error [${method} ${endpoint}]:`, error);
      throw error;
    }
  },

  // ── Authentication Methods ─────────────────────────────────────
  
  /**
   * Register a new account
   * @param {string} name
   * @param {string} email
   * @param {string} password
   * @param {string} phone (optional)
   */
  async register(name, email, password, phone = "") {
    const data = await this.request("/api/auth/register", "POST", {
      name, email, password, phone
    });
    
    // Save tokens so user is automatically logged in after registration
    this.saveTokens(data.access_token, data.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    
    return data;
  },
  
  /**
   * Log in with email and password
   */
  async login(email, password) {
    const data = await this.request("/api/auth/login", "POST", { email, password });
    this.saveTokens(data.access_token, data.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    return data;
  },
  
  /**
   * Log out — clear tokens
   */
  async logout() {
    try {
      await this.request("/api/auth/logout", "POST", null, true);
    } catch (e) {
      // Even if server logout fails, clear local tokens
    }
    this.clearTokens();
    window.location.href = "/index.html";
  },
  
  /**
   * Get a new access token using the refresh token
   * Called automatically when access token expires
   */
  async refreshAccessToken() {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) return false;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${refreshToken}`,
          "Content-Type": "application/json"
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem(TOKEN_KEY, data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },

  // ── Menu Methods ───────────────────────────────────────────────
  
  /**
   * Get all menu items, optionally filtered
   * @param {string} category - e.g. "burger", "coffee"
   * @param {string} search - search term
   */
  async getMenuItems(category = "", search = "") {
    let url = "/api/menu/?available=true";
    if (category) url += `&category=${encodeURIComponent(category)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    return this.request(url);
  },
  
  async getCategories() {
    return this.request("/api/menu/categories");
  },
  
  async getMenuByCategory(category) {
    return this.request(`/api/menu/category/${encodeURIComponent(category)}`);
  },

  // ── Cart Methods ───────────────────────────────────────────────
  
  /**
   * Get user's cart from the backend
   */
  async getCart() {
    return this.request("/api/cart/", "GET", null, true);
  },
  
  /**
   * Add item to cart
   * @param {number} menuItemId - The menu item's database ID
   * @param {number} quantity
   */
  async addToCart(menuItemId, quantity = 1) {
    return this.request("/api/cart/add", "POST", {
      menu_item_id: menuItemId,
      quantity
    }, true);
  },
  
  async updateCartItem(cartItemId, quantity) {
    return this.request(`/api/cart/update/${cartItemId}`, "PUT", { quantity }, true);
  },
  
  async removeFromCart(cartItemId) {
    return this.request(`/api/cart/remove/${cartItemId}`, "DELETE", null, true);
  },
  
  async clearCart() {
    return this.request("/api/cart/clear", "DELETE", null, true);
  },

  // ── Order Methods ──────────────────────────────────────────────
  
  /**
   * Place an order
   * @param {object} orderData - address, phone, payment method
   */
  async placeOrder(orderData) {
    return this.request("/api/orders/", "POST", orderData, true);
  },
  
  async getOrders() {
    return this.request("/api/orders/", "GET", null, true);
  },
  
  async getOrder(orderId) {
    return this.request(`/api/orders/${orderId}`, "GET", null, true);
  },

  // ── Contact Method ─────────────────────────────────────────────
  
  async submitContact(name, email, message, phone = "", subject = "") {
    return this.request("/api/contact/", "POST", { name, email, message, phone, subject });
  }
};


// ════════════════════════════════════════════════════════════════
// UI HELPERS — functions that connect API results to your HTML
// ════════════════════════════════════════════════════════════════

/**
 * Update the cart count badge in the navbar.
 * Call this whenever the cart changes.
 */
async function updateCartBadge() {
  if (!CafeAPI.isLoggedIn()) {
    document.querySelectorAll(".cart-count").forEach(el => {
      el.textContent = "0";
      el.style.display = "none";
    });
    return;
  }
  
  try {
    const cart = await CafeAPI.getCart();
    const count = cart.item_count || 0;
    document.querySelectorAll(".cart-count").forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? "inline-block" : "none";
    });
  } catch (e) {
    console.warn("Could not update cart badge:", e);
  }
}

/**
 * Show a toast notification (small popup message)
 * @param {string} message - Text to show
 * @param {string} type - "success", "error", "info"
 */
function showToast(message, type = "success") {
  // Remove existing toast
  const existing = document.querySelector(".cafe-toast");
  if (existing) existing.remove();
  
  const toast = document.createElement("div");
  toast.className = "cafe-toast";
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    z-index: 9999;
    animation: slideIn 0.3s ease;
    background: ${type === "success" ? "#10b981" : type === "error" ? "#ef4444" : "#3b82f6"};
  `;
  
  document.body.appendChild(toast);
  
  // Auto-remove after 3 seconds
  setTimeout(() => toast.remove(), 3000);
}

/**
 * Handle "Add to Cart" button clicks on food pages.
 * 
 * In your HTML food cards, add:
 *   <button class="add-to-cart" data-item-id="5" data-item-name="Veg Burger">
 *     Add to Cart
 *   </button>
 */
document.addEventListener("click", async function(e) {
  const btn = e.target.closest(".add-to-cart");
  if (!btn) return;
  
  if (!CafeAPI.isLoggedIn()) {
    showToast("Please log in to add items to cart", "info");
    setTimeout(() => window.location.href = "/login.html", 1500);
    return;
  }
  
  const itemId = parseInt(btn.dataset.itemId);
  const itemName = btn.dataset.itemName || "Item";
  
  if (!itemId) {
    console.error("Button missing data-item-id attribute");
    return;
  }
  
  // Disable button while processing
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = "Adding...";
  
  try {
    await CafeAPI.addToCart(itemId, 1);
    showToast(`${itemName} added to cart! 🛒`);
    await updateCartBadge();
    btn.textContent = "✓ Added";
    setTimeout(() => {
      btn.textContent = originalText;
      btn.disabled = false;
    }, 1500);
  } catch (error) {
    showToast(error.message || "Failed to add item", "error");
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

// Initialize cart badge when page loads
document.addEventListener("DOMContentLoaded", updateCartBadge);
