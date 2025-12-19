#!/usr/bin/env python3
"""
Manual API Testing Script for Intelligent Book Management System

This script tests all API endpoints manually and provides detailed output.
Run this with: python scripts/test_api.py

Prerequisites:
1. Start the server: uvicorn app.main:app --reload
2. Make sure you have httpx installed: pip install httpx
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
import httpx

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_test(name: str, passed: bool, details: str = ""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"  {status} | {name}")
    if details and not passed:
        print(f"         {Colors.YELLOW}Details: {details}{Colors.END}")


def print_response(response: httpx.Response):
    print(f"    {Colors.CYAN}Status: {response.status_code}{Colors.END}")
    try:
        data = response.json()
        print(f"    {Colors.CYAN}Response: {json.dumps(data, indent=2, default=str)[:500]}{Colors.END}")
    except:
        print(f"    {Colors.CYAN}Response: {response.text[:200]}{Colors.END}")


async def test_health_check(client: httpx.AsyncClient) -> bool:
    """Test health check endpoint"""
    response = await client.get(f"{BASE_URL}/health")
    return response.status_code == 200


async def test_root_endpoint(client: httpx.AsyncClient) -> bool:
    """Test root endpoint"""
    response = await client.get(f"{BASE_URL}/")
    return response.status_code == 200 and "Intelligent Book Management System" in response.json().get("message", "")


class BookTests:
    """Tests for book endpoints"""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.created_book_id: Optional[int] = None
    
    async def test_create_book(self) -> bool:
        """POST /books - Create a new book"""
        book_data = {
            "title": f"Test Book {datetime.now().strftime('%H%M%S')}",
            "author": "Test Author",
            "genre": "Science Fiction",
            "year_published": 2024,
            "summary": "A test book about testing. This is a great story about software testing."
        }
        response = await self.client.post(f"{BASE_URL}{API_PREFIX}/books/", json=book_data)
        if response.status_code == 200:
            self.created_book_id = response.json()["id"]
            return True
        print_response(response)
        return False
    
    async def test_get_books(self) -> bool:
        """GET /books - Get all books"""
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/books/")
        return response.status_code == 200 and isinstance(response.json(), list)
    
    async def test_get_book_by_id(self) -> bool:
        """GET /books/<id> - Get book by ID"""
        if not self.created_book_id:
            return False
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}")
        return response.status_code == 200 and response.json()["id"] == self.created_book_id
    
    async def test_update_book(self) -> bool:
        """PUT /books/<id> - Update book"""
        if not self.created_book_id:
            return False
        update_data = {"title": "Updated Test Book", "summary": "Updated summary for testing."}
        response = await self.client.put(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}", json=update_data)
        return response.status_code == 200 and response.json()["title"] == "Updated Test Book"
    
    async def test_filter_by_genre(self) -> bool:
        """GET /books?genre=<genre> - Filter by genre"""
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/books/?genre=Science")
        return response.status_code == 200
    
    async def test_search_books(self) -> bool:
        """GET /books?search=<term> - Search books"""
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/books/?search=Test")
        return response.status_code == 200
    
    async def test_generate_summary(self) -> bool:
        """POST /books/<id>/generate-summary - Generate AI summary"""
        if not self.created_book_id:
            return False
        response = await self.client.post(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}/generate-summary")
        return response.status_code == 200 and "summary" in response.json()
    
    async def test_get_book_summary(self) -> bool:
        """GET /books/<id>/summary - Get book summary with reviews"""
        if not self.created_book_id:
            return False
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}/summary")
        return response.status_code == 200 and "review_summary" in response.json()
    
    async def test_delete_book(self) -> bool:
        """DELETE /books/<id> - Delete book"""
        if not self.created_book_id:
            return False
        response = await self.client.delete(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}")
        return response.status_code == 200


class ReviewTests:
    """Tests for review endpoints"""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.created_book_id: Optional[int] = None
        self.created_review_id: Optional[int] = None
    
    async def setup(self) -> bool:
        """Create a book for testing reviews"""
        book_data = {
            "title": f"Review Test Book {datetime.now().strftime('%H%M%S')}",
            "author": "Review Test Author",
            "genre": "Fiction",
            "year_published": 2023,
            "summary": "A book for testing reviews."
        }
        response = await self.client.post(f"{BASE_URL}{API_PREFIX}/books/", json=book_data)
        if response.status_code == 200:
            self.created_book_id = response.json()["id"]
            return True
        return False
    
    async def test_add_review_to_book(self) -> bool:
        """POST /books/<id>/reviews - Add review to book"""
        if not self.created_book_id:
            return False
        review_data = {
            "user_id": 1,
            "rating": 4.5,
            "review_text": "This is a great book! Really enjoyed reading it."
        }
        response = await self.client.post(
            f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}/reviews", 
            json=review_data
        )
        if response.status_code == 200:
            self.created_review_id = response.json()["id"]
            return True
        print_response(response)
        return False
    
    async def test_get_book_reviews(self) -> bool:
        """GET /books/<id>/reviews - Get all reviews for book"""
        if not self.created_book_id:
            return False
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}/reviews")
        return response.status_code == 200 and isinstance(response.json(), list)
    
    async def test_get_review_by_id(self) -> bool:
        """GET /reviews/<id> - Get review by ID"""
        if not self.created_review_id:
            return False
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/reviews/{self.created_review_id}")
        return response.status_code == 200
    
    async def test_update_review(self) -> bool:
        """PUT /reviews/<id> - Update review"""
        if not self.created_review_id:
            return False
        update_data = {"rating": 5.0, "review_text": "Updated: Even better than I thought!"}
        response = await self.client.put(
            f"{BASE_URL}{API_PREFIX}/reviews/{self.created_review_id}", 
            json=update_data
        )
        return response.status_code == 200 and response.json()["rating"] == 5.0
    
    async def test_get_review_summary(self) -> bool:
        """GET /reviews/book/<id>/summary - Get AI review summary"""
        if not self.created_book_id:
            return False
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/reviews/book/{self.created_book_id}/summary")
        return response.status_code == 200 and "summary" in response.json()
    
    async def test_delete_review(self) -> bool:
        """DELETE /reviews/<id> - Delete review"""
        if not self.created_review_id:
            return False
        response = await self.client.delete(f"{BASE_URL}{API_PREFIX}/reviews/{self.created_review_id}")
        return response.status_code == 200
    
    async def cleanup(self):
        """Clean up test book"""
        if self.created_book_id:
            await self.client.delete(f"{BASE_URL}{API_PREFIX}/books/{self.created_book_id}")


class RecommendationTests:
    """Tests for recommendation endpoints"""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.created_book_ids: list = []
    
    async def setup(self) -> bool:
        """Create books for testing recommendations"""
        genres = ["Science Fiction", "Fantasy", "Mystery"]
        for i, genre in enumerate(genres):
            book_data = {
                "title": f"Recommendation Test Book {i+1}",
                "author": f"Author {i+1}",
                "genre": genre,
                "year_published": 2020 + i,
                "summary": f"A {genre.lower()} book for testing recommendations."
            }
            response = await self.client.post(f"{BASE_URL}{API_PREFIX}/books/", json=book_data)
            if response.status_code == 200:
                self.created_book_ids.append(response.json()["id"])
        return len(self.created_book_ids) == 3
    
    async def test_get_popular_books(self) -> bool:
        """GET /recommendations/popular - Get popular books"""
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/recommendations/popular")
        return response.status_code == 200 and isinstance(response.json(), list)
    
    async def test_get_popular_books_with_genre(self) -> bool:
        """GET /recommendations/popular?genre=<genre> - Get popular books by genre"""
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/recommendations/popular?genre=Fiction")
        return response.status_code == 200
    
    async def test_get_similar_books(self) -> bool:
        """GET /recommendations/similar/<id> - Get similar books"""
        if not self.created_book_ids:
            return False
        response = await self.client.get(f"{BASE_URL}{API_PREFIX}/recommendations/similar/{self.created_book_ids[0]}")
        # May return 404 if no similar books or 200 with list
        return response.status_code in [200, 404]
    
    async def cleanup(self):
        """Clean up test books"""
        for book_id in self.created_book_ids:
            await self.client.delete(f"{BASE_URL}{API_PREFIX}/books/{book_id}")


class GenerateSummaryTests:
    """Tests for generate-summary endpoint"""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
    
    async def test_generate_summary(self) -> bool:
        """POST /generate-summary - Generate summary for content"""
        request_data = {
            "content": "This is a story about a brave knight who embarks on a quest to save the kingdom. "
                       "Along the way, he meets allies and faces many challenges. "
                       "In the end, good triumphs over evil and peace is restored."
        }
        response = await self.client.post(f"{BASE_URL}{API_PREFIX}/generate-summary", json=request_data)
        if response.status_code == 200:
            data = response.json()
            return "summary" in data and "content_length" in data and "generated_at" in data
        print_response(response)
        return False
    
    async def test_generate_summary_empty(self) -> bool:
        """POST /generate-summary with empty content - Should fail"""
        request_data = {"content": ""}
        response = await self.client.post(f"{BASE_URL}{API_PREFIX}/generate-summary", json=request_data)
        return response.status_code == 400  # Should reject empty content


async def run_all_tests():
    """Run all API tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print("  INTELLIGENT BOOK MANAGEMENT SYSTEM - API TESTS")
    print(f"{'='*60}{Colors.END}\n")
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    passed = 0
    failed = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test health and root endpoints
        print_header("1. BASIC ENDPOINTS")
        
        result = await test_health_check(client)
        print_test("GET /health - Health check", result)
        passed += 1 if result else 0
        failed += 0 if result else 1
        
        result = await test_root_endpoint(client)
        print_test("GET / - Root endpoint", result)
        passed += 1 if result else 0
        failed += 0 if result else 1
        
        # Book tests
        print_header("2. BOOK ENDPOINTS (CRUD)")
        book_tests = BookTests(client)
        
        tests = [
            ("POST /books - Create book", book_tests.test_create_book),
            ("GET /books - Get all books", book_tests.test_get_books),
            ("GET /books/<id> - Get book by ID", book_tests.test_get_book_by_id),
            ("PUT /books/<id> - Update book", book_tests.test_update_book),
            ("GET /books?genre=<genre> - Filter by genre", book_tests.test_filter_by_genre),
            ("GET /books?search=<term> - Search books", book_tests.test_search_books),
            ("POST /books/<id>/generate-summary - AI summary", book_tests.test_generate_summary),
            ("GET /books/<id>/summary - Book + review summary", book_tests.test_get_book_summary),
            ("DELETE /books/<id> - Delete book", book_tests.test_delete_book),
        ]
        
        for name, test_func in tests:
            result = await test_func()
            print_test(name, result)
            passed += 1 if result else 0
            failed += 0 if result else 1
        
        # Review tests
        print_header("3. REVIEW ENDPOINTS (CRUD)")
        review_tests = ReviewTests(client)
        await review_tests.setup()
        
        tests = [
            ("POST /books/<id>/reviews - Add review", review_tests.test_add_review_to_book),
            ("GET /books/<id>/reviews - Get book reviews", review_tests.test_get_book_reviews),
            ("GET /reviews/<id> - Get review by ID", review_tests.test_get_review_by_id),
            ("PUT /reviews/<id> - Update review", review_tests.test_update_review),
            ("GET /reviews/book/<id>/summary - AI review summary", review_tests.test_get_review_summary),
            ("DELETE /reviews/<id> - Delete review", review_tests.test_delete_review),
        ]
        
        for name, test_func in tests:
            result = await test_func()
            print_test(name, result)
            passed += 1 if result else 0
            failed += 0 if result else 1
        
        await review_tests.cleanup()
        
        # Recommendation tests
        print_header("4. RECOMMENDATION ENDPOINTS")
        rec_tests = RecommendationTests(client)
        await rec_tests.setup()
        
        tests = [
            ("GET /recommendations/popular - Popular books", rec_tests.test_get_popular_books),
            ("GET /recommendations/popular?genre=<g> - By genre", rec_tests.test_get_popular_books_with_genre),
            ("GET /recommendations/similar/<id> - Similar books", rec_tests.test_get_similar_books),
        ]
        
        for name, test_func in tests:
            result = await test_func()
            print_test(name, result)
            passed += 1 if result else 0
            failed += 0 if result else 1
        
        await rec_tests.cleanup()
        
        # Generate summary tests
        print_header("5. GENERATE SUMMARY ENDPOINT")
        summary_tests = GenerateSummaryTests(client)
        
        tests = [
            ("POST /generate-summary - Generate AI summary", summary_tests.test_generate_summary),
            ("POST /generate-summary (empty) - Validation", summary_tests.test_generate_summary_empty),
        ]
        
        for name, test_func in tests:
            result = await test_func()
            print_test(name, result)
            passed += 1 if result else 0
            failed += 0 if result else 1
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("  TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")
    
    total = passed + failed
    print(f"  Total Tests: {total}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.END}")
    print(f"  Success Rate: {(passed/total)*100:.1f}%\n")
    
    if failed == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.END}\n")
    else:
        print(f"  {Colors.YELLOW}⚠️  Some tests failed. Check the output above.{Colors.END}\n")
    
    return failed == 0


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Before running tests, make sure the server is running:")
    print("  uvicorn app.main:app --reload")
    print("="*60 + "\n")
    
    try:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    except httpx.ConnectError:
        print(f"\n{Colors.RED}ERROR: Could not connect to server at {BASE_URL}")
        print(f"Make sure the server is running: uvicorn app.main:app --reload{Colors.END}\n")
        exit(1)

