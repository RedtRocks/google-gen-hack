# Azure Deployment Guide

Complete guide to deploy the Legal Document Demystifier application to Microsoft Azure.

---

## 📋 Prerequisites

Before deploying to Azure, ensure you have:

1. **Azure Account**

   - Sign up at [azure.microsoft.com](https://azure.microsoft.com/free/)
   - Free tier includes: 750 hours of B1 compute, 5GB storage, 1TB bandwidth

2. **Azure CLI**

   - Download from: https://aka.ms/installazurecliwindows
   - Verify installation: `az --version`

3. **Node.js** (for building frontend)

   - Version 18+ recommended
   - Download from: https://nodejs.org/

4. **Python 3.11+**

   - Already required for local development

5. **Git** (optional, for Git-based deployment)

6. **Gemini API Key**
   - Get from: https://aistudio.google.com/app/apikey
   - Required for document analysis features

---

## 🚀 Deployment Methods

Choose one of the following deployment methods:

### Method 1: Automated PowerShell Script (Recommended)

The easiest way to deploy using the provided automation script.

#### Steps:

```powershell
# 1. Open PowerShell in the project directory
cd "c:\Computer\Coding\genhack - Copy"

# 2. Run the deployment script
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "legal-demystifier-app" -Location "East US" -Sku "B1"
```

**Parameters:**

- `ResourceGroup`: Name for your Azure resource group (e.g., "legal-demystifier-rg")
- `AppName`: Unique name for your web app (e.g., "legal-demystifier-app")
- `Location`: Azure region (e.g., "East US", "West Europe", "Southeast Asia")
- `Sku`: Pricing tier (B1=Basic, S1=Standard, P1V2=Premium)

The script will:

- ✅ Check Azure CLI installation
- ✅ Login to Azure
- ✅ Create resource group
- ✅ Create App Service plan
- ✅ Create Web App
- ✅ Configure settings (port, API key)
- ✅ Build frontend
- ✅ Deploy application
- ✅ Display app URL

---

### Method 2: Azure CLI Manual Deployment

Step-by-step manual deployment using Azure CLI.

#### 1. Login to Azure

```powershell
az login
```

#### 2. Create Resource Group

```powershell
az group create --name legal-demystifier-rg --location "East US"
```

#### 3. Create App Service Plan

```powershell
az appservice plan create `
  --name legal-demystifier-plan `
  --resource-group legal-demystifier-rg `
  --sku B1 `
  --is-linux
```

**Pricing Tiers:**

- **Free (F1)**: Free, 60 min/day CPU, 1GB RAM, 1GB storage
- **Basic (B1)**: ~$13/month, 1 core, 1.75GB RAM, 10GB storage
- **Standard (S1)**: ~$70/month, 1 core, 1.75GB RAM, 50GB storage
- **Premium (P1V2)**: ~$80/month, 1 core, 3.5GB RAM, 250GB storage

#### 4. Create Web App

```powershell
az webapp create `
  --resource-group legal-demystifier-rg `
  --plan legal-demystifier-plan `
  --name legal-demystifier-app `
  --runtime "PYTHON:3.11"
```

**Note:** App name must be globally unique (becomes: `https://legal-demystifier-app.azurewebsites.net`)

#### 5. Configure App Settings

```powershell
# Set port configuration
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --settings WEBSITES_PORT=8080 SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Set API key (replace with your actual key)
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --settings GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"

# Set startup command
az webapp config set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --startup-file "python main.py"
```

#### 6. Build Frontend

```powershell
# Install dependencies (if not done)
npm install

# Build frontend
npm run client:build
```

#### 7. Deploy Application

```powershell
az webapp up `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --runtime "PYTHON:3.11"
```

---

### Method 3: Azure Portal Manual Deployment

Deploy using the Azure Portal web interface.

#### Steps:

1. **Login to Azure Portal**

   - Go to: https://portal.azure.com/
   - Sign in with your Azure account

2. **Create Web App**

   - Click "Create a resource"
   - Search for "Web App"
   - Click "Create"

3. **Configure Basic Settings**

   - **Subscription**: Select your subscription
   - **Resource Group**: Create new "legal-demystifier-rg"
   - **Name**: "legal-demystifier-app" (must be unique)
   - **Publish**: Code
   - **Runtime stack**: Python 3.11
   - **Operating System**: Linux
   - **Region**: East US (or preferred)

4. **Configure App Service Plan**

   - Click "Create new"
   - Name: "legal-demystifier-plan"
   - Pricing tier: B1 (or preferred)
   - Click "Review + Create"
   - Click "Create"

5. **Configure Application Settings**

   - Go to your Web App
   - Navigate to: Configuration → Application settings
   - Add new settings:
     - `GEMINI_API_KEY`: Your API key
     - `WEBSITES_PORT`: 8080
     - `SCM_DO_BUILD_DURING_DEPLOYMENT`: true
   - Click "Save"

6. **Configure Startup Command**

   - Navigate to: Configuration → General settings
   - Startup Command: `python main.py`
   - Click "Save"

7. **Deploy Code**

   **Option A: Using Git**

   ```powershell
   # Get deployment credentials from Azure Portal
   # Settings → Deployment Center → Local Git/FTPS credentials

   # Add Azure remote
   git remote add azure <git-clone-url>

   # Push to Azure
   git push azure main
   ```

   **Option B: Using ZIP Deploy**

   ```powershell
   # Create deployment package
   Compress-Archive -Path * -DestinationPath deploy.zip

   # Deploy using Azure CLI
   az webapp deployment source config-zip `
     --resource-group legal-demystifier-rg `
     --name legal-demystifier-app `
     --src deploy.zip
   ```

   **Option C: Using VS Code**

   - Install "Azure App Service" extension
   - Right-click on your Web App
   - Select "Deploy to Web App"
   - Select project folder

---

### Method 4: Docker Container Deployment

Deploy using the pre-configured Docker container.

#### Steps:

1. **Build Docker Image**

```powershell
# Build frontend first
npm install
npm run client:build

# Build Docker image
docker build -t legal-demystifier:latest .
```

2. **Push to Azure Container Registry**

```powershell
# Create container registry
az acr create `
  --resource-group legal-demystifier-rg `
  --name legaldemystifieracr `
  --sku Basic

# Login to registry
az acr login --name legaldemystifieracr

# Tag image
docker tag legal-demystifier:latest legaldemystifieracr.azurecr.io/legal-demystifier:latest

# Push image
docker push legaldemystifieracr.azurecr.io/legal-demystifier:latest
```

3. **Create Web App from Container**

```powershell
az webapp create `
  --resource-group legal-demystifier-rg `
  --plan legal-demystifier-plan `
  --name legal-demystifier-app `
  --deployment-container-image-name legaldemystifieracr.azurecr.io/legal-demystifier:latest
```

4. **Configure Settings**

```powershell
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --settings GEMINI_API_KEY="YOUR_API_KEY" WEBSITES_PORT=8080
```

---

## 🔧 Post-Deployment Configuration

### 1. Verify Deployment

```powershell
# Check deployment status
az webapp show --resource-group legal-demystifier-rg --name legal-demystifier-app --query state

# View logs
az webapp log tail --resource-group legal-demystifier-rg --name legal-demystifier-app
```

### 2. Test Application

Visit: `https://legal-demystifier-app.azurewebsites.net`

Test endpoints:

- Health check: `/health`
- Homepage: `/`
- Upload document and test analysis

### 3. Enable Application Insights (Monitoring)

```powershell
# Create Application Insights
az monitor app-insights component create `
  --app legal-demystifier-insights `
  --location "East US" `
  --resource-group legal-demystifier-rg

# Get instrumentation key
$insightsKey = az monitor app-insights component show `
  --app legal-demystifier-insights `
  --resource-group legal-demystifier-rg `
  --query instrumentationKey -o tsv

# Configure Web App to use Application Insights
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$insightsKey
```

### 4. Configure Custom Domain (Optional)

```powershell
# Add custom domain
az webapp config hostname add `
  --webapp-name legal-demystifier-app `
  --resource-group legal-demystifier-rg `
  --hostname www.yourdomain.com
```

### 5. Enable HTTPS (SSL)

```powershell
# Azure provides free SSL certificate
az webapp config ssl bind `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --certificate-thumbprint <thumbprint> `
  --ssl-type SNI
```

### 6. Configure Scaling (Auto-scale)

```powershell
# Create auto-scale rule
az monitor autoscale create `
  --resource-group legal-demystifier-rg `
  --resource legal-demystifier-plan `
  --resource-type Microsoft.Web/serverFarms `
  --name autoscale-legal-demystifier `
  --min-count 1 `
  --max-count 10 `
  --count 1

# Add scale-out rule (CPU > 70%)
az monitor autoscale rule create `
  --resource-group legal-demystifier-rg `
  --autoscale-name autoscale-legal-demystifier `
  --condition "CpuPercentage > 70 avg 5m" `
  --scale out 1
```

---

## 📊 Monitoring & Troubleshooting

### View Live Logs

```powershell
# Stream logs in real-time
az webapp log tail --resource-group legal-demystifier-rg --name legal-demystifier-app

# Download logs
az webapp log download --resource-group legal-demystifier-rg --name legal-demystifier-app
```

### Common Issues

#### 1. Application Won't Start

**Check:**

- Startup command is set: `python main.py`
- `WEBSITES_PORT=8080` is configured
- Python runtime is 3.11
- Dependencies are installed

**Solution:**

```powershell
az webapp config set --resource-group legal-demystifier-rg --name legal-demystifier-app --startup-file "python main.py"
az webapp config appsettings set --resource-group legal-demystifier-rg --name legal-demystifier-app --settings WEBSITES_PORT=8080
```

#### 2. Frontend Not Loading

**Check:**

- Frontend is built: `client/dist` folder exists
- Static files are included in deployment

**Solution:**

```powershell
# Rebuild frontend locally
npm run client:build

# Redeploy
az webapp up --resource-group legal-demystifier-rg --name legal-demystifier-app
```

#### 3. API Key Not Working

**Check:**

- `GEMINI_API_KEY` is set in Application Settings
- API key is valid (test at https://aistudio.google.com/)

**Solution:**

```powershell
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --settings GEMINI_API_KEY="YOUR_VALID_API_KEY"
```

#### 4. Out of Memory

**Solution:** Upgrade to higher tier

```powershell
az appservice plan update --name legal-demystifier-plan --resource-group legal-demystifier-rg --sku S1
```

### Useful Commands

```powershell
# Restart app
az webapp restart --resource-group legal-demystifier-rg --name legal-demystifier-app

# View configuration
az webapp config appsettings list --resource-group legal-demystifier-rg --name legal-demystifier-app

# SSH into container
az webapp ssh --resource-group legal-demystifier-rg --name legal-demystifier-app

# View deployment history
az webapp deployment list-publishing-profiles --resource-group legal-demystifier-rg --name legal-demystifier-app
```

---

## 💰 Cost Estimation

### Free Tier (F1)

- **Cost**: Free
- **Limitations**: 60 min/day CPU time, 1GB RAM, shared infrastructure
- **Best for**: Testing, demos

### Basic Tier (B1)

- **Cost**: ~$13/month
- **Resources**: 1 core, 1.75GB RAM, 10GB storage
- **Best for**: Small production apps, low traffic

### Standard Tier (S1)

- **Cost**: ~$70/month
- **Resources**: 1 core, 1.75GB RAM, 50GB storage, auto-scaling
- **Best for**: Production apps, medium traffic

### Premium Tier (P1V2)

- **Cost**: ~$80/month
- **Resources**: 1 core, 3.5GB RAM, 250GB storage, advanced features
- **Best for**: High-performance production apps

**Additional Costs:**

- Application Insights: Free tier (5GB/month)
- Custom domain: Free (if you own domain)
- SSL certificate: Free (Azure-managed)
- Storage: ~$0.03/GB/month
- Bandwidth: Free (first 5GB)

---

## 🔄 Continuous Deployment (CI/CD)

### Option 1: GitHub Actions

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: "20"

      - name: Build frontend
        run: |
          npm install
          npm run client:build

      - name: Deploy to Azure
        uses: azure/webapps-deploy@v2
        with:
          app-name: "legal-demystifier-app"
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

### Option 2: Azure DevOps

The `azure-pipelines.yml` file is already configured in your project. Set up in Azure DevOps:

1. Create Azure DevOps project
2. Connect to your GitHub repository
3. Create new pipeline from `azure-pipelines.yml`
4. Configure service connection
5. Run pipeline

---

## 🛡️ Security Best Practices

### 1. Secure API Key

```powershell
# Store API key in Azure Key Vault
az keyvault create --name legal-demystifier-kv --resource-group legal-demystifier-rg --location "East US"
az keyvault secret set --vault-name legal-demystifier-kv --name GeminiApiKey --value "YOUR_API_KEY"

# Configure Web App to use Key Vault
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --settings GEMINI_API_KEY="@Microsoft.KeyVault(SecretUri=https://legal-demystifier-kv.vault.azure.net/secrets/GeminiApiKey/)"
```

### 2. Enable HTTPS Only

```powershell
az webapp update --resource-group legal-demystifier-rg --name legal-demystifier-app --https-only true
```

### 3. Configure IP Restrictions

```powershell
az webapp config access-restriction add `
  --resource-group legal-demystifier-rg `
  --name legal-demystifier-app `
  --rule-name "AllowOffice" `
  --action Allow `
  --ip-address 203.0.113.0/24 `
  --priority 100
```

---

## 📚 Additional Resources

- **Azure Documentation**: https://docs.microsoft.com/azure/app-service/
- **Azure CLI Reference**: https://docs.microsoft.com/cli/azure/
- **Python on Azure**: https://docs.microsoft.com/azure/app-service/quickstart-python
- **Azure Pricing Calculator**: https://azure.microsoft.com/pricing/calculator/
- **Support**: https://azure.microsoft.com/support/

---

## 🎉 Quick Start Summary

```powershell
# 1. Login to Azure
az login

# 2. Run deployment script
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "legal-demystifier-app"

# 3. Access your app
# https://legal-demystifier-app.azurewebsites.net
```

**That's it! Your application is now live on Azure! 🚀**

---

## Need Help?

- Check logs: `az webapp log tail --resource-group legal-demystifier-rg --name legal-demystifier-app`
- Restart app: `az webapp restart --resource-group legal-demystifier-rg --name legal-demystifier-app`
- Azure Support: https://portal.azure.com → Help + support
