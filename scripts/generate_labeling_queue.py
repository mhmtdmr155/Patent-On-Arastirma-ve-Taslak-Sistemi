"""
Generate Complete Human Relevance Labeling Queue from All Query-Patent Combinations (PAT-0404 & PAT-0404-D03).
Prepares pairs of (Query, Patent) across active corpus.
Includes both BM25 candidates (score > 0) and non-candidates (score = 0).
Assigns distinct evaluation_group_id to prevent singleton grouping leakage.
Preserves existing human annotations, reviewer IDs, review notes, and timestamps without data loss.
Safely retains historical annotations even if a patent or query is retired from the active pool.
Uses atomic file replacement (.tmp + os.fsync + os.replace) for guaranteed crash resilience.
"""

import csv
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.retrieval.bm25_engine import BM25SearchEngine

ROOT_DIR = Path(__file__).resolve().parent.parent
QUERIES_CSV = ROOT_DIR / "data" / "annotations" / "queries.csv"
PATENTS_JSONL = ROOT_DIR / "data" / "processed" / "patents.jsonl"
QUEUE_CSV = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"

# Known verified multi-patent family mapping for active corpus (PAT-0450-D01)
VERIFIED_FAMILIES = {
    # Dresselhaus soil moisture sensor continuation family (Rain Bird Corp)
    "US7836910B2": "FAM_US_DRESSELHAUS_SOIL_01",
    "US8104498B2": "FAM_US_DRESSELHAUS_SOIL_01",
    "US8671969B2": "FAM_US_DRESSELHAUS_SOIL_01",
    # Ersavas / Rain Bird wireless irrigation control continuation family
    "US8849461B2": "FAM_US_IRR_WIRELESS_01",
    "US9241451B2": "FAM_US_IRR_WIRELESS_01",
    "US10716269B2": "FAM_US_IRR_WIRELESS_01",
    "US11064664B2": "FAM_US_IRR_WIRELESS_01",
    # Acclima TDR moisture sensor CIP family
    "US6657443B2": "FAM_US_ACCLIMA_TDR_01",
    "US6831468B2": "FAM_US_ACCLIMA_TDR_01",
}


def get_evaluation_group_id(patent_record: dict) -> tuple[str, str]:
    """
    Returns (family_id, evaluation_group_id) for a patent record.
    Uses patent_record['family_id'] if available, then fallback to VERIFIED_FAMILIES or evaluation_group_id.
    Independent patents receive a unique SINGLETON_{pub} group to prevent
    spurious cluster leakage in GroupKFold.
    """
    pub = patent_record.get("publication_number", "").strip().upper()
    fam_id = str(patent_record.get("family_id") or "").strip()
    if not fam_id:
        eval_grp = str(patent_record.get("evaluation_group_id") or "").strip()
        if eval_grp and eval_grp.startswith("FAM_"):
            fam_id = eval_grp
        elif not eval_grp:
            fam_id = VERIFIED_FAMILIES.get(pub, "")

    if fam_id:
        return fam_id, fam_id
    return "", f"SINGLETON_{pub}"


