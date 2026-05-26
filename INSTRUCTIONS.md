# SPX Rotation Calculator — PWA
## Setup & Installation Guide

---

## WHAT YOU HAVE

A Progressive Web App (PWA) that:
- Fetches **live SPX and VIX** from Yahoo Finance (no key needed)
- Fetches **live CPI, 10Y Treasury, HY Credit Spread, Fed Funds** from FRED (free API key)
- Shows a **composite rotation score 0–100** based on the Scenario A–D framework
- Sends **in-app and system notifications** when score crosses thresholds
- Works **offline** after first load
- Installs to your **Android home screen** like a native app

---

## STEP 1 — HOST THE APP (ONE-TIME, 5 MINUTES)

The PWA needs to be served over HTTPS to install on Android.
The easiest free option is **Netlify Drop** — no account needed.

### Option A: Netlify Drop (Recommended — 2 minutes)
1. Go to **https://app.netlify.com/drop**
2. Drag the entire `spx-pwa` folder onto the page
3. Netlify gives you a URL like `https://wonderful-name-123.netlify.app`
4. That's your app URL — bookmark it

### Option B: GitHub Pages (If you have a GitHub account)
1. Create a new GitHub repository (e.g. `spx-rotate`)
2. Upload all files from the `spx-pwa` folder
3. Go to Settings → Pages → Deploy from main branch
4. Your URL: `https://yourusername.github.io/spx-rotate`

### Option C: Run locally on your computer + access via phone
If your phone and computer are on the same WiFi:
```bash
# In the spx-pwa folder:
python3 -m http.server 8080
# Then on your phone, go to: http://YOUR_COMPUTER_IP:8080
# Note: PWA install won't work without HTTPS — use Netlify for full features
```

---

## STEP 2 — GET YOUR FREE FRED API KEY (2 MINUTES)

FRED (Federal Reserve Economic Data) provides free API keys.

1. Go to: **https://fredaccount.stlouisfed.org/login/secure/**
2. Click "Create Account" — takes 2 minutes
3. After login, go to **My Account → API Keys**
4. Click "Request API Key"
5. You get a 32-character key like: `abcd1234efgh5678ijkl9012mnop3456`

---

## STEP 3 — INSTALL ON YOUR ANDROID PHONE

1. Open **Chrome** on your Android phone
2. Go to your app URL (from Step 1)
3. Wait for the app to load fully
4. Chrome will show a banner: **"Add SPX Rotate to Home Screen"**
   - Tap **Install** on the banner, OR
   - Tap the ⋮ menu → **Add to Home Screen**
5. The app icon appears on your home screen
6. Tap it — it opens like a native app (full screen, no browser chrome)

---

## STEP 4 — ENTER YOUR FRED API KEY IN THE APP

1. Open the app → tap **SETTINGS** (bottom nav)
2. Paste your FRED key in the **"FRED API KEY"** field
3. Tap **SAVE KEY**
4. Go back to the Score tab and tap **⟳ REFRESH**
5. Live data loads automatically

---

## STEP 5 — ENABLE NOTIFICATIONS

1. In the app → **SETTINGS** tab
2. Tap **ENABLE NOTIFICATIONS**
3. Chrome asks permission — tap **Allow**
4. You'll get a test notification confirming it works

The app will alert you when:
- Score crosses **55** (Prepare to Rotate)
- Score crosses **75** (Rotate Now)
- Both hard gates clear simultaneously (SPX ≥20% + CPI ≤6%)

---

## HOW TO USE THE APP

### SCORE tab
- Shows your composite score and verdict
- Key readings summary (SPX, VIX, CPI, etc.)
- Tap **⟳ REFRESH** to fetch latest live data

### INDICATORS tab
- Shows all 8 indicators with live/manual status
- **Live indicators** (green "LIVE" badge): auto-populated from FRED/Yahoo
- **Manual indicators**: adjust sliders/toggles yourself
- Adjusting any indicator manually overrides live data for that indicator

### LEGEND tab
- Full explanation of all 4 verdict bands
- Hard gate conditions explained
- Historical calibration (what score would have been at COVID trough, GFC, etc.)
- Indicator weight breakdown
- Your portfolio context

### SETTINGS tab
- FRED API key management
- Notification threshold toggles
- Auto-refresh on open toggle
- Clear manual overrides

---

## WHAT'S LIVE vs MANUAL

| Indicator | Data Source | Needs FRED Key? |
|-----------|-------------|-----------------|
| SPX Drawdown | Yahoo Finance (^GSPC) | No |
| VIX | Yahoo Finance (^VIX) | No |
| HY Credit Spread | FRED: BAMLH0A0HYM2 | Yes |
| CPI Inflation | FRED: CPIAUCSL | Yes |
| 10Y Treasury Trend | FRED: DGS10 | Yes |
| Fed Policy | FRED: FEDFUNDS | Yes |
| Earnings Revisions | Manual (FactSet/Bloomberg) | N/A |
| Geopolitical Theatres | Manual (your judgment) | N/A |

---

## HARD GATES (ALWAYS CHECK THESE FIRST)

Regardless of composite score, do NOT rotate if:
1. **SPX drawdown < 20%** — minimum price trigger not met
2. **CPI inflation > 6%** — growth assets lose real value in real terms

Both gates must be clear before the score matters.

---

## TROUBLESHOOTING

**App won't install on home screen:**
- Must use Chrome (not Firefox or Samsung Browser)
- Must be served over HTTPS (Netlify/GitHub Pages)
- Try: Chrome menu ⋮ → Add to Home Screen

**Live data not loading:**
- Check internet connection
- Verify FRED API key is saved correctly (Settings tab)
- FRED updates daily — some indicators update monthly (CPI)
- Yahoo Finance data may have brief outages

**Notifications not appearing:**
- Chrome → Settings → Site Settings → Notifications → find your app URL → Allow
- Android → Settings → Apps → Chrome → Notifications → On

**Score seems wrong:**
- Check Settings → override list for any manual adjustments
- Tap "Clear All Overrides" then Refresh to reset to live data

---

## YOUR SCORING FRAMEWORK

| Score | Verdict | Action |
|-------|---------|--------|
| 75–100 | ROTATE NOW | Execute Cash → Growth Fund |
| 55–74 | PREPARE | Monitor daily, prepare paperwork |
| 35–54 | MONITOR | Check weekly, preserve optionality |
| 0–34 | HOLD CASH | Stay put, real loss is cost of discipline |

**Remember:** The SPX -20% price trigger and CPI ≤6% are hard gates that override the score entirely.

---

## FILES IN THIS PACKAGE

```
spx-pwa/
├── index.html      ← Complete app (all code in one file)
├── manifest.json   ← PWA installation metadata
├── sw.js           ← Service worker (offline + notifications)
├── icon-192.png    ← App icon (home screen)
├── icon-512.png    ← App icon (splash screen)
└── INSTRUCTIONS.md ← This file
```

---

*SPX Rotation Calculator — Scenario A–D Macro Framework*
*Data: FRED (St. Louis Fed) + Yahoo Finance*
*Not financial advice. Consult a licensed financial adviser before making superannuation allocation decisions.*
