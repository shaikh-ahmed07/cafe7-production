"""
====================================================================
CAFE 7 - ORDER ROUTES
====================================================================
Endpoints:
  POST /api/orders/           — Place a new order
  GET  /api/orders/           — Get user's order history
  GET  /api/orders/<id>       — Get single order details
  PUT  /api/orders/<id>/status — Update order status (admin)
  POST /api/orders/payment/verify — Verify Razorpay payment
====================================================================
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timezone, timedelta
import hmac
import hashlib

from app import db
from app.models import Order, OrderItem, MenuItem, CartItem, User

order_bp = Blueprint("orders", __name__)


@order_bp.route("/", methods=["POST"])
@jwt_required()
def place_order():
    """
    Place a new order from the user's cart or a direct item list.
    
    Expects JSON:
    {
        "delivery_address": "123 MG Road, Hyderabad",
        "customer_phone": "9876543210",
        "customer_name": "Ahmed Ali",
        "payment_method": "cash_on_delivery",  or "razorpay"
        "special_instructions": "No onions please",
        "items": [                        (optional: or use cart)
            {"menu_item_id": 1, "quantity": 2},
            {"menu_item_id": 5, "quantity": 1}
        ]
    }
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    
    # ── Validate delivery info ────────────────────────────────────
    required = ["delivery_address", "customer_phone"]
    for field in required:
        if not data or not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400
    
    # ── Get order items (from request body or user's cart) ────────
    items_data = data.get("items")
    
    if not items_data:
        # Use cart items from database
        cart_items = CartItem.query.filter_by(user_id=user_id).all()
        if not cart_items:
            return jsonify({"error": "Your cart is empty"}), 400
        
        items_data = [
            {"menu_item_id": ci.menu_item_id, "quantity": ci.quantity}
            for ci in cart_items
        ]
    
    # ── Validate each item and calculate total ────────────────────
    order_items = []
    subtotal = 0.0
    
    for item_data in items_data:
        menu_item_id = item_data.get("menu_item_id")
        quantity = int(item_data.get("quantity", 1))
        
        if quantity <= 0:
            continue
        
        # Fetch the menu item (also validates it exists)
        menu_item = MenuItem.query.get(menu_item_id)
        if not menu_item:
            return jsonify({"error": f"Menu item #{menu_item_id} not found"}), 404
        if not menu_item.is_available:
            return jsonify({"error": f"'{menu_item.name}' is currently unavailable"}), 400
        
        item_subtotal = float(menu_item.price) * quantity
        subtotal += item_subtotal
        
        # Create the OrderItem object (don't save yet — wait for Order to be created)
        order_items.append(OrderItem(
            menu_item_id=menu_item.id,
            item_name=menu_item.name,    # Snapshot the name at time of order
            unit_price=menu_item.price,  # Snapshot the price at time of order
            quantity=quantity,
            subtotal=item_subtotal
        ))
    
    if not order_items:
        return jsonify({"error": "No valid items in order"}), 400
    
    # ── Calculate delivery charge ─────────────────────────────────
    free_delivery_threshold = current_app.config.get("FREE_DELIVERY_ABOVE", 500)
    delivery_charge = 0.0 if subtotal >= free_delivery_threshold else current_app.config.get("DELIVERY_CHARGE", 30.0)
    total_amount = subtotal + delivery_charge
    
    # ── Create the order ──────────────────────────────────────────
    order = Order(
        user_id=user_id,
        customer_name=data.get("customer_name", user.name),
        customer_phone=data["customer_phone"],
        delivery_address=data["delivery_address"],
        special_instructions=data.get("special_instructions", ""),
        subtotal=subtotal,
        delivery_charge=delivery_charge,
        total_amount=total_amount,
        payment_method=data.get("payment_method", "cash_on_delivery"),
        status=Order.STATUS_PENDING,
        # Estimate delivery in 45 minutes
        estimated_delivery_at=datetime.now(timezone.utc) + timedelta(minutes=45)
    )
    
    # ── Save everything in one transaction ────────────────────────
    # A "transaction" means: either ALL of these succeed, or NONE do
    # This prevents half-saved orders
    try:
        db.session.add(order)
        db.session.flush()  # Assigns the order ID without committing yet
        
        for oi in order_items:
            oi.order_id = order.id
            db.session.add(oi)
        
        # Clear the user's cart after placing order
        CartItem.query.filter_by(user_id=user_id).delete()
        
        db.session.commit()
        current_app.logger.info(f"Order placed: {order.id} for user {user_id}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Order placement error: {e}")
        return jsonify({"error": "Failed to place order. Please try again."}), 500
    
    # ── Trigger background email (using Celery — see tasks.py) ────
    try:
        from app.tasks import send_order_confirmation_email
        send_order_confirmation_email.delay(order.id)  # .delay() = run in background
    except Exception:
        pass  # Email failure should NOT fail the order
    
    return jsonify({
        "message": "Order placed successfully!",
        "order_id": order.id,
        "total_amount": total_amount,
        "estimated_delivery": "45 minutes",
        "order": order.to_dict()
    }), 201


