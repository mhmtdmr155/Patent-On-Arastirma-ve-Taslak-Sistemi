import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path(r"C:\Users\mehme\Desktop\Patent_Bitirm_Data_Backup")

def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def backup_data():
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    items_to_backup = [
        ROOT_DIR / "data" / "raw",
        ROOT_DIR / "data" / "processed",
        ROOT_DIR / "data_manifest.json",
    ]

    manifest = {
        "backup_date": "2026-11-20T16:47:00Z",
        "source_dir": str(ROOT_DIR),
        "backup_dir": str(BACKUP_DIR),
        "files": [],
        "total_files": 0,
        "total_bytes": 0,
    }

    # Backup data/raw
    raw_dest = BACKUP_DIR / "data" / "raw"
    raw_dest.mkdir(parents=True, exist_ok=True)
    for p in (ROOT_DIR / "data" / "raw").glob("*"):
        if p.is_file():
            dest_file = raw_dest / p.name
            shutil.copy2(p, dest_file)
            size = dest_file.stat().st_size
            sha = get_sha256(dest_file)
            manifest["files"].append({
                "rel_path": f"data/raw/{p.name}",
                "size_bytes": size,
                "sha256": sha
            })
            manifest["total_files"] += 1
            manifest["total_bytes"] += size

    # Backup data/processed
    proc_dest = BACKUP_DIR / "data" / "processed"
    proc_dest.mkdir(parents=True, exist_ok=True)
    for p in (ROOT_DIR / "data" / "processed").glob("*"):
        if p.is_file():
            dest_file = proc_dest / p.name
            shutil.copy2(p, dest_file)
            size = dest_file.stat().st_size
            sha = get_sha256(dest_file)
            manifest["files"].append({
                "rel_path": f"data/processed/{p.name}",
                "size_bytes": size,
                "sha256": sha
            })
            manifest["total_files"] += 1
            manifest["total_bytes"] += size

    # Backup data_manifest.json
    manifest_dest = BACKUP_DIR / "data_manifest.json"
    shutil.copy2(ROOT_DIR / "data_manifest.json", manifest_dest)
    size = manifest_dest.stat().st_size
    sha = get_sha256(manifest_dest)
    manifest["files"].append({
        "rel_path": "data_manifest.json",
        "size_bytes": size,
        "sha256": sha
    })
    manifest["total_files"] += 1
    manifest["total_bytes"] += size

    # Save backup manifest
    with open(BACKUP_DIR / "backup_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("======================================================================")
    print("CORPUS DATA BACKUP COMPLETED SUCCESSFULLY")
    print("======================================================================")
    print(f"Target Directory: {BACKUP_DIR}")
    print(f"Total Files Backed Up: {manifest['total_files']}")
    print(f"Total Bytes Backed Up: {manifest['total_bytes']} bytes ({manifest['total_bytes'] / (1024*1024):.2f} MB)")
    print("Backup Manifest: C:\\Users\\mehme\\Desktop\\Patent_Bitirm_Data_Backup\\backup_manifest.json")
    print("======================================================================")

if __name__ == "__main__":
    backup_data()
