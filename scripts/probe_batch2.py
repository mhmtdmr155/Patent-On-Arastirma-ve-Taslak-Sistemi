import urllib.request
import re
import html
import time

more_candidates = [
    # Rain Bird / Hunter / Toro / HydroPoint / Rachio / Acclima / Decagon
    'US8244404B2',  # Hunter modular controller
    'US8706307B2',  # Irrigation controller user interface
    'US8948921B2',  # ETwater / HydroPoint smart irrigation
    'US9468162B2',  # Rain Bird wireless network adapter
    'US9594366B2',  # Rachio smart sprinkler
    'US10025284B2', # Rain Bird code replacement
    'US10327397B2', # Rain Bird irrigation control systems
    'US10782722B2', # Hunter demand response irrigation
    'US6904789B2',  # Decagon moisture detection
    'US8013732B2',  # HydroPoint remote device monitoring
    'US9571582B2',  # HydroPoint remote irrigation
    'US10716269B2', # Ersavas continuation (wireless node irrigation)
    'US6657443B2',  # Acclima TDR soil moisture
    'US6831468B2',  # Acclima moisture content
    'US6442453B1',  # Toro irrigation controller
    'US7640081B2',  # Rain Bird ET irrigation
    'US7844368B2',  # HydroPoint weather ET
    'US8260464B2',  # Toro soil moisture sensor based irrigation
    'US8396609B2',  # Rain Bird flow monitoring
    'US8744633B2',  # Toro wireless soil sensor
    'US8849461B2',  # Hunter smart irrigation
    'US9020644B2',  # Toro precision irrigation
    'US9477232B2',  # HydroPoint flow monitoring
    'US9678523B2',  # Rain Bird central control
    'US9781888B2',  # Toro moisture sensor assembly
    'US10123489B2', # Toro soil moisture sensor assembly
    'US10349596B2', # Hunter flow sensing
    'US10568278B2', # Rain Bird smart irrigation scheduling
    'US10645880B2', # Hunter wireless valve control
    'US10842090B2', # Toro soil moisture probe
    'US11089745B2', # Rachio smart watering based on soil moisture
]

valid = []
for pub in more_candidates:
    url = f'https://patents.google.com/patent/{pub}/en'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read(150000).decode('utf-8', errors='ignore')
            m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', text, re.I)
            title = html.unescape(m.group(1)).strip() if m else 'NO TITLE'
            has_desc = 'itemprop="description"' in text or 'id="description"' in text
            print(f'OK: {pub} -> {title[:65]} | desc:{has_desc}')
            valid.append((pub, title))
            time.sleep(0.3)
    except Exception as e:
        print(f'FAIL: {pub} -> {e}')

print(f'\nTotal valid: {len(valid)} of {len(more_candidates)}')

