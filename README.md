# Intelligent Book Management System

An AI-powered book management system built with FastAPI, PostgreSQL, and Llama3 integration. The system provides comprehensive book management, user reviews, AI-generated summaries, and personalized recommendations.

## Features

- **Book Management**: Full CRUD operations for books with search and filtering
- **User Management**: User registration, authentication with JWT tokens
- **Review System**: Users can review and rate books
- **AI Integration**: 
  - Book summaries generated using Llama3/OpenRouter
  - Review aggregation and summarization
  - Personalized book recommendations
- **Async Operations**: Built with async/await for high performance
- **Role-Based Access Control**: Admin and regular user permissions
- **Comprehensive API**: RESTful API with OpenAPI/Swagger documentation
- **Testing**: Comprehensive unit and integration tests
- **Docker Ready**: Containerized deployment with Docker Compose

## Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with async support (asyncpg)
- **ORM**: SQLAlchemy 2.0 (async)
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

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

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
   CREATE DATABASE book_management;
   CREATE USER bookmanager WITH PASSWORD 'bookpassword';
   GRANT ALL PRIVILEGES ON DATABASE book_management TO bookmanager;
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

1. **Using Docker Compose (Recommended)**
   ```bash
   cd docker
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database on port 5432
   - FastAPI application on port 8000

2. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Environment Configuration

Create a `.env` file based on `sample.env`:

```env
# Database
DATABASE_URL=postgresql://bookmanager:bookpassword@localhost:5432/book_management

# Security
SECRET_KEY=your-super-secret-key-32-chars-long
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Configuration (Optional)
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct:free

# Local Llama Model (Alternative)
LLAMA_MODEL_PATH=meta-llama/Llama-2-7b-chat-hf
LLAMA_MAX_LENGTH=512
LLAMA_TEMPERATURE=0.7
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

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio aiosqlite

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_books.py

# Run with verbose output
pytest -v
```

Test coverage includes:
- Unit tests for all services
- API endpoint integration tests
- Database operation tests
- Authentication and authorization tests

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

### Docker Deployment

1. **Build and deploy**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

2. **Scale the application**
   ```bash
   docker-compose up --scale api=3
   ```

### Cloud Deployment Options

#### AWS EC2 + RDS
1. Launch EC2 instance with Docker
2. Set up RDS PostgreSQL instance
3. Configure environment variables
4. Deploy using Docker Compose

#### AWS ECS with Fargate
1. Build and push image to ECR
2. Create ECS task definition
3. Set up RDS database
4. Configure load balancer

#### Heroku
1. Add Heroku Postgres addon
2. Set environment variables
3. Deploy using Git or Docker

## Security Features

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: bcrypt for password security
- **Role-Based Access**: Admin and user permissions
- **Input Validation**: Pydantic models for data validation
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Configuration**: Configurable cross-origin policies

## Performance Considerations

- **Async Operations**: Non-blocking database operations
- **Connection Pooling**: Efficient database connections
- **Pagination**: Large dataset handling
- **Caching Ready**: Structured for Redis/ElastiCache integration
- **Database Indexing**: Optimized queries with proper indexes

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

## Roadmap

- [ ] Redis caching integration
- [ ] Advanced recommendation algorithms
- [ ] Book cover image support
- [ ] Reading progress tracking
- [ ] Social features (friend recommendations)
- [ ] Mobile API optimizations
- [ ] GraphQL API support
- [ ] Real-time notifications