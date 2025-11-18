# Diagnostic Script for Azure Storage Integration
# Run this to check why storage isn't working in your Azure deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$AppName,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup
)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Azure Storage Diagnostic Tool" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# If not provided, try to detect from recent deployments
if (-not $AppName) {
    Write-Host "Please provide your Azure Web App name:" -ForegroundColor Yellow
    $AppName = Read-Host "App Name"
}

if (-not $ResourceGroup) {
    Write-Host "Please provide your Resource Group name:" -ForegroundColor Yellow
    $ResourceGroup = Read-Host "Resource Group"
}

Write-Host ""
Write-Host "Checking app: $AppName in resource group: $ResourceGroup" -ForegroundColor Cyan
Write-Host ""

# Check 1: Verify app exists
Write-Host "[1/6] Checking if app exists..." -ForegroundColor Yellow
try {
    $appExists = az webapp show --name $AppName --resource-group $ResourceGroup 2>$null
    if ($appExists) {
        Write-Host "✓ App exists" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ App not found. Please check the name and resource group." -ForegroundColor Red
    exit 1
}

# Check 2: Get current app settings
Write-Host ""
Write-Host "[2/6] Checking current app settings..." -ForegroundColor Yellow
$settings = az webapp config appsettings list --name $AppName --resource-group $ResourceGroup | ConvertFrom-Json

$hasGeminiKey = $settings | Where-Object { $_.name -eq "GEMINI_API_KEY" }
$hasStorageConnection = $settings | Where-Object { $_.name -eq "AZURE_STORAGE_CONNECTION_STRING" }
$hasContainerName = $settings | Where-Object { $_.name -eq "AZURE_STORAGE_CONTAINER_NAME" }

Write-Host "  GEMINI_API_KEY: $(if ($hasGeminiKey) { '✓ Set' } else { '✗ Missing' })" -ForegroundColor $(if ($hasGeminiKey) { 'Green' } else { 'Red' })
Write-Host "  AZURE_STORAGE_CONNECTION_STRING: $(if ($hasStorageConnection) { '✓ Set' } else { '✗ Missing' })" -ForegroundColor $(if ($hasStorageConnection) { 'Green' } else { 'Red' })
Write-Host "  AZURE_STORAGE_CONTAINER_NAME: $(if ($hasContainerName) { '✓ Set' } else { '⚠ Using default (documents)' })" -ForegroundColor $(if ($hasContainerName) { 'Green' } else { 'Yellow' })

# Check 3: Test storage endpoint
Write-Host ""
Write-Host "[3/6] Testing storage status endpoint..." -ForegroundColor Yellow
$appUrl = "https://$AppName.azurewebsites.net"
try {
    $response = Invoke-RestMethod -Uri "$appUrl/storage/status" -Method Get
    Write-Host "  Storage Status: $($response.enabled)" -ForegroundColor $(if ($response.enabled) { 'Green' } else { 'Red' })
    Write-Host "  Container: $($response.container_name)" -ForegroundColor Cyan
    Write-Host "  Message: $($response.message)" -ForegroundColor White
} catch {
    Write-Host "✗ Could not reach storage status endpoint" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Check 4: Verify storage_service.py is deployed
Write-Host ""
Write-Host "[4/6] Checking if storage_service.py is deployed..." -ForegroundColor Yellow
if (Test-Path "storage_service.py") {
    Write-Host "✓ storage_service.py exists locally" -ForegroundColor Green
    
    # Check if it's in the Docker image
    if (Test-Path "Dockerfile") {
        $dockerContent = Get-Content "Dockerfile" -Raw
        if ($dockerContent -match "storage_service.py") {
            Write-Host "✓ storage_service.py is included in Dockerfile" -ForegroundColor Green
        } else {
            Write-Host "✗ storage_service.py NOT included in Dockerfile" -ForegroundColor Red
            Write-Host "  Add this line to Dockerfile: COPY storage_service.py ./" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "✗ storage_service.py not found locally" -ForegroundColor Red
}

# Check 5: Verify requirements.txt has azure-storage-blob
Write-Host ""
Write-Host "[5/6] Checking requirements.txt..." -ForegroundColor Yellow
$requirements = Get-Content "requirements.txt" -Raw
if ($requirements -match "azure-storage-blob") {
    Write-Host "✓ azure-storage-blob is in requirements.txt" -ForegroundColor Green
} else {
    Write-Host "✗ azure-storage-blob NOT in requirements.txt" -ForegroundColor Red
    Write-Host "  Add this line: azure-storage-blob==12.19.0" -ForegroundColor Yellow
}

# Check 6: Check app logs for errors
Write-Host ""
Write-Host "[6/6] Checking recent application logs..." -ForegroundColor Yellow
Write-Host "  (Looking for storage-related messages...)" -ForegroundColor Gray
$logs = az webapp log tail --name $AppName --resource-group $ResourceGroup --only-show-errors 2>&1 | Select-Object -First 20
if ($logs -match "storage|AZURE_STORAGE") {
    Write-Host "  Found storage-related log entries:" -ForegroundColor Yellow
    $logs | Select-String "storage|AZURE_STORAGE" | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
} else {
    Write-Host "  No storage-related errors in recent logs" -ForegroundColor Green
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Diagnosis Complete" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Provide recommendations
Write-Host "Recommendations:" -ForegroundColor Yellow
Write-Host ""

if (-not $hasStorageConnection) {
    Write-Host "⚠ ACTION REQUIRED: Azure Storage is NOT configured" -ForegroundColor Red
    Write-Host ""
    Write-Host "To fix this, you need to:" -ForegroundColor Yellow
    Write-Host "1. Create an Azure Storage Account:" -ForegroundColor White
    Write-Host "   az storage account create --name yourstorageaccount --resource-group $ResourceGroup --location eastus --sku Standard_LRS" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Get the connection string:" -ForegroundColor White
    Write-Host "   `$connString = az storage account show-connection-string --name yourstorageaccount --resource-group $ResourceGroup --query connectionString --output tsv" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Add it to your web app:" -ForegroundColor White
    Write-Host "   az webapp config appsettings set --name $AppName --resource-group $ResourceGroup --settings AZURE_STORAGE_CONNECTION_STRING=`"`$connString`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Restart your app:" -ForegroundColor White
    Write-Host "   az webapp restart --name $AppName --resource-group $ResourceGroup" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "✓ Storage connection string is configured" -ForegroundColor Green
    Write-Host ""
    Write-Host "If storage still isn't working, try:" -ForegroundColor Yellow
    Write-Host "1. Restart the app:" -ForegroundColor White
    Write-Host "   az webapp restart --name $AppName --resource-group $ResourceGroup" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Check if the container exists:" -ForegroundColor White
    Write-Host "   az storage container exists --name documents --account-name yourstorageaccount" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. View detailed logs:" -ForegroundColor White
    Write-Host "   az webapp log tail --name $AppName --resource-group $ResourceGroup" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Need more help? Check AZURE_STORAGE_SETUP.md for detailed instructions." -ForegroundColor Cyan
Write-Host ""
