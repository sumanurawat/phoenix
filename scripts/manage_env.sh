#!/bin/bash

# Phoenix Environment Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check current branch
get_current_branch() {
    git branch --show-current
}

# Function to check service status
check_service_status() {
    local env=$1
    local service_name=$2
    
    print_info "Checking $env environment status..."
    
    if gcloud run services describe "$service_name" --region=us-central1 &>/dev/null; then
        local url=$(gcloud run services describe "$service_name" --region=us-central1 --format="value(status.url)")
        print_status "$env service is running: $url"
    else
        print_error "$env service not found or not running"
    fi
}

# Function to deploy to staging
deploy_staging() {
    print_info "Deploying to staging environment..."
    
    current_branch=$(get_current_branch)
    
    if [ "$current_branch" != "dev" ]; then
        print_warning "You're on branch '$current_branch'. Switching to 'dev' branch..."
        git checkout dev
        git pull origin dev
    fi
    
    print_info "Pushing to dev branch to trigger staging deployment..."
    git push origin dev
    
    print_status "Staging deployment triggered! Monitor at:"
    echo "https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386"
}

# Function to deploy to production
deploy_production() {
    print_warning "Deploying to PRODUCTION environment..."
    read -p "Are you sure you want to deploy to production? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Production deployment cancelled."
        return
    fi
    
    current_branch=$(get_current_branch)
    
    if [ "$current_branch" != "main" ]; then
        print_warning "You're on branch '$current_branch'. Switching to 'main' branch..."
        git checkout main
        git pull origin main
    fi
    
    print_info "Pushing to main branch to trigger production deployment..."
    git push origin main
    
    print_status "Production deployment triggered! Monitor at:"
    echo "https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386"
}

# Function to fetch logs
fetch_logs() {
    local env=$1
    shift
    local args="$@"
    
    print_info "Fetching logs from $env environment..."
    python scripts/fetch_logs.py --environment "$env" $args
}

# Function to open environment in browser
open_environment() {
    local env=$1
    
    if [ "$env" = "staging" ]; then
        open "https://phoenix-dev-234619602247.us-central1.run.app"
    elif [ "$env" = "production" ]; then
        open "https://phoenix-234619602247.us-central1.run.app"
    else
        print_error "Unknown environment: $env"
    fi
}

# Function to show help
show_help() {
    echo "Phoenix Environment Management"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  status              - Check status of both environments"
    echo "  deploy staging      - Deploy current branch to staging"
    echo "  deploy production   - Deploy to production (requires confirmation)"
    echo "  logs staging [args] - Fetch logs from staging"
    echo "  logs production [args] - Fetch logs from production"
    echo "  open staging        - Open staging environment in browser"
    echo "  open production     - Open production environment in browser"
    echo "  help               - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 deploy staging"
    echo "  $0 logs staging --hours 6"
    echo "  $0 logs production --search 'error'"
    echo "  $0 open staging"
}

# Main script logic
case "${1:-help}" in
    "status")
        print_info "Phoenix Environment Status"
        echo "Current branch: $(get_current_branch)"
        echo ""
        check_service_status "Production" "phoenix"
        check_service_status "Staging" "phoenix-dev"
        ;;
    "deploy")
        case "$2" in
            "staging")
                deploy_staging
                ;;
            "production")
                deploy_production
                ;;
            *)
                print_error "Invalid deploy target. Use 'staging' or 'production'"
                exit 1
                ;;
        esac
        ;;
    "logs")
        case "$2" in
            "staging"|"production")
                env_name="$2"
                shift 2
                fetch_logs "$env_name" "$@"
                ;;
            *)
                print_error "Invalid logs target. Use 'staging' or 'production'"
                exit 1
                ;;
        esac
        ;;
    "open")
        case "$2" in
            "staging"|"production")
                open_environment "$2"
                ;;
            *)
                print_error "Invalid open target. Use 'staging' or 'production'"
                exit 1
                ;;
        esac
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
