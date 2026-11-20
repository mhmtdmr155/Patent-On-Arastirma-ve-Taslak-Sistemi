from pathlib import Path
import re
import html
import json

raw_dir = Path("data/raw")
metadata_list = []

for p in sorted(raw_dir.glob("*.html")):
    pub = p.stem
    content = p.read_text(encoding="utf-8", errors="replace")

    # Title
    title_m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    title = html.unescape(title_m.group(1)).strip() if title_m else ""

    # Application number
    app_meta = re.search(r'itemprop=["\']applicationNumber["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if not app_meta:
        app_meta = re.search(r'<dd[^>]*itemprop=["\']applicationNumber["\'][^>]*>([^<]+)</dd>', content, re.I)
    if not app_meta:
        app_meta = re.search(r'data-application-number=["\']([^"\']+)["\']', content, re.I)
    app = html.unescape(app_meta.group(1)).strip() if app_meta else ""

    # Dates
    filing_m = re.search(r'<meta\s+name=["\']DC\.date["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']dateSubmitted["\']', content, re.I)
    filing_date = filing_m.group(1).strip() if filing_m else ""

    issue_m = re.search(r'<meta\s+name=["\']DC\.date["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']issue["\']', content, re.I)
    pub_date = issue_m.group(1).strip() if issue_m else ""

    # Assignees
    ass_orig_m = re.findall(r'<dd[^>]*itemprop=["\']assigneeOriginal["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_curr_m = re.findall(r'<dd[^>]*itemprop=["\']assigneeCurrent["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_meta_m = re.search(r'<meta\s+name=["\']DC\.contributor["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']assignee["\']', content, re.I)

    orig_assignee = html.unescape(ass_orig_m[0]).strip() if ass_orig_m else (html.unescape(ass_meta_m.group(1)).strip() if ass_meta_m else "")
    curr_assignee = html.unescape(ass_curr_m[0]).strip() if ass_curr_m else orig_assignee

    # Family ID
    fam_m = re.search(r'<section\s+itemprop=["\']family["\'][^>]*>.*?<h2>ID=(\d+)</h2>', content, re.I | re.S)
    if not fam_m:
        fam_m = re.search(r'<h2>ID=(\d+)</h2>', content)
    family_id = fam_m.group(1).strip() if fam_m else ""

    # Inventors
    inv_matches = re.findall(r'itemprop=["\']inventor["\'][^>]*>([^<]+)<', content, re.I)
    inventors = [html.unescape(inv.strip()) for inv in inv_matches if inv.strip()]

    # Continuation text
    desc_sec = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', content, re.I | re.S)
    raw_desc = desc_sec.group(1) if desc_sec else content
    clean_desc = " ".join(html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc[:3000])).split())

    cont_m = re.search(r'(This application (?:is a continuation|is a divisional|claims the benefit|claims priority).*?)(?:TECHNICAL FIELD|BACKGROUND|FIELD OF THE|SUMMARY|\Z)', clean_desc, re.I)
    cont_stmt = cont_m.group(1).strip() if cont_m else ""

    metadata_list.append({
        "pub": pub,
        "app": app,
        "filing_date": filing_date,
        "pub_date": pub_date,
        "title": title,
        "orig_assignee": orig_assignee,
        "curr_assignee": curr_assignee,
        "family_id": family_id,
        "inventors": inventors,
        "cont_stmt": cont_stmt,
    })

print(f"Total parsed: {len(metadata_list)}")
with open("artifacts/extracted_metadata_34.json", "w", encoding="utf-8") as f:
    json.dump(metadata_list, f, indent=2, ensure_ascii=False)
print("Saved artifacts/extracted_metadata_34.json")

