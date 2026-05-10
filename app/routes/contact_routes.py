"""CAFE 7 - CONTACT ROUTES"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app import db
from app.models import ContactMessage

contact_bp = Blueprint("contact", __name__)


@contact_bp.route("/", methods=["POST"])
def submit_contact():
    """
    Handle contact form submission.
    No login required — anyone can send a message.
    """
    data = request.get_json()
    
    required = ["name", "email", "message"]
    for field in required:
        if not data or not data.get(field, "").strip():
            return jsonify({"error": f"'{field}' is required"}), 400
    
    msg = ContactMessage(
        name=data["name"].strip(),
        email=data["email"].strip().lower(),
        phone=data.get("phone", "").strip(),
        subject=data.get("subject", "").strip(),
        message=data["message"].strip()
    )
    
    db.session.add(msg)
    db.session.commit()
    
    return jsonify({
        "message": "Thank you! We'll get back to you soon.",
        "id": msg.id
    }), 201


@contact_bp.route("/", methods=["GET"])
@jwt_required()
def get_messages():
    """Get all contact messages. Admin only."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return jsonify({"messages": [m.to_dict() for m in messages]}), 200


# ─────────────────────────────────────────────────────────────────

"""CAFE 7 - ADMIN ROUTES"""
from flask import Blueprint
admin_bp = Blueprint("admin", __name__)

from app.models import User, Order, MenuItem
from sqlalchemy import func


@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    """Admin dashboard with key metrics."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    # Count records
    total_users = User.query.count()
    total_orders = Order.query.count()
    total_items = MenuItem.query.filter_by(is_available=True).count()

    # Revenue: SUM of total_amount for delivered orders
    revenue_result = db.session.query(func.sum(Order.total_amount))\
        .filter_by(status=Order.STATUS_DELIVERED).scalar()
    total_revenue = float(revenue_result or 0)

    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    return jsonify({
        "metrics": {
            "total_users": total_users,
            "total_orders": total_orders,
            "total_menu_items": total_items,
            "total_revenue": total_revenue
        },
        "recent_orders": [o.to_dict() for o in recent_orders]
    }), 200


@admin_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_all_orders():
    """Get all orders for admin."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    from app.models import Order
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [o.to_dict() for o in orders]}), 200
