"""
====================================================================
CAFE 7 - AUTOMATED TESTS
====================================================================
What is testing?
  Testing means writing code that CHECKS your code works correctly.
  
  Instead of manually clicking through the website every time you
  change something, tests do it automatically!
  
  Example:
    "When I register with a valid email, I should get a JWT token back"
  
  If you break something later, the test fails and tells you exactly
  what broke. Very useful!

Types of tests here:
  - Unit tests: test one function in isolation
  - Integration tests: test the full API endpoint (request → response)
  
How to run tests:
  pip install pytest pytest-flask
  pytest tests/ -v   (-v = verbose, shows each test name)
  
  To run just one test:
  pytest tests/test_auth.py::TestAuth::test_register -v
====================================================================
"""

import pytest
import json
from app import create_app, db
from app.models import User, MenuItem, Order


# ─── Test Setup ───────────────────────────────────────────────────

@pytest.fixture
def app():
    """
    A "fixture" is a setup function — pytest runs it before each test.
    
    This creates a fresh test application with:
    - Testing config (in-memory SQLite database)
    - Blank database for each test (so tests don't interfere)
    """
    app = create_app("testing")
    
    with app.app_context():
        db.create_all()      # Create all tables
        yield app             # Run the test
        db.session.remove()
        db.drop_all()         # Clean up after test


