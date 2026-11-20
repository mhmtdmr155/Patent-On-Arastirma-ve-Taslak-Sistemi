from pathlib import Path
import re
import html

for pub in ["US8849461B2", "US9241451B2", "US10716269B2", "US11064664B2"]:
    text = Path(f"data/raw/{pub}.html").read_text(encoding="utf-8")
    app_m = re.search(r'itemprop=["\']applicationNumber["\'][^>]*>([^<]+)<', text)
    if not app_m:
        app_m = re.search(r'data-application-number=["\']([^"\']+)["\']', text)
    app = app_m.group(1).strip() if app_m else "?"
    
    # Get cross-reference text
    desc_sec = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', text, re.I | re.S)
    raw_desc = desc_sec.group(1) if desc_sec else text
    clean_desc = " ".join(html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc[:2500])).split())
    
    # Extract continuation statement
    m = re.search(r'(This application is a continuation.*?)(?:TECHNICAL FIELD|BACKGROUND|FIELD OF|SUMMARY|\Z)', clean_desc, re.I)
    stmt = m.group(1) if m else clean_desc[:300]
    print(f"=== {pub} (App: {app}) ===")
    print("  Statement:", stmt[:350])
    print()
