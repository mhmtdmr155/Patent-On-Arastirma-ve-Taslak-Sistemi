"""Audit raw HTML file sizes and hashes in data/raw/."""

import hashlib
import json
from pathlib import Path

raw_dir = Path("data/raw")
files = sorted(raw_dir.glob("*.html"))
total_disk_bytes = 0

print("=== Individual Raw HTML Files on Disk ===")
for f in files:
    size = f.stat().st_size
    total_disk_bytes += size
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    print(f"{f.name}: size={size}, sha256={sha}")

print(f"\nTotal bytes on disk: {total_disk_bytes}")

manifest_path = raw_dir / "raw_manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print("\n=== Entries in raw_manifest.json ===")
    m_total = 0
    for entry in manifest:
        s = entry.get("byte_size", 0)
        m_total += s
        print(f"{entry.get('publication_number')}: size={s}, sha256={entry.get('sha256')}")
    print(f"Total bytes in manifest: {m_total}")

