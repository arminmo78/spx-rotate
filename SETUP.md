# SPX Rotation Calculator — Automatic Data Setup

## How it works

GitHub Actions runs a Python script every weekday morning at 7am AEST.
The script fetches SPX, VIX, CPI, Treasury yield, HY spread, Fed rate, and AUD/USD
from free APIs and writes them to `data.json` in your repository.

Your app's ⟳ REFRESH button reads `data.json` — no CORS issues, no API keys in the app.

---

## One-time setup (10 minutes)

### Step 1 — Upload all files to GitHub
Make sure your GitHub repository has ALL these files:
```
index.html
manifest.json
sw.js
data.json
fetch_data.py
icon-192.png
icon-512.png
.github/workflows/fetch-data.yml
```

### Step 2 — Add your API keys as GitHub Secrets

Go to your repository on github.com:
1. Click **Settings** (top menu of your repo)
2. Click **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these two secrets:

**Secret 1:**
- Name: `AV_API_KEY`
- Value: your Alpha Vantage key (get free at alphavantage.co/support/#api-key)

**Secret 2:**
- Name: `FRED_API_KEY`
- Value: your FRED key (get free at fredaccount.stlouisfed.org → API Keys)

### Step 3 — Run it manually the first time
1. Go to your repo → **Actions** tab
2. Click **Fetch Market Data** in the left panel
3. Click **Run workflow** → **Run workflow**
4. Watch it run — takes about 30 seconds
5. When it finishes, `data.json` in your repo will have today's data

### Step 4 — Test in the app
1. Open your GitHub Pages URL in Chrome on your phone
2. Tap ⟳ REFRESH
3. All indicators update automatically

---

## After setup — daily use

The workflow runs automatically every weekday at 7am AEST.
You never need to touch it again.

Just open the app and tap ⟳ REFRESH whenever you want the latest data.

---

## What gets updated automatically vs manually

| Indicator | Auto | Source |
|---|---|---|
| SPX drawdown | ✓ | Alpha Vantage (SPY) |
| VIX | ✓ | Alpha Vantage |
| HY Credit Spread | ✓ | FRED BAMLH0A0HYM2 |
| CPI Inflation | ✓ | FRED CPIAUCSL |
| 10Y Treasury trend | ✓ | FRED DGS10 |
| Fed policy | ✓ | FRED FEDFUNDS |
| AUD/USD | ✓ | open.er-api.com |
| Earnings revisions | Manual | FactSet weekly |
| Geopolitical theatres | Manual | Your judgment |

---

## Troubleshooting

**"Data is X days old" warning in app:**
Go to your GitHub repo → Actions → Run "Fetch Market Data" manually.

**Workflow failing:**
Go to Actions tab → click the failed run → read the error log.
Most likely: API key not set correctly in Secrets.

**App shows old data after workflow runs:**
The data.json file updates but your browser may cache the old version.
Hard refresh: on phone, tap ⟳ REFRESH twice, or clear Chrome cache.
