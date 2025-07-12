#!/bin/bash

# Djobea AI Docker Deployment Script
# Comprehensive deployment with backup, monitoring, and maintenance

set -e

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="./backups"
LOG_FILE="./deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root is not recommended for security reasons."
    fi
    
    log "Prerequisites check completed."
}

# Environment setup
setup_environment() {
    log "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example "$ENV_FILE"
            warning "Please edit .env file with your actual configuration values."
        else
            error ".env.example file not found. Cannot create environment configuration."
            exit 1
        fi
    fi
    
    # Create necessary directories
    mkdir -p "$BACKUP_DIR"
    mkdir -p "./logs"
    mkdir -p "./static/uploads"
    mkdir -p "./data"
    mkdir -p "./docker/postgres"
    mkdir -p "./docker/nginx/ssl"
    
    # Set proper permissions
    chmod 755 ./logs ./static/uploads ./data
    
    log "Environment setup completed."
}

# Database backup
backup_database() {
    log "Creating database backup..."
    
    if docker-compose ps postgres | grep -q "Up"; then
        BACKUP_FILE="$BACKUP_DIR/djobea_backup_$(date +%Y%m%d_%H%M%S).sql"
        
        # Create backup
        docker-compose exec -T postgres pg_dump -U djobea_user -d djobea_ai > "$BACKUP_FILE" 2>/dev/null || true
        
        if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
            log "Database backup created: $BACKUP_FILE"
            
            # Keep only last 5 backups
            cd "$BACKUP_DIR"
            ls -t djobea_backup_*.sql | tail -n +6 | xargs -r rm
            cd ..
        else
            warning "Database backup failed or resulted in empty file."
        fi
    else
        info "PostgreSQL container not running. Skipping backup."
    fi
}

# Build and deploy
deploy() {
    log "Starting Djobea AI deployment..."
    
    # Build images
    log "Building Docker images..."
    docker-compose build --no-cache
    
    # Start services
    log "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    
    # Wait for PostgreSQL
    info "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai &>/dev/null; then
            log "PostgreSQL is ready."
            break
        fi
        sleep 2
        if [ $i -eq 30 ]; then
            error "PostgreSQL failed to start within 60 seconds."
            exit 1
        fi
    done
    
    # Wait for Redis
    info "Waiting for Redis..."
    for i in {1..15}; do
        if docker-compose exec redis redis-cli ping &>/dev/null; then
            log "Redis is ready."
            break
        fi
        sleep 2
        if [ $i -eq 15 ]; then
            error "Redis failed to start within 30 seconds."
            exit 1
        fi
    done
    
    # Wait for application
    info "Waiting for Djobea AI application..."
    for i in {1..60}; do
        if curl -f http://localhost:5000/health &>/dev/null; then
            log "Djobea AI application is ready."
            break
        fi
        sleep 2
        if [ $i -eq 60 ]; then
            error "Djobea AI application failed to start within 120 seconds."
            show_logs
            exit 1
        fi
    done
    
    log "Deployment completed successfully!"
}

# Show service status
status() {
    log "Checking service status..."
    
    echo ""
    echo "=== CONTAINER STATUS ==="
    docker-compose ps
    
    echo ""
    echo "=== HEALTH CHECKS ==="
    
    # Application health
    if curl -f http://localhost:5000/health &>/dev/null; then
        echo -e "${GREEN}✓ Application: Healthy${NC}"
    else
        echo -e "${RED}✗ Application: Unhealthy${NC}"
    fi
    
    # Database health
    if docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai &>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL: Ready${NC}"
    else
        echo -e "${RED}✗ PostgreSQL: Not ready${NC}"
    fi
    
    # Redis health
    if docker-compose exec redis redis-cli ping &>/dev/null; then
        echo -e "${GREEN}✓ Redis: Ready${NC}"
    else
        echo -e "${RED}✗ Redis: Not ready${NC}"
    fi
    
    echo ""
    echo "=== RESOURCE USAGE ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Show logs
show_logs() {
    log "Showing recent logs..."
    
    echo "=== DJOBEA AI APPLICATION LOGS ==="
    docker-compose logs --tail=50 djobea-ai
    
    echo ""
    echo "=== POSTGRESQL LOGS ==="
    docker-compose logs --tail=20 postgres
    
    echo ""
    echo "=== REDIS LOGS ==="
    docker-compose logs --tail=20 redis
}

# Maintenance
maintenance() {
    log "Performing maintenance tasks..."
    
    # Clean up old images
    info "Cleaning up old Docker images..."
    docker image prune -f
    
    # Clean up volumes (be careful with this)
    info "Cleaning up unused volumes..."
    docker volume prune -f
    
    # Update containers
    info "Pulling latest base images..."
    docker-compose pull
    
    # Create backup
    backup_database
    
    log "Maintenance completed."
}

# Stop services
stop() {
    log "Stopping Djobea AI services..."
    
    # Create backup before stopping
    backup_database
    
    # Stop services
    docker-compose down
    
    log "Services stopped."
}

# Complete cleanup
cleanup() {
    warning "This will remove all containers, volumes, and data. Are you sure? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log "Performing complete cleanup..."
        
        # Create final backup
        backup_database
        
        # Stop and remove everything
        docker-compose down -v --remove-orphans
        docker-compose rm -f
        
        # Remove images
        docker rmi $(docker images "djobea*" -q) 2>/dev/null || true
        
        log "Cleanup completed."
    else
        info "Cleanup cancelled."
    fi
}

# Restore from backup
restore() {
    if [ -z "$1" ]; then
        error "Please specify backup file: ./deploy.sh restore <backup_file>"
        exit 1
    fi
    
    BACKUP_FILE="$1"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    log "Restoring from backup: $BACKUP_FILE"
    
    # Stop application (keep database running)
    docker-compose stop djobea-ai
    
    # Restore database
    cat "$BACKUP_FILE" | docker-compose exec -T postgres psql -U djobea_user -d djobea_ai
    
    # Restart application
    docker-compose start djobea-ai
    
    log "Restore completed."
}

# Help function
show_help() {
    echo "Djobea AI Docker Deployment Script"
    echo ""
    echo "Usage: $0 {deploy|status|logs|stop|backup|restore|maintenance|cleanup|help}"
    echo ""
    echo "Commands:"
    echo "  deploy      - Deploy Djobea AI (build and start all services)"
    echo "  status      - Show service status and health checks"
    echo "  logs        - Show recent logs from all services"
    echo "  stop        - Stop all services (with backup)"
    echo "  backup      - Create database backup"
    echo "  restore     - Restore from backup file"
    echo "  maintenance - Perform maintenance tasks"
    echo "  cleanup     - Complete cleanup (removes all data)"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                           # Deploy the application"
    echo "  $0 status                           # Check status"
    echo "  $0 logs                             # View logs"
    echo "  $0 restore backups/backup_file.sql  # Restore from backup"
    echo ""
}

# Main script logic
case "${1:-help}" in
    deploy)
        check_prerequisites
        setup_environment
        backup_database
        deploy
        status
        ;;
    status)
        status
        ;;
    logs)
        show_logs
        ;;
    stop)
        stop
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore "$2"
        ;;
    maintenance)
        maintenance
        ;;
    cleanup)
        cleanup
        ;;
    help|*)
        show_help
        ;;
esac