@pytest.fixture
def client(app):
    """
    Test client — lets us make fake HTTP requests without a real server.
    Like Postman, but automated!
    """
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create a sample user in the test database."""
    with app.app_context():
        user = User(name="Test User", email="test@cafe7.com", phone="9876543210")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def sample_menu_item(app):
    """Create a sample menu item in the test database."""
    with app.app_context():
        item = MenuItem(
            name="Veg Burger",
            price=80.00,
            category="burger",
            is_available=True
        )
        db.session.add(item)
        db.session.commit()
        return item


def get_auth_token(client, email="test@cafe7.com", password="password123"):
    """Helper function: log in and return the JWT access token."""
    response = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    return response.json["access_token"]


# ═══════════════════════════════════════════════════════════════════
# TEST CLASS 1: AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════

class TestAuthentication:
    """Test the /api/auth/* endpoints"""
    
    def test_register_success(self, client):
        """
        TEST: Registering with valid data should work.
        
        We send: name, email, password
        We expect: HTTP 201 (Created) + JWT tokens
        """
        response = client.post("/api/auth/register", json={
            "name": "Ahmed Ali",
            "email": "ahmed@test.com",
            "password": "securepass123"
        })
        
        # Check HTTP status code
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        
        # Check response has the expected fields
        data = response.json
        assert "access_token" in data, "Response should contain access_token"
        assert "refresh_token" in data, "Response should contain refresh_token"
        assert "user" in data, "Response should contain user info"
        assert data["user"]["email"] == "ahmed@test.com"
    
    def test_register_duplicate_email(self, client, sample_user):
        """
        TEST: Registering with an already-used email should fail.
        Expected: HTTP 409 (Conflict)
        """
        response = client.post("/api/auth/register", json={
            "name": "Another User",
            "email": "test@cafe7.com",   # Same as sample_user
            "password": "password123"
        })
        assert response.status_code == 409
    
    def test_register_missing_fields(self, client):
        """
        TEST: Registering without required fields should fail.
        Expected: HTTP 400 (Bad Request)
        """
        response = client.post("/api/auth/register", json={
            "name": "Ahmed",
            # Missing email and password!
        })
        assert response.status_code == 400
    
    def test_register_short_password(self, client):
        """
        TEST: Password less than 8 characters should be rejected.
        """
        response = client.post("/api/auth/register", json={
            "name": "Ahmed Ali",
            "email": "ahmed2@test.com",
            "password": "abc"   # Too short!
        })
        assert response.status_code == 400
    
    def test_login_success(self, client, sample_user):
        """
        TEST: Login with correct credentials should return tokens.
        """
        response = client.post("/api/auth/login", json={
            "email": "test@cafe7.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json
        assert "access_token" in data
        assert data["user"]["email"] == "test@cafe7.com"
    
    def test_login_wrong_password(self, client, sample_user):
        """
        TEST: Wrong password should return 401 (Unauthorized).
        """
        response = client.post("/api/auth/login", json={
            "email": "test@cafe7.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_login_wrong_email(self, client):
        """
        TEST: Non-existent email should return 401 (not 404!).
        We don't want to reveal which emails are registered.
        """
        response = client.post("/api/auth/login", json={
            "email": "notregistered@test.com",
            "password": "anypassword"
        })
        assert response.status_code == 401
    
    def test_get_profile_requires_auth(self, client):
        """
        TEST: Accessing /api/auth/me without a token should fail.
        Expected: HTTP 401
        """
        response = client.get("/api/auth/me")
        assert response.status_code == 401
    
    def test_get_profile_with_token(self, client, sample_user):
        """
        TEST: Accessing /api/auth/me with valid token should return user data.
        """
        token = get_auth_token(client)
        
        response = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        assert response.json["user"]["email"] == "test@cafe7.com"


# ═══════════════════════════════════════════════════════════════════
# TEST CLASS 2: MENU
# ═══════════════════════════════════════════════════════════════════

class TestMenu:
    """Test the /api/menu/* endpoints"""
    
    def test_get_all_menu_items(self, client, sample_menu_item):
        """
        TEST: Getting menu should return list of items.
        No login required for viewing the menu!
        """
        response = client.get("/api/menu/")
        assert response.status_code == 200
        data = response.json
        assert "items" in data
        assert len(data["items"]) >= 1
    
    def test_get_items_by_category(self, client, sample_menu_item):
        """
        TEST: Filter by category should only return matching items.
        """
        response = client.get("/api/menu/category/burger")
        assert response.status_code == 200
        items = response.json["items"]
        
        # Every returned item should be a burger
        for item in items:
            assert item["category"] == "burger", f"Expected burger, got {item['category']}"
    
    def test_get_categories_list(self, client, sample_menu_item):
        """
        TEST: Should return list of available categories.
        """
        response = client.get("/api/menu/categories")
        assert response.status_code == 200
        assert "categories" in response.json
        assert isinstance(response.json["categories"], list)
    
    def test_menu_item_has_required_fields(self, client, sample_menu_item):
        """
        TEST: Each menu item in response should have all required fields.
        """
        response = client.get("/api/menu/")
        items = response.json["items"]
        
        required_fields = ["id", "name", "price", "category"]
        for item in items:
            for field in required_fields:
                assert field in item, f"Menu item missing field: {field}"


# ═══════════════════════════════════════════════════════════════════
# TEST CLASS 3: CART
# ═══════════════════════════════════════════════════════════════════

class TestCart:
    """Test the /api/cart/* endpoints"""
    
    def test_cart_requires_login(self, client):
        """
        TEST: Viewing cart without login should fail.
        """
        response = client.get("/api/cart/")
        assert response.status_code == 401
    
    def test_add_to_cart(self, client, sample_user, sample_menu_item):
        """
        TEST: Adding a valid item to cart should succeed.
        """
        token = get_auth_token(client)
        
        response = client.post("/api/cart/add",
            json={"menu_item_id": sample_menu_item.id, "quantity": 2},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
    
    def test_cart_shows_added_items(self, client, sample_user, sample_menu_item):
        """
        TEST: After adding item, cart should contain it.
        """
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Add item
        client.post("/api/cart/add",
            json={"menu_item_id": sample_menu_item.id, "quantity": 1},
            headers=headers
        )
        
        # Get cart
        response = client.get("/api/cart/", headers=headers)
        assert response.status_code == 200
        cart = response.json
        assert cart["item_count"] == 1
        assert len(cart["items"]) == 1
    
    def test_remove_from_cart(self, client, sample_user, sample_menu_item):
        """
        TEST: Removing an item should reduce cart count.
        """
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Add item
        client.post("/api/cart/add",
            json={"menu_item_id": sample_menu_item.id, "quantity": 1},
            headers=headers
        )
        
        # Get cart to find item ID
        cart_response = client.get("/api/cart/", headers=headers)
        cart_item_id = cart_response.json["items"][0]["id"]
        
        # Remove it
        response = client.delete(f"/api/cart/remove/{cart_item_id}", headers=headers)
        assert response.status_code == 200
        
        # Cart should now be empty
        cart_response = client.get("/api/cart/", headers=headers)
        assert cart_response.json["item_count"] == 0


# ═══════════════════════════════════════════════════════════════════
# TEST CLASS 4: ORDERS
# ═══════════════════════════════════════════════════════════════════

class TestOrders:
    """Test the /api/orders/* endpoints"""
    
    def test_place_order(self, client, sample_user, sample_menu_item):
        """
        TEST: Placing an order with valid items should succeed.
        """
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/orders/", json={
            "delivery_address": "123 Test Street, Hyderabad",
            "customer_phone": "9876543210",
            "customer_name": "Test User",
            "payment_method": "cash_on_delivery",
            "items": [
                {"menu_item_id": sample_menu_item.id, "quantity": 2}
            ]
        }, headers=headers)
        
        assert response.status_code == 201
        data = response.json
        assert "order_id" in data
        assert "total_amount" in data
    
    def test_order_total_calculation(self, client, sample_user, sample_menu_item):
        """
        TEST: Order total should be: (price × qty) + delivery charge
        
        sample_menu_item price = ₹80
        1 item: subtotal = ₹80, delivery = ₹30, total = ₹110
        """
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/orders/", json={
            "delivery_address": "123 Test Street",
            "customer_phone": "9876543210",
            "items": [{"menu_item_id": sample_menu_item.id, "quantity": 1}]
        }, headers=headers)
        
        data = response.json
        expected_total = 80.00 + 30.00  # price + delivery charge
        assert data["total_amount"] == expected_total
    
    def test_order_history(self, client, sample_user, sample_menu_item):
        """
        TEST: Placed orders should appear in order history.
        """
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Place an order
        client.post("/api/orders/", json={
            "delivery_address": "123 Test Street",
            "customer_phone": "9876543210",
            "items": [{"menu_item_id": sample_menu_item.id, "quantity": 1}]
        }, headers=headers)
        
        # Check order history
        response = client.get("/api/orders/", headers=headers)
        assert response.status_code == 200
        orders = response.json["orders"]
        assert len(orders) >= 1


# ═══════════════════════════════════════════════════════════════════
# TEST CLASS 5: CONTACT
# ═══════════════════════════════════════════════════════════════════

class TestContact:
    """Test the /api/contact/* endpoints"""
    
    def test_submit_contact(self, client):
        """
        TEST: Submitting a contact message should succeed.
        No login required!
        """
        response = client.post("/api/contact/", json={
            "name": "Customer",
            "email": "customer@test.com",
            "message": "I loved the food! Great service."
        })
        assert response.status_code == 201
        assert "message" in response.json
    
    def test_contact_missing_fields(self, client):
        """
        TEST: Contact form without required fields should fail.
        """
        response = client.post("/api/contact/", json={
            "name": "Customer"
            # Missing email and message
        })
        assert response.status_code == 400


# ─── Run tests ───────────────────────────────────────────────────
if __name__ == "__main__":
    # Run: python tests/test_api.py
    # Or better: pytest tests/ -v
    pytest.main([__file__, "-v"])
