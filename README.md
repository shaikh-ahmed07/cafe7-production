# ☕ Cafe 7 — Production-Grade Web Application

## Project Overview

Cafe 7 is a full-stack restaurant ordering system built with:
- **Frontend**: Your existing HTML/CSS/JavaScript pages
- **Backend**: Python Flask REST API  
- **Database**: PostgreSQL (primary) + Redis (cache)
- **Auth**: JWT (JSON Web Tokens)

---

## 🗂️ Project Structure

```
cafe7/
├── run.py                      ← Start the server (entry point)
├── requirements.txt            ← All Python packages
├── .env                        ← Your secret keys (NEVER commit this!)
│
├── config/
│   └── settings.py             ← Dev/Test/Production settings
│
├── app/                        ← Main application package
│   ├── __init__.py             ← App factory (creates Flask app)
│   ├── models/
│   │   └── __init__.py         ← Database tables (User, MenuItem, Order...)
│   └── routes/
│       ├── auth_routes.py      ← /api/auth/* (register, login)
│       ├── menu_routes.py      ← /api/menu/* (get menu items)
│       ├── cart_routes.py      ← /api/cart/* (add/remove items)
│       ├── order_routes.py     ← /api/orders/* (place orders)
│       └── contact_routes.py   ← /api/contact/* (contact form)
│
├── static/
│   └── js/
│       └── api-client.js       ← Frontend JS that calls the API
│
└── tests/
    └── test_api.py             ← Automated tests
```

---

## 🚀 Quick Start (Step by Step)

### Step 1: Install Python packages
```bash
pip install -r requirements.txt
```

### Step 2: Install and start PostgreSQL
- Download from: https://www.postgresql.org/download/
- Create a database:
```sql
CREATE DATABASE cafe7_db;
```

### Step 3: Install and start Redis
```bash
# Ubuntu/Mac:
sudo apt install redis-server   # or: brew install redis
redis-server                    # Start Redis
```

### Step 4: Create your .env file
Create a file called `.env` in the root folder:
```
SECRET_KEY=your-super-secret-random-string-here
JWT_SECRET_KEY=another-secret-for-jwt-tokens
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/cafe7_db
REDIS_HOST=localhost
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-app-password
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=your-secret
```

### Step 5: Initialize the database
```bash
flask db init       # Create migrations folder
flask db migrate    # Generate migration files
flask db upgrade    # Apply migrations (creates tables)
```

### Step 6: Run the server
```bash
python run.py
```

Server starts at: **http://localhost:5000**

---

## 🧪 API Endpoints Reference

| Method | URL | Auth? | Description |
|--------|-----|-------|-------------|
| POST | /api/auth/register | No | Create account |
| POST | /api/auth/login | No | Get JWT tokens |
| GET | /api/auth/me | Yes | Get profile |
| GET | /api/menu/ | No | Get all menu items |
| GET | /api/menu/category/burger | No | Items by category |
| GET | /api/cart/ | Yes | View cart |
| POST | /api/cart/add | Yes | Add to cart |
| DELETE | /api/cart/remove/<id> | Yes | Remove from cart |
| POST | /api/orders/ | Yes | Place order |
| GET | /api/orders/ | Yes | Order history |
| POST | /api/contact/ | No | Contact form |

---

## 🧪 Running Tests
```bash
pytest tests/ -v                    # Run all tests
pytest tests/ -v --cov=app         # With code coverage report
pytest tests/test_api.py::TestAuthentication::test_register_success -v  # One test
```

---

## 🌐 Hosting Options

### Option 1: Render.com (Free tier, easiest)
1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect your GitHub repo
4. Set environment variables in Render dashboard
5. Deploy!

### Option 2: Railway.app (Free tier + PostgreSQL)
1. `npm install -g @railway/cli`
2. `railway login`
3. `railway init`
4. `railway up`

### Option 3: AWS/GCP/Azure (Production-grade, paid)
- AWS Elastic Beanstalk or ECS
- Use RDS for PostgreSQL, ElastiCache for Redis

---

## 💰 Selling as SaaS (Software as a Service)

To sell Cafe 7 to restaurants:

### Option A: White-Label SaaS
- Host ONE shared platform
- Each restaurant gets their own subdomain: `restaurant-name.cafe7.com`
- Add a `restaurant_id` column to every database table
- Charge monthly subscription: ₹999-₹4999/month

### Option B: Self-Hosted License
- Sell the codebase as a one-time purchase
- Restaurant deploys on their own server
- Price: ₹15,000-₹50,000 + setup fee

### Key features to add for SaaS:
- Admin dashboard with analytics
- Stripe/Razorpay subscription billing
- Custom branding (logo, colors, domain)
- Multiple restaurant management
- Real-time order tracking

---

## 📊 Testing Strategy (V1)

### Level 1: Unit Tests (automated)
Test individual functions:
- Password hashing works
- Price calculation is correct
- JWT token generation/validation

### Level 2: Integration Tests (automated)
Test full API flows:
- Register → Login → Add to Cart → Place Order
- All test cases in `tests/test_api.py`

### Level 3: Manual Testing (you do this)
- Open the website, browse menu
- Add items to cart, place order
- Check that order appears in database
- Test on mobile (different screen sizes)

### Level 4: Load Testing (before launch)
- Use Apache JMeter or Locust
- Test: "Can 100 users order at the same time?"
- Identify slow database queries

---

## 🔒 Security Checklist

- [x] Passwords hashed with BCrypt (never stored plain)
- [x] JWT tokens for stateless authentication
- [x] SQL injection prevented by SQLAlchemy ORM
- [x] CORS configured (only your frontend can call API)
- [x] Input validation on all endpoints
- [ ] HTTPS (SSL certificate — add when deploying)
- [ ] Rate limiting (prevent DDoS attacks) — add flask-limiter
- [ ] Logging all security events
