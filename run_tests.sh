#!/bin/bash

# Test runner script for Intelligent Book Management System

echo "Starting test suite for Intelligent Book Management System..."
echo "=============================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Warning: Virtual environment not detected. Consider activating it:"
    echo "source venv/bin/activate"
    echo ""
fi

# Install test dependencies if not already installed
echo "Installing test dependencies..."
pip install pytest pytest-asyncio aiosqlite --quiet

# Set test environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create test database (SQLite for testing)
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

# Run tests with different options based on arguments
if [[ "$1" == "coverage" ]]; then
    echo "Running tests with coverage..."
    pip install pytest-cov --quiet
    pytest --cov=app --cov-report=html --cov-report=term-missing -v
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
elif [[ "$1" == "verbose" ]]; then
    echo "Running tests in verbose mode..."
    pytest -v -s
elif [[ "$1" == "fast" ]]; then
    echo "Running fast tests (excluding slow integration tests)..."
    pytest -v -m "not slow"
elif [[ "$1" == "integration" ]]; then
    echo "Running integration tests only..."
    pytest -v tests/test_*.py
else
    echo "Running all tests..."
    pytest -v
fi

# Cleanup test database
if [[ -f "./test.db" ]]; then
    rm ./test.db
    echo "Cleaned up test database"
fi

echo ""
echo "Test suite completed!"
echo ""
echo "Usage:"
echo "  ./run_tests.sh           - Run all tests"
echo "  ./run_tests.sh coverage  - Run with coverage report"
echo "  ./run_tests.sh verbose   - Run with detailed output"
echo "  ./run_tests.sh fast      - Run fast tests only"
echo "  ./run_tests.sh integration - Run integration tests only"
