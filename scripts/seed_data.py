#!/usr/bin/env python3
"""
Seed script to add dummy data to the database.
Run: python scripts/seed_data.py
"""
import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
database_url = os.getenv("DATABASE_URL", "postgresql://localhost/book_management")

# Remove channel_binding parameter if present
if "channel_binding" in database_url:
    database_url = re.sub(r'[&?]channel_binding=[^&]*', '', database_url)

print(f"🔌 Connecting to database...")

# Create engine and session
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Check connection
    session.execute(text("SELECT 1"))
    print("✅ Database connection successful!")
    
    # Check if data already exists
    result = session.execute(text("SELECT COUNT(*) FROM users"))
    user_count = result.scalar()
    
    if user_count > 0:
        print(f"ℹ️  Database already has {user_count} users. Skipping seed...")
        print("\n💡 To re-seed, first clear the tables:")
        print("   DELETE FROM reviews; DELETE FROM books; DELETE FROM users;")
        sys.exit(0)
    
    print("\n📝 Adding dummy data...")
    
    # ========== ADD USERS ==========
    print("\n👤 Adding users...")
    
    # Hash for password "password123" using bcrypt
    # In real scenario, use passlib to generate this
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYQqzQzJzJzK"
    
    users_data = [
        ("shefaliverma", "shefali@example.com", password_hash, "Shefali Verma", "Book lover and developer", "Fiction, Technology", True, True),
        ("john_reader", "john@example.com", password_hash, "John Reader", "Avid book collector", "Mystery, Thriller", True, False),
        ("alice_books", "alice@example.com", password_hash, "Alice Johnson", "Literature enthusiast", "Romance, Drama", True, False),
        ("tech_guru", "techguru@example.com", password_hash, "Tech Guru", "Software engineer who loves tech books", "Technology, Science", True, False),
        ("bookworm123", "bookworm@example.com", password_hash, "Book Worm", "Reading is my passion", "Fantasy, Sci-Fi", True, False),
    ]
    
    for user in users_data:
        session.execute(text("""
            INSERT INTO users (username, email, hashed_password, full_name, bio, preferred_genres, is_active, is_admin, created_at, updated_at)
            VALUES (:username, :email, :password, :full_name, :bio, :genres, :is_active, :is_admin, NOW(), NOW())
        """), {
            "username": user[0], "email": user[1], "password": user[2],
            "full_name": user[3], "bio": user[4], "genres": user[5],
            "is_active": user[6], "is_admin": user[7]
        })
    
    print(f"   ✅ Added {len(users_data)} users")
    
    # ========== ADD BOOKS ==========
    print("\n📚 Adding books...")
    
    books_data = [
        # (title, author, genre, year_published, summary)
        ("The Great Gatsby", "F. Scott Fitzgerald", "Fiction", 1925, 
         "A story of wealth, love, and the American Dream set in the Jazz Age. Nick Carraway narrates the tale of the mysterious millionaire Jay Gatsby."),
        
        ("Clean Code", "Robert C. Martin", "Technology", 2008,
         "A handbook of agile software craftsmanship. Learn how to write clean, maintainable code that stands the test of time."),
        
        ("To Kill a Mockingbird", "Harper Lee", "Fiction", 1960,
         "A powerful story of racial injustice and childhood innocence in the American South, told through the eyes of Scout Finch."),
        
        ("The Pragmatic Programmer", "David Thomas & Andrew Hunt", "Technology", 1999,
         "Classic guide covering best practices and practical approaches to software development. A must-read for every developer."),
        
        ("1984", "George Orwell", "Fiction", 1949,
         "A dystopian novel set in a totalitarian society under constant surveillance. Big Brother is watching."),
        
        ("Atomic Habits", "James Clear", "Self-Help", 2018,
         "An easy and proven way to build good habits and break bad ones. Small changes lead to remarkable results."),
        
        ("The Alchemist", "Paulo Coelho", "Fiction", 1988,
         "A magical story about Santiago, a shepherd boy who dreams of finding treasure in Egypt and discovers his Personal Legend."),
        
        ("Design Patterns", "Gang of Four", "Technology", 1994,
         "Elements of Reusable Object-Oriented Software. The definitive guide to design patterns in software engineering."),
        
        ("Pride and Prejudice", "Jane Austen", "Romance", 1813,
         "A witty tale of love and manners in Georgian England, following Elizabeth Bennet and Mr. Darcy."),
        
        ("The Hitchhiker's Guide to the Galaxy", "Douglas Adams", "Sci-Fi", 1979,
         "A comedic science fiction series following Arthur Dent's adventures through space. Don't forget your towel!"),
        
        ("Sapiens", "Yuval Noah Harari", "Non-Fiction", 2011,
         "A brief history of humankind exploring how Homo sapiens came to dominate the world."),
        
        ("The Lean Startup", "Eric Ries", "Business", 2011,
         "How today's entrepreneurs use continuous innovation to create radically successful businesses."),
        
        ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "Fantasy", 1997,
         "The beginning of Harry Potter's magical journey at Hogwarts School of Witchcraft and Wizardry."),
        
        ("Thinking, Fast and Slow", "Daniel Kahneman", "Psychology", 2011,
         "Nobel laureate Daniel Kahneman explores the two systems that drive the way we think."),
        
        ("The Catcher in the Rye", "J.D. Salinger", "Fiction", 1951,
         "Holden Caulfield's journey through New York City after being expelled from prep school."),
    ]
    
    for book in books_data:
        session.execute(text("""
            INSERT INTO books (title, author, genre, year_published, summary, created_at, updated_at)
            VALUES (:title, :author, :genre, :year, :summary, NOW(), NOW())
        """), {
            "title": book[0], "author": book[1], "genre": book[2],
            "year": book[3], "summary": book[4]
        })
    
    print(f"   ✅ Added {len(books_data)} books")
    
    # ========== ADD REVIEWS ==========
    print("\n⭐ Adding reviews...")
    
    reviews_data = [
        # (book_id, user_id, review_text, rating)
        (1, 1, "A timeless classic! The portrayal of the American Dream is hauntingly beautiful.", 5.0),
        (1, 2, "Great story but a bit slow in some parts. Still a must-read.", 4.0),
        (1, 3, "Fitzgerald's prose is simply magical. One of my favorites.", 5.0),
        
        (2, 1, "Essential reading for any developer. Changed how I write code.", 4.5),
        (2, 4, "Every software engineer should read this. Clean code is a skill.", 5.0),
        (2, 5, "Good principles but some examples feel dated. Still valuable.", 4.0),
        
        (3, 2, "Powerful and moving. The courtroom scenes are unforgettable.", 5.0),
        (3, 3, "A beautiful story about justice and growing up.", 5.0),
        
        (4, 1, "Practical advice that I still apply years later.", 4.5),
        (4, 4, "A bit dated but the core principles remain relevant.", 4.0),
        
        (5, 2, "Terrifyingly relevant in today's world. A masterpiece.", 5.0),
        (5, 5, "Dark and thought-provoking. Big Brother is indeed watching.", 4.5),
        
        (6, 1, "Life-changing! Simple concepts explained brilliantly.", 5.0),
        (6, 3, "Helped me build better habits. Highly recommended.", 4.5),
        (6, 5, "Practical and actionable advice for personal growth.", 5.0),
        
        (7, 3, "A magical journey of self-discovery. Loved every page.", 5.0),
        (7, 2, "Beautiful story with deep philosophical messages.", 4.5),
        
        (8, 4, "The bible of design patterns. Every OOP developer needs this.", 5.0),
        (8, 1, "Dense but incredibly valuable. Reference it often.", 4.0),
        
        (9, 3, "Witty, romantic, and timeless. Austen at her best!", 5.0),
        (9, 5, "Mr. Darcy is the ultimate book boyfriend!", 4.5),
        
        (10, 5, "Hilarious and absurd in the best way possible!", 5.0),
        (10, 2, "Don't panic! This book is a joyride through space.", 4.5),
        
        (11, 1, "Fascinating perspective on human history.", 4.5),
        (11, 4, "Made me think about humanity in a whole new way.", 5.0),
        
        (12, 4, "Great for entrepreneurs. Build-measure-learn loop is genius.", 4.5),
        (12, 1, "Practical startup advice. A must for founders.", 4.0),
        
        (13, 5, "The book that started it all! Pure magic.", 5.0),
        (13, 3, "Nostalgic and wonderful. Takes you back to childhood.", 5.0),
        
        (14, 1, "Dense but rewarding. Understanding cognitive biases is crucial.", 4.0),
        (14, 4, "Eye-opening exploration of how we think.", 4.5),
        
        (15, 2, "Holden's voice is unforgettable. A classic coming-of-age story.", 4.5),
        (15, 3, "Raw and honest portrayal of teenage angst.", 4.0),
    ]
    
    for review in reviews_data:
        session.execute(text("""
            INSERT INTO reviews (book_id, user_id, review_text, rating, created_at, updated_at)
            VALUES (:book_id, :user_id, :review_text, :rating, NOW(), NOW())
        """), {
            "book_id": review[0], "user_id": review[1],
            "review_text": review[2], "rating": review[3]
        })
    
    print(f"   ✅ Added {len(reviews_data)} reviews")
    
    # Commit all changes
    session.commit()
    
    print("\n" + "=" * 50)
    print("🎉 DUMMY DATA ADDED SUCCESSFULLY!")
    print("=" * 50)
    print(f"\n📊 Summary:")
    print(f"   👤 Users: {len(users_data)}")
    print(f"   📚 Books: {len(books_data)}")
    print(f"   ⭐ Reviews: {len(reviews_data)}")
    print(f"\n🔑 Login credentials:")
    print(f"   Username: shefaliverma")
    print(f"   Password: password123")
    print(f"\n🚀 Start the server:")
    print(f"   uvicorn app.main:app --reload")
    print(f"\n📖 API Docs: http://localhost:8000/docs")

except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
    raise
finally:
    session.close()

