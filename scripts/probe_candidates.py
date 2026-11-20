import urllib.request
import re
import html
import time

candidates = [
    # Rain Bird / Dresselhaus family
    'US8104498B2',
    # Toro Company
    'US7133749B2',
    'US7328089B2',
    'US10085393B2',
    # Hunter Industries
    'US9301461B2',
    # Capacitive & TDR Sensors
    'US7170302B2',
    'US7884620B2',
    'US7944220B2',
    'US10107738B2',
    'US11635402B2',
    # Additional precision irrigation patents
    'US8205806B2',
    'US8928334B2',
    'US9089098B2',
    'US9504199B2',
    'US9743588B2',
    'US10299446B2',
    'US10426107B2',
    'US10506771B2',
    'US10729074B2',
    'US10966377B2',
    'US11039577B2',
    'US11172621B2',
    'US11252882B2',
    'US11363771B2',
    'US11484000B2',
    'US11533866B2',
    'US11547070B2',
    'US11716942B2',
]

print(f"Testing {len(candidates)} candidate patents...")
valid_patents = []
for pub in candidates:
    url = f"https://patents.google.com/patent/{pub}/en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read(150000).decode("utf-8", errors="ignore")
            m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', text, re.I)
            title = html.unescape(m.group(1)).strip() if m else "NO TITLE"
            has_desc = "itemprop=\"description\"" in text or "id=\"description\"" in text or "heading=\"description\"" in text.lower()
            print(f"OK: {pub} -> {title[:60]} | desc:{has_desc}")
            valid_patents.append((pub, title))
            time.sleep(0.5)
    except Exception as e:
        print(f"FAIL: {pub} -> {e}")

print(f"\nTotal valid: {len(valid_patents)} of {len(candidates)}")

