import hashlib
import os
from pathlib import Path
import tempfile
import zipfile

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
ZIP_PATH = ARTIFACTS_DIR / "PAT-0450-D01_code_audit.zip"

INCLUDED_FILES = [
    "app.py",
    "tools/labeling_app.py",
    "README.md",
    ".gitignore",
    "requirements.txt",
    "requirements-lock.txt",
    "sanitized_manifest.txt",
    "data_manifest.json",
    "data/annotations/queries.csv",
    "artifacts/patent_metadata_audit.csv",
    "docs/data_quality_report.md",
    "docs/source_feasibility.md",
    "docs/ml_relevance_design.md",
    "docs/ml_preparation_report.md",
    "docs/relevance_labeling_guide.md",
    "docs/labeling_user_guide.md",
]

INCLUDED_DIRS = [
    "src/ml",
    "src/retrieval",
    "src/data",
    "tests",
    "scripts",
]

FORBIDDEN_EXTENSIONS = {".pyc", ".tmp", ".log"}
FORBIDDEN_NAMES = {".env", "labeling_queue.csv", "patents.jsonl", "chunks.jsonl", "PAT-0450_code_audit.zip", "PAT-0404-D01_code_audit.zip"}
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".git", ".venv", "raw", "downloads", "processed_backup_d01"}


def should_include(rel_path_str: str) -> bool:
    p = Path(rel_path_str)
    for part in p.parts:
        if part in FORBIDDEN_PARTS:
            return False
    if p.name in FORBIDDEN_NAMES:
        return False
    if p.suffix in FORBIDDEN_EXTENSIONS:
        return False
    return True


def build_and_verify_audit_zip():
    files_to_pack = set()

    # Individual files
    for f in INCLUDED_FILES:
        target = ROOT_DIR / f
        if target.exists() and should_include(f):
            files_to_pack.add(f)
        elif not target.exists():
            print(f"[WARN] Expected file does not exist: {f}")

    # Directories
    for d in INCLUDED_DIRS:
        dir_path = ROOT_DIR / d
        if dir_path.exists():
            for root, _, files in os.walk(dir_path):
                for file_name in files:
                    full_p = Path(root) / file_name
                    rel_p = full_p.relative_to(ROOT_DIR).as_posix()
                    if should_include(rel_p):
                        files_to_pack.add(rel_p)

    sorted_files = sorted(list(files_to_pack))

    # Build zip
    with zipfile.ZipFile(ZIP_PATH, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_f in sorted_files:
            abs_f = ROOT_DIR / rel_f
            zf.write(abs_f, arcname=rel_f)

    # Calculate SHA256 and size
    size_bytes = ZIP_PATH.stat().st_size
    h = hashlib.sha256()
    with open(ZIP_PATH, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    sha256_hex = h.hexdigest()

    # Verify extraction
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            zf.extractall(tmp_dir)
            extracted_files = [p.relative_to(tmp_dir).as_posix() for p in Path(tmp_dir).rglob("*") if p.is_file()]

        # Ensure no forbidden files inside zip
        for ef in extracted_files:
            for forbidden in FORBIDDEN_NAMES:
                if forbidden in ef:
                    raise AssertionError(f"Forbidden file found in zip: {ef}")
            for forbidden_part in FORBIDDEN_PARTS:
                if forbidden_part in Path(ef).parts:
                    raise AssertionError(f"Forbidden path part found in zip: {ef}")

        assert len(extracted_files) == len(sorted_files), (
            f"Extracted count mismatch: {len(extracted_files)} vs {len(sorted_files)}"
        )

    print("======================================================================")
    print("AUDIT ZIP BUILD AND EXTRACTION VERIFICATION COMPLETE")
    print("======================================================================")
    print(f"PATH: {ZIP_PATH.as_posix()}")
    print(f"SIZE: {size_bytes} bytes ({size_bytes / 1024:.2f} KB)")
    print(f"SHA-256: {sha256_hex}")
    print(f"TOTAL FILES IN PACK: {len(sorted_files)}")
    print("VERIFICATION: Successfully extracted in isolated sandbox; 0 forbidden files.")
    print("======================================================================")
    print("\nFILES INCLUDED:")
    for f in sorted_files:
        print(f"  - {f}")


if __name__ == "__main__":
    build_and_verify_audit_zip()
