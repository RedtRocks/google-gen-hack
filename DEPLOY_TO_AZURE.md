# 🚀 Azure Deployment - Complete Guide

## What Has Been Configured

Your project has been fully configured for Azure deployment with:

### ✅ Configuration Files Created

1. **`azure-webapp.yaml`** - Azure configuration reference
2. **`.deployment`** - Azure build settings
3. **`startup.sh`** - Application startup script
4. **`azure-pipelines.yml`** - CI/CD pipeline (optional)
5. **`deploy_azure.ps1`** - **Automated deployment script** ⭐
6. **`.dockerignore`** - Updated for Azure

### ✅ Documentation Created

1. **`AZURE_DEPLOYMENT_GUIDE.md`** - Full deployment guide (40+ pages)
2. **`AZURE_CHECKLIST.md`** - Pre-deployment checklist
3. **`AZURE_QUICK_REFERENCE.md`** - Quick command reference
4. **`AZURE_CONFIGURATION_SUMMARY.md`** - Configuration overview

### ✅ Updated Files

- **`README.md`** - Added Azure deployment section

---

## 🎯 Deploy to Azure in 3 Steps

### Step 1: Install Azure CLI

Download and install from: https://aka.ms/installazurecliwindows

Verify installation:

```powershell
az --version
```

### Step 2: Build Frontend

```powershell
npm install
npm run client:build
```

### Step 3: Deploy!

```powershell
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "your-unique-app-name"
```

**That's it!** The script will:

- Login to Azure
- Create all resources
- Configure settings
- Deploy your application
- Display your app URL

---

## 📋 Prerequisites Checklist

Before deploying, ensure you have:

