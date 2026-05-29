# Deployment Guide

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit — Breathe ESG prototype"
git remote add origin https://github.com/YOUR_USERNAME/breathe-esg.git
git push -u origin main
```

Share the repo with:
- saurav@breatheesg.com
- rahul@breatheesg.com  
- shivang@breatheesg.com

(GitHub → Settings → Collaborators → Add by email)

---

## Step 2: Deploy Backend on Railway

1. Go to https://railway.app → New Project → Deploy from GitHub Repo
2. Select your repo → select the `backend/` folder as root
3. Railway auto-detects Python → add these environment variables:

| Variable | Value |
|---|---|
| `SECRET_KEY` | any long random string (e.g. `openssl rand -hex 32`) |
| `DEBUG` | `False` |
| `DATABASE_URL` | (auto-set when you add PostgreSQL plugin) |

4. Add PostgreSQL: Railway dashboard → + Add Plugin → PostgreSQL
5. In Settings → set Root Directory to `backend`
6. Deploy → Railway runs `python manage.py migrate && python setup_demo.py` automatically (via Procfile `release` command)
7. Copy your backend URL (e.g. `https://breathe-esg-backend.railway.app`)

---

## Step 3: Deploy Frontend on Railway (or Vercel)

### Option A: Vercel (easiest for React)
1. https://vercel.com → New Project → Import from GitHub
2. Set Root Directory to `frontend`
3. Add environment variable: `REACT_APP_API_URL=https://your-backend.railway.app`
4. Deploy

### Option B: Railway
1. New Service in same Railway project → GitHub → select `frontend/` as root
2. Build command: `npm run build`
3. Start command: `npx serve -s build`
4. Add env var: `REACT_APP_API_URL=https://your-backend.railway.app`

---

## Step 4: Test the live app

1. Visit your frontend URL
2. Login: `analyst` / `demo1234`
3. Upload sample files from `sample_data/` on the Ingest page
4. Go to Review Queue — approve/flag/reject records
5. Check Overview dashboard

---

## Credentials to share in your submission email

```
Live URL: https://your-frontend.vercel.app
Backend API: https://your-backend.railway.app

Login: analyst / demo1234
Admin: admin / admin1234
```
