#!/bin/bash
# Deployment script for fotbollsplan-bevattning
# This script pulls the latest code, installs dependencies, and restarts services
# Can be run manually or triggered by GitHub Actions

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions for colored output
print_header() {
    echo -e "\n${BLUE}===================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Determine project directory
if [ -z "$PROJECT_DIR" ]; then
    PROJECT_DIR="/home/pi/fotbollsplan-bevattning"
fi

print_header "Starting deployment to $PROJECT_DIR"

# Navigate to project directory
if [ ! -d "$PROJECT_DIR" ]; then
    print_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1
print_success "Changed to project directory"

# Pull latest changes from git
print_header "Pulling latest changes from repository"
git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Current branch: $CURRENT_BRANCH"

# If on main branch, pull latest. Otherwise, inform user
if [ "$CURRENT_BRANCH" = "main" ]; then
    git pull origin main
    print_success "Pulled latest changes from main branch"
else
    print_info "Not on main branch. Skipping git pull."
fi

# Activate virtual environment
print_header "Activating Python virtual environment"
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found. Please run install_complete.py first."
    exit 1
fi

source .venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_header "Upgrading pip"
pip install --upgrade pip --quiet
print_success "pip upgraded"

# Install/update dependencies
print_header "Installing/updating dependencies"
if [ -f "api_requirements.txt" ]; then
    pip install -r api_requirements.txt --quiet
    print_success "API dependencies installed"
else
    print_error "api_requirements.txt not found"
fi

if [ -f "display_requirements.txt" ]; then
    pip install -r display_requirements.txt --quiet
    print_success "Display dependencies installed"
else
    print_info "display_requirements.txt not found (optional)"
fi

# Restart services
print_header "Restarting systemd services"

# Function to restart a service if it exists
restart_service() {
    local service_name=$1
    if systemctl list-unit-files | grep -q "^${service_name}.service"; then
        if sudo systemctl restart "$service_name"; then
            print_success "$service_name restarted successfully"
        else
            print_error "Failed to restart $service_name"
        fi
    else
        print_info "$service_name service not found (may not be installed yet)"
    fi
}

# Restart main services
restart_service "bevattning-api"
restart_service "display-manager"
restart_service "bevattning-scheduler"

# Verify service status
print_header "Verifying service status"

verify_service() {
    local service_name=$1
    if systemctl is-active --quiet "$service_name"; then
        print_success "$service_name is running"
    else
        if systemctl list-unit-files | grep -q "^${service_name}.service"; then
            print_error "$service_name is not running"
        else
            print_info "$service_name is not installed"
        fi
    fi
}

verify_service "bevattning-api"
verify_service "display-manager"
verify_service "bevattning-scheduler"

# Show brief status
print_header "Deployment Summary"
echo "Project Directory: $PROJECT_DIR"
echo "Current Branch: $CURRENT_BRANCH"
echo "Last Commit: $(git log -1 --oneline)"
echo ""

print_header "Deployment completed successfully!"
