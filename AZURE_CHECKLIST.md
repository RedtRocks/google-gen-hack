# Azure Pre-Deployment Checklist

Use this checklist before deploying to Azure to ensure everything is configured correctly.

---

## ✅ Pre-Deployment Checklist

### 1. Prerequisites Installed
- [ ] Azure CLI installed and working (`az --version`)
- [ ] Azure account created (https://azure.microsoft.com/free/)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.11+ installed (`python --version`)
- [ ] Git installed (optional, for Git deployment)

### 2. API Keys & Configuration
- [ ] Gemini API key obtained from https://aistudio.google.com/app/apikey
- [ ] API key tested locally (run `python test_api_key.py`)
- [ ] `.env` file contains valid `GEMINI_API_KEY`

### 3. Application Build
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Frontend built successfully (`npm run client:build`)
- [ ] `client/dist` folder exists and contains built files
- [ ] Python dependencies listed in `requirements.txt`

### 4. Local Testing
- [ ] Application runs locally (`python main.py`)
- [ ] Can access http://localhost:8080
- [ ] Document upload works
- [ ] Document analysis works
- [ ] Question answering works
- [ ] No errors in console/logs

### 5. Azure Configuration
- [ ] Chosen unique app name (e.g., `legal-demystifier-app-yourname`)
- [ ] Decided on Azure region (e.g., "East US", "West Europe")
- [ ] Decided on pricing tier (B1 recommended for start)
- [ ] Resource group name chosen (e.g., `legal-demystifier-rg`)

### 6. Deployment Files Ready
- [ ] `azure-webapp.yaml` - Configuration reference
- [ ] `azure-pipelines.yml` - CI/CD pipeline (optional)
- [ ] `deploy_azure.ps1` - Automated deployment script
- [ ] `startup.sh` - Azure startup script
- [ ] `.deployment` - Azure build configuration
- [ ] `Dockerfile` - Container deployment (optional)
- [ ] `requirements.txt` - Python dependencies
- [ ] `main.py` - Application entry point

### 7. Security Review
- [ ] No API keys hardcoded in source files
- [ ] `.env` file in `.gitignore`
- [ ] Sensitive data not committed to Git
- [ ] CORS configuration reviewed in `main.py`

### 8. Git Repository (if using Git deployment)
- [ ] All changes committed
- [ ] Latest code pushed to GitHub/Azure DevOps
- [ ] Branch strategy defined (main/master)

---

## 🚀 Quick Deployment Steps

Once all checklist items are complete, deploy using:

### Method 1: Automated Script (Easiest)
```powershell
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "your-unique-app-name" -Location "East US" -Sku "B1"
```

### Method 2: Manual Azure CLI
```powershell
# Build frontend
npm run client:build

# Deploy to Azure
az webapp up --resource-group legal-demystifier-rg --name your-unique-app-name --runtime "PYTHON:3.11"

# Set API key
az webapp config appsettings set --resource-group legal-demystifier-rg --name your-unique-app-name --settings GEMINI_API_KEY="YOUR_KEY"
```

---

## 🔍 Post-Deployment Verification

After deployment, verify:

- [ ] App URL accessible (https://your-app-name.azurewebsites.net)
- [ ] Health endpoint works (https://your-app-name.azurewebsites.net/health)
- [ ] Homepage loads correctly
- [ ] Can upload and analyze documents
- [ ] Can ask questions about documents
- [ ] No errors in Azure logs (`az webapp log tail`)

---

## 📝 Configuration Checklist

### Azure App Settings (verify in portal or CLI)
- [ ] `GEMINI_API_KEY` - Your API key
- [ ] `WEBSITES_PORT` - Set to 8080
- [ ] `SCM_DO_BUILD_DURING_DEPLOYMENT` - Set to true
- [ ] `PORT` - Set to 8080 (optional, defaults to 8080)

### Azure App Configuration
- [ ] Startup command: `python main.py`
- [ ] Runtime: Python 3.11
- [ ] Operating system: Linux
- [ ] Always On: Enabled (recommended for B1+)

---

## 🛠️ Troubleshooting Quick Reference

### App won't start
```powershell
# Check logs
az webapp log tail --resource-group legal-demystifier-rg --name your-app-name

# Verify startup command
az webapp config show --resource-group legal-demystifier-rg --name your-app-name --query linuxFxVersion

# Restart app
az webapp restart --resource-group legal-demystifier-rg --name your-app-name
```

### Frontend not loading
```powershell
# Rebuild frontend locally
npm run client:build

# Verify dist folder exists
dir client\dist

# Redeploy
az webapp up --resource-group legal-demystifier-rg --name your-app-name
```

### API errors
```powershell
# Verify API key is set
az webapp config appsettings list --resource-group legal-demystifier-rg --name your-app-name --query "[?name=='GEMINI_API_KEY']"

# Update API key
az webapp config appsettings set --resource-group legal-demystifier-rg --name your-app-name --settings GEMINI_API_KEY="NEW_KEY"
```

---

## 📞 Need Help?

- **Full Guide**: See `AZURE_DEPLOYMENT_GUIDE.md`
- **Azure Docs**: https://docs.microsoft.com/azure/app-service/
- **View Logs**: Azure Portal → Your App → Log stream
- **Support**: https://portal.azure.com → Help + support

---

## 🎯 Ready to Deploy?

If all checklist items are ✅, you're ready to deploy!

Run: `.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "your-unique-app-name"`

Good luck! 🚀
