# Windows Deployment Guide for Djobea AI

## Prerequisites

### Required Software
1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Ensure WSL 2 backend is enabled
   - Minimum requirements: Windows 10 64-bit Pro, Enterprise, or Education

2. **PowerShell** (Usually pre-installed)
   - Windows PowerShell 5.1 or later
   - Or PowerShell Core 7.x

3. **Git for Windows** (Optional but recommended)
   - Download from: https://git-scm.windows.com/
   - Includes Git Bash for Linux-style commands

## Deployment Options

### Option 1: PowerShell Script (Recommended)
```powershell
# Navigate to project directory
cd djobea-ai

# Deploy the application
.\deploy.ps1 deploy

# Check status
.\deploy.ps1 status

# View logs
.\deploy.ps1 logs
```

### Option 2: Batch File (Command Prompt)
```cmd
REM Navigate to project directory
cd djobea-ai

REM Deploy the application
deploy.bat deploy

REM Check status
deploy.bat status

REM View logs
deploy.bat logs
```

### Option 3: Git Bash (Linux-style)
```bash
# Navigate to project directory
cd djobea-ai

# Deploy the application
./deploy.sh deploy

# Check status
./deploy.sh status

# View logs
./deploy.sh logs
```

## Windows-Specific Features

### PowerShell Script Features
- **Native Windows Integration**: Full PowerShell cmdlets and .NET framework access
- **Enhanced Error Handling**: Windows-specific error messages and troubleshooting
- **Path Handling**: Automatic Windows path format conversion
- **Service Management**: Windows-compatible service checks and monitoring
- **Color Output**: Windows Console color support

### Cross-Platform Compatibility
The bash script (`deploy.sh`) has been enhanced with Windows detection:
- Automatic OS detection (Windows/Linux/macOS)
- Windows-specific Docker Desktop checks
- Modified permission handling for Windows filesystems
- Alternative health check methods for Windows environments

## Environment Setup

### 1. Create Environment File
```powershell
# Copy example environment file
Copy-Item .env.example .env

# Edit with your configuration
notepad .env
```

### 2. Required Environment Variables
```env
# Database Configuration
POSTGRES_PASSWORD=your_secure_password

# API Keys (Required)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_whatsapp_number

# Application Configuration
SECRET_KEY=your_secret_key
ENVIRONMENT=production
```

## Windows Deployment Commands

### PowerShell Commands
```powershell
# Full deployment
.\deploy.ps1 deploy

# Service status
.\deploy.ps1 status

# View logs
.\deploy.ps1 logs

# Stop services
.\deploy.ps1 stop

# Database backup
.\deploy.ps1 backup

# Restore database
.\deploy.ps1 restore "backups\backup_file.sql"

# Maintenance
.\deploy.ps1 maintenance

# Complete cleanup
.\deploy.ps1 cleanup

# Help
.\deploy.ps1 help
```

### Command Prompt Commands
```cmd
REM Full deployment
deploy.bat deploy

REM Service status
deploy.bat status

REM View logs
deploy.bat logs

REM Stop services
deploy.bat stop

REM Database backup
deploy.bat backup

REM Help
deploy.bat help
```

## Windows-Specific Troubleshooting

### Docker Desktop Issues

1. **Docker Not Running**
   ```
   Error: Docker is not running. Please start Docker Desktop.
   ```
   **Solution**: Open Docker Desktop from Start Menu or System Tray

2. **WSL 2 Not Enabled**
   ```
   Error: WSL 2 installation is incomplete
   ```
   **Solution**: 
   - Enable WSL 2 in Windows Features
   - Install WSL 2 Linux kernel update
   - Restart Docker Desktop

3. **Hyper-V Conflicts**
   ```
   Error: Hyper-V is not available
   ```
   **Solution**:
   - Enable Hyper-V in Windows Features
   - Or use Docker Desktop WSL 2 backend instead

### PowerShell Execution Policy

If you get execution policy errors:
```powershell
# Check current policy
Get-ExecutionPolicy

# Set execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run script with bypass (temporary)
powershell -ExecutionPolicy Bypass -File deploy.ps1 deploy
```

### Path and Permission Issues

1. **Long Path Names**
   - Enable long path support in Windows
   - Use shorter directory names if needed

2. **File Permissions**
   - Run PowerShell as Administrator if needed
   - Check Docker Desktop has proper permissions

3. **Antivirus Software**
   - Add project directory to antivirus exclusions
   - Add Docker Desktop to exclusions

### Network and Firewall

1. **Port Access**
   ```
   Error: Cannot access http://localhost:5000
   ```
   **Solution**:
   - Check Windows Firewall settings
   - Allow Docker Desktop through firewall
   - Verify ports 5000, 5432, 6379 are not blocked

2. **VPN/Proxy Issues**
   - Disable VPN during deployment
   - Configure Docker Desktop proxy settings if needed

## Windows File System Considerations

### Volume Mounts
Windows paths in docker-compose.yml are automatically handled:
```yaml
volumes:
  - ./logs:/app/logs              # Works on Windows
  - ./static/uploads:/app/static/uploads
  - ./data:/app/data
```

### Backup Files
Backup files are stored with Windows-compatible naming:
```
backups\djobea_backup_20250712_143022.sql
```

### Log Files
Log files use Windows line endings and paths:
```
.\deployment.log
.\logs\application.log
```

## Performance Optimization for Windows

### Docker Desktop Settings
1. **Memory Allocation**: Increase Docker memory limit (8GB recommended)
2. **CPU Allocation**: Allocate sufficient CPU cores (4+ recommended)
3. **Disk Space**: Ensure adequate disk space for containers and volumes

### Windows-Specific Settings
```powershell
# Check available resources
Get-ComputerInfo | Select-Object TotalPhysicalMemory, CsProcessors

# Monitor Docker resource usage
docker stats --no-stream
```

## Windows Service Integration

### Running as Windows Service (Optional)
To run Djobea AI as a Windows service:

1. Install NSSM (Non-Sucking Service Manager)
2. Create service wrapper script
3. Register as Windows service

```cmd
REM Install as service
nssm install "Djobea AI" "C:\path\to\deploy.bat" "deploy"

REM Start service
nssm start "Djobea AI"
```

## Backup and Maintenance on Windows

### Automated Backups
```powershell
# Create scheduled task for daily backups
$action = New-ScheduledTaskAction -Execute "PowerShell" -Argument "-File C:\path\to\deploy.ps1 backup"
$trigger = New-ScheduledTaskTrigger -Daily -At "2:00AM"
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Djobea AI Backup"
```

### Windows Update Considerations
- Schedule deployments after Windows updates
- Test in development environment first
- Keep backup before major Windows updates

## Support and Resources

### Windows-Specific Documentation
- Docker Desktop for Windows: https://docs.docker.com/desktop/windows/
- PowerShell Documentation: https://docs.microsoft.com/powershell/
- WSL 2 Setup: https://docs.microsoft.com/windows/wsl/

### Common Windows Commands
```powershell
# Check Windows version
winver

# Check PowerShell version
$PSVersionTable.PSVersion

# Check Docker version
docker --version
docker-compose --version

# Check available ports
netstat -an | findstr ":5000"
```

The Djobea AI platform is now fully compatible with Windows environments and provides multiple deployment options to suit different Windows configurations and user preferences.