"""
====================================================================
CAFE 7 - CONFIGURATION SETTINGS
====================================================================
What is this file?
  All your app settings in one place.
  Never hardcode passwords or secret keys in your code!
  
  We use environment variables (.env file) for sensitive data.
  Think of it like: your code says "get the password from the safe"
  instead of writing the password on the wall.

Three environments:
  - Development: your laptop, with debug mode ON
  - Testing:     when running automated tests
  - Production:  live website, debug OFF, security ON

How to use:
  Create a .env file in the root folder with:
    SECRET_KEY=your_super_secret_key_here
    DATABASE_URL=postgresql://user:password@localhost/cafe7_db
    REDIS_HOST=localhost
====================================================================
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load variables from .env file into environment
# (python-dotenv library does this)
load_dotenv()


class BaseConfig:
    """
    Settings shared by ALL environments.
    
    Child classes (Development, Production) inherit these
    and can override specific values.
    """
    
    # ─── Security ────────────────────────────────────────────────
    # SECRET_KEY is like a master password for signing cookies and tokens
    # MUST be a long random string in production — never use "dev" in production!
    SECRET_KEY = os.environ.get("SECRET_KEY", "cafe7-dev-secret-change-in-production")
    
    # ─── JWT (Login Token) Settings ──────────────────────────────
    # JWT = JSON Web Token — like a tamper-proof ID card for logged-in users
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cafe7-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)    # Token expires after 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)   # Refresh token lasts 30 days
    JWT_TOKEN_LOCATION = ["headers"]                 # Token comes in HTTP headers
    
    # ─── Database ─────────────────────────────────────────────────
    # DATABASE_URL format: postgresql://username:password@host:port/database_name
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/cafe7_db"  # Default for local dev
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False   # Saves memory — we don't need this feature
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,    # Recycle connections every 5 minutes
        "pool_pre_ping": True,  # Test connection before using it
        "pool_size": 10,        # Keep 10 connections ready
        "max_overflow": 20      # Allow up to 20 extra connections when busy
    }
    
    # ─── Redis ───────────────────────────────────────────────────
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    CART_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # Cart saved for 7 days
    
    # ─── Email (SendGrid or Gmail) ────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_SENDER", "noreply@cafe7.com")
    
    # ─── Payment (Razorpay — popular in India) ───────────────────
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
    
    # ─── File Upload (Cloudinary for images) ─────────────────────
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # Max file size: 5MB
    
    # ─── CORS (which websites can talk to our API) ────────────────
    ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5500").split(",")
    
    # ─── Business Settings ────────────────────────────────────────
    DELIVERY_CHARGE = 30        # ₹30 delivery fee
    FREE_DELIVERY_ABOVE = 500   # Free delivery if order > ₹500
    RESTAURANT_NAME = "Cafe 7"
    RESTAURANT_PHONE = "+91-XXXXXXXXXX"


class DevelopmentConfig(BaseConfig):
    """
    Development settings — runs on your laptop.
    Debug mode ON means Flask shows detailed error messages.
    """
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Print every SQL query to console (very helpful for learning!)
    TESTING = False
    

class TestingConfig(BaseConfig):
    """
    Testing settings — used when you run automated tests.
    Uses a separate test database so tests don't mess up real data.
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # In-memory DB, very fast for tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)  # Short expiry for testing
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    """
    Production settings — the live website.
    Debug OFF for security. Errors are logged, not shown to users.
    """
    DEBUG = False
    TESTING = False
    
    # In production, database URL MUST come from environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    
    # Extra security headers for production
    SESSION_COOKIE_SECURE = True      # Cookie only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True    # JavaScript can't read the cookie
    SESSION_COOKIE_SAMESITE = "Lax"  # Prevent CSRF attacks


# Dictionary mapping config name → config class
# This is used in create_app() to pick the right config
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
