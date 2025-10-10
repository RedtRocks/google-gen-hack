#!/bin/bash

# Legal Document Demystifier - GCP Deployment Script

echo "🏛️ Legal Document Demystifier - GCP Deployment"
echo "=============================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK is not installed. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Ensure Node.js toolchain is available for frontend build
if ! command -v npm &> /dev/null; then
    echo "❌ Node.js (npm) is required to build the frontend. Please install it first:"
    echo "   https://nodejs.org/en/download/package-manager"
    exit 1
fi

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Please login to Google Cloud first:"
    echo "   gcloud auth login"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No project set. Please set your project:"
    echo "   gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Using project: $PROJECT_ID"

echo "🛠️ Installing frontend dependencies (npm install --legacy-peer-deps)..."
npm install --legacy-peer-deps

echo "🛠️ Building frontend (npm run client:build)..."
npm run client:build

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY environment variable not set."
    echo "   Please set it before deploying:"
    echo "   export GEMINI_API_KEY='your-api-key-here'"
    read -p "   Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Deploy options
echo ""
echo "Choose deployment method:"
echo "1) Cloud Run (Recommended - Serverless)"
echo "2) App Engine (Traditional)"
echo "3) Build only (Docker image)"

read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "🚀 Deploying to Cloud Run..."
        
        # Build and deploy to Cloud Run
        gcloud run deploy legal-demystifier \
            --source . \
            --platform managed \
            --region us-central1 \
            --allow-unauthenticated \
            --set-env-vars GEMINI_API_KEY="$GEMINI_API_KEY" \
            --memory 1Gi \
            --cpu 1 \
            --max-instances 10
        
        echo "✅ Deployment complete!"
        echo "🌐 Your app is available at:"
        gcloud run services describe legal-demystifier --region us-central1 --format 'value(status.url)'
        ;;
        
    2)
        echo "🚀 Deploying to App Engine..."
        
        # Update app.yaml with API key
        if [ ! -z "$GEMINI_API_KEY" ]; then
            sed -i.bak "s/your-gemini-api-key-here/$GEMINI_API_KEY/g" app.yaml
        fi
        
        gcloud app deploy app.yaml --quiet
        
        # Restore original app.yaml
        if [ -f app.yaml.bak ]; then
            mv app.yaml.bak app.yaml
        fi
        
        echo "✅ Deployment complete!"
        echo "🌐 Your app is available at:"
        gcloud app browse --no-launch-browser
        ;;
        
    3)
        echo "🔨 Building Docker image..."
        
        # Build image
        docker build -t gcr.io/$PROJECT_ID/legal-demystifier .
        
        # Push to Container Registry
        docker push gcr.io/$PROJECT_ID/legal-demystifier
        
        echo "✅ Image built and pushed!"
        echo "📦 Image: gcr.io/$PROJECT_ID/legal-demystifier"
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment process completed!"
echo ""
echo "📚 Next steps:"
echo "   1. Test your application"
echo "   2. Set up custom domain (optional)"
echo "   3. Configure monitoring and logging"
echo "   4. Set up CI/CD pipeline (optional)"