"""
Verify Direct BM25Okapi vs BM25SearchEngine across benchmark queries (PAT-0301-D01).
"""
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rank_bm25 import BM25Okapi
from src.retrieval.tokenizer import tokenize
from src.retrieval.bm25_engine import BM25SearchEngine

chunks_path = Path("data/processed/chunks.jsonl")
patents_path = Path("data/processed/patents.jsonl")

chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
patents = {p["publication_number"]: p for p in [json.loads(line) for line in patents_path.read_text(encoding="utf-8").splitlines() if line.strip()]}

tokenized_corpus = [tokenize(c["text"], remove_stopwords=True) for c in chunks]
bm25 = BM25Okapi(tokenized_corpus)

engine = BM25SearchEngine(chunks_path=chunks_path, patents_path=patents_path)

test_queries = [
    "soil moisture sensor",
    "wireless irrigation controller",
    "series RLC circuit",
    "automatic irrigation",
    "remote monitoring gateway",
    "quantum blockchain cryptocurrency",
    "",
    "toprak nem sensörü",
]

print(f"Loaded {len(chunks)} chunks and {len(patents)} patents.\n")

for q in test_queries:
    tokens = tokenize(q, remove_stopwords=True)
    raw_scores = bm25.get_scores(tokens) if tokens else []

    # Direct aggregation using max pooling
    matches = {}
    for s, c in zip(raw_scores, chunks):
        if s > 0.0:
            pub = c["publication_number"]
            if pub not in matches or s > matches[pub][0]:
                matches[pub] = (float(s), c)

    sorted_direct = sorted(matches.items(), key=lambda x: (-x[1][0], x[0]))

    engine_res = engine.search(q, top_k_patents=20)

    print(f"=== QUERY: '{q}' ===")
    print(f"Tokens: {tokens}")
    print(f"Total matching patents (score > 0): {len(sorted_direct)}")
    print(f"Engine candidate count: {len(engine_res)}")
    print("Top 5 Results:")
    for idx, (pub, (score, chunk)) in enumerate(sorted_direct[:5], start=1):
        p_title = patents[pub]["title"]
        print(f"  {idx}. {pub} | Score: {score:.6f} (rounded: {round(score, 4)}) | Chunk: {chunk['chunk_id']} | Sec: {chunk['section']} | Title: {p_title}")

    # Verify parity
    assert len(sorted_direct) == len(engine_res), f"Matching count mismatch for query '{q}': {len(sorted_direct)} vs {len(engine_res)}"
    for idx, r in enumerate(engine_res[:5]):
        expected_pub = sorted_direct[idx][0]
        expected_score = sorted_direct[idx][1][0]
        assert r.publication_number == expected_pub, f"Rank {idx+1} pub mismatch: {r.publication_number} vs {expected_pub}"
        assert abs(r.bm25_score - round(expected_score, 4)) < 1e-4, f"Score mismatch: {r.bm25_score} vs {expected_score}"
        assert r.title == patents[expected_pub]["title"], f"Title mismatch: {r.title} vs {patents[expected_pub]['title']}"

    print("Parity: 100% MATCH between Direct BM25Okapi and BM25SearchEngine.\n")
