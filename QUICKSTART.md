# Quick Start Guide - Legal Document Demystifier

## The Issue You Encountered

You're seeing an "API error: 400" because the GEMINI_API_KEY is either:
- Not set
- Set to the placeholder "YOUR_API_KEY"
- Invalid

## How to Fix This

### Step 1: Get Your API Key
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the generated key

### Step 2: Set the API Key

**Option A: Using .env file (recommended for development)**
```powershell
# Copy the example file
copy .env.example .env

# Then edit .env file and replace:
# GEMINI_API_KEY=your-gemini-api-key-here
# with your actual key
```

**Option B: Set directly in PowerShell**
```powershell
$env:GEMINI_API_KEY="paste-your-actual-api-key-here"
python main.py
```

### Step 3: Restart the Server
If the server is already running, stop it (Ctrl+C) and start again:
```powershell
python main.py
```

You should see:
```
INFO:     Started server process [xxxxx]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

If you see the warning:
```
⚠️  GEMINI_API_KEY is not set or is a placeholder
```
Then your API key is still not properly configured.

### Step 4: Test the Application
1. Open http://localhost:8080
2. Paste some sample text (e.g., a simple contract clause)
3. Click "Analyze Document"
4. You should see a proper analysis with summary, key points, risks, etc.

## Sample Text for Testing

You can use this simple contract clause:
```
This Agreement shall be effective as of January 1, 2024 (the "Effective Date"). 
Either party may terminate this Agreement with 30 days written notice. 
The Contractor agrees to provide services for $5,000 per month, payable within 
15 days of invoice. Late payments will incur a 5% penalty per month.
```

## Still Having Issues?

1. **Check your API key is valid**: Test it at https://aistudio.google.com
2. **Check you have API quota**: Free tier has limits
3. **Check logs**: Look for error messages in the terminal where Python is running
4. **Restart everything**: Stop server, rebuild frontend (`npm run client:build`), start server again

## API Key Best Practices

- Never commit your API key to git
- Use `.env` file (already in .gitignore)
- For production, use environment variables or secret management
- Monitor your API usage at https://aistudio.google.com
