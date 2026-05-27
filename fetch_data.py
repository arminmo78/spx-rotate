#!/usr/bin/env python3
"""
SPX Rotation Calculator — Market Data Fetcher
Runs daily via GitHub Actions. Writes data.json to repository root.
APIs:
  - FRED: SP500 (actual SPX values), VIXCLS, CPIAUCSL, DGS10, BAMLH0A0HYM2, FEDFUNDS
  - open.er-api.com: AUD/USD (no key needed)
  - Alpha Vantage: NOT used for SPX (FRED is more reliable and uses actual SPX values)
"""

import os, json, requests
from datetime import datetime, timedelta, timezone

FRED_KEY = os.environ.get('FRED_API_KEY', '')
SYDNEY   = timezone(timedelta(hours=10))
now      = datetime.now(SYDNEY)

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
    "earnings":      1,    # Manual — carry over
    "geopolitical":  3,    # Manual — carry over
    "audusd":        None,
    "audusdRate":    None,
}

# Load previous data to carry over manual fields and stored ATH
stored_ath = 0.0
stored_aud = 0.0
try:
    with open('data.json', 'r') as f:
        prev = json.load(f)
        stored_ath      = float(prev.get('spxATH') or 0)
        stored_aud      = float(prev.get('audusdRate') or 0)
        result['earnings']     = prev.get('earnings', 1)
        result['geopolitical'] = prev.get('geopolitical', 3)
except Exception:
    pass

def fred_get(series_id, limit=30):
    start = (datetime.now() - timedelta(days=max(limit*3, 400))).strftime('%Y-%m-%d')
    end   = datetime.now().strftime('%Y-%m-%d')
    r = requests.get('https://api.stlouisfed.org/fred/series/observations', params={
        'series_id': series_id, 'api_key': FRED_KEY, 'file_type': 'json',
        'sort_order': 'desc', 'observation_start': start,
        'observation_end': end, 'limit': limit
    }, timeout=15)
    r.raise_for_status()
    data = r.json()
    if 'error_message' in data:
        raise Exception(data['error_message'])
    return [o for o in data.get('observations', []) if o['value'] not in ('.','')]

if not FRED_KEY:
    result['errors'].append('FRED_API_KEY not set')
else:
    # ── SP500 actual index values (NOT SPY ETF) ─────────────────────────────
    try:
        obs = fred_get('SP500', limit=1260)  # ~5 years daily
        if obs:
            vals = [float(o['value']) for o in obs]
            current = vals[0]
            ath     = max(stored_ath, max(vals))
            result['spxCurrent'] = round(current, 2)
            result['spxATH']     = round(ath, 2)
            result['spxDrop']    = round(max(0, (ath - current) / ath * 100), 2)
    except Exception as e:
        result['errors'].append(f'SP500: {e}')

    # ── VIX ────────────────────────────────────────────────────────────────
    try:
        obs = fred_get('VIXCLS', limit=5)
        if obs:
            result['vix'] = round(float(obs[0]['value']), 2)
    except Exception as e:
        result['errors'].append(f'VIX: {e}')

    # ── CPI YoY ────────────────────────────────────────────────────────────
    try:
        obs = fred_get('CPIAUCSL', limit=14)
        if len(obs) >= 13:
            latest   = float(obs[0]['value'])
            year_ago = float(obs[12]['value'])
            result['inflation'] = round((latest - year_ago) / year_ago * 100, 2)
    except Exception as e:
        result['errors'].append(f'CPI: {e}')

    # ── 10Y Treasury ───────────────────────────────────────────────────────
    try:
        obs = fred_get('DGS10', limit=30)
        vals = [float(o['value']) for o in obs]
        if len(vals) >= 20:
            result['treasuryYield'] = round(vals[0], 3)
            recent = sum(vals[:5]) / 5
            older  = sum(vals[15:20]) / 5
            result['treasuryTrend'] = 2 if recent > older + 0.05 else (0 if recent < older - 0.05 else 1)
    except Exception as e:
        result['errors'].append(f'10Y: {e}')

    # ── HY Spread ──────────────────────────────────────────────────────────
    try:
        obs = fred_get('BAMLH0A0HYM2', limit=5)
        if obs:
            result['creditSpread'] = round(float(obs[0]['value']) * 100)
    except Exception as e:
        result['errors'].append(f'HY: {e}')

    # ── Fed Funds ──────────────────────────────────────────────────────────
    try:
        obs = fred_get('FEDFUNDS', limit=6)
        if len(obs) >= 2:
            latest = float(obs[0]['value'])
            old    = float(obs[-1]['value'])
            result['fedRate']   = round(latest, 3)
            result['fedPolicy'] = 0 if latest < old - 0.1 else (2 if latest > old + 0.1 else 1)
    except Exception as e:
        result['errors'].append(f'Fed: {e}')

# ── AUD/USD ────────────────────────────────────────────────────────────────
try:
    r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
    d = r.json()
    if d.get('rates', {}).get('AUD'):
        aud = round(1 / d['rates']['AUD'], 4)
        result['audusdRate'] = aud
        if stored_aud > 0:
            chg = (aud - stored_aud) / stored_aud * 100
            result['audusd'] = 2 if chg > 0.5 else (0 if chg < -0.5 else 1)
        else:
            result['audusd'] = 1
except Exception as e:
    result['errors'].append(f'AUD: {e}')

# ── Write data.json ────────────────────────────────────────────────────────
fetched = [k for k in ['spxDrop','vix','creditSpread','inflation',
                        'treasuryTrend','fedPolicy','audusd']
           if result[k] is not None]
result['fetchedCount']      = len(fetched)
result['fetchedIndicators'] = fetched

with open('data.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f"✓ {result['fetchedAt']}")
print(f"  SPX:  {result['spxCurrent']} (ATH {result['spxATH']}, -{result['spxDrop']}%)")
print(f"  VIX:  {result['vix']}")
print(f"  CPI:  {result['inflation']}%  10Y: {result['treasuryYield']}%")
print(f"  HY:   {result['creditSpread']}bps  Fed: {result['fedRate']}%")
print(f"  AUD:  {result['audusdRate']}")
if result['errors']:
    print(f"  Errs: {result['errors']}")
