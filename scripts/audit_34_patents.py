import re
import html
import json
from pathlib import Path

ROOT = Path.cwd()
raw_dir = ROOT / "data" / "raw"
patents_jsonl = ROOT / "data" / "processed" / "patents.jsonl"

processed_map = {}
if patents_jsonl.exists():
    for line in patents_jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            processed_map[rec["publication_number"]] = rec

results = []

for html_file in sorted(raw_dir.glob("*.html")):
    pub = html_file.stem
    content = html_file.read_text(encoding="utf-8", errors="replace")

    # Title
    title_m = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    source_title = html.unescape(title_m.group(1)).strip() if title_m else "UNKNOWN"

    # Application number
    app_meta = re.search(r'itemprop=["\']applicationNumber["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if not app_meta:
        app_meta = re.search(r'<dd[^>]*itemprop=["\']applicationNumber["\'][^>]*>([^<]+)</dd>', content, re.I)
    raw_app = app_meta.group(1).strip() if app_meta else "UNKNOWN"

    # Assignees
    ass_orig = re.findall(r'<dd[^>]*itemprop=["\']assigneeOriginal["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_curr = re.findall(r'<dd[^>]*itemprop=["\']assigneeCurrent["\'][^>]*>([^<]+)</dd>', content, re.I)
    ass_meta = re.search(r'<meta\s+name=["\']DC\.contributor["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']assignee["\']', content, re.I)
    assignee_meta = html.unescape(ass_meta.group(1)).strip() if ass_meta else ""
    assignee_orig = [html.unescape(a.strip()) for a in ass_orig if a.strip()]
    assignee_curr = [html.unescape(a.strip()) for a in ass_curr if a.strip()]

    # Inventors
    inv_matches = re.findall(r'itemprop=["\']inventor["\'][^>]*>([^<]+)<', content, re.I)
    inventors = [html.unescape(inv.strip()) for inv in inv_matches if inv.strip()]

    # Family ID from Google Patents HTML
    # Check for family metadata or family link
    fam_m = re.search(r'itemprop=["\']familyId["\']\s+content=["\']([^"\']+)["\']', content, re.I)
    if not fam_m:
        fam_m = re.search(r'data-family-id=["\']([^"\']+)["\']', content, re.I)
    if not fam_m:
        fam_m = re.search(r'href=["\']/patent/[^/]+/en\?familyId=([^"\'&]+)["\']', content, re.I)
    if not fam_m:
        # Check in application priority links or JSON in page
        fam_m = re.search(r'"familyId":\s*["\']?(\d+)["\']?', content, re.I)

    source_family_id = fam_m.group(1).strip() if fam_m else "UNKNOWN"

    # Continuation text in background or description
    desc_start = ""
    desc_sec = re.search(r'<section[^>]*itemprop=["\']description["\'][^>]*>(.*?)</section>', content, re.I | re.S)
    if desc_sec:
        raw_desc = desc_sec.group(1)
        # Look for continuation or cross reference
        cross_ref = re.search(r'(?:CROSS-REFERENCE TO RELATED APPLICATIONS?|CROSS REFERENCE)(.*?)(?:TECHNICAL FIELD|BACKGROUND|SUMMARY)', raw_desc, re.I | re.S)
        if cross_ref:
            desc_start = " ".join(html.unescape(re.sub(r'<[^>]+>', ' ', cross_ref.group(1))).split())[:300]
        else:
            # First 250 characters of description
            desc_start = " ".join(html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc[:1000])).split())[:300]

    proc_rec = processed_map.get(pub, {})
    proc_title = proc_rec.get("title", "")
    proc_assignee = proc_rec.get("assignee", "")

    results.append({
        "publication_number": pub,
        "raw_app": raw_app,
        "source_title": source_title,
        "proc_title": proc_title,
        "assignee_meta": assignee_meta,
        "assignee_orig": assignee_orig,
        "assignee_curr": assignee_curr,
        "proc_assignee": proc_assignee,
        "inventors": inventors[:3],
        "source_family_id": source_family_id,
        "desc_start": desc_start,
    })

for r in results:
    print(f"=== {r['publication_number']} ===")
    print(f"  App: {r['raw_app']}")
    print(f"  Source Title: {r['source_title']}")
    print(f"  Proc Title:   {r['proc_title']}")
    print(f"  Title Match:  {r['source_title'] == r['proc_title']}")
    print(f"  Assignee Orig: {r['assignee_orig']} | Curr: {r['assignee_curr']} | Meta: {r['assignee_meta']}")
    print(f"  Proc Assignee: {r['proc_assignee']}")
    print(f"  Family ID: {r['source_family_id']}")
    print(f"  Continuation Note: {r['desc_start'][:120]}")