@order_bp.route("/", methods=["GET"])
@jwt_required()
def get_user_orders():
    """
    Get order history for the logged-in user.
    Shows most recent orders first.
    """
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    
    # paginate() splits results into pages — prevents loading 1000 orders at once
    orders_page = Order.query.filter_by(user_id=user_id)\
        .order_by(Order.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "orders": [order.to_dict() for order in orders_page.items],
        "total": orders_page.total,
        "page": page,
        "per_page": per_page,
        "has_next": orders_page.has_next,
        "has_prev": orders_page.has_prev
    }), 200


@order_bp.route("/<string:order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id):
    """Get details of a specific order."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    order = Order.query.get_or_404(order_id, description="Order not found")
    
    # Security: only the order owner or admin can view it
    if order.user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "You can only view your own orders"}), 403
    
    return jsonify({"order": order.to_dict()}), 200


@order_bp.route("/<string:order_id>/status", methods=["PUT"])
@jwt_required()
def update_order_status(order_id):
    """
    Update order status. Admin only.
    
    Expects: { "status": "confirmed" }
    Valid statuses: pending, confirmed, preparing, out_for_delivery, delivered, cancelled
    """
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    
    valid_statuses = [
        Order.STATUS_PENDING, Order.STATUS_CONFIRMED,
        Order.STATUS_PREPARING, Order.STATUS_OUT_FOR_DELIVERY,
        Order.STATUS_DELIVERED, Order.STATUS_CANCELLED
    ]
    
    new_status = data.get("status")
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Valid: {valid_statuses}"}), 400
    
    old_status = order.status
    order.status = new_status
    db.session.commit()
    
    current_app.logger.info(f"Order {order_id} status: {old_status} → {new_status}")
    
    return jsonify({
        "message": f"Order status updated to '{new_status}'",
        "order": order.to_dict()
    }), 200


@order_bp.route("/payment/verify", methods=["POST"])
@jwt_required()
def verify_payment():
    """
    Verify Razorpay payment after the user pays.
    
    Razorpay sends 3 IDs back to the frontend.
    We verify the signature to make sure the payment is genuine
    (prevents fake payments!).
    
    Expects:
    {
        "razorpay_order_id": "order_...",
        "razorpay_payment_id": "pay_...",
        "razorpay_signature": "abc123...",
        "order_id": "<our internal order ID>"
    }
    """
    data = request.get_json()
    
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    our_order_id = data.get("order_id")
    
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({"error": "Missing payment details"}), 400
    
    # Verify the signature using HMAC-SHA256
    # This proves the payment came from Razorpay, not a fake request
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
    expected_signature = hmac.new(
        key_secret.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, razorpay_signature):
        current_app.logger.warning(f"Payment signature mismatch for order {our_order_id}")
        return jsonify({"error": "Payment verification failed"}), 400
    
    # Update our order with the payment details
    order = Order.query.get_or_404(our_order_id)
    order.payment_id = razorpay_payment_id
    order.payment_status = "paid"
    order.status = Order.STATUS_CONFIRMED
    db.session.commit()
    
    return jsonify({
        "message": "Payment verified! Your order is confirmed.",
        "order": order.to_dict()
    }), 200
