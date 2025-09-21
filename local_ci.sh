#!/bin/bash
set -euo pipefail

# Term MCP DeepSeek Local CI Simulation Script
# This script simulates the GitHub Actions CI pipeline locally
# to ensure the fixes work before pushing to GitHub

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check if required tools are available
check_requirements() {
    print_header "Checking Requirements"

    local missing_tools=()

    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi

    if ! command -v pip3 &> /dev/null; then
        missing_tools+=("pip3")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install them and try again."
        exit 1
    fi

    print_success "All required tools are available"
}

# Set up Python environment
setup_python() {
    print_header "Setting up Python Environment"

    print_status "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate

    print_status "Upgrading pip..."
    pip install --upgrade pip

    print_status "Installing project dependencies..."
    pip install -r requirements.txt

    print_status "Installing test dependencies..."
    pip install -r tests/requirements.txt

    print_success "Python environment set up"
}

# Run tests
run_tests() {
    print_header "Running Tests"

    source venv/bin/activate

    print_status "Setting up test environment variables..."
    export DEEPSEEK_API_KEY="test-key"
    export SECRET_KEY="test-secret-key"
    export DEBUG="true"

    print_status "Running pytest with the same tests as CI..."
    echo "=========================================== PYTEST OUTPUT ==========================================="
    if pytest tests/test_health.py tests/test_input_validator.py tests/test_auth_guard.py tests/test_api_integration.py::TestAPIIntegration::test_health_endpoint -v; then
        echo ""
        print_success "All tests passed successfully!"
        return 0
    else
        echo ""
        print_error "Some tests failed"
        return 1
    fi
}

# Main function
main() {
    print_header "Term MCP DeepSeek Local CI Simulation"
    print_status "This script simulates the GitHub Actions CI pipeline locally"
    echo ""

    check_requirements
    setup_python

    if run_tests; then
        print_header "🎉 Local CI Simulation Passed!"
        print_success "All checks completed successfully."
        print_status "You can now push your changes to GitHub with confidence."
        echo ""
        print_status "To clean up manually if needed:"
        echo "  rm -rf venv"
        exit 0
    else
        print_header "❌ Local CI Simulation Failed"
        print_error "Please fix the issues before pushing to GitHub."
        exit 1
    fi
}

# Run main function
main "$@"