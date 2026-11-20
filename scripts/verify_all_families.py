from pathlib import Path
import re
import html
from collections import defaultdict

raw_dir = Path("data/raw")
patents = []

for p in sorted(raw_dir.glob("*.html")):
    pub = p.stem
    content = p.read_text(encoding="utf-8", errors="replace")
    
    # Title
    title_m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    title = html.unescape(title_m.group(1)).strip() if title_m else "UNKNOWN"

    # Family ID
    fam_m = re.search(r'<section\s+itemprop=["\']family["\'][^>]*>.*?<h2>ID=(\d+)</h2>', content, re.I | re.S)
    if not fam_m:
        fam_m = re.search(r'<h2>ID=(\d+)</h2>', content)
    family_id = fam_m.group(1).strip() if fam_m else "UNKNOWN"

    # Assignees
    ass_orig_m = re.findall(r'<dd[^>]*itemprop=["\']assigneeOriginal["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_curr_m = re.findall(r'<dd[^>]*itemprop=["\']assigneeCurrent["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_meta_m = re.search(r'<meta\s+name=["\']DC\.contributor["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']assignee["\']', content, re.I)
    
    orig_assignee = html.unescape(ass_orig_m[0]).strip() if ass_orig_m else (html.unescape(ass_meta_m.group(1)).strip() if ass_meta_m else "UNKNOWN")
    curr_assignee = html.unescape(ass_curr_m[0]).strip() if ass_curr_m else orig_assignee

    # Application number
    app_meta = re.search(r'itemprop=["\']applicationNumber["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if not app_meta:
        app_meta = re.search(r'<dd[^>]*itemprop=["\']applicationNumber["\'][^>]*>([^<]+)</dd>', content, re.I)
    if not app_meta:
        app_meta = re.search(r'data-application-number=["\']([^"\']+)["\']', content, re.I)
    app = html.unescape(app_meta.group(1)).strip() if app_meta else "UNKNOWN"

    patents.append({
        "pub": pub,
        "app": app,
        "family_id": family_id,
        "orig_assignee": orig_assignee,
        "curr_assignee": curr_assignee,
        "title": title
    })

by_fam = defaultdict(list)
for p in patents:
    by_fam[p["family_id"]].append(p["pub"])

print("=== Google Patents Family ID Groupings ===")
for fam_id, pubs in by_fam.items():
    if len(pubs) > 1:
        print(f"Family ID {fam_id} has {len(pubs)} members: {pubs}")
    else:
        print(f"Family ID {fam_id} singleton: {pubs[0]}")

print("\nTotal distinct Google Patents Family IDs:", len(by_fam))

