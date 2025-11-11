# 📦 Azure Blob Storage Integration Guide

This guide shows you how to set up Azure Blob Storage to store all uploaded PDF files separately in the cloud.

---

## 🎯 What This Feature Does

When users upload PDF files to your Legal Document Demystifier app:
- ✅ Files are automatically stored in Azure Blob Storage
- ✅ Each file gets a unique name with timestamp
- ✅ Metadata is stored (filename, upload time, file size, etc.)
- ✅ You can list, download, and manage all uploaded files
- ✅ Files persist even if your app restarts
- ✅ Generates temporary secure download URLs

---

## 🚀 Part 1: Create Azure Storage Account

### Step 1.1: Using Azure CLI (Recommended)

```powershell
# Login to Azure
az login

# Set your subscription
az account set --subscription "Your Subscription Name"

# Create Storage Account
az storage account create `
  --name "legaldemystifierstorage" `
  --resource-group "legal-demystifier-rg" `
  --location "eastus" `
  --sku "Standard_LRS" `
  --kind "StorageV2" `
  --access-tier "Hot"

# Note: Storage account name must be:
# - Globally unique
# - 3-24 characters
# - Only lowercase letters and numbers
# - No special characters
```

### Step 1.2: Create Blob Container

```powershell
# Get storage account connection string
$connectionString = az storage account show-connection-string `
  --name "legaldemystifierstorage" `
  --resource-group "legal-demystifier-rg" `
  --query "connectionString" `
  --output tsv

Write-Host "Connection String: $connectionString"

# Create container for documents
az storage container create `
  --name "documents" `
  --account-name "legaldemystifierstorage" `
  --connection-string $connectionString `
  --public-access "off"

# Verify container was created
az storage container list `
  --account-name "legaldemystifierstorage" `
  --connection-string $connectionString `
  --output table
```

### Step 1.3: Using Azure Portal (Alternative)

1. Go to https://portal.azure.com
2. Click **"Create a resource"**
3. Search for **"Storage account"**
4. Click **"Create"**

**Settings:**
- **Storage account name**: `legaldemystifierstorage`
- **Region**: Same as your web app (e.g., East US)
- **Performance**: Standard
- **Redundancy**: Locally-redundant storage (LRS)

5. Click **"Review + Create"** → **"Create"**

**Create Container:**
1. Go to your storage account
2. Click **"Containers"** in the left menu
3. Click **"+ Container"**
4. Name: `documents`
5. Public access level: **Private**
6. Click **"Create"**

---

## 🔧 Part 2: Configure Your Application

### Step 2.1: Get Storage Connection String

```powershell
# Get connection string
az storage account show-connection-string `
  --name "legaldemystifierstorage" `
  --resource-group "legal-demystifier-rg" `
  --query "connectionString" `
  --output tsv
```

**Or from Azure Portal:**
1. Go to your Storage Account
2. Click **"Access keys"** (under Security + networking)
3. Copy the **Connection string** from key1

### Step 2.2: Update Local .env File (For Testing)

```powershell
# Edit your .env file
notepad .env
```

Add these lines:
```env
# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=legaldemystifierstorage;AccountKey=your-key-here;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=documents
```

Save the file.

### Step 2.3: Install Dependencies Locally

```powershell
# Activate virtual environment
.venv\Scripts\activate

# Install new dependency
pip install azure-storage-blob==12.19.0

# Or install all requirements
pip install -r requirements.txt
```

### Step 2.4: Test Locally

```powershell
# Start your app
python main.py
```

Open http://localhost:8080 and test:
1. Upload a PDF file
2. The file should be stored in Azure Blob Storage
3. Check storage status: http://localhost:8080/storage/status
4. List files: http://localhost:8080/storage/files

---

## ☁️ Part 3: Deploy to Azure

### Step 3.1: Configure Azure Web App Settings

```powershell
# Add storage connection string to your Azure Web App
az webapp config appsettings set `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname" `
  --settings `
    AZURE_STORAGE_CONNECTION_STRING="your-connection-string-here" `
    AZURE_STORAGE_CONTAINER_NAME="documents"
