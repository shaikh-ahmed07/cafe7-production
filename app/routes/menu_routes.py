"""
====================================================================
CAFE 7 - MENU API ROUTES
====================================================================
Endpoints:
  GET    /api/menu/              — All menu items (with filters)
  GET    /api/menu/categories    — List of all categories
  GET    /api/menu/<category>    — Items in a specific category
  GET    /api/menu/item/<id>     — Single item details
  POST   /api/menu/              — Add new item (admin only)
  PUT    /api/menu/item/<id>     — Update item (admin only)
  DELETE /api/menu/item/<id>     — Delete item (admin only)

Caching Strategy:
  Menu items don't change often. Instead of hitting PostgreSQL
  every time someone opens the menu (which could be 100s of times),
  we cache the data in Redis for 10 minutes.
  
  Flow:
  1. Request comes in for /api/menu
  2. Check Redis: "do we have cached menu data?"
  3. If YES → return cached data instantly (milliseconds!)
  4. If NO → query PostgreSQL, save to Redis, return data
====================================================================
"""

import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt

from app import db, redis_client
from app.models import MenuItem

menu_bp = Blueprint("menu", __name__)

CACHE_TTL = 600  # Cache menu for 10 minutes (600 seconds)


def get_from_cache(key):
    """Try to get data from Redis cache. Returns None if unavailable."""
    if redis_client is None:
        return None
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def save_to_cache(key, data, ttl=CACHE_TTL):
    """Save data to Redis cache with expiry time."""
    if redis_client is None:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(data))
    except Exception:
        pass  # Cache failure is OK — we'll just query DB next time


def invalidate_menu_cache():
    """Clear menu cache when admin updates items."""
    if redis_client is None:
        return
    try:
        # Delete all keys starting with "menu:"
        keys = redis_client.keys("menu:*")
        if keys:
            redis_client.delete(*keys)
    except Exception:
        pass


@menu_bp.route("/", methods=["GET"])
def get_all_menu_items():
    """
    Get all menu items. Supports filtering and searching.
    
    Query parameters:
      ?category=burger      — filter by category
      ?search=chicken       — search by name
      ?available=true       — only show available items
      ?featured=true        — only featured items
    
    Example: GET /api/menu/?category=coffee&available=true
    """
    # Read query parameters from the URL
    category = request.args.get("category", "").lower().strip()
    search = request.args.get("search", "").strip()
    available_only = request.args.get("available", "true").lower() == "true"
    featured_only = request.args.get("featured", "false").lower() == "true"
    
    # Build cache key from the filters
    cache_key = f"menu:all:{category}:{search}:{available_only}:{featured_only}"
    
    # Check cache first
    cached = get_from_cache(cache_key)
    if cached:
        return jsonify({"items": cached, "source": "cache"}), 200
    
    # Build database query step by step
    # query = "SELECT * FROM menu_items WHERE ..."
    query = MenuItem.query
    
    if available_only:
        query = query.filter_by(is_available=True)
    
    if category:
        query = query.filter_by(category=category)
    
    if featured_only:
        query = query.filter_by(is_featured=True)
    
    if search:
        # ILIKE = case-insensitive LIKE (PostgreSQL)
        # %{search}% means "contains search anywhere in the name"
        query = query.filter(MenuItem.name.ilike(f"%{search}%"))
    
    items = query.order_by(MenuItem.category, MenuItem.sort_order, MenuItem.name).all()
    
    # Convert to list of dicts for JSON response
    items_data = [item.to_dict() for item in items]
    
    # Save to cache
    save_to_cache(cache_key, items_data)
    
    return jsonify({
        "items": items_data,
        "count": len(items_data),
        "source": "database"
    }), 200


