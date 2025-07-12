# Djobea AI Docker Deployment Script for Windows
# PowerShell version with comprehensive deployment, backup, monitoring, and maintenance

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "status", "logs", "stop", "backup", "restore", "maintenance", "cleanup", "help")]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$BackupFile = ""
)

# Configuration
$COMPOSE_FILE = "docker-compose.yml"
$ENV_FILE = ".env"
$BACKUP_DIR = "./backups"
$LOG_FILE = "./deployment.log"

# Colors for output
function Write-Success($message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $message" -ForegroundColor Green
    Add-Content -Path $LOG_FILE -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $message"
}

function Write-Error($message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $message" -ForegroundColor Red
    Add-Content -Path $LOG_FILE -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $message"
}

function Write-Warning($message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] WARNING: $message" -ForegroundColor Yellow
    Add-Content -Path $LOG_FILE -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] WARNING: $message"
}

function Write-Info($message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] INFO: $message" -ForegroundColor Blue
    Add-Content -Path $LOG_FILE -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] INFO: $message"
}

# Check prerequisites
function Test-Prerequisites {
    Write-Success "Checking prerequisites..."
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed. Please install Docker Desktop for Windows first."
        exit 1
    }
    
    # Check Docker Compose
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        # Try docker compose (newer syntax)
        try {
            docker compose version | Out-Null
        }
        catch {
            Write-Error "Docker Compose is not installed. Please install Docker Compose first."
            exit 1
        }
    }
    
    # Check if Docker is running
    try {
        docker info | Out-Null
    }
    catch {
        Write-Error "Docker is not running. Please start Docker Desktop."
        exit 1
    }
    
    Write-Success "Prerequisites check completed."
}

# Environment setup
function Initialize-Environment {
    Write-Success "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if (-not (Test-Path $ENV_FILE)) {
        Write-Warning ".env file not found. Creating from .env.example..."
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" $ENV_FILE
            Write-Warning "Please edit .env file with your actual configuration values."
        }
        else {
            Write-Error ".env.example file not found. Cannot create environment configuration."
            exit 1
        }
    }
    
    # Create necessary directories
    $directories = @($BACKUP_DIR, "./logs", "./static/uploads", "./data", "./docker/postgres", "./docker/nginx/ssl")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Success "Environment setup completed."
}

# Database backup
function Backup-Database {
    Write-Success "Creating database backup..."
    
    $containers = docker-compose ps --format json | ConvertFrom-Json
    $postgresContainer = $containers | Where-Object { $_.Service -eq "postgres" -and $_.State -eq "running" }
    
    if ($postgresContainer) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = "$BACKUP_DIR/djobea_backup_$timestamp.sql"
        
        # Create backup
        try {
            docker-compose exec -T postgres pg_dump -U djobea_user -d djobea_ai | Out-File -FilePath $backupFile -Encoding UTF8
            
            if ((Test-Path $backupFile) -and ((Get-Item $backupFile).Length -gt 0)) {
                Write-Success "Database backup created: $backupFile"
                
                # Keep only last 5 backups
                Get-ChildItem $BACKUP_DIR -Name "djobea_backup_*.sql" | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -Skip 5 | 
                    ForEach-Object { Remove-Item "$BACKUP_DIR/$_" -Force }
            }
            else {
                Write-Warning "Database backup failed or resulted in empty file."
            }
        }
        catch {
            Write-Warning "Database backup failed: $($_.Exception.Message)"
        }
    }
    else {
        Write-Info "PostgreSQL container not running. Skipping backup."
    }
}

# Build and deploy
function Start-Deployment {
    Write-Success "Starting Djobea AI deployment..."
    
    # Build images
    Write-Success "Building Docker images..."
    docker-compose build --no-cache
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Docker images."
        exit 1
    }
    
    # Start services
    Write-Success "Starting services..."
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start services."
        exit 1
    }
    
    # Wait for services to be healthy
    Write-Success "Waiting for services to be healthy..."
    
    # Wait for PostgreSQL
    Write-Info "Waiting for PostgreSQL..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "PostgreSQL is ready."
                break
            }
        }
        catch {}
        
        Start-Sleep -Seconds 2
        if ($i -eq 30) {
            Write-Error "PostgreSQL failed to start within 60 seconds."
            Show-Logs
            exit 1
        }
    }
    
    # Wait for Redis
    Write-Info "Waiting for Redis..."
    for ($i = 1; $i -le 15; $i++) {
        try {
            docker-compose exec redis redis-cli ping | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Redis is ready."
                break
            }
        }
        catch {}
        
        Start-Sleep -Seconds 2
        if ($i -eq 15) {
            Write-Error "Redis failed to start within 30 seconds."
            Show-Logs
            exit 1
        }
    }
    
    # Wait for application
    Write-Info "Waiting for Djobea AI application..."
    for ($i = 1; $i -le 60; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Success "Djobea AI application is ready."
                break
            }
        }
        catch {}
        
        Start-Sleep -Seconds 2
        if ($i -eq 60) {
            Write-Error "Djobea AI application failed to start within 120 seconds."
            Show-Logs
            exit 1
        }
    }
    
    Write-Success "Deployment completed successfully!"
}

