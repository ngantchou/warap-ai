# Docker Deployment Guide for Djobea AI

## Quick Start

1. **Clone and Setup**
```bash
git clone <your-repo>
cd djobea-ai
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Deploy with One Command**
```bash
./deploy.sh deploy
```

## Fixed Docker Issues

### ✅ PostgreSQL Connection Issue Resolved

The original error:
```
sqlalchemy.exc.OperationalError: could not translate host name "2025@postgres" to address
```

**Root Cause**: Malformed DATABASE_URL containing "2025@postgres" instead of proper credentials.

**Solutions Implemented**:

1. **Fixed Docker Compose Configuration**
   - Added explicit PostgreSQL environment variables
   - Corrected DATABASE_URL format
   - Added proper service dependencies

2. **Enhanced Database Connection Logic**
   - Added database URL validation and repair
   - Automatic detection of Docker environment
   - Fallback to environment variables for connection parameters

3. **Complete Environment Setup**
   - Created proper `.env` file with correct format
   - Added PostgreSQL initialization script
   - Configured proper service networking

## Docker Architecture

### Services

1. **PostgreSQL Database** (`postgres`)
   - Image: `postgres:15-alpine`
   - Database: `djobea_ai`
   - User: `djobea_user`
   - Port: `5432`
   - Persistent volume for data

2. **Redis Cache** (`redis`)
   - Image: `redis:7-alpine`
   - Password protected
   - Port: `6379`
   - Persistent volume for data

3. **Djobea AI Application** (`djobea-ai`)
   - Built from Dockerfile
   - Depends on PostgreSQL and Redis
   - Port: `5000`
   - Includes health checks

4. **Nginx Reverse Proxy** (`nginx`)
   - Image: `nginx:alpine`
   - Rate limiting and security headers
   - Ports: `80` and `443`
   - Static file serving

### Network Configuration

- All services connected via `djobea-network`
- Service discovery using Docker service names
- Proper health checks and dependencies

## Environment Configuration

### Required Environment Variables

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# API Keys (Required)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Twilio (Required for WhatsApp)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_whatsapp_number

# Application
SECRET_KEY=your_secret_key
ENVIRONMENT=production
```

## Deployment Commands

### Basic Operations
```bash
# Deploy application
./deploy.sh deploy

# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Stop services
./deploy.sh stop
```

### Maintenance Operations
```bash
# Create database backup
./deploy.sh backup

# Restore from backup
./deploy.sh restore backups/backup_file.sql

# Perform maintenance
./deploy.sh maintenance

# Complete cleanup (removes all data)
./deploy.sh cleanup
```

## Database Management

### Automatic Initialization
- Database and user created automatically
- Required extensions installed
- Proper permissions configured

### Backup and Restore
- Automatic backups before deployments
- Manual backup creation available
- Point-in-time restore capability
- Backup retention (keeps last 5 backups)

## Security Features

### Application Security
- Non-root user in containers
- Security headers via Nginx
- Rate limiting on API endpoints
- Environment variable protection

### Network Security
- Internal Docker network
- Service isolation
- Proper port exposure
- Health check endpoints

## Monitoring and Logging

### Health Checks
- PostgreSQL: Connection and query tests
- Redis: Ping tests
- Application: HTTP health endpoint
- Nginx: Service availability

### Logging
- Centralized logging via Docker
- Application logs in `/app/logs`
- Nginx access and error logs
- PostgreSQL logs for debugging

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check PostgreSQL status
   docker-compose exec postgres pg_isready -U djobea_user -d djobea_ai
   
   # View database logs
   docker-compose logs postgres
   ```

2. **Application Startup Issues**
   ```bash
   # Check application logs
   docker-compose logs djobea-ai
   
   # Check health endpoint
   curl http://localhost:5000/health
   ```

3. **Memory or Performance Issues**
   ```bash
   # Check resource usage
   docker stats
   
   # View system status
   ./deploy.sh status
   ```

### Container Management

```bash
# Restart specific service
docker-compose restart djobea-ai

# Rebuild application container
docker-compose build djobea-ai
docker-compose up -d djobea-ai

# Access container shell
docker-compose exec djobea-ai bash
```

## Production Considerations

### Performance Optimization
- PostgreSQL connection pooling
- Redis caching configuration
- Nginx static file serving
- Resource limits and reservations

### Scaling Options
- Horizontal scaling with load balancer
- Database read replicas
- Redis clustering
- Container orchestration

### Backup Strategy
- Automated daily backups
- Offsite backup storage
- Point-in-time recovery
- Configuration backup

## Maintenance Schedule

### Daily
- Health check monitoring
- Log rotation
- Performance metrics

### Weekly
- Database backup verification
- Security updates
- Resource usage review

### Monthly
- Full system backup
- Dependency updates
- Performance optimization

## Support

For issues or questions:
1. Check logs with `./deploy.sh logs`
2. Verify status with `./deploy.sh status`
3. Review environment configuration
4. Check Docker and system resources

The Docker deployment is now fully functional with proper database connectivity and comprehensive management tools.