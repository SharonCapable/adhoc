# Railway Deployment Checklist

## ✅ Files Created/Updated

- [x] `Procfile` - Start command for Railway
- [x] `railway.json` - Railway configuration
- [x] `.env.example` - Environment variables template
- [x] `.gitignore` - Updated to allow .env.example
- [x] `requirements.txt` - Added version pins for FastAPI/uvicorn
- [x] `README.md` - Added Railway deployment guide

## 📝 Pre-Deployment Steps

1. **Commit and Push to GitHub**
   ```bash
   git add .
   git commit -m "Add Railway deployment configuration"
   git push origin main
   ```

2. **Verify Sensitive Files Are Ignored**
   - ✅ `.env` (ignored)
   - ✅ `credentials.json` (ignored)
   - ✅ `token.json` (ignored)
   - ✅ `service-account.json` (ignored)

## 🚀 Railway Deployment

1. **Create New Project on Railway**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose: `adhoc-research`

2. **Set Environment Variables**
   
   Required:
   ```
   ANTHROPIC_API_KEY=<your_key>
   GEMINI_API_KEY=<your_key>
   LLM_PROVIDER=anthropic
   LLM_MODEL=claude-3-5-sonnet-20241022
   ENVIRONMENT=production
   ```
   
   Optional (Slack):
   ```
   SLACK_BOT_TOKEN=<your_token>
   SLACK_APP_TOKEN=<your_token>
   ```

3. **Deploy**
   - Railway auto-detects Procfile
   - Builds and deploys automatically
   - Get your URL: `https://your-app.railway.app`

## 🧪 Testing

After deployment, test these endpoints:

```bash
# Health check
curl https://your-app.railway.app/health

# Root endpoint
curl https://your-app.railway.app/

# Research endpoint (POST)
curl -X POST https://your-app.railway.app/research \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "frameworkSource": null}'
```

## 🔍 Troubleshooting

**Build fails:**
- Check Railway build logs
- Verify requirements.txt has all dependencies

**App crashes on start:**
- Check Railway deployment logs
- Verify environment variables are set
- Ensure ANTHROPIC_API_KEY is valid

**API returns errors:**
- Check Railway runtime logs
- Test locally first: `uvicorn api_server:app --reload`
- Verify all environment variables match .env.example

## 📌 Important Notes

- Railway automatically assigns a PORT environment variable
- The Procfile uses `$PORT` to bind to Railway's assigned port
- Service account JSON should be added as environment variable for production
- Google Drive access may need additional configuration in production
