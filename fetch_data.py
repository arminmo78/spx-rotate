#!/usr/bin/env python3
"""
SPX Rotation Calculator — Market Data Fetcher
Runs daily via GitHub Actions. Writes data.json to repository root.

Sources:
  SPX:  Alpha Vantage ^GSPC (actual S&P 500 index value ~7473)
  VIX:  Alpha Vantage ^VIX
  REST: FRED API (CPI, 10Y Treasury, HY Spread, Fed Funds)
  AUD:  open.er-api.com (no key needed)
"""

import os, json, requests
from datetime import datetime, timedelta, timezone

AV_KEY   = os.environ.get('AV_API_KEY', '')
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
    "earnings":      1,
    "geopolitical":  3,
    "audusd":        None,
    "audusdRate":    None,
}

# Load previous run to carry over ATH and manual fields
stored_ath = 0.0
stored_aud = 0.0
try:
    with open('data.json', 'r') as f:
        prev = json.load(f)
        stored_ath           = float(prev.get('spxATH') or 0)
        stored_aud           = float(prev.get('audusdRate') or 0)
        result['earnings']    = prev.get('earnings', 1)
        result['geopolitical']= prev.get('geopolitical', 3)
        print(f"  Loaded prev ATH: {stored_ath}")
except Exception as e:
    print(f"  No prev data.json: {e}")

# ── Alpha Vantage: ^GSPC (actual S&P 500 index) ───────────────────────────
if AV_KEY:
    try:
        r = requests.get(
            'https://www.alphavantage.co/query',
            params={'function':'GLOBAL_QUOTE','symbol':'^GSPC','apikey':AV_KEY},
            timeout=15
        )
        d = r.json()
        print(f"  AV ^GSPC response keys: {list(d.keys())}")
        q = d.get('Global Quote', {})
        print(f"  AV ^GSPC quote: {q}")
        
        if q.get('05. price'):
            current = float(q['05. price'])
            # Sanity check - SPX should be between 3000 and 12000
            if 3000 <= current <= 12000:
                ath = max(stored_ath, current)
                result['spxCurrent'] = round(current, 2)
                result['spxATH']     = round(ath, 2)
                result['spxDrop']    = round(max(0,(ath-current)/ath*100), 2)
                print(f"  SPX: {current} | ATH: {ath} | Drop: {result['spxDrop']}%")
            else:
                result['errors'].append(f'AV ^GSPC: value {current} out of expected range 3000-12000')
                print(f"  AV ^GSPC out of range: {current}")
        elif 'Information' in d:
            result['errors'].append(f"AV ^GSPC: {d['Information'][:80]}")
            print(f"  AV limit: {d['Information'][:80]}")
        else:
            result['errors'].append(f'AV ^GSPC: no price in response')
            print(f"  AV ^GSPC no price. Full response: {d}")
    except Exception as e:
        result['errors'].append(f'AV ^GSPC: {e}')
        print(f"  AV ^GSPC error: {e}")

    # ── Alpha Vantage: ^VIX ───────────────────────────────────────────────
    try:
        r = requests.get(
            'https://www.alphavantage.co/query',
            params={'function':'GLOBAL_QUOTE','symbol':'^VIX','apikey':AV_KEY},
            timeout=15
        )
        d = r.json()
        q = d.get('Global Quote', {})
        print(f"  AV ^VIX quote: {q.get('05. price','no price')}")
        
        if q.get('05. price'):
            vix = float(q['05. price'])
            # VIX should be between 5 and 150
            if 5 <= vix <= 150:
                result['vix'] = round(vix, 2)
                print(f"  VIX: {vix}")
            else:
                result['errors'].append(f'AV ^VIX: value {vix} out of range')
        elif 'Information' in d:
            result['errors'].append(f"AV ^VIX: rate limit")
    except Exception as e:
        result['errors'].append(f'AV ^VIX: {e}')
        print(f"  AV ^VIX error: {e}")
else:
    result['errors'].append('AV_API_KEY not set')
    print("  No AV key")

# ── FRED helper ───────────────────────────────────────────────────────────
def fred_get(series_id, limit=30):
    start = (datetime.now()-timedelta(days=max(limit*3,400))).strftime('%Y-%m-%d')
    end   = datetime.now().strftime('%Y-%m-%d')
    r = requests.get('https://api.stlouisfed.org/fred/series/observations', params={
        'series_id':series_id,'api_key':FRED_KEY,'file_type':'json',
        'sort_order':'desc','observation_start':start,
        'observation_end':end,'limit':limit
    }, timeout=15)
    r.raise_for_status()
    d = r.json()
    if 'error_message' in d:
        raise Exception(d['error_message'])
    obs = [o for o in d.get('observations',[]) if o['value'] not in ('.','')]
    print(f"  FRED {series_id}: {len(obs)} obs, latest={obs[0]['value'] if obs else 'none'}")
    return obs

if FRED_KEY:
    # CPI
    try:
        obs = fred_get('CPIAUCSL', 14)
        if len(obs) >= 13:
            result['inflation'] = round((float(obs[0]['value'])-float(obs[12]['value']))/float(obs[12]['value'])*100, 2)
    except Exception as e:
        result['errors'].append(f'CPI: {e}')

    # 10Y Treasury
    try:
        obs = fred_get('DGS10', 30)
        vals = [float(o['value']) for o in obs]
        if len(vals) >= 20:
            result['treasuryYield'] = round(vals[0], 3)
            recent = sum(vals[:5])/5
            older  = sum(vals[15:20])/5
            result['treasuryTrend'] = 2 if recent>older+0.05 else (0 if recent<older-0.05 else 1)
    except Exception as e:
        result['errors'].append(f'10Y: {e}')

    # HY Spread
    try:
        obs = fred_get('BAMLH0A0HYM2', 5)
        if obs:
            result['creditSpread'] = round(float(obs[0]['value'])*100)
    except Exception as e:
        result['errors'].append(f'HY: {e}')

    # Fed Funds
    try:
        obs = fred_get('FEDFUNDS', 6)
        if len(obs) >= 2:
            latest = float(obs[0]['value'])
            old    = float(obs[-1]['value'])
            result['fedRate']   = round(latest, 3)
            result['fedPolicy'] = 0 if latest<old-0.1 else (2 if latest>old+0.1 else 1)
    except Exception as e:
        result['errors'].append(f'Fed: {e}')
else:
    result['errors'].append('FRED_API_KEY not set')

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

# ── Write ─────────────────────────────────────────────────────────────────
fetched = [k for k in ['spxDrop','vix','creditSpread','inflation',
                        'treasuryTrend','fedPolicy','audusd'] if result[k] is not None]
result['fetchedCount']      = len(fetched)
result['fetchedIndicators'] = fetched

with open('data.json','w') as f:
    json.dump(result, f, indent=2)

print(f"\n✓ {result['fetchedAt']}")
print(f"  SPX:    {result['spxCurrent']} (ATH {result['spxATH']}, -{result['spxDrop']}%)")
print(f"  VIX:    {result['vix']}")
print(f"  CPI:    {result['inflation']}%")
print(f"  10Y:    {result['treasuryYield']}% trend={result['treasuryTrend']}")
print(f"  HY:     {result['creditSpread']}bps")
print(f"  Fed:    {result['fedRate']}% dir={result['fedPolicy']}")
print(f"  AUD:    {result['audusdRate']}")
print(f"  Errors: {result['errors']}")