```

**Replace:**
- `legal-demystifier-rg` with your resource group name
- `legal-demystifier-yourname` with your web app name
- `your-connection-string-here` with your actual connection string

**Or using Azure Portal:**
1. Go to your Web App
2. Click **"Configuration"** (under Settings)
3. Click **"+ New application setting"**
4. Add:
   - Name: `AZURE_STORAGE_CONNECTION_STRING`
   - Value: `your-connection-string`
5. Add another:
   - Name: `AZURE_STORAGE_CONTAINER_NAME`
   - Value: `documents`
6. Click **"Save"**

### Step 3.2: Deploy Updated Code

```powershell
# Build frontend if changed
npm run client:build

# Deploy to Azure
az webapp up `
  --name "legal-demystifier-yourname" `
  --resource-group "legal-demystifier-rg"
```

### Step 3.3: Restart Your App

```powershell
az webapp restart `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname"
```

---

## 🧪 Part 4: Test the Storage Feature

### Test 1: Check Storage Status

Visit: `https://your-app-name.azurewebsites.net/storage/status`

Expected response:
```json
{
  "enabled": true,
  "container_name": "documents",
  "message": "Storage service is active"
}
```

### Test 2: Upload a File

1. Go to your app: `https://your-app-name.azurewebsites.net`
2. Upload a PDF file
3. Analyze it
4. File is automatically stored in Azure!

### Test 3: List Stored Files

Visit: `https://your-app-name.azurewebsites.net/storage/files`

You'll see all uploaded files with metadata:
```json
{
  "files": [
    {
      "name": "20251110_123456_abcd1234_contract.pdf",
      "size": 245678,
      "created_at": "2025-11-10T12:34:56Z",
      "content_type": "application/pdf",
      "metadata": {
        "original_filename": "contract.pdf",
        "document_type": "contract",
        "user_role": "individual"
      }
    }
  ],
  "count": 1
}
```

### Test 4: Get File Information

Visit: `https://your-app-name.azurewebsites.net/storage/file/20251110_123456_abcd1234_contract.pdf`

You'll get file details and a temporary download URL.

### Test 5: View in Azure Portal

1. Go to Azure Portal
2. Navigate to your Storage Account
3. Click **"Containers"** → **"documents"**
4. See all uploaded files!

---

## 📊 Part 5: New API Endpoints

Your app now has these new endpoints:

### GET /storage/status
Check if storage is enabled
```bash
curl https://your-app.azurewebsites.net/storage/status
```

### GET /storage/files
List all stored files
```bash
curl https://your-app.azurewebsites.net/storage/files
```

Query parameters:
- `prefix`: Filter files (e.g., `?prefix=20251110`)
- `max_results`: Limit results (e.g., `?max_results=50`)

### GET /storage/file/{blob_name}
Get file information and download URL
```bash
curl https://your-app.azurewebsites.net/storage/file/20251110_123456_abcd1234_contract.pdf
```

### GET /storage/document/{document_id}
Get storage info for analyzed document
```bash
curl https://your-app.azurewebsites.net/storage/document/your-document-id
```

### DELETE /storage/file/{blob_name}
Delete a stored file
```bash
curl -X DELETE https://your-app.azurewebsites.net/storage/file/20251110_123456_abcd1234_contract.pdf
```

---

## 🔒 Part 6: Security Best Practices

### Use Managed Identity (Recommended for Production)

Instead of connection strings, use Managed Identity:

```powershell
# Enable system-assigned managed identity for your web app
az webapp identity assign `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname"

# Get the identity principal ID
$principalId = az webapp identity show `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname" `
  --query "principalId" `
  --output tsv

# Grant the web app access to storage
az role assignment create `
  --assignee $principalId `
  --role "Storage Blob Data Contributor" `
  --scope "/subscriptions/{subscription-id}/resourceGroups/legal-demystifier-rg/providers/Microsoft.Storage/storageAccounts/legaldemystifierstorage"
```

Then update `storage_service.py` to use Managed Identity instead of connection string.

### Configure CORS (If needed for direct browser uploads)

```powershell
az storage cors add `
  --methods GET POST PUT DELETE `
  --origins "https://your-app.azurewebsites.net" `
  --allowed-headers "*" `
  --exposed-headers "*" `
  --max-age 3600 `
  --services b `
  --account-name "legaldemystifierstorage"
```

---

## 💰 Part 7: Storage Costs

### Pricing (Standard LRS - East US)

