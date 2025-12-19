# Deployment Guide

This document provides detailed instructions for deploying the Intelligent Book Management System using Docker.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker-based Deployment](#docker-based-deployment)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Health Monitoring](#health-monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd intelligent-book-management-system

# Copy and configure environment file
cp sample.env .env

# Edit .env with your settings (important: change SECRET_KEY and passwords)
nano .env  # or use your preferred editor

# Start with Docker Compose
cd docker
docker-compose --env-file ../.env up -d
```

The application will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Cache Stats**: http://localhost:8000/cache/stats

### Option 2: Local Development

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp sample.env .env
# Edit .env with your database settings

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Docker-based Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

### Verify Installation

```bash
docker --version
docker-compose --version
```

### Project Structure

```
docker/
├── Dockerfile              # Application container definition
├── docker-compose.yml      # Development environment
└── docker-compose.prod.yml # Production environment
```

### Development Deployment

```bash
cd docker
docker-compose up -d
```

This starts:
- **PostgreSQL 15** database on port 5432
- **Redis 7** cache on port 6379
- **FastAPI application** on port 8000

### Production Deployment

```bash
cd docker

# Create production environment file
cp ../sample.env ../.env.prod
# Edit .env.prod with production values

# Deploy with production compose
docker-compose -f docker-compose.prod.yml --env-file ../.env.prod up -d
```

Production setup includes:
- Health checks for all services
- Automatic restart policies
- **Redis caching** with persistence (AWS ElastiCache compatible)
- Memory limits for cache (256MB with LRU eviction)

### Docker Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api

# Rebuild containers
docker-compose up -d --build

# Remove all containers and volumes
docker-compose down -v

# Scale the API (multiple instances)
docker-compose up -d --scale api=3

# Execute command in container
docker-compose exec api python -c "print('Hello')"

# Run database migrations
docker-compose exec api alembic upgrade head
```

### Dockerfile Overview

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Configuration

#### Development (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: bookmanager
      POSTGRES_PASSWORD: bookpassword
      POSTGRES_DB: book_management
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://bookmanager:bookpassword@db:5432/book_management
      SECRET_KEY: your-secret-key
    depends_on:
      - db

volumes:
  postgres_data:
```

#### Production (`docker-compose.prod.yml`)

Includes additional features:
- Health checks for API, DB, and Redis
- Automatic restart policies
- **Redis caching** with persistence and LRU eviction
- Memory limits for cache (256MB)

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT signing key (32+ chars) | `your-super-secret-key-here` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | AI service API key | - |
| `OPENROUTER_MODEL` | AI model to use | `meta-llama/llama-3-8b-instruct:free` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration | `30` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ALLOWED_HOSTS` | CORS allowed hosts | `*` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `REDIS_PORT` | Redis port for Docker | `6379` |
| `CACHE_ENABLED` | Enable/disable caching | `true` |

### Sample Environment File

```env
# Database Configuration
POSTGRES_USER=bookadmin
POSTGRES_PASSWORD=BookPass@2024Secure
POSTGRES_DB=intelligent_books_db

# Security Configuration
SECRET_KEY=f8a7b3c9d2e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI Configuration (Optional - for Llama3 summaries)
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct:free

# Redis Cache Configuration (AWS ElastiCache Compatible)
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true

# Application Configuration
LOG_LEVEL=INFO
ALLOWED_HOSTS=*

# Docker Ports
API_PORT=8000
DB_PORT=5432
REDIS_PORT=6379
```

---

## Database Setup

### Using Docker (Automatic)

When using Docker Compose, PostgreSQL is automatically configured.

### Manual Setup (Local Development)

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database and user
CREATE DATABASE intelligent_books_db;
CREATE USER bookadmin WITH PASSWORD 'BookPass@2024Secure';
GRANT ALL PRIVILEGES ON DATABASE intelligent_books_db TO bookadmin;

-- Exit
\q
```

### Run Migrations

```bash
# Local development
alembic upgrade head

# Docker
docker-compose exec api alembic upgrade head
```

### Seed Sample Data (Optional)

```bash
# Local
python scripts/seed_data.py

# Docker
docker-compose exec api python scripts/seed_data.py
```

---

## Health Monitoring

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Basic health check |
| `GET /` | Application info |
| `GET /docs` | API documentation |

### Check Application Health

```bash
# Using curl
curl http://localhost:8000/health

# Expected response
{"status": "healthy", "version": "1.0.0"}
```

### Docker Health Checks

The production Docker Compose includes automatic health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Monitor Container Status

```bash
# View container health
docker-compose ps

# View resource usage
docker stats
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

```
sqlalchemy.exc.OperationalError: connection refused
```

**Solution:**
```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Verify DATABASE_URL format
echo $DATABASE_URL
```

#### 2. Port Already in Use

```
Error: bind: address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill the process or use different port
docker-compose down
docker-compose up -d
```

#### 3. Container Build Fails

**Solution:**
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### 4. Permission Denied

**Solution:**
```bash
# Fix file permissions
chmod +x run_tests.sh
chmod -R 755 app/
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Debug Mode

Enable debug logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env file
LOG_LEVEL=DEBUG

# Restart containers
docker-compose restart api
```

---

## Quick Reference

### Start Application

```bash
# Docker (recommended)
cd docker && docker-compose up -d

# Local
source venv/bin/activate && uvicorn app.main:app --reload
```

### Stop Application

```bash
# Docker
docker-compose down

# Local
# Press Ctrl+C
```

### View API Documentation

```
http://localhost:8000/docs
```

### Run Tests

```bash
# Local
python -m pytest tests/ -v

# Docker
docker-compose exec api python -m pytest tests/ -v
```

### Check Health

```bash
curl http://localhost:8000/health
```

---

## Security Checklist

- [ ] Change `SECRET_KEY` from default value
- [ ] Use strong database password
- [ ] Set appropriate `ALLOWED_HOSTS` for production
- [ ] Keep dependencies updated
- [ ] Use HTTPS in production (configure reverse proxy)
- [ ] Regularly backup database

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Open an issue in the GitHub repository
