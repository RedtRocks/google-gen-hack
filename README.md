# 🏛️ Legal Document Demystifier

An AI-powered prototype that simplifies complex legal documents into clear, accessible guidance, empowering users to make informed decisions.

## 🎯 Problem Statement

Legal documents—such as rental agreements, loan contracts, and terms of service—are often filled with complex, impenetrable jargon that is incomprehensible to the average person. This creates a significant information asymmetry, where individuals may unknowingly agree to unfavorable terms, exposing them to financial and legal risks.

## 💡 Solution

Our AI solution uses Google Cloud's Gemini AI to:
- **Simplify** complex legal language into plain English
- **Highlight** key points and potential risks
- **Provide** actionable recommendations
- **Answer** specific questions about documents
- **Empower** users to make informed decisions

## ✨ Features

### 📄 Document Analysis
- Upload PDF, DOC, or paste text directly
- Support for various document types (contracts, agreements, terms of service, etc.)
- Customizable analysis based on user role and complexity preference
- Comprehensive breakdown including:
  - Clear summary
  - Key points extraction
  - Risk identification
  - Actionable recommendations
  - Simplified explanations

### 💬 Interactive Q&A
- Ask specific questions about your document
- Get contextual answers with relevant document sections
- Confidence levels for each response

### 🎨 User-Friendly Interface
- Clean, intuitive web interface
- Mobile-responsive design
- Real-time analysis feedback
- No legal expertise required

## 🚀 Quick Start

### Prerequisites
- Google Cloud Platform account
- Gemini API key
- Python 3.9+
- Docker (optional)

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd legal-document-demystifier
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

3. **Run locally:**
   ```bash
   python main.py
   ```

4. **Open browser:**
   Navigate to `http://localhost:8080`

### GCP Deployment

#### Option 1: Cloud Run (Recommended)
```bash
# Make deploy script executable
chmod +x deploy.sh

# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Deploy
./deploy.sh
```

#### Option 2: Manual Cloud Run
```bash
gcloud run deploy legal-demystifier \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars GEMINI_API_KEY="your-api-key-here"
```

#### Option 3: App Engine
```bash
# Update app.yaml with your API key
gcloud app deploy
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │────│   FastAPI App    │────│   Gemini AI     │
│   (HTML/JS)     │    │   (Python)       │    │   (Google)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌──────────────────┐
                       │   Document       │
                       │   Processing     │
                       │   (PDF/Text)     │
                       └──────────────────┘
```

## 📁 Project Structure

```
legal-document-demystifier/
├── main.py              # Main FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── app.yaml            # App Engine configuration
├── cloudbuild.yaml     # Cloud Build configuration
├── deploy.sh           # Deployment script
├── .env.example        # Environment variables template
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `PORT`: Server port (default: 8080)

### Document Types Supported
- Contracts
- Rental Agreements
- Loan Agreements
- Terms of Service
- Privacy Policies
- Employment Contracts
- Other legal documents

### User Roles
- Individual/Consumer
- Small Business Owner
- Tenant/Renter
- Borrower
- Employee

### Complexity Levels
- **Simple**: No legal jargon, everyday language
- **Detailed**: Moderate detail with explained legal terms
- **Expert**: Full legal context and terminology

## 🛡️ Security & Privacy

- Documents are processed in memory only
- No permanent storage of user documents
- API keys are securely managed through environment variables
- HTTPS encryption for all communications

## 📊 API Endpoints

### `POST /analyze-document`
Upload and analyze a legal document file.

### `POST /analyze-text`
Analyze legal document text directly.

### `POST /ask-question`
Ask specific questions about a document.

### `GET /health`
Health check endpoint.

## 🎨 Customization

The application can be easily customized for specific use cases:

1. **Document Types**: Add new document categories in the form
2. **Analysis Prompts**: Modify prompts in `create_analysis_prompt()`
3. **UI Styling**: Update the embedded CSS in the HTML template
4. **API Integration**: Extend with additional AI services

## 🚀 Deployment Options

### Cloud Run (Serverless)
- **Pros**: Auto-scaling, pay-per-use, easy deployment
- **Best for**: Variable traffic, cost optimization

### App Engine (Traditional)
- **Pros**: Integrated with GCP services, automatic scaling
- **Best for**: Consistent traffic, enterprise features

### Container Engine (GKE)
- **Pros**: Full Kubernetes control, advanced orchestration
- **Best for**: Complex deployments, microservices

## 📈 Monitoring & Logging

The application includes:
- Health check endpoints
- Structured logging
- Error handling and reporting
- Performance metrics

## 🤝 Contributing

This is a hackathon prototype. For production use, consider:

1. **Database Integration**: Add persistent storage for documents and analytics
2. **User Authentication**: Implement user accounts and session management
3. **Advanced AI Features**: Add document comparison, clause extraction
4. **Mobile App**: Create native mobile applications
5. **Enterprise Features**: Multi-tenant support, admin dashboards

## 📄 License

This project is created for hackathon purposes. Please ensure compliance with Google Cloud and Gemini AI terms of service.

## 🆘 Support

For issues or questions:
1. Check the logs: `gcloud logs read`
2. Verify API key configuration
3. Ensure all required GCP APIs are enabled
4. Check resource quotas and limits

## 🎉 Demo

The application provides a complete end-to-end experience:

1. **Upload** a legal document (PDF or text)
2. **Select** your role and preferred complexity level
3. **Get** instant analysis with key points, risks, and recommendations
4. **Ask** follow-up questions about specific clauses
5. **Make** informed decisions based on clear explanations

Perfect for hackathon demonstrations and real-world legal document analysis needs!