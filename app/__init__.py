from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import redis
import logging
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
mail = Mail()
redis_client = None

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


def create_app(config_name="development"):
    app = Flask(__name__)

    from config.settings import config_by_name
    app.config.from_object(config_by_name[config_name])

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Cafe 7 in [{config_name}] mode")

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    global redis_client
    try:
        redis_client = redis.Redis(
            host=app.config.get("REDIS_HOST", "localhost"),
            port=app.config.get("REDIS_PORT", 6379),
            db=0,
            decode_responses=True,
            socket_timeout=5
        )
        redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        redis_client = None

    _register_blueprints(app)
    _register_error_handlers(app)

    # Serve frontend HTML files
    @app.route("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/<path:filename>")
    def frontend(filename):
        return send_from_directory(STATIC_DIR, filename)

    with app.app_context():
        db.create_all()
        logger.info("Database tables ready")


    @app.route("/seed-menu-cafe7-secret")
    def seed_menu():
        from app.models import MenuItem
        if MenuItem.query.count() > 0:
            return "Already seeded: " + str(MenuItem.query.count()) + " items"
        items = [
            ("Veg Burger","burger",80),("Veg Cheese Burger","burger",100),
            ("Grilled Chicken Burger","burger",120),("Grilled Chicken Cheese Burger","burger",140),
            ("KFC Zinger Burger","burger",150),("Cheese Chicken Burger","burger",130),
            ("Margherita","pizza",150),("Veg Cheese Burst","pizza",180),
            ("Corn Cheese Burst","pizza",190),("Veg Mexican Cheese Burst","pizza",200),
            ("Chicken Cheese Burst","pizza",220),("Chicken Mexican Cheese Burst","pizza",230),
            ("Egg Wrap","wrap",80),("Egg Cheese Wrap","wrap",100),
            ("Paneer Wrap","wrap",100),("Paneer Cheese Wrap","wrap",120),
            ("Chicken Cheese Wrap","wrap",130),("Chicken Wrap","wrap",100),
            ("Shawarma","shawarma",80),("Special Shawarma","shawarma",100),
            ("Dry Fruits Shawarma","shawarma",120),("Chicken Cheese Shawarma","shawarma",120),
            ("Americano","coffee",60),("Latte","coffee",80),
            ("Caffe Mocha","coffee",90),("Chocolate Coffee","coffee",90),
            ("Cold Coffee Shake","coffee",80),("Cold Coffee Crush","coffee",100),
            ("Redbull Coffee","coffee",150),("Strawberry","shake",80),
            ("Mango","shake",80),("Vanilla","shake",80),("Oreo","shake",100),
            ("Kit-Kat","shake",100),("Butterscotch","shake",90),
            ("Kiwi","shake",90),("Blue Curacao","shake",110),
            ("Lemon Mint","shake",70),("Blackcurrant","shake",80),
            ("Peach","shake",80),("Sitafal","shake",100),("Blueberry","shake",80),
            ("Cream Kunafa","desert",120),("Butterscotch Kunafa","desert",130),
            ("Nutella Kunafa","desert",140),("Cream Cheese Kunafa","desert",150),
            ("Mango Cream","desert",100),("Sitafal Cream","desert",110),
            ("Khajoor Cream","desert",110),("Shehdood Cream","desert",120),("Rasmalai","desert",120),
        ]
        for name, cat, price in items:
            db.session.add(MenuItem(name=name, category=cat, price=price, is_available=True))
        db.session.commit()
        return 'Seeded ' + str(len(items)) + ' items!'
    return app


def _register_blueprints(app):
    from app.routes.auth_routes import auth_bp
    from app.routes.menu_routes import menu_bp
    from app.routes.cart_routes import cart_bp
    from app.routes.order_routes import order_bp
    from app.routes.contact_routes import contact_bp
    from app.routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp,    url_prefix="/api/auth")
    app.register_blueprint(menu_bp,    url_prefix="/api/menu")
    app.register_blueprint(cart_bp,    url_prefix="/api/cart")
    app.register_blueprint(order_bp,   url_prefix="/api/orders")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")
    app.register_blueprint(admin_bp,   url_prefix="/api/admin")


def _register_error_handlers(app):
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized", "message": "Please log in"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden", "message": "You don't have permission"}), 403

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Server error: {e}")
        return jsonify({"error": "Internal server error", "message": "Something went wrong"}), 500
