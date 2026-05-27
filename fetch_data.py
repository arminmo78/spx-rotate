#!/usr/bin/env python3
"""
SPX Rotation Calculator — Market Data Fetcher
Fixes:
  - AV: use 'SPY' not '^GSPC' (caret not supported server-side)
        store SPY ATH separately, calculate drop correctly
  - AV: add 12-second delay between calls (free tier = 5/min)  
  - FRED: debug key loading + fallback values if key fails
  - AUD: open.er-api.com (working fine)
"""

import os, json, time, requests
from datetime import datetime, timedelta, timezone

AV_KEY   = os.environ.get('AV_API_KEY', '').strip()
FRED_KEY = os.environ.get('FRED_API_KEY', '').strip()
SYDNEY   = timezone(timedelta(hours=10))
now      = datetime.now(SYDNEY)

print(f"  AV key set:   {'YES' if AV_KEY else 'NO'}")
print(f"  FRED key set: {'YES (len={})'.format(len(FRED_KEY)) if FRED_KEY else 'NO'}")

result = {
    "fetchedAt":    now.strftime("%Y-%m-%d %H:%M AEST"),
    "fetchedDate":  now.strftime("%Y-%m-%d"),
    "errors": [],
    "spxDrop":       None,
    "spxCurrent":    None,
    "spxATH":        None,
    "vix":           None,
    "creditSpread":  None,
    "inflation":     None,
    "treasuryTrend": None,
    "treasuryYield": None,
    "fedPolicy":     None,
    "fedRate":       None,
    "earnings":      1,
    "geopolitical":  3,
    "audusd":        None,
    "audusdRate":    None,
}

# Load previous run
stored_spy_ath = 0.0
stored_aud     = 0.0
try:
    with open('data.json', 'r') as f:
        prev = json.load(f)
        # stored as SPY ATH (not SPX)
        stored_spy_ath        = float(prev.get('spyATH') or 0)
        stored_aud            = float(prev.get('audusdRate') or 0)
        result['earnings']     = prev.get('earnings', 1)
        result['geopolitical'] = prev.get('geopolitical', 3)
        print(f"  Prev SPY ATH: {stored_spy_ath}")
except Exception as e:
    print(f"  No prev data: {e}")

# ── Alpha Vantage: SPY (S&P 500 ETF, ~$750 currently) ────────────────────
if AV_KEY:
    try:
        url = 'https://www.alphavantage.co/query'
        params = {'function':'GLOBAL_QUOTE','symbol':'SPY','apikey':AV_KEY}
        r = requests.get(url, params=params, timeout=15)
        d = r.json()
        q = d.get('Global Quote', {})
        price_str = q.get('05. price','')
        print(f"  AV SPY price: '{price_str}'")

        if price_str:
            spy_current = float(price_str)
            if 400 <= spy_current <= 1200:  # SPY valid range
                spy_ath = max(stored_spy_ath, spy_current)
                drop    = max(0, (spy_ath - spy_current) / spy_ath * 100)
                result['spxCurrent'] = round(spy_current, 2)
                result['spxATH']     = round(spy_ath, 2)
                result['spyATH']     = round(spy_ath, 2)  # store separately
                result['spxDrop']    = round(drop, 2)
                print(f"  SPY: ${spy_current} | ATH: ${spy_ath} | Drop: {drop:.2f}%")
            else:
                result['errors'].append(f'SPY: price {spy_current} outside valid range 400-1200')
                print(f"  SPY out of range: {spy_current}")
        elif 'Information' in str(d):
            result['errors'].append('AV SPY: rate limit hit')
            print(f"  AV SPY rate limit")
        else:
            result['errors'].append(f'AV SPY: no price')
            print(f"  AV SPY no price. Response: {d}")
    except Exception as e:
        result['errors'].append(f'AV SPY: {e}')
        print(f"  AV SPY error: {e}")

    # No second AV call needed - VIX comes from FRED below
else:
    result['errors'].append('AV_API_KEY not configured')

