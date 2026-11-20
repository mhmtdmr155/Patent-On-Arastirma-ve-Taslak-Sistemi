import json
import csv
from pathlib import Path

ROOT = Path.cwd()
patents_path = ROOT / "data" / "processed" / "patents.jsonl"
chunks_path = ROOT / "data" / "processed" / "chunks.jsonl"
queries_path = ROOT / "data" / "annotations" / "queries.csv"
queue_path = ROOT / "data" / "annotations" / "labeling_queue.csv"
raw_manifest_path = ROOT / "data" / "raw" / "raw_manifest.json"
data_manifest_path = ROOT / "data_manifest.json"

patents = [json.loads(l) for l in patents_path.read_text(encoding="utf-8").splitlines() if l.strip()]
chunks = [json.loads(l) for l in chunks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
queries = list(csv.DictReader(open(queries_path, encoding="utf-8")))
queue = list(csv.DictReader(open(queue_path, encoding="utf-8")))
raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
data_manifest = json.loads(data_manifest_path.read_text(encoding="utf-8"))

labeled_count = sum(1 for r in queue if r.get("human_relevance_label", "").strip())
eval_groups = set(r.get("evaluation_group_id", "") for r in queue)

print(f"Patents on disk: {len(patents)}")
print(f"Chunks on disk: {len(chunks)}")
print(f"Queries on disk: {len(queries)}")
print(f"Queue pairs on disk: {len(queue)}")
print(f"Human labels on disk: {labeled_count}")
print(f"Evaluation groups on disk: {len(eval_groups)}")
print(f"Raw manifest entries: {len(raw_manifest)}")
print(f"Data manifest total_patents: {data_manifest.get('total_patents')}")
print(f"Data manifest total_chunks: {data_manifest.get('total_chunks')}")

