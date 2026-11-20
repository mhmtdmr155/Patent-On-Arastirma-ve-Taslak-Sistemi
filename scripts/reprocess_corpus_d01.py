from pathlib import Path
import json
import sys

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.pipeline import PatentPipeline

pipeline = PatentPipeline()
records, chunks, manifest = pipeline.run_pipeline()

print(f"Reprocessed {len(records)} patents.")
print(f"Generated {len(chunks)} chunks.")
print(f"Status summary: {manifest['status_summary']}")

# Check evaluation groups across records
eval_groups = {r.evaluation_group_id for r in records}
print(f"Distinct evaluation groups: {len(eval_groups)}")

# Check family verification statuses
fam_statuses = {r.family_verification_status for r in records}
print(f"Family verification statuses: {fam_statuses}")

# Check source family IDs
source_fam_ids = {r.source_family_id for r in records}
print(f"Source family IDs count: {len(source_fam_ids)} (all non-empty: {all(bool(x) for x in source_fam_ids)})")

