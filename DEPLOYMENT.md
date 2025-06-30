# Deployment Guide

This guide covers different deployment scenarios for the Fabric Management Portal.

## Quick Start (Development)

### Windows
```cmd
# Clone and setup
git clone <repository-url>
cd fabricrequestportalv2

# Run development script
dev-start.bat
```

### Linux/macOS
```bash
# Clone and setup
git clone <repository-url>
cd fabricrequestportalv2

# Make script executable and run
chmod +x dev-start.sh
./dev-start.sh
```

## Docker Deployment

### Basic Docker Run
```bash
# Build the image
docker build -t fabric-portal .

# Run with environment file
docker run -d \
  --name fabric-portal \
  --env-file .env \
  -p 8000:8000 \
  fabric-portal
```

### Docker Compose (Recommended)
```bash
# Development mode
docker-compose up -d

# Production mode with nginx
docker-compose --profile production up -d
```

## Azure Container Apps Deployment

### Prerequisites
- Azure CLI installed and logged in
- Container registry (Azure Container Registry recommended)

### Steps

1. **Build and push image**
   ```bash
   # Login to Azure Container Registry
   az acr login --name yourregistry

   # Build and tag image
   docker build -t yourregistry.azurecr.io/fabric-portal:latest .

   # Push image
   docker push yourregistry.azurecr.io/fabric-portal:latest
   ```

2. **Create Container App**
   ```bash
   # Create resource group
   az group create --name fabric-portal-rg --location eastus

   # Create container app environment
   az containerapp env create \
     --name fabric-portal-env \
     --resource-group fabric-portal-rg \
     --location eastus

   # Create container app
   az containerapp create \
     --name fabric-portal \
     --resource-group fabric-portal-rg \
     --environment fabric-portal-env \
     --image yourregistry.azurecr.io/fabric-portal:latest \
     --target-port 8000 \
     --ingress external \
     --env-vars \
       TENANT_ID=your-tenant-id \
       CLIENT_ID=your-client-id \
       CLIENT_SECRET=your-client-secret \
       DB_SERVER=your-db-server \
       DB_NAME=your-db-name
   ```

## Azure App Service Deployment

### Using Azure CLI
```bash
# Create App Service plan
az appservice plan create \
  --name fabric-portal-plan \
  --resource-group fabric-portal-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --resource-group fabric-portal-rg \
  --plan fabric-portal-plan \
  --name fabric-portal-app \
  --deployment-container-image-name yourregistry.azurecr.io/fabric-portal:latest

# Configure environment variables
az webapp config appsettings set \
  --resource-group fabric-portal-rg \
  --name fabric-portal-app \
  --settings \
    TENANT_ID=your-tenant-id \
    CLIENT_ID=your-client-id \
    CLIENT_SECRET=your-client-secret \
    DB_SERVER=your-db-server \
    DB_NAME=your-db-name
```

## Environment Configuration

### Required Environment Variables
```bash
# Azure Configuration
TENANT_ID=your-azure-tenant-id
CLIENT_ID=your-app-registration-client-id
CLIENT_OBJECT_ID=your-app-registration-object-id
CLIENT_SECRET=your-app-registration-secret

# Database Configuration
DB_SERVER=your-database-server.database.windows.net
DB_NAME=your-database-name
```

### Optional Configuration
```bash
# Development settings
offlinemode=1  # Use fallback authentication
USER_ID=development-user-id
USER_MAIL=admin@yourdomain.com

# Azure subscriptions
SUBSCRIPTIONS=subscription-id-1,subscription-id-2
```

## Security Configuration

### Azure App Registration
1. **Create App Registration** in Azure Active Directory
2. **Configure API Permissions**:
   - Microsoft Graph: User.Read
   - Power BI Service: Workspace.ReadWrite.All
3. **Create Client Secret** and note the value
4. **Configure Authentication**:
   - Add redirect URIs for your deployment URLs
   - Enable ID tokens and access tokens

### Database Security
1. **Azure SQL Database**:
   - Configure firewall rules
   - Enable Azure AD authentication
   - Create contained database users

2. **Connection Security**:
   - Use Azure AD authentication when possible
   - Store connection strings securely
   - Enable SSL/TLS encryption

### Application Security
1. **Enable Easy Auth** (for Azure App Service):
   ```bash
   az webapp auth update \
     --resource-group fabric-portal-rg \
     --name fabric-portal-app \
     --enabled true \
     --action LoginWithAzureActiveDirectory \
     --aad-client-id your-client-id \
     --aad-client-secret your-client-secret
   ```

2. **Configure HTTPS**:
   - Enable HTTPS only
   - Configure custom domains with SSL certificates
   - Use HSTS headers

## Monitoring and Troubleshooting

### Health Checks
- Application health: `GET /debug/user`
- Headers check: `GET /debug/headers`

### Logging
```bash
# View container logs (Docker)
docker logs fabric-portal

# View Azure Container App logs
az containerapp logs show \
  --name fabric-portal \
  --resource-group fabric-portal-rg \
  --follow

# View Azure App Service logs
az webapp log tail \
  --resource-group fabric-portal-rg \
  --name fabric-portal-app
```

### Common Issues

1. **Database Connection**:
   - Check firewall rules
   - Verify ODBC driver installation
   - Test connection strings

2. **Authentication Issues**:
   - Verify App Registration configuration
   - Check Easy Auth setup
   - Review JWT token validation

3. **Fabric API Errors**:
   - Verify client permissions
   - Check capacity availability
   - Review API rate limits

## Performance Optimization

### Production Settings
```bash
# Increase worker processes
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Configure gunicorn (alternative)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
```

### Database Optimization
- Use connection pooling
- Index frequently queried columns
- Monitor query performance

### Caching
- Implement Redis for session caching
- Cache frequently accessed data
- Use CDN for static assets

## Backup and Recovery

### Database Backup
```bash
# Azure SQL Database automated backups are enabled by default
# Manual backup example:
az sql db export \
  --resource-group fabric-portal-rg \
  --server your-server \
  --name your-database \
  --admin-user your-admin \
  --admin-password your-password \
  --storage-key your-storage-key \
  --storage-key-type StorageAccessKey \
  --storage-uri https://yourstorageaccount.blob.core.windows.net/backups/backup.bacpac
```

### Application Backup
- Container images are stored in registry
- Source code in version control
- Environment configuration documented
