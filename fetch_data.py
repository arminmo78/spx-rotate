#!/usr/bin/env python3
"""
SPX Rotation Calculator — Market Data Fetcher
Runs daily via GitHub Actions. Writes data.json to repository root.
APIs used (all free):
  - Alpha Vantage: SPY price, VIX (free key, 25 calls/day)
  - FRED: CPI, 10Y Treasury, HY Spread, Fed Funds (free key)
  - open.er-api.com: AUD/USD (no key needed)
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

AV_KEY   = os.environ.get('AV_API_KEY', '')
FRED_KEY = os.environ.get('FRED_API_KEY', '')

SYDNEY_OFFSET = timezone(timedelta(hours=10))  # AEST
now_sydney = datetime.now(SYDNEY_OFFSET)

result = {
    "fetchedAt": now_sydney.strftime("%Y-%m-%d %H:%M AEST"),
    "fetchedDate": now_sydney.strftime("%Y-%m-%d"),
    "errors": [],
    # Indicator values (app-ready)
    "spxDrop":       None,   # % below ATH, positive number
    "spxCurrent":    None,   # current SPY price
    "spxATH":        None,   # all-time high SPY
    "vix":           None,   # VIX level
    "creditSpread":  None,   # HY OAS in bps
    "inflation":     None,   # US CPI YoY %
    "treasuryTrend": None,   # 0=Falling, 1=Flat, 2=Rising
    "treasuryYield": None,   # 10Y yield %
    "fedPolicy":     None,   # 0=Cutting, 1=Paused, 2=Hiking
    "fedRate":       None,   # Fed funds rate %
    "earnings":      None,   # 0=Stabilising, 1=Mixed, 2=Falling (manual - not auto-fetched)
    "geopolitical":  None,   # count (manual - not auto-fetched)
    "audusd":        None,   # 0=Falling, 1=Flat, 2=Rising
    "audusdRate":    None,   # AUD/USD exchange rate
}

# ── Load stored ATH from data.json (to track across runs) ──────────────────
stored_ath = 0.0
stored_aud = 0.0
try:
    with open('data.json', 'r') as f:
        prev = json.load(f)
        stored_ath = float(prev.get('spxATH') or 0)
        stored_aud = float(prev.get('audusdRate') or 0)
        # Carry over manual indicators
        result['earnings']    = prev.get('earnings', 1)
        result['geopolitical'] = prev.get('geopolitical', 3)
except Exception:
    result['earnings']    = 1  # Mixed (default)
    result['geopolitical'] = 3  # 3 theatres (default)

# ── Alpha Vantage: SPY ──────────────────────────────────────────────────────
if AV_KEY:
    try:
        r = requests.get(
            'https://www.alphavantage.co/query',
            params={'function': 'GLOBAL_QUOTE', 'symbol': 'SPY', 'apikey': AV_KEY},
            timeout=15
        )
        q = r.json().get('Global Quote', {})
        if q.get('05. price'):
            current = float(q['05. price'])
            ath = max(stored_ath, current)
            result['spxCurrent'] = round(current, 2)
            result['spxATH']     = round(ath, 2)
            drop = max(0, (ath - current) / ath * 100)
            result['spxDrop']    = round(drop, 2)
        elif q.get('Information'):
            result['errors'].append('AV SPY: API call limit reached')
        else:
            result['errors'].append(f'AV SPY: unexpected response {list(q.keys())}')
    except Exception as e:
        result['errors'].append(f'AV SPY: {e}')
else:
    result['errors'].append('AV_API_KEY not set — SPY not fetched')

# ── Alpha Vantage: VIX ──────────────────────────────────────────────────────
if AV_KEY:
    try:
        r = requests.get(
            'https://www.alphavantage.co/query',
            params={'function': 'GLOBAL_QUOTE', 'symbol': 'VIX', 'apikey': AV_KEY},
            timeout=15
        )
        q = r.json().get('Global Quote', {})
        if q.get('05. price'):
            result['vix'] = round(float(q['05. price']), 2)
        elif q.get('Information'):
            result['errors'].append('AV VIX: API call limit reached')
    except Exception as e:
        result['errors'].append(f'AV VIX: {e}')

# ── FRED: CPI (year-over-year) ──────────────────────────────────────────────
if FRED_KEY:
    try:
        start = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
        r = requests.get(
            'https://api.stlouisfed.org/fred/series/observations',
            params={
                'series_id': 'CPIAUCSL', 'api_key': FRED_KEY,
                'file_type': 'json', 'sort_order': 'desc',
                'observation_start': start, 'limit': 14
            },
            timeout=15
        )
        obs = [o for o in r.json().get('observations', []) if o['value'] not in ('.', '')]
        if len(obs) >= 13:
            latest   = float(obs[0]['value'])
            year_ago = float(obs[12]['value'])
            result['inflation'] = round((latest - year_ago) / year_ago * 100, 2)
    except Exception as e:
        result['errors'].append(f'FRED CPI: {e}')
else:
    result['errors'].append('FRED_API_KEY not set — CPI/Treasury/Spread/Fed not fetched')

# ── FRED: 10Y Treasury yield + trend ───────────────────────────────────────
if FRED_KEY:
    try:
        start = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        r = requests.get(
            'https://api.stlouisfed.org/fred/series/observations',
            params={
                'series_id': 'DGS10', 'api_key': FRED_KEY,
                'file_type': 'json', 'sort_order': 'desc',
                'observation_start': start, 'limit': 30
            },
            timeout=15
        )
        obs = [float(o['value']) for o in r.json().get('observations', [])
               if o['value'] not in ('.', '')]
        if len(obs) >= 20:
            result['treasuryYield'] = round(obs[0], 3)
            recent = sum(obs[:5]) / 5
            older  = sum(obs[15:20]) / 5
            if recent > older + 0.05:
                result['treasuryTrend'] = 2   # Rising
            elif recent < older - 0.05:
                result['treasuryTrend'] = 0   # Falling
            else:
                result['treasuryTrend'] = 1   # Flat
    except Exception as e:
        result['errors'].append(f'FRED 10Y: {e}')

# ── FRED: HY Credit Spread (% → bps) ───────────────────────────────────────
if FRED_KEY:
    try:
        start = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        r = requests.get(
            'https://api.stlouisfed.org/fred/series/observations',
            params={
                'series_id': 'BAMLH0A0HYM2', 'api_key': FRED_KEY,
                'file_type': 'json', 'sort_order': 'desc',
                'observation_start': start, 'limit': 5
            },
            timeout=15
        )
        obs = [o for o in r.json().get('observations', []) if o['value'] not in ('.', '')]
        if obs:
            result['creditSpread'] = round(float(obs[0]['value']) * 100)
    except Exception as e:
        result['errors'].append(f'FRED HY: {e}')

# ── FRED: Fed Funds Rate + direction ────────────────────────────────────────
if FRED_KEY:
    try:
        start = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
        r = requests.get(
            'https://api.stlouisfed.org/fred/series/observations',
            params={
                'series_id': 'FEDFUNDS', 'api_key': FRED_KEY,
                'file_type': 'json', 'sort_order': 'desc',
                'observation_start': start, 'limit': 6
            },
            timeout=15
        )
        obs = [o for o in r.json().get('observations', []) if o['value'] not in ('.', '')]
        if len(obs) >= 2:
            latest = float(obs[0]['value'])
            old    = float(obs[-1]['value'])
            result['fedRate'] = round(latest, 3)
            if latest < old - 0.1:
                result['fedPolicy'] = 0   # Cutting
            elif latest > old + 0.1:
                result['fedPolicy'] = 2   # Hiking
            else:
                result['fedPolicy'] = 1   # Paused
    except Exception as e:
        result['errors'].append(f'FRED Fed: {e}')

# ── AUD/USD via open.er-api.com (no key needed) ─────────────────────────────
try:
    r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=10)
    d = r.json()
    if d.get('rates', {}).get('AUD'):
        aud_usd = round(1 / d['rates']['AUD'], 4)
        result['audusdRate'] = aud_usd
        # Trend vs previous run
        if stored_aud > 0:
            change_pct = (aud_usd - stored_aud) / stored_aud * 100
            if change_pct > 0.5:
                result['audusd'] = 2    # Rising
            elif change_pct < -0.5:
                result['audusd'] = 0    # Falling
            else:
                result['audusd'] = 1    # Flat
        else:
            result['audusd'] = 1        # Unknown — default flat
except Exception as e:
    result['errors'].append(f'AUD/USD: {e}')

# ── Summary ──────────────────────────────────────────────────────────────────
fetched = [k for k in ['spxDrop','vix','creditSpread','inflation',
                        'treasuryTrend','fedPolicy','audusd']
           if result[k] is not None]
result['fetchedCount'] = len(fetched)
result['fetchedIndicators'] = fetched

# ── Write data.json ──────────────────────────────────────────────────────────
with open('data.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f"✓ data.json written — {now_sydney.strftime('%Y-%m-%d %H:%M AEST')}")
print(f"  Fetched: {fetched}")
if result['errors']:
    print(f"  Errors:  {result['errors']}")
print(f"  SPX:  -{result.get('spxDrop','?')}%  VIX: {result.get('vix','?')}")
print(f"  CPI:  {result.get('inflation','?')}%  10Y: {result.get('treasuryYield','?')}%")
print(f"  HY:   {result.get('creditSpread','?')}bps  Fed: {result.get('fedRate','?')}%")
print(f"  AUD:  {result.get('audusdRate','?')}  Trend: {['Falling','Flat','Rising'][result.get('audusd',1)]}")
