#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running tests with coverage...${NC}"

# Run tests with coverage
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    
    # Check coverage threshold
    COVERAGE=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if (( $(echo "$COVERAGE >= 80" | bc -l) )); then
        echo -e "${GREEN}Coverage is at ${COVERAGE}%${NC}"
    else
        echo -e "${RED}Coverage is below 80% (${COVERAGE}%)${NC}"
        exit 1
    fi
else
    echo -e "${RED}Tests failed!${NC}"
    exit 1
fi

# Generate coverage badge
coverage-badge -o coverage.svg

echo -e "${YELLOW}Coverage report generated in coverage_html/ directory${NC}"
echo -e "${YELLOW}Coverage XML report generated as coverage.xml${NC}"
echo -e "${YELLOW}Coverage badge generated as coverage.svg${NC}" 