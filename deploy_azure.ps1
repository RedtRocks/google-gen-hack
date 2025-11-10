# Azure Deployment Script for PowerShell
# This script automates the deployment process to Azure App Service

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$AppName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "East US",
    
    [Parameter(Mandatory=$false)]
    [string]$Sku = "B1"
)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Azure Deployment Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
Write-Host "Checking Azure CLI installation..." -ForegroundColor Yellow
try {
    az --version | Out-Null
    Write-Host "✓ Azure CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Azure CLI is not installed" -ForegroundColor Red
    Write-Host "Please install from: https://aka.ms/installazurecliwindows" -ForegroundColor Red
    exit 1
}

# Login to Azure
Write-Host ""
Write-Host "Logging into Azure..." -ForegroundColor Yellow
az login

# Create Resource Group
Write-Host ""
Write-Host "Creating resource group '$ResourceGroup'..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Resource group created" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create resource group" -ForegroundColor Red
    exit 1
}

# Create App Service Plan
Write-Host ""
Write-Host "Creating App Service Plan..." -ForegroundColor Yellow
$PlanName = "$AppName-plan"
az appservice plan create --name $PlanName --resource-group $ResourceGroup --sku $Sku --is-linux
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ App Service Plan created" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create App Service Plan" -ForegroundColor Red
    exit 1
}

# Create Web App
Write-Host ""
Write-Host "Creating Web App '$AppName'..." -ForegroundColor Yellow
az webapp create --resource-group $ResourceGroup --plan $PlanName --name $AppName --runtime "PYTHON:3.11"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Web App created" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create Web App" -ForegroundColor Red
    exit 1
}

# Configure Web App Settings
Write-Host ""
Write-Host "Configuring Web App settings..." -ForegroundColor Yellow
az webapp config set --resource-group $ResourceGroup --name $AppName --startup-file "python main.py"
az webapp config appsettings set --resource-group $ResourceGroup --name $AppName --settings WEBSITES_PORT=8080 SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Get GEMINI_API_KEY from .env file
$envFile = ".env"
if (Test-Path $envFile) {
    $geminiKey = Select-String -Path $envFile -Pattern "GEMINI_API_KEY=(.+)" | ForEach-Object { $_.Matches.Groups[1].Value }
    if ($geminiKey) {
        Write-Host "Setting GEMINI_API_KEY from .env file..." -ForegroundColor Yellow
        az webapp config appsettings set --resource-group $ResourceGroup --name $AppName --settings GEMINI_API_KEY=$geminiKey
        Write-Host "✓ API key configured" -ForegroundColor Green
    }
}

# Build frontend
Write-Host ""
Write-Host "Building frontend..." -ForegroundColor Yellow
if (Test-Path "node_modules") {
    npm run client:build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Frontend built successfully" -ForegroundColor Green
    } else {
        Write-Host "⚠ Frontend build failed, continuing anyway..." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠ node_modules not found. Run 'npm install' first or deploy without frontend build" -ForegroundColor Yellow
}

# Deploy the application
Write-Host ""
Write-Host "Deploying application to Azure..." -ForegroundColor Yellow
az webapp up --resource-group $ResourceGroup --name $AppName --runtime "PYTHON:3.11"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Application deployed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Deployment failed" -ForegroundColor Red
    exit 1
}

# Get the app URL
$appUrl = "https://$AppName.azurewebsites.net"

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your application is available at:" -ForegroundColor Yellow
Write-Host $appUrl -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Visit $appUrl to access your application" -ForegroundColor White
Write-Host "2. Configure custom domain (optional)" -ForegroundColor White
Write-Host "3. Enable Application Insights for monitoring" -ForegroundColor White
Write-Host "4. Set up deployment slots for staging" -ForegroundColor White
Write-Host ""
