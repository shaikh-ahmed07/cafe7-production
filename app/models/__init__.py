"""
====================================================================
CAFE 7 - DATABASE MODELS
====================================================================
What is this file?
  Each Python class here = one table in your PostgreSQL database.
  
  This is called ORM (Object Relational Mapping):
  - Object = Python class
  - Relational = PostgreSQL table
  - Mapping = they represent each other
  
  Instead of writing SQL like:
    INSERT INTO users (name, email) VALUES ('Ali', 'ali@gmail.com')
  
  You write Python like:
    user = User(name='Ali', email='ali@gmail.com')
    db.session.add(user)
    db.session.commit()
  
  Much easier to read and safe from SQL injection attacks!

Models in this file:
  1. User         — people who register/login
  2. MenuItem     — food and drinks on your menu
  3. CartItem     — items in a user's cart (temporary)
  4. Order        — placed orders with status
  5. OrderItem    — which items are in each order
  6. ContactMessage — messages from the contact page
====================================================================
"""

from datetime import datetime, timezone
from app import db, bcrypt
import uuid


def generate_uuid():
    """Generate a unique ID string. UUID = Universally Unique Identifier"""
    return str(uuid.uuid4())


# ══════════════════════════════════════════════════════════════════
# MODEL 1: USER
# Stores everyone who creates an account
# ══════════════════════════════════════════════════════════════════
class User(db.Model):
    """
    Represents a registered customer.
    
    Relationship: One user → Many orders
                 One user → Many cart items
    """
    __tablename__ = "users"  # The actual table name in PostgreSQL

    # ── Columns ──────────────────────────────────────────────────
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)             # Full name
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)  
    # index=True makes searching by email MUCH faster
    password_hash = db.Column(db.String(255), nullable=False)    # NEVER store plain password!
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default="customer")          # "customer" or "admin"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    # This tells SQLAlchemy: each User has many Orders
    # backref="user" means you can do: order.user to get the user
    orders = db.relationship("Order", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    cart_items = db.relationship("CartItem", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    # ── Password Methods ──────────────────────────────────────────
    def set_password(self, plain_password):
        """
        Hash the password before saving.
        BCrypt converts 'mypassword123' → '$2b$12$...'  (unreadable)
        Even if hackers steal your database, they can't read passwords.
        """
        self.password_hash = bcrypt.generate_password_hash(plain_password).decode("utf-8")

    def check_password(self, plain_password):
        """
        Compare entered password with stored hash.
        Returns True if correct, False if wrong.
        """
        return bcrypt.check_password_hash(self.password_hash, plain_password)

    def to_dict(self):
        """Convert User object to dictionary (for sending as JSON to frontend)"""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        """How this object looks when printed — useful for debugging"""
        return f"<User {self.name} ({self.email})>"


# ══════════════════════════════════════════════════════════════════
# MODEL 2: MENU ITEM
# Every item you sell: burgers, coffee, pizza, etc.
# ══════════════════════════════════════════════════════════════════
class MenuItem(db.Model):
    """
    Represents one item on the Cafe 7 menu.
    
    Categories: burger, pizza, wrap, shawarma, coffee, shake, desert
    """
    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)    # Stores exact decimal (e.g. 120.00)
    category = db.Column(db.String(50), nullable=False, index=True)
    # Categories: burger, pizza, wrap, shawarma, coffee, shake, desert
    
    image_url = db.Column(db.String(500), nullable=True)   # URL to the food image
    is_available = db.Column(db.Boolean, default=True)      # Can turn off items temporarily
    is_featured = db.Column(db.Boolean, default=False)      # Show on homepage
    sort_order = db.Column(db.Integer, default=0)           # Control display order
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    order_items = db.relationship("OrderItem", backref="menu_item", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),         # Convert Decimal to float for JSON
            "category": self.category,
            "image_url": self.image_url,
            "is_available": self.is_available,
            "is_featured": self.is_featured
        }

    def __repr__(self):
        return f"<MenuItem {self.name} - ₹{self.price}>"


# ══════════════════════════════════════════════════════════════════
# MODEL 3: CART ITEM
# Temporary storage: what's in a user's cart right now
# ══════════════════════════════════════════════════════════════════
class CartItem(db.Model):
    """
    Items in a user's shopping cart.
    
    Note: When an order is PLACED, cart items are deleted.
    Cart is temporary; orders are permanent.
    """
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys — these link to other tables
    # user_id references the id column in the users table
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship: lets us do cart_item.item to get the MenuItem object
    item = db.relationship("MenuItem", lazy="joined")

    # Unique constraint: a user can't have the same item twice (just increase quantity)
    __table_args__ = (
        db.UniqueConstraint("user_id", "menu_item_id", name="unique_user_cart_item"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "menu_item": self.item.to_dict() if self.item else None,
            "quantity": self.quantity,
            "subtotal": float(self.item.price * self.quantity) if self.item else 0
        }


# ══════════════════════════════════════════════════════════════════
# MODEL 4: ORDER
# A confirmed purchase by a customer
# ══════════════════════════════════════════════════════════════════
class Order(db.Model):
    """
    A placed order.
    
    Status flow:
    pending → confirmed → preparing → out_for_delivery → delivered
                                                        ↘ cancelled
    """
    __tablename__ = "orders"

    # Status choices — using constants prevents typos
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PREPARING = "preparing"
    STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Pricing
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_charge = db.Column(db.Numeric(10, 2), default=30.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Order details
    status = db.Column(db.String(30), default=STATUS_PENDING, index=True)
    delivery_address = db.Column(db.Text, nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    special_instructions = db.Column(db.Text, nullable=True)
    
    # Payment
    payment_method = db.Column(db.String(30), default="cash_on_delivery")
    payment_id = db.Column(db.String(100), nullable=True)   # Razorpay payment ID
    payment_status = db.Column(db.String(20), default="pending")
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    estimated_delivery_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    items = db.relationship("OrderItem", backref="order", lazy="joined", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "subtotal": float(self.subtotal),
            "delivery_charge": float(self.delivery_charge),
            "total_amount": float(self.total_amount),
            "status": self.status,
            "delivery_address": self.delivery_address,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Order {self.id[:8]} - ₹{self.total_amount} - {self.status}>"


# ══════════════════════════════════════════════════════════════════
# MODEL 5: ORDER ITEM
# Each individual item within one order
# ══════════════════════════════════════════════════════════════════
class OrderItem(db.Model):
    """
    One line in an order (like a receipt line item).
    
    Example: Order #123 contains:
      - 2x Veg Burger @ ₹80 = ₹160   ← this is one OrderItem
      - 1x Cold Coffee @ ₹60 = ₹60   ← this is another OrderItem
    """
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True)
    
    # We store name and price at time of order — in case you change the menu later
    item_name = db.Column(db.String(200), nullable=False)    # Snapshot of name
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)# Price when ordered
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)  # unit_price × quantity

    def to_dict(self):
        return {
            "id": self.id,
            "item_name": self.item_name,
            "unit_price": float(self.unit_price),
            "quantity": self.quantity,
            "subtotal": float(self.subtotal)
        }


# ══════════════════════════════════════════════════════════════════
# MODEL 6: CONTACT MESSAGE
# Messages submitted via the contact form
# ══════════════════════════════════════════════════════════════════
class ContactMessage(db.Model):
    """Stores contact form submissions from customers"""
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)   # Admin can mark as read
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "subject": self.subject,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
