"""
Run this once to add all Cafe 7 menu items to the database.
Usage: python seed_menu.py
"""
from app import create_app, db
from app.models import MenuItem

app = create_app("development")

menu_items = [
    # BURGERS
    {"name": "Veg Burger", "price": 80, "category": "burger", "image_url": "images/veg burger.jfif"},
    {"name": "Veg Cheese Burger", "price": 100, "category": "burger", "image_url": "images/veg cheese burger.jfif"},
    {"name": "Grilled Chicken Burger", "price": 120, "category": "burger", "image_url": "images/Grilled chicken burger.jfif"},
    {"name": "Grilled Chicken Cheese Burger", "price": 140, "category": "burger", "image_url": "images/Grilled chicken  cheese burger.jfif"},
    {"name": "KFC Zinger Burger", "price": 150, "category": "burger", "image_url": "images/kfc zinger burger.jfif"},
    {"name": "Cheese Chicken Burger", "price": 130, "category": "burger", "image_url": "images/cheese  chick burger.jfif"},
    # PIZZAS
    {"name": "Margherita", "price": 150, "category": "pizza", "image_url": "images/magherita.jfif"},
    {"name": "Veg Cheese Burst", "price": 180, "category": "pizza", "image_url": "images/veg cheese burst.jfif"},
    {"name": "Corn Cheese Burst", "price": 190, "category": "pizza", "image_url": "images/corn cheese burst.jfif"},
    {"name": "Veg Mexican Cheese Burst", "price": 200, "category": "pizza", "image_url": "images/veg mexican cheese burst.jfif"},
    {"name": "Chicken Cheese Burst", "price": 220, "category": "pizza", "image_url": "images/chicken cheeese burst.jfif"},
    {"name": "Chicken Mexican Cheese Burst", "price": 230, "category": "pizza", "image_url": "images/chicken mexican cheese burst.jfif"},
    # WRAPS
    {"name": "Egg Wrap", "price": 80, "category": "wrap", "image_url": "images/egg wrap.jfif"},
    {"name": "Egg Cheese Wrap", "price": 100, "category": "wrap", "image_url": "images/egg cheese wrap.jfif"},
    {"name": "Paneer Wrap", "price": 100, "category": "wrap", "image_url": "images/paneer wrap.jfif"},
    {"name": "Paneer Cheese Wrap", "price": 120, "category": "wrap", "image_url": "images/paneer cheese wrap.jfif"},
    {"name": "Chicken Cheese Wrap", "price": 130, "category": "wrap", "image_url": "images/chciken cheese wrap.jfif"},
    # SHAWARMA
    {"name": "Shawarma", "price": 80, "category": "shawarma", "image_url": "images/shawarma.jfif"},
    {"name": "Special Shawarma", "price": 100, "category": "shawarma", "image_url": "images/special shawarma.jfif"},
    {"name": "Dry Fruits Shawarma", "price": 120, "category": "shawarma", "image_url": "images/dry fruits shawarma.jfif"},
    {"name": "Chicken Cheese Shawarma", "price": 120, "category": "shawarma", "image_url": "images/chicken  cheese shawarma.jfif"},
    # COFFEE
    {"name": "Americano", "price": 60, "category": "coffee", "image_url": "images/americano.jfif"},
    {"name": "Latte", "price": 80, "category": "coffee", "image_url": "images/latte.jfif"},
    {"name": "Caffe Mocha", "price": 90, "category": "coffee", "image_url": "images/caffe-mocha.jpeg"},
    {"name": "Chocolate Coffee", "price": 90, "category": "coffee", "image_url": "images/chocolate coffee.jfif"},
    {"name": "Cold Coffee", "price": 80, "category": "coffee", "image_url": "images/cold cofee shake.jfif"},
    {"name": "Cold Coffee with Crush", "price": 100, "category": "coffee", "image_url": "images/cold coffee with crush.avif"},
    {"name": "RedBull Coffee", "price": 150, "category": "coffee", "image_url": "images/redbull coffee.jpg"},
    # SHAKES
    {"name": "Strawberry Shake", "price": 80, "category": "shake", "image_url": "images/strawberry.jpg"},
    {"name": "Mango Shake", "price": 80, "category": "shake", "image_url": "images/mango.webp"},
    {"name": "Vanilla Shake", "price": 80, "category": "shake", "image_url": "images/vanilla.jpg"},
    {"name": "Oreo Shake", "price": 100, "category": "shake", "image_url": "images/oreo.jfif"},
    {"name": "KitKat Shake", "price": 100, "category": "shake", "image_url": "images/kit kat.jpg"},
    {"name": "Butterscotch Shake", "price": 90, "category": "shake", "image_url": "images/butterscotch.jfif"},
    {"name": "Kiwi Shake", "price": 90, "category": "shake", "image_url": "images/kiwi.jpg"},
    {"name": "Blue Curacao", "price": 110, "category": "shake", "image_url": "images/blue curacao.jpg"},
    {"name": "Lemon Mint", "price": 70, "category": "shake", "image_url": "images/lemon mint.jfif"},
    {"name": "Blackcurrant", "price": 80, "category": "shake", "image_url": "images/blackcurrent.jfif"},
    {"name": "Peach", "price": 80, "category": "shake", "image_url": "images/peach.jfif"},
    {"name": "Sitafal", "price": 100, "category": "shake", "image_url": "images/sitafal.jfif"},
    # DESSERTS
    {"name": "Cream Kunafa", "price": 120, "category": "desert", "image_url": "desert-img/cream kunafa.jpg"},
    {"name": "Butterscotch Kunafa", "price": 130, "category": "desert", "image_url": "desert-img/butterscotch kunafa.jfif"},
    {"name": "Nutella Kunafa", "price": 140, "category": "desert", "image_url": "desert-img/nutella kunafa.jfif"},
    {"name": "Cream Cheese Kunafa", "price": 150, "category": "desert", "image_url": "desert-img/cream cheese kunafa.webp"},
    {"name": "Mango Cream", "price": 100, "category": "desert", "image_url": "desert-img/mango cream.jpg"},
    {"name": "Sitafal Cream", "price": 110, "category": "desert", "image_url": "desert-img/sitafal cream.jpg"},
    {"name": "Khajoor Cream", "price": 110, "category": "desert", "image_url": "desert-img/khajoor cream.jpg"},
    {"name": "Shehdood Cream", "price": 120, "category": "desert", "image_url": "desert-img/Shehdood cream.jpg"},
]

with app.app_context():
    # Clear existing items first
    MenuItem.query.delete()
    db.session.commit()
    
    for item_data in menu_items:
        item = MenuItem(
            name=item_data["name"],
            price=item_data["price"],
            category=item_data["category"],
            image_url=item_data["image_url"],
            is_available=True,
            is_featured=False
        )
        db.session.add(item)
    
    db.session.commit()
    print(f"✅ Successfully added {len(menu_items)} menu items!")
    print("\nCategories added:")
    from sqlalchemy import func
    results = db.session.query(MenuItem.category, func.count(MenuItem.id)).group_by(MenuItem.category).all()
    for category, count in results:
        print(f"  {category}: {count} items")
