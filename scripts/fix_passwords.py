#!/usr/bin/env python3
"""
Fix user passwords in the database.
Run: python scripts/fix_passwords.py
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Get database URL
database_url = os.getenv("DATABASE_URL", "postgresql://localhost/book_management")
if "channel_binding" in database_url:
    database_url = re.sub(r'[&?]channel_binding=[^&]*', '', database_url)

print("🔐 Fixing user passwords...")

engine = create_engine(database_url)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Generate proper bcrypt hash for "password123"
    password = "password123"
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    print(f"✅ Generated new bcrypt hash: {password_hash[:20]}...")
    
    # Update all users with the new hash
    result = session.execute(
        text("UPDATE users SET hashed_password = :hash"),
        {"hash": password_hash}
    )
    
    session.commit()
    print(f"✅ Updated {result.rowcount} users with new password hash")
    
    # Verify
    test_result = session.execute(text("SELECT username, hashed_password FROM users LIMIT 1"))
    row = test_result.fetchone()
    if row:
        print(f"\n🧪 Testing password for user: {row[0]}")
        is_valid = bcrypt.checkpw(password.encode('utf-8'), row[1].encode('utf-8'))
        print(f"   Password verification: {'✅ SUCCESS' if is_valid else '❌ FAILED'}")
    
    print("\n🎉 Passwords fixed! Login should work now.")
    print("   Username: shefaliverma")
    print("   Password: password123")

except Exception as e:
    session.rollback()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()