- [ ] **Azure account** (sign up at https://azure.microsoft.com/free/)
- [ ] **Azure CLI installed** (https://aka.ms/installazurecliwindows)
- [ ] **Node.js 18+** installed
- [ ] **Python 3.11+** installed
- [ ] **Gemini API key** (get from https://aistudio.google.com/app/apikey)
- [ ] **Frontend built** (`npm run client:build`)
- [ ] **Unique app name** chosen (e.g., "legal-demystifier-yourname")

---

## 💡 Deployment Script Parameters

```powershell
.\deploy_azure.ps1 `
  -ResourceGroup "legal-demystifier-rg" `      # Resource group name
  -AppName "your-unique-app-name" `            # Your app name (globally unique)
  -Location "East US" `                        # Azure region (optional)
  -Sku "B1"                                    # Pricing tier (optional)
```

### Common Azure Regions

- `"East US"` - Virginia, USA
- `"West Europe"` - Netherlands
- `"Southeast Asia"` - Singapore
- `"Australia East"` - New South Wales

### Pricing Tiers

- `"F1"` - Free (limited, testing only)
- `"B1"` - Basic ~$13/month ⭐ **Recommended**
- `"S1"` - Standard ~$70/month (includes auto-scaling)
- `"P1V2"` - Premium ~$80/month (high performance)

---

## 🔧 What Happens During Deployment

1. **Checks & Login**

   - Verifies Azure CLI is installed
   - Logs you into Azure

2. **Creates Resources**

   - Resource Group (container for all resources)
   - App Service Plan (hosting plan)
   - Web App (your application)

3. **Configures App**

   - Sets Python 3.11 runtime
   - Configures port 8080
   - Sets GEMINI_API_KEY from .env
   - Enables build on deployment

4. **Builds Frontend**

   - Runs `npm run client:build` if node_modules exists
   - Creates production-ready React app

5. **Deploys Application**

   - Uploads your code to Azure
   - Installs Python dependencies
   - Starts the application

6. **Shows Result**
   - Displays your app URL
   - Provides next steps

---

## 🌐 After Deployment

Your app will be available at:

```
https://your-app-name.azurewebsites.net
```

### Test Your Deployment

1. **Visit your app URL**

   - Should load the homepage

2. **Check health endpoint**

   ```powershell
   curl https://your-app-name.azurewebsites.net/health
   ```

3. **Test document analysis**

   - Upload a PDF or paste text
   - Verify analysis works
   - Ask follow-up questions

4. **Check logs**
   ```powershell
   az webapp log tail --resource-group legal-demystifier-rg --name your-app-name
   ```

---

## 🛠️ Common Commands

### View Logs

```powershell
# Stream live logs
az webapp log tail --resource-group legal-demystifier-rg --name your-app-name

# Download logs
az webapp log download --resource-group legal-demystifier-rg --name your-app-name
```

### Restart Application

```powershell
az webapp restart --resource-group legal-demystifier-rg --name your-app-name
```

### Update API Key

```powershell
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name your-app-name `
  --settings GEMINI_API_KEY="new-api-key"
```

### Redeploy After Changes

```powershell
# Rebuild frontend (if changed)
npm run client:build

# Redeploy
az webapp up --resource-group legal-demystifier-rg --name your-app-name
```

### Check App Status

```powershell
az webapp show --resource-group legal-demystifier-rg --name your-app-name --query state
```

---

## 🐛 Troubleshooting

### Problem: App Won't Start

**Solution 1: Check Logs**

```powershell
az webapp log tail --resource-group legal-demystifier-rg --name your-app-name
```

**Solution 2: Verify Settings**

```powershell
# Check startup command
az webapp config show --resource-group legal-demystifier-rg --name your-app-name

# Verify API key is set
az webapp config appsettings list --resource-group legal-demystifier-rg --name your-app-name
```

**Solution 3: Restart**

```powershell
az webapp restart --resource-group legal-demystifier-rg --name your-app-name
```

### Problem: Frontend Not Loading

**Solution:**

```powershell
# Rebuild frontend locally
npm run client:build

# Verify dist folder exists
dir client\dist

# Redeploy
az webapp up --resource-group legal-demystifier-rg --name your-app-name
```

### Problem: API Key Not Working

**Solution:**

```powershell
# Update API key
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name your-app-name `
  --settings GEMINI_API_KEY="your-valid-api-key"

# Restart app
az webapp restart --resource-group legal-demystifier-rg --name your-app-name
```

### Problem: Out of Memory

**Solution: Upgrade Tier**

```powershell
az appservice plan update `
  --name legal-demystifier-plan `
  --resource-group legal-demystifier-rg `
  --sku S1
```

---

## 📊 Monitoring Your App

### Enable Application Insights (Free)

```powershell
# Create Application Insights
az monitor app-insights component create `
  --app legal-demystifier-insights `
  --location "East US" `
  --resource-group legal-demystifier-rg

# Get instrumentation key
$key = az monitor app-insights component show `
  --app legal-demystifier-insights `
  --resource-group legal-demystifier-rg `
  --query instrumentationKey -o tsv

# Configure app to use it
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name your-app-name `
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$key
```

### View Metrics in Azure Portal

1. Go to https://portal.azure.com
2. Navigate to your Web App
3. Click "Monitoring" → "Metrics"
4. View CPU, Memory, Requests, Response Time

---

## 💰 Cost Management

### Free Tier (F1)

- **Cost:** $0
- **Use:** Testing only (60 minutes CPU/day)

### Basic Tier (B1) - Recommended

- **Cost:** ~$13/month
- **Resources:** 1 core, 1.75GB RAM, 10GB storage
- **Use:** Small production apps

### Reduce Costs

```powershell
# Stop app when not in use (doesn't delete data)
az webapp stop --resource-group legal-demystifier-rg --name your-app-name

# Start app when needed
az webapp start --resource-group legal-demystifier-rg --name your-app-name
```

### Delete Resources (Cleanup)

```powershell
# Delete entire resource group (removes everything)
az group delete --name legal-demystifier-rg --yes
```

---

## 🔒 Security Best Practices

### 1. Use Azure Key Vault for API Keys

```powershell
# Create Key Vault
az keyvault create --name legal-demystifier-kv --resource-group legal-demystifier-rg --location "East US"

# Store API key
az keyvault secret set --vault-name legal-demystifier-kv --name GeminiApiKey --value "your-api-key"

# Configure app to use it
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name your-app-name `
  --settings GEMINI_API_KEY="@Microsoft.KeyVault(SecretUri=https://legal-demystifier-kv.vault.azure.net/secrets/GeminiApiKey/)"
```

### 2. Enable HTTPS Only

```powershell
az webapp update --resource-group legal-demystifier-rg --name your-app-name --https-only true
```

### 3. Configure Custom Domain (Optional)

```powershell
az webapp config hostname add `
  --webapp-name your-app-name `
  --resource-group legal-demystifier-rg `
  --hostname www.yourdomain.com
```

---

## 📚 Documentation Reference

| Document                           | Purpose                  | When to Use                        |
| ---------------------------------- | ------------------------ | ---------------------------------- |
| **AZURE_DEPLOYMENT_GUIDE.md**      | Complete guide           | Detailed instructions, all methods |
| **AZURE_CHECKLIST.md**             | Pre-deployment checklist | Before deploying                   |
| **AZURE_QUICK_REFERENCE.md**       | Quick commands           | Daily operations                   |
| **AZURE_CONFIGURATION_SUMMARY.md** | Configuration overview   | Understanding setup                |
| **THIS FILE**                      | Quick start guide        | First deployment                   |

---

## 🎓 Next Steps After Deployment

1. **Test Thoroughly**

   - Upload various document types
   - Test all features
   - Check error handling

2. **Configure Monitoring**

   - Enable Application Insights
   - Set up alerts for errors
   - Monitor performance

3. **Set Up CI/CD (Optional)**

   - Configure GitHub Actions or Azure DevOps
   - Automate deployments
   - See `azure-pipelines.yml`

4. **Configure Custom Domain (Optional)**

   - Purchase domain
   - Configure DNS
   - Enable SSL

5. **Optimize Performance**
   - Review pricing tier
   - Configure auto-scaling
   - Enable caching

---

## 🆘 Getting Help

### Documentation

- **Azure Docs:** https://docs.microsoft.com/azure/app-service/
- **Azure CLI Docs:** https://docs.microsoft.com/cli/azure/
- **Python on Azure:** https://docs.microsoft.com/azure/app-service/quickstart-python

### Tools

- **Azure Portal:** https://portal.azure.com
- **Pricing Calculator:** https://azure.microsoft.com/pricing/calculator/
- **Status:** https://status.azure.com/

### Support

- **Azure Support:** https://portal.azure.com → Help + support
- **Community:** https://docs.microsoft.com/answers/
- **Stack Overflow:** Tag `azure-app-service`

---

## ✅ Summary

You now have everything you need to deploy to Azure:

✅ **Automated deployment script** (`deploy_azure.ps1`)  
✅ **Comprehensive documentation** (4 detailed guides)  
✅ **Configuration files** (ready to use)  
✅ **Troubleshooting guides** (common issues covered)  
✅ **Cost estimates** (know what you'll pay)  
✅ **Security best practices** (keep it safe)

---

## 🚀 Ready to Deploy?

Run this command to get started:

```powershell
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "your-unique-app-name"
```

**Good luck with your deployment! 🎉**

---

## 📞 Quick Support

- **Can't install Azure CLI?** → https://aka.ms/installazurecliwindows
- **Need API key?** → https://aistudio.google.com/app/apikey
- **App not working?** → Check logs: `az webapp log tail --resource-group legal-demystifier-rg --name your-app-name`
- **Want to delete everything?** → `az group delete --name legal-demystifier-rg --yes`

---

**Remember:** Your app name must be globally unique!

Try: `legal-demystifier-yourname` or `legal-doc-analyzer-yourcompany`
