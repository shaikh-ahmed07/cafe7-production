"""
====================================================================
CAFE 7 - CART ROUTES
====================================================================
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import CartItem, MenuItem

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/", methods=["GET"])
@jwt_required()
def get_cart():
    """Get current user's cart contents."""
    user_id = get_jwt_identity()
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    
    items_data = [ci.to_dict() for ci in cart_items]
    subtotal = sum(item["subtotal"] for item in items_data)
    delivery_charge = 0 if subtotal >= 500 else 30
    
    return jsonify({
        "items": items_data,
        "item_count": len(items_data),
        "subtotal": subtotal,
        "delivery_charge": delivery_charge,
        "total": subtotal + delivery_charge
    }), 200


@cart_bp.route("/add", methods=["POST"])
@jwt_required()
def add_to_cart():
    """
    Add an item to cart or increase quantity.
    
    Expects: { "menu_item_id": 1, "quantity": 2 }
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    menu_item_id = data.get("menu_item_id")
    quantity = int(data.get("quantity", 1))
    
    if not menu_item_id or quantity <= 0:
        return jsonify({"error": "Valid menu_item_id and quantity required"}), 400
    
    # Check menu item exists and is available
    menu_item = MenuItem.query.filter_by(id=menu_item_id, is_available=True).first()
    if not menu_item:
        return jsonify({"error": "Item not available"}), 404
    
    # Check if item already in cart
    existing = CartItem.query.filter_by(user_id=user_id, menu_item_id=menu_item_id).first()
    
    if existing:
        existing.quantity += quantity  # Increase quantity
    else:
        new_item = CartItem(user_id=user_id, menu_item_id=menu_item_id, quantity=quantity)
        db.session.add(new_item)
    
    db.session.commit()
    return jsonify({"message": f"{menu_item.name} added to cart"}), 200


@cart_bp.route("/update/<int:cart_item_id>", methods=["PUT"])
@jwt_required()
def update_cart_item(cart_item_id):
    """Update quantity of a cart item."""
    user_id = get_jwt_identity()
    data = request.get_json()
    quantity = int(data.get("quantity", 1))
    
    cart_item = CartItem.query.filter_by(id=cart_item_id, user_id=user_id).first_or_404()
    
    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    
    db.session.commit()
    return jsonify({"message": "Cart updated"}), 200


@cart_bp.route("/remove/<int:cart_item_id>", methods=["DELETE"])
@jwt_required()
def remove_from_cart(cart_item_id):
    """Remove an item from the cart."""
    user_id = get_jwt_identity()
    cart_item = CartItem.query.filter_by(id=cart_item_id, user_id=user_id).first_or_404()
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({"message": "Item removed from cart"}), 200


@cart_bp.route("/clear", methods=["DELETE"])
@jwt_required()
def clear_cart():
    """Clear all items from the user's cart."""
    user_id = get_jwt_identity()
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"message": "Cart cleared"}), 200
