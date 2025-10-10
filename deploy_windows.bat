@echo off
REM Legal Document Demystifier - Windows GCP Deployment Script

echo 🏛️ Legal Document Demystifier - GCP Deployment
echo ==============================================

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Google Cloud SDK is not installed. Please install it first:
    echo    https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Check if npm is installed
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js (npm) is required to build the frontend. Please install it first:
    echo    https://nodejs.org/en/download/
    pause
    exit /b 1
)

REM Check if user is logged in
for /f %%i in ('gcloud auth list --filter=status:ACTIVE --format="value(account)"') do set ACTIVE_ACCOUNT=%%i
if "%ACTIVE_ACCOUNT%"=="" (
    echo ❌ Please login to Google Cloud first:
    echo    gcloud auth login
    pause
    exit /b 1
)

REM Get project ID
for /f %%i in ('gcloud config get-value project') do set PROJECT_ID=%%i
if "%PROJECT_ID%"=="" (
    echo ❌ No project set. Please set your project:
    echo    gcloud config set project YOUR_PROJECT_ID
    pause
    exit /b 1
)

echo 📋 Using project: %PROJECT_ID%

echo 🛠️ Installing frontend dependencies (npm install --legacy-peer-deps)...
npm install --legacy-peer-deps
if %errorlevel% neq 0 (
    echo ❌ Failed to install frontend dependencies.
    pause
    exit /b 1
)

echo 🛠️ Building frontend (npm run client:build)...
npm run client:build
if %errorlevel% neq 0 (
    echo ❌ Frontend build failed.
    pause
    exit /b 1
)

REM Check for API key
if "%GEMINI_API_KEY%"=="" (
    echo ⚠️  GEMINI_API_KEY environment variable not set.
    echo    Please set it before deploying:
    echo    set GEMINI_API_KEY=your-api-key-here
    set /p CONTINUE="   Do you want to continue anyway? (y/N): "
    if /i not "%CONTINUE%"=="y" exit /b 1
)

REM Enable required APIs
echo 🔧 Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

REM Deploy options
echo.
echo Choose deployment method:
echo 1) Cloud Run (Recommended - Serverless)
echo 2) App Engine (Traditional)
echo 3) Build only (Docker image)
echo.

set /p CHOICE="Enter choice (1-3): "

if "%CHOICE%"=="1" (
    echo 🚀 Deploying to Cloud Run...
    
    gcloud run deploy legal-demystifier --source . --platform managed --region us-central1 --allow-unauthenticated --set-env-vars GEMINI_API_KEY="%GEMINI_API_KEY%" --memory 1Gi --cpu 1 --max-instances 10
    
    echo ✅ Deployment complete!
    echo 🌐 Your app is available at:
    gcloud run services describe legal-demystifier --region us-central1 --format "value(status.url)"
    
) else if "%CHOICE%"=="2" (
    echo 🚀 Deploying to App Engine...
    
    REM Update app.yaml with API key
    if not "%GEMINI_API_KEY%"=="" (
        powershell -Command "(Get-Content app.yaml) -replace 'your-gemini-api-key-here', '%GEMINI_API_KEY%' | Set-Content app.yaml.tmp"
        move app.yaml.tmp app.yaml
    )
    
    gcloud app deploy app.yaml --quiet
    
    echo ✅ Deployment complete!
    echo 🌐 Your app is available at:
    gcloud app browse --no-launch-browser
    
) else if "%CHOICE%"=="3" (
    echo 🔨 Building Docker image...
    
    REM Build image
    docker build -t gcr.io/%PROJECT_ID%/legal-demystifier .
    
    REM Push to Container Registry
    docker push gcr.io/%PROJECT_ID%/legal-demystifier
    
    echo ✅ Image built and pushed!
    echo 📦 Image: gcr.io/%PROJECT_ID%/legal-demystifier
    
) else (
    echo ❌ Invalid choice
    pause
    exit /b 1
)

echo.
echo 🎉 Deployment process completed!
echo.
echo 📚 Next steps:
echo    1. Test your application
echo    2. Set up custom domain (optional)
echo    3. Configure monitoring and logging
echo    4. Set up CI/CD pipeline (optional)

pause