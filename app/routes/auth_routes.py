"""
====================================================================
CAFE 7 - AUTHENTICATION ROUTES
====================================================================
What is this file?
  These are the API endpoints for user registration and login.
  
  Endpoints (URLs) in this blueprint:
    POST /api/auth/register  — Create a new account
    POST /api/auth/login     — Log in and get a JWT token
    POST /api/auth/refresh   — Get a new token (before it expires)
    GET  /api/auth/me        — Get logged-in user's profile
    POST /api/auth/logout    — Log out
    
What is JWT?
  JWT = JSON Web Token
  
  Think of it like a government ID card:
  1. You register at the ID office (register endpoint)
  2. You show your ID and get a temporary visitor pass (JWT token)
  3. Every time you visit a restricted area, you show your pass
  4. The pass expires after a while — you need to get a new one
  
  In code:
  - Client sends username+password → server returns a token string
  - Client sends token in every future request header:
    Authorization: Bearer eyJhbGciOiJIUzI1Ni...
====================================================================
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import datetime, timezone

from app import db
from app.models import User

# Create the blueprint — all routes here will be prefixed with /api/auth
auth_bp = Blueprint("auth", __name__)

# Track revoked (logged-out) tokens in memory
# In production, use Redis for this
REVOKED_TOKENS = set()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user account.
    
    Expects JSON body:
    {
        "name": "Ahmed Ali",
        "email": "ahmed@gmail.com",
        "password": "securepassword123",
        "phone": "9876543210"  (optional)
    }
    
    Returns:
    {
        "message": "Account created successfully",
        "user": {...},
        "access_token": "eyJ...",
        "refresh_token": "eyJ..."
    }
    """
    # ── Step 1: Get the data the frontend sent ────────────────────
    data = request.get_json()
    
    # ── Step 2: Validate required fields ──────────────────────────
    required = ["name", "email", "password"]
    for field in required:
        if not data or not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400
    
    name = data["name"].strip()
    email = data["email"].strip().lower()  # Always store email lowercase
    password = data["password"]
    phone = data.get("phone", "").strip()
    
    # ── Step 3: Validate input quality ────────────────────────────
    if len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters"}), 400
    
    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email address"}), 400
    
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    
    # ── Step 4: Check if email already exists ─────────────────────
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists"}), 409
    
    # ── Step 5: Create the user ───────────────────────────────────
    new_user = User(name=name, email=email, phone=phone)
    new_user.set_password(password)   # This hashes the password — never stores plain text!
    
    # ── Step 6: Save to database ──────────────────────────────────
    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()  # Undo any partial changes
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed. Please try again."}), 500
    
    # ── Step 7: Create JWT tokens ─────────────────────────────────
    # additional_claims = extra data we put inside the token
    access_token = create_access_token(
        identity=new_user.id,
        additional_claims={"role": new_user.role, "name": new_user.name}
    )
    refresh_token = create_refresh_token(identity=new_user.id)
    
    return jsonify({
        "message": "Account created successfully! Welcome to Cafe 7!",
        "user": new_user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 201  # 201 = Created


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Log in with email and password. Returns JWT tokens.
    
    Expects:
    { "email": "ahmed@gmail.com", "password": "securepassword123" }
    
    Returns:
    { "access_token": "...", "refresh_token": "...", "user": {...} }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Find user by email
    user = User.query.filter_by(email=email).first()
    
    # check_password compares the entered password with the stored hash
    if not user or not user.check_password(password):
        # IMPORTANT: Give the same vague error for both wrong email AND wrong password
        # This prevents "email enumeration" attacks (hackers finding valid emails)
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Check if account is active
    if not user.is_active:
        return jsonify({"error": "Your account has been deactivated. Contact support."}), 403
    
    # Update last login time
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()
    
    # Create tokens
    access_token = create_access_token(
        identity=user.id,
        additional_claims={"role": user.role, "name": user.name}
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": f"Welcome back, {user.name}!",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()  # This decorator means: "token required to access this route"
def get_current_user():
    """
    Get the currently logged-in user's profile.
    
    The frontend sends: Authorization: Bearer <token>
    We decode the token to find the user ID, then fetch from DB.
    """
    # get_jwt_identity() reads the user ID we stored in the token
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)  # Only refresh tokens can access this
def refresh_token():
    """
    Get a new access token using the refresh token.
    
    Access tokens expire in 1 hour.
    Instead of logging out, the frontend can silently get a new one
    using the longer-lived refresh token (30 days).
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({"error": "Invalid session"}), 401
    
    new_access_token = create_access_token(
        identity=user_id,
        additional_claims={"role": user.role, "name": user.name}
    )
    
    return jsonify({"access_token": new_access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Log out the user by revoking their token.
    
    JWT tokens can't be "deleted" like session cookies.
    Instead, we keep a list of revoked tokens.
    """
    jti = get_jwt()["jti"]  # jti = JWT ID (unique identifier for this token)
    REVOKED_TOKENS.add(jti)
    return jsonify({"message": "Logged out successfully"}), 200