# Show service status
function Get-ServiceStatus {
    Write-Success "Checking service status..."
    
    Write-Host ""
    Write-Host "=== CONTAINER STATUS ===" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host ""
    Write-Host "=== HEALTH CHECKS ===" -ForegroundColor Cyan
    
    # Application health
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Application: Healthy" -ForegroundColor Green
        }
        else {
            Write-Host "✗ Application: Unhealthy" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "✗ Application: Unhealthy" -ForegroundColor Red
    }
    
    # Database health
    try {
        docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ PostgreSQL: Ready" -ForegroundColor Green
        }
        else {
            Write-Host "✗ PostgreSQL: Not ready" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "✗ PostgreSQL: Not ready" -ForegroundColor Red
    }
    
    # Redis health
    try {
        docker-compose exec redis redis-cli ping | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Redis: Ready" -ForegroundColor Green
        }
        else {
            Write-Host "✗ Redis: Not ready" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "✗ Redis: Not ready" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "=== RESOURCE USAGE ===" -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Show logs
function Show-Logs {
    Write-Success "Showing recent logs..."
    
    Write-Host "=== DJOBEA AI APPLICATION LOGS ===" -ForegroundColor Cyan
    docker-compose logs --tail=50 djobea-ai
    
    Write-Host ""
    Write-Host "=== POSTGRESQL LOGS ===" -ForegroundColor Cyan
    docker-compose logs --tail=20 postgres
    
    Write-Host ""
    Write-Host "=== REDIS LOGS ===" -ForegroundColor Cyan
    docker-compose logs --tail=20 redis
}

# Maintenance
function Start-Maintenance {
    Write-Success "Performing maintenance tasks..."
    
    # Clean up old images
    Write-Info "Cleaning up old Docker images..."
    docker image prune -f
    
    # Clean up volumes (be careful with this)
    Write-Info "Cleaning up unused volumes..."
    docker volume prune -f
    
    # Update containers
    Write-Info "Pulling latest base images..."
    docker-compose pull
    
    # Create backup
    Backup-Database
    
    Write-Success "Maintenance completed."
}

# Stop services
function Stop-Services {
    Write-Success "Stopping Djobea AI services..."
    
    # Create backup before stopping
    Backup-Database
    
    # Stop services
    docker-compose down
    
    Write-Success "Services stopped."
}

# Complete cleanup
function Start-Cleanup {
    $response = Read-Host "This will remove all containers, volumes, and data. Are you sure? (y/N)"
    
    if ($response -match "^[yY]([eE][sS])?$") {
        Write-Success "Performing complete cleanup..."
        
        # Create final backup
        Backup-Database
        
        # Stop and remove everything
        docker-compose down -v --remove-orphans
        docker-compose rm -f
        
        # Remove images
        try {
            $images = docker images "djobea*" -q
            if ($images) {
                docker rmi $images
            }
        }
        catch {}
        
        Write-Success "Cleanup completed."
    }
    else {
        Write-Info "Cleanup cancelled."
    }
}

# Restore from backup
function Restore-Database {
    param([string]$BackupFilePath)
    
    if (-not $BackupFilePath) {
        Write-Error "Please specify backup file: .\deploy.ps1 restore <backup_file>"
        exit 1
    }
    
    if (-not (Test-Path $BackupFilePath)) {
        Write-Error "Backup file not found: $BackupFilePath"
        exit 1
    }
    
    Write-Success "Restoring from backup: $BackupFilePath"
    
    # Stop application (keep database running)
    docker-compose stop djobea-ai
    
    # Restore database
    Get-Content $BackupFilePath | docker-compose exec -T postgres psql -U djobea_user -d djobea_ai
    
    # Restart application
    docker-compose start djobea-ai
    
    Write-Success "Restore completed."
}

# Help function
function Show-Help {
    Write-Host "Djobea AI Docker Deployment Script for Windows" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 {deploy|status|logs|stop|backup|restore|maintenance|cleanup|help}" -ForegroundColor White
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  deploy      - Deploy Djobea AI (build and start all services)"
    Write-Host "  status      - Show service status and health checks"
    Write-Host "  logs        - Show recent logs from all services"
    Write-Host "  stop        - Stop all services (with backup)"
    Write-Host "  backup      - Create database backup"
    Write-Host "  restore     - Restore from backup file"
    Write-Host "  maintenance - Perform maintenance tasks"
    Write-Host "  cleanup     - Complete cleanup (removes all data)"
    Write-Host "  help        - Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\deploy.ps1 deploy                           # Deploy the application"
    Write-Host "  .\deploy.ps1 status                           # Check status"
    Write-Host "  .\deploy.ps1 logs                             # View logs"
    Write-Host "  .\deploy.ps1 restore backups\backup_file.sql  # Restore from backup"
    Write-Host ""
    Write-Host "Requirements:" -ForegroundColor Magenta
    Write-Host "  - Docker Desktop for Windows"
    Write-Host "  - PowerShell 5.1 or later"
    Write-Host "  - Windows 10/11 or Windows Server 2016+"
    Write-Host ""
}

# Main script logic
switch ($Command) {
    "deploy" {
        Test-Prerequisites
        Initialize-Environment
        Backup-Database
        Start-Deployment
        Get-ServiceStatus
    }
    "status" {
        Get-ServiceStatus
    }
    "logs" {
        Show-Logs
    }
    "stop" {
        Stop-Services
    }
    "backup" {
        Backup-Database
    }
    "restore" {
        Restore-Database -BackupFilePath $BackupFile
    }
    "maintenance" {
        Start-Maintenance
    }
    "cleanup" {
        Start-Cleanup
    }
    default {
        Show-Help
    }
}