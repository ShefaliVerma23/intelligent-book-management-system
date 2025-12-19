#!/usr/bin/env python3
"""
Database initialization script for the Intelligent Book Management System.
This script creates all tables and adds sample data for testing.

Usage:
    python scripts/init_db.py

Author: Shefali Verma
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.models.base import engine, Base, AsyncSessionLocal
from app.models.books import Book
from app.models.users import User
from app.models.reviews import Review


async def init_database():
    """Initialize the database with tables and sample data"""
    print("🚀 Initializing database...")
    
    # Create all tables
    async with engine.begin() as conn:
        print("📦 Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created successfully!")
    
    # Add sample data
    async with AsyncSessionLocal() as session:
        try:
            # Check if data already exists
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            if user_count > 0:
                print("ℹ️  Sample data already exists. Skipping...")
                return
            
            print("📝 Adding sample data...")
            
            # Create sample user
            sample_user = User(
                username="shefaliverma",
                email="shefali@example.com",
                full_name="Shefali Verma",
                bio="Book enthusiast and software developer",
                preferred_genres="Fiction, Technology, Self-Help",
                is_active=True,
                is_admin=True
            )
            sample_user.set_password("password123")
            session.add(sample_user)
            
            # Create another sample user for testing
            test_user = User(
                username="testuser",
                email="test@example.com",
                full_name="Test User",
                is_active=True,
                is_admin=False
            )
            test_user.set_password("testpass123")
            session.add(test_user)
            
            await session.flush()  # Get user IDs
            
            # Create sample books
            sample_books = [
                Book(
                    title="The Great Gatsby",
                    author="F. Scott Fitzgerald",
                    genre="Fiction",
                    year_published=1925,
                    summary="A story of wealth, love, and the American Dream in the Jazz Age."
                ),
                Book(
                    title="Clean Code",
                    author="Robert C. Martin",
                    genre="Technology",
                    year_published=2008,
                    summary="A handbook of agile software craftsmanship with practical advice on writing clean, maintainable code."
                ),
                Book(
                    title="Atomic Habits",
                    author="James Clear",
                    genre="Self-Help",
                    year_published=2018,
                    summary="An easy and proven way to build good habits and break bad ones."
                ),
                Book(
                    title="To Kill a Mockingbird",
                    author="Harper Lee",
                    genre="Fiction",
                    year_published=1960,
                    summary="A powerful story of racial injustice and childhood innocence in the American South."
                ),
                Book(
                    title="The Pragmatic Programmer",
                    author="David Thomas, Andrew Hunt",
                    genre="Technology",
                    year_published=1999,
                    summary="Classic guide covering best practices and practical approaches to software development."
                ),
            ]
            
            for book in sample_books:
                session.add(book)
            
            await session.flush()  # Get book IDs
            
            # Create sample reviews
            sample_reviews = [
                Review(
                    book_id=sample_books[0].id,
                    user_id=sample_user.id,
                    review_text="A timeless classic that captures the essence of the American Dream. Beautifully written!",
                    rating=5.0
                ),
                Review(
                    book_id=sample_books[1].id,
                    user_id=sample_user.id,
                    review_text="Essential reading for any developer. Changed how I write code.",
                    rating=4.5
                ),
                Review(
                    book_id=sample_books[2].id,
                    user_id=test_user.id,
                    review_text="Practical and actionable advice. Highly recommended for personal growth.",
                    rating=5.0
                ),
                Review(
                    book_id=sample_books[0].id,
                    user_id=test_user.id,
                    review_text="Great story but a bit slow in places. Still worth reading.",
                    rating=4.0
                ),
            ]
            
            for review in sample_reviews:
                session.add(review)
            
            await session.commit()
            print("✅ Sample data added successfully!")
            
            print("\n📊 Database Summary:")
            print(f"   - Users: 2 (shefaliverma, testuser)")
            print(f"   - Books: {len(sample_books)}")
            print(f"   - Reviews: {len(sample_reviews)}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error adding sample data: {e}")
            raise


async def verify_connection():
    """Verify database connection"""
    print("🔌 Testing database connection...")
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def main():
    """Main function"""
    print("=" * 50)
    print("  Intelligent Book Management System")
    print("  Database Initialization Script")
    print("=" * 50)
    print()
    
    # Verify connection first
    if not await verify_connection():
        print("\n⚠️  Please check your DATABASE_URL in .env file")
        sys.exit(1)
    
    # Initialize database
    await init_database()
    
    print("\n" + "=" * 50)
    print("  🎉 Database setup complete!")
    print("=" * 50)
    print("\nYou can now run the API server:")
    print("  uvicorn app.main:app --reload")
    print()


if __name__ == "__main__":
    asyncio.run(main())