def load_existing_annotations(queue_path: Path) -> dict[str, dict]:
    """
    Strictly load existing annotations from an existing labeling queue CSV.
    CRITICAL SAFETY RULES:
    1. Fails fast with RuntimeError if the file is unreadable or malformed.
    2. Rejects duplicate pair_ids.
    3. Rejects invalid label formats.
    4. Prevents any possibility of silent data loss.
    """
    existing_labels: dict[str, dict] = {}
    if not queue_path.exists():
        return existing_labels

    try:
        with open(queue_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required_cols = {"pair_id", "query_id", "publication_number", "human_relevance_label"}
            if reader.fieldnames is None or not required_cols.issubset(set(reader.fieldnames)):
                raise ValueError(f"Existing queue at {queue_path} is missing required columns: {required_cols}")

            for row_idx, row in enumerate(reader, start=2):
                pid = row.get("pair_id", "").strip()
                if not pid:
                    raise ValueError(f"Malformed row at line {row_idx} in {queue_path}: empty pair_id")

                if pid in existing_labels:
                    raise ValueError(f"Duplicate pair_id '{pid}' detected at line {row_idx} in {queue_path}")

                lbl = str(row.get("human_relevance_label", "")).strip()
                if lbl:
                    if lbl not in {"0", "1", "2"}:
                        raise ValueError(f"Invalid human_relevance_label '{lbl}' in row {row_idx} ({pid})")

                    existing_labels[pid] = {
                        "pair_id": pid,
                        "query_id": row.get("query_id", pid.split("_")[0]).strip(),
                        "query_text": row.get("query_text", "").strip(),
                        "publication_number": row.get("publication_number", pid.split("_", 1)[1] if "_" in pid else "").strip(),
                        "patent_title": row.get("patent_title", "").strip(),
                        "source_url": row.get("source_url", "").strip(),
                        "family_id": row.get("family_id", "").strip(),
                        "evaluation_group_id": row.get("evaluation_group_id", "").strip(),
                        "human_relevance_label": lbl,
                        "reviewer_id": row.get("reviewer_id", "").strip(),
                        "review_status": row.get("review_status", "REVIEWED").strip(),
                        "review_notes": row.get("review_notes", "").strip(),
                        "reviewed_at": row.get("reviewed_at", "").strip(),
                    }
    except Exception as err:
        raise RuntimeError(
            f"CRITICAL SAFETY STOP: Failed to read existing labeling queue at {queue_path}: {err}. "
            "Aborting queue regeneration to prevent accidental loss of human annotations!"
        ) from err

    return existing_labels


def build_candidate_queue(
    queries: list[dict],
    patents: list[dict],
    chunks: list[dict] | None = None,
    existing_labels: dict[str, dict] | None = None,
    abort_on_query_change: bool = True,
) -> list[dict]:
    """
    Build the list of candidate rows across all (query, patent) combinations.
    CRITICAL INTEGRITY GUARANTEES:
    1. Duplicate pair_ids are strictly rejected.
    2. If query_text changed for an already annotated pair:
       - If abort_on_query_change is True: raises RuntimeError to stop accidental migration.
       - If abort_on_query_change is False: preserves the label and adds an explanatory review note.
       - NEVER resets or wipes a human label silently!
    3. If an existing annotated pair belongs to a patent/query not in the active set:
       - Preserves the historical annotation in the output queue with an audit note.
       - NEVER drops historical human work silently!
    """
    existing_labels = existing_labels or {}
    engine = BM25SearchEngine()
    queue_rows = []
    seen_pair_ids = set()

    for q_entry in queries:
        qid = q_entry["query_id"]
        qtext = q_entry["query_text"]

        # Search BM25 for this query across current active patents
        bm25_matches = engine.search(qtext, top_k_patents=len(patents))
        match_map = {r.publication_number: (rank, r) for rank, r in enumerate(bm25_matches, start=1)}

        for p in patents:
            pub = p["publication_number"]
            pair_id = f"{qid}_{pub}"

            if pair_id in seen_pair_ids:
                raise ValueError(f"Duplicate pair_id generated: {pair_id}")
            seen_pair_ids.add(pair_id)

            fam_id, eval_group_id = get_evaluation_group_id(p)
            title = p.get("title", "")
            source_url = p.get("source_url", f"https://patents.google.com/patent/{pub}/en")

            if pub in match_map:
                rank, res = match_map[pub]
                bm25_candidate = True
                bm25_score_str = f"{res.bm25_score:.4f}"
                bm25_rank_str = str(rank)
                evidence_chunk_id = res.chunk_id
            else:
                bm25_candidate = False
                bm25_score_str = "0.0000"
                bm25_rank_str = ""
                evidence_chunk_id = ""

            # Check if previous human annotation exists for this pair
            prev_label = existing_labels.get(pair_id, {})
            prev_qtext = prev_label.get("query_text", "")
            has_human_label = bool(prev_label.get("human_relevance_label"))

            if has_human_label and prev_qtext and prev_qtext != qtext:
                if abort_on_query_change:
                    raise RuntimeError(
                        f"CRITICAL SAFETY STOP: Query text for '{qid}' changed from '{prev_qtext}' to '{qtext}', "
                        f"but existing human annotation '{prev_label['human_relevance_label']}' exists for pair '{pair_id}'. "
                        "Automatic label migration or wiping is forbidden to prevent data loss."
                    )
                # If explicit preservation is enabled:
                human_label = prev_label["human_relevance_label"]
                reviewer_id = prev_label.get("reviewer_id", "")
                review_status = prev_label.get("review_status", "REVIEWED")
                review_notes = (prev_label.get("review_notes", "") + f" [QUERY TEXT MODIFIED: was '{prev_qtext}']").strip()
                reviewed_at = prev_label.get("reviewed_at", "")
            else:
                human_label = prev_label.get("human_relevance_label", "")
                reviewer_id = prev_label.get("reviewer_id", "")
                review_status = (
                    "REVIEWED" if human_label
                    else prev_label.get("review_status", "PENDING_HUMAN_REVIEW")
                )
                review_notes = prev_label.get("review_notes", "")
                reviewed_at = prev_label.get("reviewed_at", "")

            queue_rows.append({
                "pair_id": pair_id,
                "query_id": qid,
                "query_text": qtext,
                "publication_number": pub,
                "patent_title": title,
                "source_url": source_url,
                "family_id": fam_id,
                "evaluation_group_id": eval_group_id,
                "bm25_score": bm25_score_str,
                "bm25_rank": bm25_rank_str,
                "bm25_candidate": bm25_candidate,
                "evidence_chunk_id": evidence_chunk_id,
                "human_relevance_label": human_label,
                "reviewer_id": reviewer_id,
                "review_status": review_status,
                "review_notes": review_notes,
                "reviewed_at": reviewed_at,
            })

    # RETENTION GUARANTEE: Retain historical annotations if any patent/query was retired from active set
    for pid, prev_data in existing_labels.items():
        if pid not in seen_pair_ids and prev_data.get("human_relevance_label"):
            seen_pair_ids.add(pid)
            retained_notes = (
                prev_data.get("review_notes", "")
                + " [RETAINED HISTORICAL ANNOTATION: patent or query retired from active corpus]"
            ).strip()
            queue_rows.append({
                "pair_id": pid,
                "query_id": prev_data.get("query_id", pid.split("_")[0]),
                "query_text": prev_data.get("query_text", ""),
                "publication_number": prev_data.get("publication_number", pid.split("_", 1)[1] if "_" in pid else ""),
                "patent_title": prev_data.get("patent_title", "Historical Patent"),
                "source_url": prev_data.get("source_url", ""),
                "family_id": prev_data.get("family_id", ""),
                "evaluation_group_id": prev_data.get("evaluation_group_id", ""),
                "bm25_score": "0.0000",
                "bm25_rank": "",
                "bm25_candidate": False,
                "evidence_chunk_id": "",
                "human_relevance_label": prev_data.get("human_relevance_label", ""),
                "reviewer_id": prev_data.get("reviewer_id", ""),
                "review_status": prev_data.get("review_status", "REVIEWED"),
                "review_notes": retained_notes,
                "reviewed_at": prev_data.get("reviewed_at", ""),
            })

    # Sort queue by query_id ascending, then bm25_score descending, then publication_number ascending
    queue_rows.sort(key=lambda r: (r["query_id"], -float(r["bm25_score"]), r["publication_number"]))
    return queue_rows


def generate_queue(
    queries_path: Path | None = None,
    patents_path: Path | None = None,
    queue_path: Path | None = None,
    abort_on_query_change: bool = True,
) -> int:
    """
    Generate or expand the annotation queue CSV across all (Query, Patent) combinations.
    Strictly preserves existing human annotations.
    Aborts immediately if existing queue cannot be read or validated, preventing data loss.
    Uses atomic file replacement (.tmp + os.replace) and fsync.
    """
    q_csv = queries_path or QUERIES_CSV
    p_jsonl = patents_path or PATENTS_JSONL
    out_csv = queue_path or QUEUE_CSV

    if not q_csv.exists():
        raise FileNotFoundError(f"Queries file not found at {q_csv}")
    if not p_jsonl.exists():
        raise FileNotFoundError(f"Patents file not found at {p_jsonl}")

    # 1. Strictly load existing annotations to preserve human work
    existing_labels = load_existing_annotations(out_csv)

    # 2. Load patents
    patents = []
    for line in p_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        patents.append(json.loads(line))

    patents.sort(key=lambda p: p["publication_number"])
    print(f"Loaded {len(patents)} patents from {p_jsonl}")

    # 3. Load queries
    queries = []
    with open(q_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append(row)

    queries.sort(key=lambda q: q["query_id"])
    print(f"Loaded {len(queries)} queries from {q_csv}")

    queue_rows = build_candidate_queue(
        queries=queries,
        patents=patents,
        existing_labels=existing_labels,
        abort_on_query_change=abort_on_query_change,
    )

    fieldnames = [
        "pair_id",
        "query_id",
        "query_text",
        "publication_number",
        "patent_title",
        "source_url",
        "family_id",
        "evaluation_group_id",
        "bm25_score",
        "bm25_rank",
        "bm25_candidate",
        "evidence_chunk_id",
        "human_relevance_label",
        "reviewer_id",
        "review_status",
        "review_notes",
        "reviewed_at",
    ]

    # 4. Atomic write using temporary file and fsync
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_csv.with_suffix(".tmp")

    try:
        with open(tmp_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(queue_rows)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (AttributeError, OSError):
                pass

        # Atomic in-place replacement
        os.replace(tmp_path, out_csv)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    print(f"Safely generated {len(queue_rows)} query-patent pairs in {out_csv}")
    print(f"Preserved {len(existing_labels)} existing human annotations.")
    return len(queue_rows)


if __name__ == "__main__":
    try:
        count = generate_queue()
        print(f"Done. Candidate pairs count: {count}")
    except Exception as exc:
        print(f"Error during queue generation: {exc}", file=sys.stderr)
        sys.exit(1)