| Component | Price | Usage |
|-----------|-------|-------|
| **Storage** | $0.018/GB/month | First 50 GB/month |
| **Write Operations** | $0.05/10,000 ops | Uploads |
| **Read Operations** | $0.004/10,000 ops | Downloads |
| **List Operations** | $0.05/10,000 ops | Listing files |

**Example Monthly Cost:**
- 1,000 file uploads (50 GB total): ~$1
- 5,000 downloads: ~$0.20
- 100 list operations: ~$0.01
- **Total**: ~$1.21/month

### Monitor Costs

```powershell
# View storage metrics
az monitor metrics list `
  --resource "/subscriptions/{subscription-id}/resourceGroups/legal-demystifier-rg/providers/Microsoft.Storage/storageAccounts/legaldemystifierstorage" `
  --metric "UsedCapacity" "Transactions" `
  --output table
```

---

## 🛠️ Part 8: Manage Storage

### View All Files in Portal

1. Go to Azure Portal
2. Navigate to Storage Account → Containers → documents
3. See all files with:
   - Name
   - Size
   - Upload date
   - Download/delete options

### Download Files via CLI

```powershell
# Download a specific file
az storage blob download `
  --account-name "legaldemystifierstorage" `
  --container-name "documents" `
  --name "20251110_123456_abcd1234_contract.pdf" `
  --file "downloaded-contract.pdf" `
  --connection-string $connectionString
```

### Delete Old Files

```powershell
# Delete files older than 90 days
$cutoffDate = (Get-Date).AddDays(-90)

az storage blob list `
  --account-name "legaldemystifierstorage" `
  --container-name "documents" `
  --connection-string $connectionString `
  --query "[?properties.creationTime<'$($cutoffDate.ToString('yyyy-MM-ddTHH:mm:ssZ'))'].name" `
  --output tsv | ForEach-Object {
    az storage blob delete `
      --account-name "legaldemystifierstorage" `
      --container-name "documents" `
      --name $_ `
      --connection-string $connectionString
}
```

### Set Up Lifecycle Management

Auto-delete files after certain period:

```powershell
# Create lifecycle policy
@"
{
  "rules": [
    {
      "enabled": true,
      "name": "DeleteOldDocuments",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "delete": {
              "daysAfterModificationGreaterThan": 365
            }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["documents/"]
        }
      }
    }
  ]
}
"@ | Out-File -FilePath "lifecycle-policy.json" -Encoding utf8

az storage account management-policy create `
  --account-name "legaldemystifierstorage" `
  --resource-group "legal-demystifier-rg" `
  --policy "@lifecycle-policy.json"
```

This deletes files automatically after 365 days.

---

## 🐛 Troubleshooting

### Issue: "Storage service not configured"

**Solution:**
```powershell
# Check if environment variable is set
az webapp config appsettings list `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname" `
  --query "[?name=='AZURE_STORAGE_CONNECTION_STRING']"

# If not set, add it
az webapp config appsettings set `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname" `
  --settings AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
```

### Issue: "Container not found"

**Solution:**
```powershell
# Create the container
az storage container create `
  --name "documents" `
  --account-name "legaldemystifierstorage" `
  --connection-string $connectionString
```

### Issue: Files not uploading

**Check logs:**
```powershell
az webapp log tail `
  --resource-group "legal-demystifier-rg" `
  --name "legal-demystifier-yourname"
```

Look for storage-related errors.

---

## ✅ Summary

You now have:
- ✅ Azure Blob Storage configured
- ✅ Files automatically stored in cloud
- ✅ API endpoints to manage files
- ✅ Secure temporary download URLs
- ✅ Metadata tracking
- ✅ File lifecycle management

**All user-uploaded PDFs are now safely stored in Azure Blob Storage!** 🎉

---

## 📚 Additional Resources

- **Azure Storage Docs**: https://docs.microsoft.com/azure/storage/
- **Blob Storage REST API**: https://docs.microsoft.com/rest/api/storageservices/
- **Python SDK Docs**: https://docs.microsoft.com/python/api/azure-storage-blob/
- **Pricing Calculator**: https://azure.microsoft.com/pricing/calculator/

---

## 🔄 Next Steps

1. Test locally first
2. Deploy to Azure
3. Upload test files
4. Check Azure Portal to see stored files
5. Test API endpoints
6. Set up lifecycle policies
7. Monitor costs

Your file storage is now production-ready! 🚀