@menu_bp.route("/categories", methods=["GET"])
def get_categories():
    """
    Get all available categories.
    Returns: ["burger", "pizza", "wrap", "shawarma", "coffee", "shake", "desert"]
    """
    cache_key = "menu:categories"
    cached = get_from_cache(cache_key)
    if cached:
        return jsonify({"categories": cached}), 200
    
    # SELECT DISTINCT category FROM menu_items WHERE is_available=true
    categories = db.session.query(MenuItem.category)\
        .filter_by(is_available=True)\
        .distinct()\
        .order_by(MenuItem.category)\
        .all()
    
    # categories is a list of tuples: [("burger",), ("pizza",), ...]
    # We extract just the first element from each tuple
    category_list = [c[0] for c in categories]
    
    save_to_cache(cache_key, category_list)
    return jsonify({"categories": category_list}), 200


@menu_bp.route("/category/<string:category>", methods=["GET"])
def get_by_category(category):
    """
    Get all items in a specific category.
    Example: GET /api/menu/category/burger
    """
    cache_key = f"menu:category:{category.lower()}"
    cached = get_from_cache(cache_key)
    if cached:
        return jsonify({"items": cached, "category": category}), 200
    
    items = MenuItem.query.filter_by(
        category=category.lower(),
        is_available=True
    ).order_by(MenuItem.sort_order, MenuItem.name).all()
    
    if not items:
        return jsonify({"error": f"No items found in category '{category}'"}), 404
    
    items_data = [item.to_dict() for item in items]
    save_to_cache(cache_key, items_data)
    
    return jsonify({"items": items_data, "category": category, "count": len(items_data)}), 200


@menu_bp.route("/item/<int:item_id>", methods=["GET"])
def get_menu_item(item_id):
    """Get details of a single menu item by ID."""
    item = MenuItem.query.get_or_404(item_id, description=f"Menu item #{item_id} not found")
    return jsonify({"item": item.to_dict()}), 200


# ─── Admin-only routes (require JWT + admin role) ─────────────────

def admin_required(fn):
    """
    Custom decorator to check if user is admin.
    
    A decorator wraps a function with extra logic.
    @admin_required means: "run this check before the function"
    """
    from functools import wraps
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


@menu_bp.route("/item", methods=["POST"])
@admin_required
def add_menu_item():
    """
    Add a new menu item. Admin only.
    
    Expects JSON:
    {
        "name": "Special Burger",
        "description": "With extra cheese",
        "price": 120.00,
        "category": "burger",
        "image_url": "https://cloudinary.com/..."
    }
    """
    data = request.get_json()
    
    # Validate required fields
    required = ["name", "price", "category"]
    for field in required:
        if not data or not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400
    
    item = MenuItem(
        name=data["name"].strip(),
        description=data.get("description", "").strip(),
        price=float(data["price"]),
        category=data["category"].lower().strip(),
        image_url=data.get("image_url"),
        is_available=data.get("is_available", True),
        is_featured=data.get("is_featured", False),
        sort_order=data.get("sort_order", 0)
    )
    
    db.session.add(item)
    db.session.commit()
    
    invalidate_menu_cache()  # Clear cache so new item shows up
    
    return jsonify({"message": "Item added", "item": item.to_dict()}), 201


@menu_bp.route("/item/<int:item_id>", methods=["PUT"])
@admin_required
def update_menu_item(item_id):
    """Update an existing menu item. Admin only."""
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()
    
    # Update only the fields that were sent
    if "name" in data:
        item.name = data["name"].strip()
    if "price" in data:
        item.price = float(data["price"])
    if "description" in data:
        item.description = data["description"].strip()
    if "is_available" in data:
        item.is_available = bool(data["is_available"])
    if "image_url" in data:
        item.image_url = data["image_url"]
    
    db.session.commit()
    invalidate_menu_cache()
    
    return jsonify({"message": "Item updated", "item": item.to_dict()}), 200


@menu_bp.route("/item/<int:item_id>", methods=["DELETE"])
@admin_required
def delete_menu_item(item_id):
    """Delete a menu item. Admin only."""
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    invalidate_menu_cache()
    return jsonify({"message": f"'{item.name}' deleted"}), 200
