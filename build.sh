#!/bin/bash

# Smart Home Health Hub - Build Script
# This script automates the deployment process for the SHH system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service names
BACKEND_SERVICE="shh-device.backend"
FRONTEND_SERVICE="shh-device.frontend"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service exists
service_exists() {
    systemctl list-unit-files | grep -q "^$1.service"
}

# Function to check if service is active
service_is_active() {
    systemctl is-active --quiet "$1" 2>/dev/null
}

# Function to create backend service
create_backend_service() {
    local project_root="$1"
    local service_file="/etc/systemd/system/${BACKEND_SERVICE}.service"
    
    print_status "Creating backend service file..."
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Smart Home Health Hub Backend
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=${project_root}/backend
Environment=PATH=${project_root}/.venv/bin
ExecStart=${project_root}/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$BACKEND_SERVICE"
    print_success "Backend service created and enabled"
}

# Function to create frontend service
create_frontend_service() {
    local project_root="$1"
    local service_file="/etc/systemd/system/${FRONTEND_SERVICE}.service"
    
    print_status "Creating frontend service file..."
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Smart Home Health Hub Frontend
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=${project_root}/frontend
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/npx serve -s dist -l 3000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$FRONTEND_SERVICE"
    print_success "Frontend service created and enabled"
}

# Function to stop service if running
stop_service_if_running() {
    local service_name="$1"
    if service_exists "$service_name"; then
        if service_is_active "$service_name"; then
            print_status "Stopping $service_name service..."
            sudo systemctl stop "$service_name"
            print_success "$service_name service stopped"
        else
            print_status "$service_name service is not running"
        fi
    fi
}

# Function to start service
start_service() {
    local service_name="$1"
    if service_exists "$service_name"; then
        print_status "Starting $service_name service..."
        sudo systemctl start "$service_name"
        print_success "$service_name service started"
    fi
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists git; then
    print_error "Git is not installed"
    exit 1
fi

if ! command_exists python3; then
    print_error "Python 3 is not installed"
    exit 1
fi

if ! command_exists pip; then
    print_error "Pip is not installed"
    exit 1
fi

if ! command_exists npm; then
    print_error "NPM is not installed"
    exit 1
fi

if ! command_exists systemctl; then
    print_error "systemctl is not available - this script requires systemd"
    exit 1
fi

print_success "All prerequisites are available"

# Store the original directory
ORIGINAL_DIR=$(pwd)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_status "Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Check and create services if needed
print_status "Checking for existing services..."

if ! service_exists "$BACKEND_SERVICE"; then
    print_warning "Backend service does not exist, creating it..."
    create_backend_service "$PROJECT_ROOT"
else
    print_success "Backend service already exists"
fi

if ! service_exists "$FRONTEND_SERVICE"; then
    print_warning "Frontend service does not exist, creating it..."
    create_frontend_service "$PROJECT_ROOT"
else
    print_success "Frontend service already exists"
fi

# Stop services before build
print_status "Stopping services for build process..."
stop_service_if_running "$BACKEND_SERVICE"
stop_service_if_running "$FRONTEND_SERVICE"

# Step 1: Pull from GitHub
print_status "Pulling latest changes from GitHub..."
if git pull origin $(git branch --show-current); then
    print_success "Successfully pulled latest changes"
else
    print_error "Failed to pull from GitHub"
    exit 1
fi

# Step 2: Backend setup
print_status "Setting up backend..."
cd backend

# Check if virtual environment exists, create if not
if [ ! -d "../.venv" ]; then
    print_status "Creating Python virtual environment..."
    cd ..
    python3 -m venv .venv
    cd backend
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source ../.venv/bin/activate

# Install/update requirements
print_status "Installing/updating Python requirements..."
if pip install -r requirements.txt; then
    print_success "Python requirements installed"
else
    print_error "Failed to install Python requirements"
    exit 1
fi

# Run Alembic migrations
print_status "Running database migrations..."
if alembic upgrade head; then
    print_success "Database migrations completed"
else
    print_warning "Database migrations may have failed - continuing anyway"
fi

# Step 3: Frontend setup
print_status "Setting up frontend..."
cd ../frontend

# Install npm dependencies
print_status "Installing NPM dependencies..."
if npm install; then
    print_success "NPM dependencies installed"
else
    print_error "Failed to install NPM dependencies"
    exit 1
fi

# Install serve globally if not present (needed for frontend service)
if ! command_exists serve; then
    print_status "Installing serve package globally for frontend service..."
    if npm install -g serve; then
        print_success "Serve package installed globally"
    else
        print_warning "Failed to install serve globally - frontend service may not work"
    fi
else
    print_success "Serve package is already available"
fi

# Build frontend
print_status "Building frontend..."
if npm run build; then
    print_success "Frontend build completed"
else
    print_error "Frontend build failed"
    exit 1
fi

# Return to original directory
cd "$ORIGINAL_DIR"

# Start services after successful build
print_status "Starting services after successful build..."
start_service "$BACKEND_SERVICE"
start_service "$FRONTEND_SERVICE"

print_success "Build process completed successfully!"
print_status "Services are now running:"
echo "  - Backend service: $BACKEND_SERVICE"
echo "  - Frontend service: $FRONTEND_SERVICE"
print_status "Service management commands:"
echo "  - Check status: sudo systemctl status $BACKEND_SERVICE"
echo "  - Check status: sudo systemctl status $FRONTEND_SERVICE"
echo "  - View logs: sudo journalctl -u $BACKEND_SERVICE -f"
echo "  - View logs: sudo journalctl -u $FRONTEND_SERVICE -f"
echo "  - Stop services: sudo systemctl stop $BACKEND_SERVICE $FRONTEND_SERVICE"
echo "  - Start services: sudo systemctl start $BACKEND_SERVICE $FRONTEND_SERVICE"
