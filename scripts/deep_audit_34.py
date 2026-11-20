from pathlib import Path
import re
import html
import json

raw_dir = Path("data/raw")

audit_records = []

for html_file in sorted(raw_dir.glob("*.html")):
    pub = html_file.stem
    content = html_file.read_text(encoding="utf-8", errors="replace")

    # Title
    title_m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    title = html.unescape(title_m.group(1)).strip() if title_m else "UNKNOWN"

    # Application number
    app_meta = re.search(r'itemprop=["\']applicationNumber["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if not app_meta:
        app_meta = re.search(r'<dd[^>]*itemprop=["\']applicationNumber["\'][^>]*>([^<]+)</dd>', content, re.I)
    if not app_meta:
        app_meta = re.search(r'data-application-number=["\']([^"\']+)["\']', content, re.I)
    app = html.unescape(app_meta.group(1)).strip() if app_meta else "UNKNOWN"

    # Assignees
    ass_orig_m = re.findall(r'<dd[^>]*itemprop=["\']assigneeOriginal["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_curr_m = re.findall(r'<dd[^>]*itemprop=["\']assigneeCurrent["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_meta_m = re.search(r'<meta\s+name=["\']DC\.contributor["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']assignee["\']', content, re.I)
    
    orig_assignee = html.unescape(ass_orig_m[0]).strip() if ass_orig_m else (html.unescape(ass_meta_m.group(1)).strip() if ass_meta_m else "UNKNOWN")
    curr_assignee = html.unescape(ass_curr_m[0]).strip() if ass_curr_m else orig_assignee

    # Family ID
    fam_m = re.search(r'<section\s+itemprop=["\']family["\'][^>]*>.*?<h2>ID=(\d+)</h2>', content, re.I | re.S)
    if not fam_m:
        fam_m = re.search(r'<h2>ID=(\d+)</h2>', content)
    family_id = fam_m.group(1).strip() if fam_m else "UNKNOWN"

    # Inventors
    inv_matches = re.findall(r'itemprop=["\']inventor["\'][^>]*>([^<]+)<', content, re.I)
    inventors = [html.unescape(inv.strip()) for inv in inv_matches if inv.strip()]

    # Priority / Continuation note
    desc_sec = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', content, re.I | re.S)
    raw_desc = desc_sec.group(1) if desc_sec else content
    clean_desc = " ".join(html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc[:3000])).split())

    cont_m = re.search(r'(This application (?:is a continuation|is a divisional|claims the benefit|claims priority).*?)(?:TECHNICAL FIELD|BACKGROUND|FIELD OF THE|SUMMARY|\Z)', clean_desc, re.I)
    cont_stmt = cont_m.group(1).strip() if cont_m else "None"

    audit_records.append({
        "publication_number": pub,
        "application_number": app,
        "title": title,
        "original_assignee": orig_assignee,
        "current_assignee": curr_assignee,
        "source_family_id": family_id,
        "inventors": inventors,
        "continuation_statement": cont_stmt[:250],
    })

print(f"Audited {len(audit_records)} patents.")
for r in audit_records:
    print(f"{r['publication_number']} | Fam:{r['source_family_id']} | Assignee:{r['original_assignee']} (Curr:{r['current_assignee']}) | Title:{r['title']}")
    if r['continuation_statement'] != "None":
        print(f"   Continuation: {r['continuation_statement'][:140]}")

