import json
from pathlib import Path

with open("artifacts/extracted_metadata_34.json", "r", encoding="utf-8") as f:
    extracted = {r["pub"]: r for r in json.load(f)}

existing_patents = {}
with open("data/processed/patents.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        existing_patents[data["publication_number"]] = data

print(f"{'PUB':<14} | {'EXTRACTED TITLE':<35} | {'CURRENT JSONL TITLE':<35} | {'SAME?'}")
print("-" * 95)
for pub in sorted(extracted.keys()):
    ext_t = extracted[pub]["title"]
    cur_t = existing_patents.get(pub, {}).get("title", "MISSING")
    same = "YES" if ext_t == cur_t else "DIFF"
    print(f"{pub:<14} | {ext_t[:35]:<35} | {cur_t[:35]:<35} | {same}")

print("\n" + "="*95)
print(f"{'PUB':<14} | {'EXTRACTED ASSIGNEE (ORIG)':<30} | {'CURRENT JSONL ASSIGNEE':<30} | {'SAME?'}")
print("-" * 95)
for pub in sorted(extracted.keys()):
    ext_a = extracted[pub]["orig_assignee"]
    cur_a = existing_patents.get(pub, {}).get("assignee", "MISSING")
    same = "YES" if ext_a == cur_a else "DIFF"
    print(f"{pub:<14} | {ext_a[:30]:<30} | {cur_a[:30]:<30} | {same}")

