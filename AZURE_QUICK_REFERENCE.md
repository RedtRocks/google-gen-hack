# Azure Deployment - Quick Reference

One-page quick reference for deploying to Azure.

---

## 🚀 Quick Deploy (3 Commands)

```powershell
# 1. Build frontend
npm run client:build

# 2. Login to Azure
az login

# 3. Deploy
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "your-app-name"
```

---

## 📋 Essential Information

### Your App Details
- **App Name**: Choose a unique name (e.g., `legal-demystifier-yourname`)
- **URL**: `https://YOUR-APP-NAME.azurewebsites.net`
- **Resource Group**: `legal-demystifier-rg` (or your choice)
- **Runtime**: Python 3.11
- **Region**: East US (or your choice)

### Required Settings
```powershell
GEMINI_API_KEY=your_api_key_here
WEBSITES_PORT=8080
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

---

## 🔧 Essential Commands

### Deploy
```powershell
# Automated deployment
.\deploy_azure.ps1 -ResourceGroup "legal-demystifier-rg" -AppName "your-app-name"

# Manual deployment
az webapp up --resource-group legal-demystifier-rg --name your-app-name --runtime "PYTHON:3.11"
```

### Configure API Key
```powershell
az webapp config appsettings set `
  --resource-group legal-demystifier-rg `
  --name your-app-name `
  --settings GEMINI_API_KEY="YOUR_API_KEY"
```

### View Logs
```powershell
# Stream live logs
az webapp log tail --resource-group legal-demystifier-rg --name your-app-name

# Download logs
az webapp log download --resource-group legal-demystifier-rg --name your-app-name
```

### Restart App
```powershell
az webapp restart --resource-group legal-demystifier-rg --name your-app-name
```

### Check Status
```powershell
az webapp show --resource-group legal-demystifier-rg --name your-app-name --query state
```

---

## 🐛 Quick Troubleshooting

### App Won't Start
```powershell
# Check startup command
az webapp config show --resource-group legal-demystifier-rg --name your-app-name

# Set correct startup command
az webapp config set --resource-group legal-demystifier-rg --name your-app-name --startup-file "python main.py"

# Check port settings
az webapp config appsettings set --resource-group legal-demystifier-rg --name your-app-name --settings WEBSITES_PORT=8080
```

### Frontend Not Loading
```powershell
# Rebuild frontend
npm run client:build

# Verify build
dir client\dist

# Redeploy
az webapp up --resource-group legal-demystifier-rg --name your-app-name
```

### API Key Issues
```powershell
# Check if API key is set
az webapp config appsettings list --resource-group legal-demystifier-rg --name your-app-name

# Update API key
az webapp config appsettings set --resource-group legal-demystifier-rg --name your-app-name --settings GEMINI_API_KEY="NEW_KEY"
```

---

## 💰 Pricing Quick Reference

| Tier | Monthly Cost | Resources | Best For |
|------|--------------|-----------|----------|
| F1 (Free) | $0 | 60min/day, 1GB RAM | Testing |
| B1 (Basic) | ~$13 | 1 core, 1.75GB RAM | Small apps |
| S1 (Standard) | ~$70 | 1 core, 1.75GB RAM, auto-scale | Production |
| P1V2 (Premium) | ~$80 | 1 core, 3.5GB RAM | High performance |

---

## 🔗 Important URLs

- **Azure Portal**: https://portal.azure.com/
- **Azure CLI Docs**: https://docs.microsoft.com/cli/azure/
- **Get API Key**: https://aistudio.google.com/app/apikey
- **Azure Pricing**: https://azure.microsoft.com/pricing/calculator/

---

## 📞 Getting Help

- **Full Guide**: See `AZURE_DEPLOYMENT_GUIDE.md`
- **Checklist**: See `AZURE_CHECKLIST.md`
- **View App Logs**: Azure Portal → Your App → Log stream
- **Azure Support**: https://portal.azure.com → Help + support

---

## ✅ Post-Deployment Check

- [ ] Visit `https://your-app-name.azurewebsites.net`
- [ ] Test `/health` endpoint
- [ ] Upload and analyze a document
- [ ] Ask a question about the document
- [ ] Check logs for errors

---

**Need detailed steps?** See `AZURE_DEPLOYMENT_GUIDE.md`

**Ready to deploy?** Run `.\deploy_azure.ps1`
