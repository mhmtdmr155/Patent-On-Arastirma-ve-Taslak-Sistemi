from pathlib import Path
import re
from collections import defaultdict

raw_dir = Path("data/raw")
family_ids = {}

for html_file in sorted(raw_dir.glob("*.html")):
    pub = html_file.stem
    content = html_file.read_text(encoding="utf-8", errors="replace")
    fam_m = re.search(r'<section\s+itemprop=["\']family["\'][^>]*>.*?<h2>ID=(\d+)</h2>', content, re.I | re.S)
    if fam_m:
        family_ids[pub] = fam_m.group(1)
    else:
        fam_m2 = re.search(r'<h2>ID=(\d+)</h2>', content)
        family_ids[pub] = fam_m2.group(1) if fam_m2 else "NOT_FOUND"

print(f"Extracted Google Patents Family IDs for {len(family_ids)} files:")
for pub, fid in sorted(family_ids.items()):
    print(f"  {pub}: {fid}")

grouped = defaultdict(list)
for pub, fid in family_ids.items():
    grouped[fid].append(pub)

print("\n=== MULTI-PATENT FAMILIES IN CORPUS ===")
for fid, members in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
    if len(members) > 1:
        print(f"  Family ID {fid} ({len(members)} patents): {members}")

print(f"\nTotal distinct Google Patents Family IDs: {len(grouped)}")
singletons = [members[0] for fid, members in grouped.items() if len(members) == 1]
print(f"Total singletons: {len(singletons)}")

