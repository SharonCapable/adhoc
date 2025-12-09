# 🚀 Quick Railway Deployment Guide

## ✅ What Was Fixed

1. **Environment Variable Name**: Changed `GOOGLE_API_KEY` → `GEMINI_API_KEY`
2. **Missing Files**: Added `Procfile` and `railway.json` (now committed to GitHub)
3. **All files pushed to GitHub** ✅

## 📋 Deploy to Railway NOW

### Step 1: Redeploy on Railway

Since you already tried deploying, Railway should auto-detect the new commit. If not:

1. Go to your Railway project dashboard
2. Click **"Redeploy"** or trigger a new deployment
3. Railway will now find the `Procfile` and start correctly

### Step 2: Set Environment Variables in Railway

Go to **Variables** tab and add these **EXACT** variable names:

```
ANTHROPIC_API_KEY=<paste_your_anthropic_key>
GEMINI_API_KEY=<paste_your_gemini_key>
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ENVIRONMENT=production
```

**⚠️ IMPORTANT**: Use `GEMINI_API_KEY` not `GOOGLE_API_KEY`

### Step 3: Wait for Deployment

Railway will:
- ✅ Detect Python
- ✅ Install dependencies from `requirements.txt`
- ✅ Find `Procfile` with start command
- ✅ Start with: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`

### Step 4: Test Your Deployment

Once deployed, you'll get a URL like: `https://adhoc-production-xxxx.up.railway.app`

Test it:
```bash
# Health check
curl https://your-app.railway.app/health

# Should return:
# {"status":"ok","python_version":"...","cwd":"..."}
```

## 🔍 What Changed in Git

```
✅ Procfile - Tells Railway how to start
✅ railway.json - Railway configuration
✅ .env.example - Environment variable template (GEMINI_API_KEY)
✅ .gitignore - Updated to allow .env.example
✅ requirements.txt - Version pins for FastAPI/uvicorn
✅ README.md - Railway deployment guide
✅ RAILWAY_DEPLOYMENT.md - Detailed deployment checklist
```

## 💡 Why It Failed Before

Railway couldn't find a start command because:
- `Procfile` wasn't committed to GitHub
- `railway.json` wasn't committed to GitHub

**Now both files are in GitHub**, so Railway will detect them automatically!

## 🎯 Next Steps

1. Go to Railway dashboard
2. Trigger redeploy (or it may auto-deploy from the new commit)
3. Add environment variables (use `GEMINI_API_KEY`)
4. Wait for deployment to complete
5. Test the `/health` endpoint

---

**You're all set!** The deployment should work now. 🚀
