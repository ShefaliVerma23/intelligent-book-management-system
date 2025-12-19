#!/bin/bash
#
# Test Runner for Intelligent Book Management System
# Usage: ./run_tests.sh [option]
#
# Options:
#   all      - Run all pytest tests (default)
#   books    - Run only book tests
#   reviews  - Run only review tests
#   recs     - Run only recommendation tests
#   api      - Run manual API tests (requires server running)
#   coverage - Run tests with coverage report
#   verbose  - Run all tests with verbose output
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Intelligent Book Management System Tests${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest pytest-asyncio aiosqlite httpx
fi

case "$1" in
    "books")
        echo -e "\n${YELLOW}Running Book Tests...${NC}\n"
        python -m pytest tests/test_books.py -v
        ;;
    "reviews")
        echo -e "\n${YELLOW}Running Review Tests...${NC}\n"
        python -m pytest tests/test_reviews.py -v
        ;;
    "recs")
        echo -e "\n${YELLOW}Running Recommendation Tests...${NC}\n"
        python -m pytest tests/test_recommendations.py -v
        ;;
    "auth")
        echo -e "\n${YELLOW}Running Auth Tests...${NC}\n"
        python -m pytest tests/test_auth.py -v
        ;;
    "api")
        echo -e "\n${YELLOW}Running Manual API Tests...${NC}"
        echo -e "${YELLOW}Make sure server is running: uvicorn app.main:app --reload${NC}\n"
        python scripts/test_api.py
        ;;
    "coverage")
        echo -e "\n${YELLOW}Running Tests with Coverage...${NC}\n"
        pip install pytest-cov -q
        python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
        echo -e "\n${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;
    "verbose")
        echo -e "\n${YELLOW}Running All Tests (Verbose)...${NC}\n"
        python -m pytest tests/ -v -s
        ;;
    "all"|"")
        echo -e "\n${YELLOW}Running All Tests...${NC}\n"
        python -m pytest tests/ -v
        ;;
    *)
        echo "Usage: ./run_tests.sh [option]"
        echo ""
        echo "Options:"
        echo "  all      - Run all pytest tests (default)"
        echo "  books    - Run only book tests"
        echo "  reviews  - Run only review tests"
        echo "  recs     - Run only recommendation tests"
        echo "  auth     - Run only auth tests"
        echo "  api      - Run manual API tests (requires server running)"
        echo "  coverage - Run tests with coverage report"
        echo "  verbose  - Run all tests with verbose output"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Tests Completed!${NC}"
echo -e "${GREEN}============================================${NC}"
