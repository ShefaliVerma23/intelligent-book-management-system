# Testing Guide - Intelligent Book Management System

This document provides comprehensive instructions for testing all APIs and functionalities of the Intelligent Book Management System.

---

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Prerequisites](#prerequisites)
3. [Method 1: Automated Testing with Pytest](#method-1-automated-testing-with-pytest)
4. [Method 2: Manual API Testing Script](#method-2-manual-api-testing-script)
5. [Method 3: Interactive Testing with Swagger UI](#method-3-interactive-testing-with-swagger-ui)
6. [Method 4: Testing with cURL Commands](#method-4-testing-with-curl-commands)
7. [Method 5: Testing with Postman](#method-5-testing-with-postman)
8. [Test Coverage Report](#test-coverage-report)
9. [Test File Structure](#test-file-structure)
10. [Endpoint Testing Reference](#endpoint-testing-reference)

---

## Testing Overview

The system includes **88 comprehensive tests** covering all endpoints and functionalities:

| Test Category | Test Count | Description |
|---------------|------------|-------------|
| Authentication | 11 | User registration, login, logout, token validation |
| Books CRUD | 18 | Create, read, update, delete books + filtering |
| Reviews CRUD | 13 | Create, read, update, delete reviews |
| Recommendations | 14 | Popular books, similar books, ML recommendations |
| Users CRUD | 10 | User management operations |
| AI Summary | 22 | Book summaries, review summaries, content generation |

---

## Prerequisites

Before running tests, ensure you have:

```bash
# 1. Navigate to project directory
cd /Users/shefaliverma/Documents/intelligent-book-management-system

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Verify installation
python -c "import pytest; print('pytest version:', pytest.__version__)"
```

---

## Method 1: Automated Testing with Pytest

### Overview
Pytest provides comprehensive automated testing with async support for all API endpoints.

### Running Tests

#### Run All Tests
```bash
# Using pytest directly
python -m pytest tests/ -v

# Using the shell script
./run_tests.sh all
```

#### Run Specific Test Categories
```bash
# Book tests only
./run_tests.sh books
# or
python -m pytest tests/test_books.py -v

# Review tests only
./run_tests.sh reviews
# or
python -m pytest tests/test_reviews.py -v

# Authentication tests only
./run_tests.sh auth
# or
python -m pytest tests/test_auth.py -v

# Recommendation tests only
./run_tests.sh recs
# or
python -m pytest tests/test_recommendations.py -v

# User tests only
python -m pytest tests/test_users.py -v
```

#### Run with Verbose Output
```bash
./run_tests.sh verbose
# or
python -m pytest tests/ -v -s
```

#### Run a Single Test
```bash
python -m pytest tests/test_books.py::TestBooks::test_create_book -v
```

### Expected Output
```
============================= test session starts ==============================
platform darwin -- Python 3.11.12, pytest-7.4.3
plugins: asyncio-0.21.1, anyio-3.7.1
asyncio: mode=Mode.AUTO
collected 66 items

tests/test_auth.py::TestAuthentication::test_register_user PASSED        [  1%]
tests/test_auth.py::TestAuthentication::test_login_success PASSED        [  6%]
...
tests/test_users.py::TestUsers::test_update_user_preferences PASSED      [100%]

============================= 66 passed in 14.15s ==============================
```

---

## Method 2: Manual API Testing Script

### Overview
A custom Python script that tests all API endpoints against a running server with colored output and detailed results.

### Running the Script

#### Step 1: Start the Server
```bash
# Terminal 1
cd /Users/shefaliverma/Documents/intelligent-book-management-system
source venv/bin/activate
uvicorn app.main:app --reload
```

#### Step 2: Run the Test Script
```bash
# Terminal 2
cd /Users/shefaliverma/Documents/intelligent-book-management-system
source venv/bin/activate
python scripts/test_api.py
```

Or using the shell script:
```bash
./run_tests.sh api
```

### Expected Output
```
============================================================
  INTELLIGENT BOOK MANAGEMENT SYSTEM - API TESTS
============================================================

Testing against: http://localhost:8000
Time: 2025-12-19 17:07:08

============================================================
1. BASIC ENDPOINTS
============================================================

  ✓ PASS | GET /health - Health check
  ✓ PASS | GET / - Root endpoint

============================================================
2. BOOK ENDPOINTS (CRUD)
============================================================

  ✓ PASS | POST /books - Create book
  ✓ PASS | GET /books - Get all books
  ✓ PASS | GET /books/<id> - Get book by ID
  ...

============================================================
  TEST SUMMARY
============================================================

  Total Tests: 22
  Passed: 22
  Failed: 0
  Success Rate: 100.0%

  🎉 ALL TESTS PASSED! 🎉
```

---

## Method 3: Interactive Testing with Swagger UI

### Overview
FastAPI provides an automatic interactive API documentation interface.

### Accessing Swagger UI

1. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Open in browser:**
   ```
   http://localhost:8000/docs
   ```

3. **Alternative ReDoc interface:**
   ```
   http://localhost:8000/redoc
   ```

### Using Swagger UI

1. **Expand an endpoint** - Click on any endpoint to expand it
2. **Try it out** - Click the "Try it out" button
3. **Fill parameters** - Enter required parameters and request body
4. **Execute** - Click "Execute" to send the request
5. **View response** - See the response code, body, and headers

### Testing Authentication Flow

1. **Register a user:** `POST /api/v1/auth/register`
2. **Login:** `POST /api/v1/auth/login`
3. **Copy the access_token** from response
4. **Click "Authorize"** button (top right)
5. **Enter:** `Bearer <your_token>`
6. **Now test protected endpoints**

---

## Method 4: Testing with cURL Commands

### Overview
Command-line testing using cURL for quick endpoint verification.

### Setup
```bash
# Set base URL variable
BASE_URL="http://localhost:8000/api/v1"
```

### Book Endpoints

```bash
# POST /books - Create a new book
curl -X POST "$BASE_URL/books/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "genre": "Fiction",
    "year_published": 1925,
    "summary": "A story about the American Dream in the Jazz Age."
  }'

# GET /books - Get all books
curl -X GET "$BASE_URL/books/"

# GET /books - Get books with filtering
curl -X GET "$BASE_URL/books/?genre=Fiction&author=Fitzgerald"

# GET /books - Search books
curl -X GET "$BASE_URL/books/?search=gatsby"

# GET /books/<id> - Get book by ID
curl -X GET "$BASE_URL/books/1"

# PUT /books/<id> - Update a book
curl -X PUT "$BASE_URL/books/1" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Updated: A classic American novel about wealth and dreams."
  }'

# DELETE /books/<id> - Delete a book
curl -X DELETE "$BASE_URL/books/1"

# POST /books/<id>/generate-summary - Generate AI summary for book
curl -X POST "$BASE_URL/books/1/generate-summary"

# GET /books/<id>/summary - Get book summary with review aggregation
curl -X GET "$BASE_URL/books/1/summary"
```

### Review Endpoints

```bash
# POST /books/<id>/reviews - Add review to book
curl -X POST "$BASE_URL/books/1/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "rating": 4.5,
    "review_text": "Excellent book! A timeless classic."
  }'

# GET /books/<id>/reviews - Get all reviews for a book
curl -X GET "$BASE_URL/books/1/reviews"

# GET /reviews/<id> - Get review by ID
curl -X GET "$BASE_URL/reviews/1"

# PUT /reviews/<id> - Update a review
curl -X PUT "$BASE_URL/reviews/1" \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5.0,
    "review_text": "Updated: Absolutely magnificent!"
  }'

# DELETE /reviews/<id> - Delete a review
curl -X DELETE "$BASE_URL/reviews/1"

# GET /reviews/book/<id>/summary - Get AI summary of reviews
curl -X GET "$BASE_URL/reviews/book/1/summary"
```

### Recommendation Endpoints

```bash
# GET /recommendations/popular - Get popular books
curl -X GET "$BASE_URL/recommendations/popular"

# GET /recommendations/popular with filters
curl -X GET "$BASE_URL/recommendations/popular?limit=10&genre=Fiction"

# GET /recommendations/similar/<id> - Get similar books
curl -X GET "$BASE_URL/recommendations/similar/1?limit=5"
```

### Generate Summary Endpoint

```bash
# POST /generate-summary - Generate AI summary for content
curl -X POST "$BASE_URL/generate-summary" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a story about a young wizard who discovers magical powers. He attends a prestigious school for wizards and makes lifelong friends. Together, they embark on adventures and face challenges that test their courage and friendship."
  }'
```

### Authentication Endpoints

```bash
# POST /auth/register - Register new user
curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123",
    "full_name": "Test User"
  }'

# POST /auth/login - Login (get token)
curl -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepassword123"

# GET /auth/me - Get current user (requires auth)
curl -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# POST /auth/logout - Logout
curl -X POST "$BASE_URL/auth/logout"
```

### Health Check

```bash
# Health check endpoint
curl -X GET "http://localhost:8000/health"

# Root endpoint
curl -X GET "http://localhost:8000/"
```

---

## Method 5: Testing with Postman

### Overview
Import API endpoints into Postman for team collaboration and advanced testing.

### Setup

1. **Create a new Collection** named "Book Management API"

2. **Set Environment Variables:**
   - `base_url`: `http://localhost:8000/api/v1`
   - `access_token`: (will be set after login)

3. **Create Requests:**

#### Books Collection
| Method | Name | URL |
|--------|------|-----|
| POST | Create Book | `{{base_url}}/books/` |
| GET | Get All Books | `{{base_url}}/books/` |
| GET | Get Book by ID | `{{base_url}}/books/:id` |
| PUT | Update Book | `{{base_url}}/books/:id` |
| DELETE | Delete Book | `{{base_url}}/books/:id` |
| GET | Get Book Summary | `{{base_url}}/books/:id/summary` |
| POST | Generate Book Summary | `{{base_url}}/books/:id/generate-summary` |

#### Reviews Collection
| Method | Name | URL |
|--------|------|-----|
| POST | Add Review | `{{base_url}}/books/:id/reviews` |
| GET | Get Book Reviews | `{{base_url}}/books/:id/reviews` |
| GET | Get Review | `{{base_url}}/reviews/:id` |
| PUT | Update Review | `{{base_url}}/reviews/:id` |
| DELETE | Delete Review | `{{base_url}}/reviews/:id` |

#### Recommendations Collection
| Method | Name | URL |
|--------|------|-----|
| GET | Popular Books | `{{base_url}}/recommendations/popular` |
| GET | Similar Books | `{{base_url}}/recommendations/similar/:id` |

#### AI Summary
| Method | Name | URL |
|--------|------|-----|
| POST | Generate Summary | `{{base_url}}/generate-summary` |

### Auto-set Token Script
Add this to your Login request's "Tests" tab:
```javascript
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    pm.environment.set("access_token", jsonData.access_token);
}
```

---

## Test Coverage Report

### Generate Coverage Report
```bash
./run_tests.sh coverage
# or
python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

### View HTML Report
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Expected Coverage
```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
app/__init__.py                             0      0   100%
app/api/__init__.py                         0      0   100%
app/api/routes/__init__.py                  0      0   100%
app/api/routes/auth.py                     35      2    94%
app/api/routes/books.py                    58      3    95%
app/api/routes/recommendations.py          47      4    91%
app/api/routes/reviews.py                  38      2    95%
app/api/routes/users.py                    32      2    94%
app/api/schemas.py                         48      0   100%
app/config/settings.py                     22      0   100%
app/main.py                                45      5    89%
app/models/base.py                         35      3    91%
app/models/books.py                        14      0   100%
app/models/reviews.py                      17      0   100%
app/models/users.py                        28      2    93%
app/services/auth_service.py              42      4    90%
app/services/book_service.py              38      2    95%
app/services/llama_service.py             72      8    89%
app/services/recommendation_service.py    85      6    93%
app/services/review_service.py            48      3    94%
app/services/user_service.py              35      2    94%
-----------------------------------------------------------
TOTAL                                     739     48    94%
```

---

## Test File Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
│   ├── event_loop          # Async event loop fixture
│   ├── setup_database      # Database setup/teardown
│   ├── db_session          # Database session fixture
│   ├── async_client        # Async HTTP client fixture
│   ├── test_user           # Test user fixture
│   ├── test_book           # Test book fixture
│   ├── test_review         # Test review fixture
│   └── auth_headers        # Authentication headers fixture
├── test_auth.py             # Authentication tests (11 tests)
│   ├── test_register_user
│   ├── test_register_duplicate_email
│   ├── test_login_success
│   ├── test_login_wrong_password
│   ├── test_get_current_user
│   └── ... more
├── test_books.py            # Book CRUD tests (18 tests)
│   ├── test_create_book
│   ├── test_get_books
│   ├── test_get_book_by_id
│   ├── test_update_book
│   ├── test_delete_book
│   ├── test_filter_books_by_genre
│   ├── test_generate_book_summary
│   └── ... more
├── test_reviews.py          # Review CRUD tests (13 tests)
│   ├── test_create_review
│   ├── test_get_reviews
│   ├── test_update_review
│   ├── test_delete_review
│   ├── test_get_book_review_summary
│   └── ... more
├── test_recommendations.py  # Recommendation tests (14 tests)
│   ├── test_get_popular_books
│   ├── test_get_similar_books
│   ├── test_generate_summary
│   └── ... more
└── test_users.py            # User CRUD tests (10 tests)
    ├── test_create_user
    ├── test_get_users
    ├── test_update_user
    ├── test_delete_user
    └── ... more

scripts/
└── test_api.py              # Manual API testing script (22 tests)
```

---

## Endpoint Testing Reference

### Required Endpoints (As Per Specification)

| # | Endpoint | Method | Status | Test File |
|---|----------|--------|--------|-----------|
| 1 | `/books` | POST | ✅ Tested | test_books.py |
| 2 | `/books` | GET | ✅ Tested | test_books.py |
| 3 | `/books/<id>` | GET | ✅ Tested | test_books.py |
| 4 | `/books/<id>` | PUT | ✅ Tested | test_books.py |
| 5 | `/books/<id>` | DELETE | ✅ Tested | test_books.py |
| 6 | `/books/<id>/reviews` | POST | ✅ Tested | test_books.py |
| 7 | `/books/<id>/reviews` | GET | ✅ Tested | test_books.py |
| 8 | `/books/<id>/summary` | GET | ✅ Tested | test_books.py |
| 9 | `/recommendations` | GET | ✅ Tested | test_recommendations.py |
| 10 | `/generate-summary` | POST | ✅ Tested | test_recommendations.py |

### Additional Endpoints Tested

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/register` | POST | User registration |
| `/auth/login` | POST | User login |
| `/auth/me` | GET | Current user profile |
| `/auth/logout` | POST | User logout |
| `/users/` | GET, POST | User CRUD |
| `/users/<id>` | GET, PUT, DELETE | User CRUD |
| `/reviews/` | GET, POST | Review CRUD |
| `/reviews/<id>` | GET, PUT, DELETE | Review CRUD |
| `/recommendations/popular` | GET | Popular books |
| `/recommendations/similar/<id>` | GET | Similar books |

---

## Troubleshooting

### Common Issues

#### 1. Server Not Running
```
ERROR: Could not connect to server at http://localhost:8000
```
**Solution:** Start the server first:
```bash
uvicorn app.main:app --reload
```

#### 2. Database Connection Error
```
sqlalchemy.exc.OperationalError: connection refused
```
**Solution:** Check database configuration in `.env` file

#### 3. Test Fixtures Not Loading
```
AttributeError: 'async_generator' object has no attribute 'post'
```
**Solution:** Ensure `pytest.ini` has `asyncio_mode = auto`

#### 4. Import Errors
```
ModuleNotFoundError: No module named 'app'
```
**Solution:** Run tests from project root directory

---

## Quick Reference Commands

```bash
# All pytest tests
python -m pytest tests/ -v

# Single test file
python -m pytest tests/test_books.py -v

# Single test
python -m pytest tests/test_books.py::TestBooks::test_create_book -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=html

# Manual API tests
python scripts/test_api.py

# Using shell script
./run_tests.sh all      # All tests
./run_tests.sh books    # Book tests
./run_tests.sh reviews  # Review tests
./run_tests.sh auth     # Auth tests
./run_tests.sh recs     # Recommendation tests
./run_tests.sh coverage # With coverage
./run_tests.sh api      # Manual API tests
```

---

## Contact

For any testing-related questions or issues, please refer to the main README.md or create an issue in the project repository.

