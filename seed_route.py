"""Add a temporary seed endpoint to seed menu on Render"""
from app import create_app, db
from app.models import MenuItem

# Add this to app/__init__.py temporarily
seed_code = '''
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
            ("Caffè Mocha","coffee",90),("Chocolate Coffee","coffee",90),
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
        return "Seeded " + str(len(items)) + " menu items successfully!"
'''
print(seed_code)
