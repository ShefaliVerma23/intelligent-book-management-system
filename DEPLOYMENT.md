# Deployment Guide

This document provides detailed instructions for deploying the Intelligent Book Management System in various environments.

## Quick Start (Development)

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd intelligent-book-management-system
   cp sample.env .env  # Edit with your settings
   ```

2. **Using Docker Compose (Recommended)**
   ```bash
   cd docker
   docker-compose up -d
   ```
   
   The application will be available at:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs

## Production Deployment Options

### 1. Docker-based Deployment (Cloud-Ready)

#### Prerequisites
- Docker and Docker Compose installed
- PostgreSQL database (can be containerized or external)
- Domain name (optional, for SSL)

#### Steps

1. **Environment Configuration**
   ```bash
   # Create production environment file
   cp sample.env .env.prod
   
   # Edit .env.prod with production values:
   # - Strong SECRET_KEY (32+ characters)
   # - Production database URL
   # - OpenRouter API key for AI features
   # - Set LOG_LEVEL=INFO or WARNING
   ```

2. **Deploy with Production Compose**
   ```bash
   cd docker
   docker-compose -f docker-compose.prod.yml --env-file ../.env.prod up -d
   ```

3. **Database Migration**
   ```bash
   # Run inside the container
   docker exec -it <container_name> alembic upgrade head
   ```

### 2. AWS Deployment

#### Option A: EC2 + RDS

1. **Setup RDS PostgreSQL Instance**
   - Launch RDS PostgreSQL 15
   - Configure security groups
   - Note connection string

2. **Launch EC2 Instance**
   ```bash
   # On EC2 instance
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Deploy Application**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd intelligent-book-management-system
   
   # Configure environment
   cp sample.env .env
   # Edit .env with RDS connection string
   
   # Deploy
   cd docker
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Configure Load Balancer**
   - Create Application Load Balancer
   - Configure target group (port 8000)
   - Add SSL certificate
   - Configure health checks (`/health` endpoint)

#### Option B: ECS with Fargate

1. **Build and Push to ECR**
   ```bash
   # Create ECR repository
   aws ecr create-repository --repository-name book-management
   
   # Build and push image
   docker build -f docker/Dockerfile -t book-management .
   docker tag book-management:latest <account-id>.dkr.ecr.<region>.amazonaws.com/book-management:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/book-management:latest
   ```

2. **Create ECS Task Definition**
   ```json
   {
     "family": "book-management-task",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "512",
     "memory": "1024",
     "executionRoleArn": "arn:aws:iam::<account>:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "book-management",
         "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/book-management:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "DATABASE_URL",
             "value": "postgresql://user:password@rds-endpoint:5432/database"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/book-management",
             "awslogs-region": "<region>",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

### 3. Heroku Deployment

1. **Prepare Application**
   ```bash
   # Create Procfile
   echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile
   
   # Create runtime.txt
   echo "python-3.11.5" > runtime.txt
   ```

2. **Deploy to Heroku**
   ```bash
   # Install Heroku CLI and login
   heroku create your-app-name
   
   # Add PostgreSQL addon
   heroku addons:create heroku-postgresql:mini
   
   # Set environment variables
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set OPENROUTER_API_KEY="your-api-key"
   
   # Deploy
   git push heroku main
   
   # Run migrations
   heroku run alembic upgrade head
   ```

### 4. Digital Ocean App Platform

1. **Create App Specification**
   ```yaml
   # .do/app.yaml
   name: book-management-system
   services:
   - name: api
     source_dir: /
     github:
       repo: your-username/intelligent-book-management-system
       branch: main
     run_command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: DATABASE_URL
       value: ${db.DATABASE_URL}
     - key: SECRET_KEY
       value: your-secret-key
     http_port: 8000
   databases:
   - name: db
     engine: PG
     version: "15"
     size_slug: db-s-dev-database
   ```

2. **Deploy**
   ```bash
   doctl apps create --spec .do/app.yaml
   ```

## Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes | - |
| `OPENROUTER_API_KEY` | AI service API key | No | - |
| `LLAMA_MODEL_PATH` | Local model path | No | microsoft/DialoGPT-medium |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration | No | 30 |
| `LOG_LEVEL` | Logging level | No | INFO |
| `ALLOWED_HOSTS` | CORS allowed hosts | No | * |

## Health Monitoring

The application provides several health endpoints:

- `GET /health` - Basic health check
- `GET /` - Application info
- `GET /docs` - API documentation

### Monitoring with External Services

#### AWS CloudWatch (for ECS/EC2)
```bash
# Install CloudWatch agent
# Configure custom metrics for response time, error rates
```

#### Prometheus + Grafana
```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

## SSL/TLS Configuration

### Using Nginx (Recommended)

1. **Obtain SSL Certificate**
   ```bash
   # Using Let's Encrypt
   sudo certbot --nginx -d yourdomain.com
   ```

2. **Nginx Configuration**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
       
       location / {
           proxy_pass http://api:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

## Performance Optimization

### Database Optimization
- Use connection pooling (built-in with SQLAlchemy)
- Add database indexes for frequently queried fields
- Consider read replicas for high traffic

### Application Optimization
- Enable gzip compression
- Use Redis for caching (optional service in docker-compose)
- Configure proper logging levels
- Use async database operations (already implemented)

### Container Optimization
```dockerfile
# Multi-stage build for smaller images
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
WORKDIR /app
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database URL format
   # Verify database is accessible
   docker exec -it postgres_container psql -U username -d database
   ```

2. **AI Service Issues**
   ```bash
   # Check API keys
   # Verify OpenRouter connectivity
   # Check model availability
   ```

3. **Authentication Problems**
   ```bash
   # Verify SECRET_KEY is set
   # Check token expiration times
   # Validate user credentials
   ```

### Logging

Enable debug logging for troubleshooting:
```bash
export LOG_LEVEL=DEBUG
```

View logs:
```bash
# Docker Compose
docker-compose logs -f api

# Heroku
heroku logs --tail

# AWS ECS
aws logs describe-log-groups
```

## Backup and Recovery

### Database Backups
```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec postgres_container pg_dump -U username database > backup_$DATE.sql

# Upload to S3 (optional)
aws s3 cp backup_$DATE.sql s3://your-backup-bucket/
```

### Application State
- User-generated content is in the database
- AI model cache can be regenerated
- Configuration is in environment variables

## Security Checklist

- [ ] Use strong SECRET_KEY (32+ characters)
- [ ] Enable HTTPS in production
- [ ] Configure proper CORS settings
- [ ] Use environment variables for secrets
- [ ] Regular security updates for dependencies
- [ ] Database access restricted to application
- [ ] Monitor for unusual activity
- [ ] Implement rate limiting (optional)

## Support and Maintenance

### Regular Maintenance Tasks
- Monitor application logs
- Update dependencies monthly
- Database performance tuning
- Security patches
- Backup verification

### Support Channels
- GitHub Issues for bugs
- Documentation updates
- Performance optimization requests
