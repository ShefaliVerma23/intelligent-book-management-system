# Intelligent Book Management System

An AI-powered book management system built with FastAPI, PostgreSQL, and Llama3 integration. The system provides comprehensive book management, user reviews, AI-generated summaries, and personalized recommendations.

---

## 📑 Table of Contents

1. [Quick Start Guide](#-quick-start-guide)
2. [Verification Guide](#-verification-guide)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [API Endpoints](#api-endpoints)
7. [Setup Instructions](#setup-instructions)
8. [Running the Application](#running-the-application)
9. [Testing](#testing)
10. [Database Schema](#database-schema)
11. [Deployment](#deployment)
12. [Security Features](#security-features)
13. [Bonus Features (Caching)](#bonus-features-implemented)
14. [Troubleshooting](#troubleshooting)
15. [Roadmap](#roadmap)

---

## 🚀 Quick Start Guide

### Option 1: Docker (Recommended - One Command Setup)

```bash
# Clone and start everything
git clone <repository-url>
cd intelligent-book-management-system
cp sample.env .env
cd docker && docker-compose --env-file ../.env up -d

# Verify it's running
curl http://localhost:8000/health
```

**Access Points:**
- 🌐 **API**: http://localhost:8000
- 📚 **Swagger Docs**: http://localhost:8000/docs
- 📊 **Cache Stats**: http://localhost:8000/cache/stats

### Option 2: Local Development (Without Docker)

```bash
# 1. Clone repository
git clone <repository-url>
cd intelligent-book-management-system

# 2. Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp sample.env .env
# Edit .env with your database credentials

# 4. Start PostgreSQL and Redis (if not running)
# macOS: brew services start postgresql && brew services start redis
# Ubuntu: sudo systemctl start postgresql redis

# 5. Create database
psql -U postgres -c "CREATE DATABASE intelligent_books_db;"
psql -U postgres -c "CREATE USER bookadmin WITH PASSWORD 'BookPass@2024Secure';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE intelligent_books_db TO bookadmin;"

# 6. Run migrations
alembic upgrade head

# 7. Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ✅ Verification Guide

### Step 1: Verify Application is Running

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0","ai_model":"...","cache_enabled":true}
```

### Step 2: Verify Redis Caching

```bash
# Method 1: Using test script
python scripts/test_caching.py

# Method 2: Using API endpoint
curl http://localhost:8000/cache/stats

# Expected response:
# {"status":"connected","hits":0,"misses":0,"keys":0}
```

### Step 3: Verify Database Connection

```bash
# Create a test user via API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"Test@123"}'

# Expected: User created successfully
```

### Step 4: Verify All Tests Pass

```bash
# Run complete test suite
python -m pytest tests/ -v

# Expected: All 66 tests should pass
```

### Step 5: Verify AI Integration

```bash
# Test AI summary generation
curl -X POST http://localhost:8000/api/v1/generate-summary \
  -H "Content-Type: application/json" \
  -d '{"content":"This is a test book about Python programming and web development."}'

# Expected: AI-generated summary response
```

### Quick Verification Checklist

| Component | Command | Expected Result |
|-----------|---------|-----------------|
| API Health | `curl localhost:8000/health` | `{"status":"healthy"...}` |
| Cache | `curl localhost:8000/cache/stats` | `{"status":"connected"...}` |
| Docs | Open `localhost:8000/docs` | Swagger UI loads |
| Tests | `pytest tests/ -v` | 66 tests passed |
| Database | Register user via `/auth/register` | User created |

---

## Features

- **Book Management**: Full CRUD operations for books with search and filtering
- **User Management**: User registration, authentication with JWT tokens
- **Review System**: Users can review and rate books
- **AI Integration**: 
  - Book summaries generated using Llama3/OpenRouter
  - Review aggregation and summarization
  - Personalized book recommendations
- **Redis Caching**: AWS ElastiCache-compatible caching for improved performance
  - Popular books caching (TTL: 2 minutes)
  - Similar books caching (TTL: 3 minutes)
  - AI summary caching (TTL: 5 minutes)
  - Cache stats and management endpoints
- **Async Operations**: Built with async/await for high performance
- **Role-Based Access Control**: Admin and regular user permissions
- **Comprehensive API**: RESTful API with OpenAPI/Swagger documentation
- **Testing**: Comprehensive unit and integration tests
- **Docker Ready**: Containerized deployment with Docker Compose

## Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with async support (asyncpg)
- **ORM**: SQLAlchemy 2.0 (async)
- **Cache**: Redis (AWS ElastiCache compatible)
- **AI/ML**: 
  - Transformers library for local Llama models
  - OpenRouter API integration for cloud-based AI
- **Authentication**: JWT tokens with passlib for password hashing
- **Testing**: pytest with async support
- **Containerization**: Docker & Docker Compose
- **Migration**: Alembic for database migrations

## Project Structure

```
intelligent-book-management-system/
├── app/
│   ├── api/
│   │   ├── routes/          # API route handlers
│   │   │   ├── auth.py      # Authentication endpoints
│   │   │   ├── books.py     # Book management endpoints
│   │   │   ├── reviews.py   # Review management endpoints
│   │   │   ├── users.py     # User management endpoints
│   │   │   └── recommendations.py  # AI recommendations
│   │   └── schemas.py       # Pydantic models for API
│   ├── config/
│   │   └── settings.py      # Application configuration
│   ├── models/              # Database models
│   │   ├── base.py          # Base model and database setup
│   │   ├── books.py         # Book model
│   │   ├── reviews.py       # Review model
│   │   └── users.py         # User model
│   ├── services/            # Business logic layer
│   │   ├── auth_service.py  # Authentication logic
│   │   ├── book_service.py  # Book operations
│   │   ├── cache_service.py # Redis caching (ElastiCache compatible)
│   │   ├── llama_service.py # AI/ML operations
│   │   ├── recommendation_service.py  # Recommendation logic
│   │   ├── review_service.py # Review operations
│   │   └── user_service.py  # User operations
│   └── main.py              # FastAPI application entry point
├── docker/
│   ├── Dockerfile           # Container definition
│   └── docker-compose.yml   # Multi-container setup
├── migrations/              # Database migrations
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
└── sample.env              # Environment variables template
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user profile
- `POST /api/v1/auth/logout` - Logout user

### Books
- `POST /api/v1/books/` - Create a new book
- `GET /api/v1/books/` - Get all books (with filtering)
- `GET /api/v1/books/{id}` - Get specific book
- `PUT /api/v1/books/{id}` - Update book
- `DELETE /api/v1/books/{id}` - Delete book
- `POST /api/v1/books/{id}/generate-summary` - Generate AI summary
- `GET /api/v1/books/{id}/summary` - Get book summary with reviews
- `POST /api/v1/books/{id}/reviews` - Add review to book
- `GET /api/v1/books/{id}/reviews` - Get all reviews for book

### Reviews
- `POST /api/v1/reviews/` - Create review
- `GET /api/v1/reviews/` - Get all reviews (with filtering)
- `GET /api/v1/reviews/{id}` - Get specific review
- `PUT /api/v1/reviews/{id}` - Update review
- `DELETE /api/v1/reviews/{id}` - Delete review
- `GET /api/v1/reviews/book/{book_id}/summary` - Get AI review summary

### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/` - Get all users
- `GET /api/v1/users/{id}` - Get specific user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Recommendations
- `GET /api/v1/recommendations/` - Get personalized recommendations
- `GET /api/v1/recommendations/popular` - Get popular books
- `POST /api/v1/recommendations/generate-summary` - Generate content summary

### Cache Management
- `GET /cache/stats` - Get Redis cache statistics (hits, misses, keys)
- `POST /cache/clear` - Clear all cached data

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (optional - for caching)
- Docker & Docker Compose (recommended)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd intelligent-book-management-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp sample.env .env
   # Edit .env with your configuration
   ```

5. **Set up PostgreSQL database**
   ```sql
   CREATE DATABASE intelligent_books_db;
   CREATE USER bookadmin WITH PASSWORD 'BookPass@2024Secure';
   GRANT ALL PRIVILEGES ON DATABASE intelligent_books_db TO bookadmin;
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Setup

1. **Configure Environment Variables**
   ```bash
   # Copy sample environment file
   cp sample.env .env
   
   # Edit with your settings (important: change SECRET_KEY and passwords)
   nano .env
   ```

2. **Start with Docker Compose**
   ```bash
   cd docker
   docker-compose --env-file ../.env up -d
   ```

   This will start:
   - PostgreSQL database on port 5432 (configurable via `DB_PORT`)
   - FastAPI application on port 8000 (configurable via `API_PORT`)

3. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

4. **Useful Commands**
   ```bash
   # View logs
   docker-compose logs -f
   
   # Stop services
   docker-compose down
   
   # Rebuild after code changes
   docker-compose --env-file ../.env up -d --build
   ```

### Environment Configuration

Create a `.env` file based on `sample.env`:

```bash
cp sample.env .env
```

**Key Environment Variables:**

```env
# Database Configuration
POSTGRES_USER=bookadmin
POSTGRES_PASSWORD=BookPass@2024Secure
POSTGRES_DB=intelligent_books_db
POSTGRES_HOST=db              # Use 'localhost' for local dev, 'db' for Docker
POSTGRES_PORT=5432

# Security
SECRET_KEY=f8a7b3c9d2e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI Configuration (Optional - for Llama3 summaries)
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct:free

# Docker Ports
API_PORT=8000
DB_PORT=5432
```

**For Local Development (without Docker):**
```env
DATABASE_URL=postgresql://bookadmin:BookPass@2024Secure@localhost:5432/intelligent_books_db
```

## AI Integration Options

The system supports multiple AI backends:

### 1. OpenRouter (Recommended for Production)
- Sign up at [OpenRouter](https://openrouter.ai/)
- Get API key and set `OPENROUTER_API_KEY`
- Choose model (default: `meta-llama/llama-3-8b-instruct:free`)

### 2. Local Llama Model
- Uses Hugging Face Transformers
- Requires significant GPU/CPU resources
- Fallback to smaller models for development

### 3. Fallback Mode
- Simple text processing when AI is unavailable
- Ensures system functionality without AI dependencies

## Running the Application

### Method 1: Docker Compose (Recommended)

**Start all services:**
```bash
cd docker
docker-compose --env-file ../.env up -d
```

**What gets started:**
| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Database server |
| Redis | 6379 | Cache server |
| FastAPI | 8000 | Application server |

**Useful Docker commands:**
```bash
# View running containers
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Rebuild after code changes
docker-compose --env-file ../.env up -d --build

# Run database migrations
docker-compose exec api alembic upgrade head

# Access container shell
docker-compose exec api bash
```

### Method 2: Local Development

**Prerequisites:**
- Python 3.11+
- PostgreSQL 15+ running
- Redis 7+ running (optional, for caching)

**Start the server:**
```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Start with auto-reload (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start without auto-reload (production-like)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Run in background:**
```bash
# Start in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Or using screen
screen -S bookapi
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Press Ctrl+A, then D to detach
```

### Method 3: Production Deployment

```bash
cd docker
docker-compose -f docker-compose.prod.yml --env-file ../.env.prod up -d
```

**Production features:**
- Health checks for all services
- Automatic restart policies
- Redis with memory limits (256MB LRU)
- Optimized logging (WARNING level)

---

## Testing

### Run All Tests

```bash
# Install test dependencies (if not already)
pip install pytest pytest-asyncio aiosqlite

# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_books.py -v

# Run specific test class
python -m pytest tests/test_books.py::TestBooks -v

# Run specific test
python -m pytest tests/test_books.py::TestBooks::test_create_book -v
```

### Test Categories

```bash
# Run using test script
./run_tests.sh all        # All tests
./run_tests.sh auth       # Authentication tests
./run_tests.sh books      # Book CRUD tests
./run_tests.sh reviews    # Review tests
./run_tests.sh users      # User tests
./run_tests.sh recommendations  # AI recommendation tests
```

### Test Cache Functionality

```bash
# Run caching verification script
python scripts/test_caching.py
```

### Expected Test Results

```
tests/test_auth.py          - 8 tests  ✅
tests/test_books.py         - 15 tests ✅
tests/test_reviews.py       - 13 tests ✅
tests/test_users.py         - 10 tests ✅
tests/test_recommendations.py - 12 tests ✅
─────────────────────────────────────────
Total: 66 tests passed
```

Test coverage includes:
- Unit tests for all services
- API endpoint integration tests
- Database operation tests
- Authentication and authorization tests
- Cache functionality tests

## Database Schema

### Books Table
- `id`: Primary key
- `title`: Book title
- `author`: Book author
- `isbn`: ISBN number
- `genre`: Book genre
- `publication_year`: Publication year
- `description`: Book description
- `ai_summary`: AI-generated summary
- `average_rating`: Calculated average rating
- `total_reviews`: Number of reviews

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `hashed_password`: Encrypted password
- `full_name`: User's full name
- `preferred_genres`: JSON array of preferences
- `is_active`: Account status
- `is_admin`: Admin privileges

### Reviews Table
- `id`: Primary key
- `book_id`: Foreign key to books
- `user_id`: Foreign key to users
- `rating`: Rating (1.0-5.0)
- `title`: Review title
- `content`: Review text
- `helpful_votes`: Community helpfulness votes

## Deployment

### Docker Deployment (Recommended)

```bash
# 1. Configure environment
cp sample.env .env
nano .env  # Edit with your settings

# 2. Start services
cd docker
docker-compose --env-file ../.env up -d

# 3. Verify deployment
curl http://localhost:8000/health
```

### Production Deployment

```bash
# Use production compose file
cd docker
docker-compose -f docker-compose.prod.yml --env-file ../.env.prod up -d
```

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Security Features

### Authentication & Authorization

| Feature | Implementation | Description |
|---------|----------------|-------------|
| **JWT Authentication** | `python-jose` | HS256 signed tokens with configurable expiration |
| **Password Hashing** | `bcrypt` | Secure one-way password hashing with salt |
| **Role-Based Access** | `is_admin`, `is_active` | Admin and regular user permission levels |
| **Token Validation** | HTTPBearer | Bearer token authentication for protected endpoints |

### Security Measures

| Feature | Implementation | Description |
|---------|----------------|-------------|
| **Input Validation** | Pydantic models | Automatic request/response validation |
| **SQL Injection Protection** | SQLAlchemy ORM | Parameterized queries prevent injection |
| **CORS Configuration** | FastAPI middleware | Configurable cross-origin policies |
| **SSL/TLS Support** | asyncpg + SSL context | Encrypted database connections |
| **Environment Secrets** | python-dotenv | Secrets stored in environment variables |

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST FLOW                              │
├─────────────────────────────────────────────────────────────┤
│  Client Request                                              │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ CORS Check  │ ← Configurable allowed origins             │
│  └─────────────┘                                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ JWT Token   │ ← Bearer token validation                  │
│  │ Validation  │   HS256 algorithm                          │
│  └─────────────┘                                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ Role Check  │ ← is_active, is_admin verification        │
│  └─────────────┘                                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ Input       │ ← Pydantic validation                      │
│  │ Validation  │   Type checking & constraints              │
│  └─────────────┘                                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ SQLAlchemy  │ ← SQL injection prevention                 │
│  │ ORM         │   Parameterized queries                    │
│  └─────────────┘                                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ PostgreSQL  │ ← SSL/TLS encrypted connection             │
│  │ Database    │   bcrypt password storage                  │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/auth/register` | POST | Register new user | No |
| `/api/v1/auth/login` | POST | Get JWT token | No |
| `/api/v1/auth/me` | GET | Get current user profile | Yes |
| `/api/v1/auth/logout` | POST | Logout user | No |

### Security Best Practices Implemented

- ✅ Passwords hashed with bcrypt (never stored in plain text)
- ✅ JWT tokens with expiration (default: 30 minutes)
- ✅ Role-based access control (Admin/User roles)
- ✅ Input validation on all endpoints
- ✅ SQL injection prevention via ORM
- ✅ CORS protection with configurable origins
- ✅ SSL/TLS support for database connections
- ✅ Secrets managed via environment variables
- ✅ Non-root user in Docker container

## Performance Considerations

- **Async Operations**: Non-blocking database operations
- **Connection Pooling**: Efficient database connections
- **Pagination**: Large dataset handling
- **Redis Caching**: Integrated caching for recommendations and AI summaries
- **Database Indexing**: Optimized queries with proper indexes

## Bonus Features Implemented

| Bonus Feature | Status | Description |
|---------------|--------|-------------|
| **Redis Caching** | ✅ Implemented | AWS ElastiCache-compatible caching for recommendations, popular books, similar books, and AI summaries |
| **Unit & Integration Tests** | ✅ Implemented | Comprehensive pytest test suite covering all API endpoints |
| **AWS SageMaker** | ❌ Not Implemented | ML model uses local inference or OpenRouter API instead |

### Caching Details

The Redis caching layer provides:

```
┌─────────────────────────────────────────────────────────────┐
│                    CACHING ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│  Cache Key Pattern          │ TTL      │ Data Cached        │
├─────────────────────────────┼──────────┼────────────────────┤
│  rec:{user_id}:{genre}      │ 60s      │ User recommendations│
│  popular:{genre}:{limit}    │ 120s     │ Popular books list │
│  similar:{book_id}:{limit}  │ 180s     │ Similar books      │
│  summary:{content_hash}     │ 300s     │ AI-generated text  │
└─────────────────────────────────────────────────────────────┘

Cache Endpoints:
  GET  /cache/stats  → View cache statistics (hits, misses, keys)
  POST /cache/clear  → Invalidate all cached data
```

**Benefits:**
- Reduces database load for frequently accessed data
- Speeds up AI summary responses (cached summaries)
- Compatible with AWS ElastiCache for cloud deployment
- Graceful degradation when cache is unavailable

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the development team.

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Failed

```
Error: could not connect to server: Connection refused
```

**Solution:**
```bash
# Check if PostgreSQL is running
# macOS:
brew services list | grep postgresql
brew services start postgresql

# Ubuntu:
sudo systemctl status postgresql
sudo systemctl start postgresql

# Docker:
docker-compose ps  # Check if db container is running
docker-compose logs db  # Check database logs
```

#### 2. Redis Connection Failed

```
Warning: Redis cache not available - running without cache
```

**Solution:**
```bash
# Check if Redis is running
# macOS:
brew services start redis

# Ubuntu:
sudo systemctl start redis

# Docker: Redis starts automatically with docker-compose

# Verify connection:
redis-cli ping  # Should return PONG
```

**Note:** The application works fine without Redis (graceful degradation).

#### 3. Port Already in Use

```
Error: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --port 8001
```

#### 4. Migration Errors

```
Error: Target database is not up to date
```

**Solution:**
```bash
# Check current migration status
alembic current

# Upgrade to latest
alembic upgrade head

# If issues persist, reset migrations (development only!)
alembic downgrade base
alembic upgrade head
```

#### 5. Docker Container Won't Start

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs -f

# Rebuild containers
docker-compose down
docker-compose --env-file ../.env up -d --build

# Clean slate (removes all data)
docker-compose down -v
docker-compose --env-file ../.env up -d
```

#### 6. Tests Failing

```bash
# Ensure you're in virtual environment
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio aiosqlite

# Run tests with verbose output
python -m pytest tests/ -v --tb=long
```

#### 7. AI Summary Not Working

**Check OpenRouter API Key:**
```bash
# Verify API key is set
echo $OPENROUTER_API_KEY

# Test API connectivity
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

**Note:** Without API key, the system uses local fallback (basic text processing).

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Overall application health |
| `GET /cache/stats` | Redis cache status |
| `GET /docs` | API documentation |

### Getting Help

1. Check logs: `docker-compose logs -f` or application console
2. Review [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup
3. Review [TESTING.md](TESTING.md) for test documentation
4. Open an issue on GitHub

---

## Roadmap

- [x] Redis caching integration (AWS ElastiCache compatible)
- [x] Comprehensive test suite (66 tests)
- [x] Docker deployment ready
- [ ] Advanced recommendation algorithms
- [ ] Book cover image support
- [ ] Reading progress tracking
- [ ] Social features (friend recommendations)
- [ ] Mobile API optimizations
- [ ] GraphQL API support
- [ ] Real-time notifications