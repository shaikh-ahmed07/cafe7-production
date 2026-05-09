// Universal cart and quantity handler
(function(){
  const CART_KEY = 'final_cafe_cart_v1';
  
  // In-memory fallback for environments without localStorage
  let memoryCart = [];
  const hasLocalStorage = (function() {
    try {
      const test = '__storage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch(e) {
      return false;
    }
  })();

  // Helpers with fallback storage
  function getCart(){ 
    if (hasLocalStorage) {
      try {
        return JSON.parse(localStorage.getItem(CART_KEY) || '[]');
      } catch(e) {
        console.warn('Failed to read from localStorage:', e);
        return memoryCart;
      }
    }
    return memoryCart;
  }
  
  function saveCart(c){ 
    if (hasLocalStorage) {
      try {
        localStorage.setItem(CART_KEY, JSON.stringify(c));
      } catch(e) {
        console.warn('Failed to write to localStorage:', e);
        memoryCart = c;
      }
    } else {
      memoryCart = c;
    }
  }

  // Find product card ancestor (whose parent has class 'container')
  function findProductCard(el){
    let cur = el;
    while(cur && cur.tagName && cur.tagName.toLowerCase() !== 'body'){
      if(cur.parentElement && cur.parentElement.classList && cur.parentElement.classList.contains('container')){
        return cur;
      }
      cur = cur.parentElement;
    }
    return el.closest('div') || el;
  }

  // Parse name and price from a product card
  function parseProductFromCard(card){
    if(!card) return null;
    
    // name: prefer heading elements
    let nameEl = card.querySelector('h1, h2, h3, h4, .title, .name');
    let name = nameEl ? nameEl.innerText.trim() : null;
    
    if(!name){
      // fallback: use image alt or filename
      let img = card.querySelector('img');
      if(img && img.alt) name = img.alt.trim();
      else if(img && img.src) {
        try {
          name = img.src.split('/').pop().split('.')[0].replace(/[-_]/g, ' ');
        } catch(e) {
          name = 'Item';
        }
      }
    }
    
    // price: look for pattern like '50rs' or '50 rs' or 'Rs 50' or '₹50'
    let txt = card.innerText || '';
    let priceMatch = txt.match(/(?:rs|Rs|RS|₹)?\s*(\d+(?:\.\d{1,2})?)\s*(?:rs|Rs|RS|rupees|₹)?/i);
    let price = priceMatch ? parseFloat(priceMatch[1]) : 0;
    
    // quantity: look for input with class quantity-input
    let qtyInput = card.querySelector('input.quantity-input');
    let qty = qtyInput ? Math.max(1, parseInt(qtyInput.value) || 1) : 1;
    
    return { 
      name: name || 'Item', 
      price: price, 
      qty: qty 
    };
  }

  // Add to cart
  function addToCart(item){
    if (!item || !item.name) return;
    
    let cart = getCart();
    // create id from name+price
    let id = (item.name || 'item')
      .toString()
      .trim()
      .toLowerCase()
      .replace(/\s+/g,'-')
      .replace(/[^a-z0-9\-]/g,'') + '-' + String(item.price);
    
    let existing = cart.find(c => c.id === id);
    if(existing){
      existing.qty = (existing.qty || 0) + (item.qty || 1);
    } else {
      cart.push({ 
        id, 
        name: item.name, 
        price: item.price, 
        qty: item.qty 
      });
    }
    saveCart(cart);
    
    // dispatch event
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('cartUpdated', {detail: {cart}}));
    }
  }

  // Remove from cart
  function removeFromCart(id){
    let cart = getCart().filter(i => i.id !== id);
    saveCart(cart);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('cartUpdated', {detail: {cart}}));
    }
  }

  // Update qty in cart
  function updateCartQty(id, qty){
    let cart = getCart();
    let item = cart.find(i => i.id === id);
    if(item){
      item.qty = Math.max(0, parseInt(qty) || 0);
      if(item.qty <= 0) {
        cart = cart.filter(i => i.id !== id);
      }
      saveCart(cart);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('cartUpdated', {detail: {cart}}));
      }
    }
  }

  // Event delegation for increment/decrement buttons anywhere
  document.addEventListener('click', function(e){
    const t = e.target;
    
    if(t.matches('.increment')){
      e.preventDefault();
      let input = t.closest('div') ? t.closest('div').querySelector('input.quantity-input') : null;
      if(!input) {
        input = t.parentElement ? t.parentElement.querySelector('input.quantity-input') : null;
      }
      if(input){
        let val = parseInt(input.value) || 1;
        let maxVal = input.max ? parseInt(input.max) : Infinity;
        val = Math.min(val + 1, maxVal);
        input.value = val;
      }
    } 
    else if(t.matches('.decrement')){
      e.preventDefault();
      let input = t.closest('div') ? t.closest('div').querySelector('input.quantity-input') : null;
      if(!input && t.parentElement) {
        input = t.parentElement.querySelector('input.quantity-input');
      }
      if(input){
        let val = parseInt(input.value) || 1;
        let minVal = input.min ? parseInt(input.min) : 1;
        val = Math.max(val - 1, minVal);
        input.value = val;
      }
    } 
    else if(t.matches('.btn, .add-to-cart')){
      e.preventDefault();
      
      // Add to cart
      let card = findProductCard(t);
      let prod = parseProductFromCard(card);
      
      if(prod && prod.price > 0){
        addToCart(prod);
        
        // UI feedback
        let originalText = t.innerText;
        t.innerText = '✓ Added';
        t.style.backgroundColor = '#10b981';
        
        setTimeout(() => {
          t.innerText = originalText || 'Add';
          t.style.backgroundColor = '';
        }, 1000);
      } else {
        alert('Could not determine product details. Make sure each product card contains a price and a name.');
      }
    }
  });

  // Expose functions globally for cart page
  if (typeof window !== 'undefined') {
    window.__CafeCart = {
      getCart, 
      saveCart, 
      addToCart, 
      removeFromCart, 
      updateCartQty
    };
  }

  // Update cart-count badges
  function updateBadges(){
    const count = getCart().reduce((s, i) => s + (i.qty || 0), 0);
    document.querySelectorAll('.cart-count').forEach(el => {
      el.innerText = count;
      el.style.display = count > 0 ? 'inline-block' : 'none';
    });
  }
  
  if (typeof window !== 'undefined') {
    window.addEventListener('cartUpdated', updateBadges);
    document.addEventListener('DOMContentLoaded', updateBadges);
  }

})();