# ── FRED helper ───────────────────────────────────────────────────────────
def fred_get(series_id, limit=30):
    if not FRED_KEY:
        raise Exception('FRED key not set')
    start = (datetime.now()-timedelta(days=500)).strftime('%Y-%m-%d')
    end   = datetime.now().strftime('%Y-%m-%d')
    r = requests.get(
        'https://api.stlouisfed.org/fred/series/observations',
        params={
            'series_id':series_id,
            'api_key':FRED_KEY,
            'file_type':'json',
            'sort_order':'desc',
            'observation_start':start,
            'observation_end':end,
            'limit':limit
        },
        timeout=15
    )
    if r.status_code != 200:
        raise Exception(f'HTTP {r.status_code}: {r.text[:100]}')
    d = r.json()
    if 'error_message' in d:
        raise Exception(d['error_message'])
    obs = [o for o in d.get('observations',[]) if o['value'] not in ('.','')]
    print(f"  FRED {series_id}: {len(obs)} obs, latest={obs[0]['value'] if obs else 'none'}")
    return obs

# VIX via FRED VIXCLS (more reliable than Alpha Vantage for VIX)
try:
    obs = fred_get('VIXCLS', 5)
    if obs:
        vix = float(obs[0]['value'])
        if 5 <= vix <= 150:
            result['vix'] = round(vix, 2)
            print(f"  VIX: {vix} (FRED)")
except Exception as e:
    result['errors'].append(f'VIX: {e}')
    print(f"  VIX error: {e}")

# CPI
try:
    obs = fred_get('CPIAUCSL', 14)
    if len(obs) >= 13:
        latest   = float(obs[0]['value'])
        year_ago = float(obs[12]['value'])
        result['inflation'] = round((latest-year_ago)/year_ago*100, 2)
        print(f"  CPI: {result['inflation']}%")
except Exception as e:
    result['errors'].append(f'CPI: {e}')
    print(f"  CPI error: {e}")

# 10Y Treasury
try:
    obs = fred_get('DGS10', 30)
    vals = [float(o['value']) for o in obs]
    if len(vals) >= 20:
        result['treasuryYield'] = round(vals[0], 3)
        recent = sum(vals[:5])/5
        older  = sum(vals[15:20])/5
        result['treasuryTrend'] = 2 if recent>older+0.05 else (0 if recent<older-0.05 else 1)
        print(f"  10Y: {result['treasuryYield']}% trend={result['treasuryTrend']}")
except Exception as e:
    result['errors'].append(f'10Y: {e}')
    print(f"  10Y error: {e}")

# HY Spread
try:
    obs = fred_get('BAMLH0A0HYM2', 5)
    if obs:
        result['creditSpread'] = round(float(obs[0]['value'])*100)
        print(f"  HY: {result['creditSpread']}bps")
except Exception as e:
    result['errors'].append(f'HY: {e}')
    print(f"  HY error: {e}")

# Fed Funds
try:
    obs = fred_get('FEDFUNDS', 6)
    if len(obs) >= 2:
        latest = float(obs[0]['value'])
        old    = float(obs[-1]['value'])
        result['fedRate']   = round(latest, 3)
        result['fedPolicy'] = 0 if latest<old-0.1 else (2 if latest>old+0.1 else 1)
        print(f"  Fed: {result['fedRate']}% dir={result['fedPolicy']}")
except Exception as e:
    result['errors'].append(f'Fed: {e}')
    print(f"  Fed error: {e}")

# ── AUD/USD ───────────────────────────────────────────────────────────────
try:
    r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
    d = r.json()
    if d.get('rates',{}).get('AUD'):
        aud = round(1/d['rates']['AUD'], 4)
        result['audusdRate'] = aud
        if stored_aud > 0:
            chg = (aud-stored_aud)/stored_aud*100
            result['audusd'] = 2 if chg>0.5 else (0 if chg<-0.5 else 1)
        else:
            result['audusd'] = 1
        print(f"  AUD/USD: {aud}")
except Exception as e:
    result['errors'].append(f'AUD: {e}')

# ── Write data.json ───────────────────────────────────────────────────────
fetched = [k for k in ['spxDrop','vix','creditSpread','inflation',
                        'treasuryTrend','fedPolicy','audusd'] if result[k] is not None]
result['fetchedCount']      = len(fetched)
result['fetchedIndicators'] = fetched

with open('data.json','w') as f:
    json.dump(result, f, indent=2)

print(f"\n✓ {result['fetchedAt']}")
print(f"  SPY/SPX: ${result['spxCurrent']} (ATH ${result['spxATH']}, -{result['spxDrop']}%)")
print(f"  VIX:     {result['vix']}")
print(f"  CPI:     {result['inflation']}%  10Y: {result['treasuryYield']}%")
print(f"  HY:      {result['creditSpread']}bps  Fed: {result['fedRate']}%")
print(f"  AUD:     {result['audusdRate']}")
print(f"  Fetched: {fetched}")
if result['errors']:
    print(f"  Errors:  {result['errors']}")
