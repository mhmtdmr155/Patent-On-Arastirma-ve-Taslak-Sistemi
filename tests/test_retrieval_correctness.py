"""
Automated Retrieval Correctness, BM25 Engine, Tokenizer, and Parity Tests (PAT-0301-D01).
Tests T15 to T26: Verifies Unicode tokenization, BM25 direct calculation parity,
candidate deduplication, provenance completeness, and dynamic scoring behavior.
"""

import json
from pathlib import Path
import pytest
from rank_bm25 import BM25Okapi
from streamlit.testing.v1 import AppTest

from src.retrieval.bm25_engine import BM25SearchEngine, SearchResult
from src.retrieval.tokenizer import tokenize

ROOT_DIR = Path(__file__).resolve().parent.parent
CHUNKS_JSONL = ROOT_DIR / "data" / "processed" / "chunks.jsonl"
PATENTS_JSONL = ROOT_DIR / "data" / "processed" / "patents.jsonl"
APP_PATH = str(ROOT_DIR / "app.py")


def test_t15_unicode_tokenizer_no_fake_subtokens_for_turkish() -> None:
    """T15: Turkish words like 'sensörü' are preserved as whole tokens without spurious 'r' fragment."""
    tokens = tokenize("toprak nem sensörü", remove_stopwords=True)
    assert "r" not in tokens
    assert "sens" not in tokens
    assert tokens == ["toprak", "nem", "sensörü"]

    # When searched against English corpus, this produces 0 matches
    engine = BM25SearchEngine()
    results = engine.search("toprak nem sensörü", top_k_patents=20)
    assert len(results) == 0


def test_t16_tokenizer_preserves_technical_identifiers() -> None:
    """T16: Preserves CPC codes, circuit terms, voltage/capacitance units, and hyphenated terms."""
    query = "series RLC circuit with 5V supply, 100pF capacitor, in-ground sensor A01G25/16"
    tokens = tokenize(query, remove_stopwords=True)
    assert "rlc" in tokens
    assert "5v" in tokens
    assert "100pf" in tokens
    assert "in-ground" in tokens
    assert "a01g25/16" in tokens


def test_t17_direct_bm25_and_engine_search_parity() -> None:
    """T17: Direct BM25Okapi calculation from raw chunks strictly matches BM25SearchEngine output."""
    chunks = [json.loads(l) for l in CHUNKS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    patents = {p["publication_number"]: p for p in [json.loads(l) for l in PATENTS_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]}

    tokenized_corpus = [tokenize(c["text"], remove_stopwords=True) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    engine = BM25SearchEngine()

    test_queries = [
        "soil moisture sensor",
        "wireless irrigation controller",
        "series RLC circuit",
        "automatic irrigation",
        "remote monitoring gateway",
    ]

    for q in test_queries:
        tokens = tokenize(q, remove_stopwords=True)
        raw_scores = bm25.get_scores(tokens)

        # Direct max-pooling aggregation
        matches: dict[str, tuple[float, dict]] = {}
        for s, c in zip(raw_scores, chunks):
            if s > 0.0:
                pub = c["publication_number"]
                if pub not in matches or s > matches[pub][0]:
                    matches[pub] = (float(s), c)

        sorted_direct = sorted(matches.items(), key=lambda x: (-x[1][0], x[0]))
        engine_res = engine.search(q, top_k_patents=20)

        expected_count = min(len(sorted_direct), 20)
        assert expected_count == len(engine_res), f"Query '{q}' count mismatch"
        for idx, (pub, (score, chunk)) in enumerate(sorted_direct[:20]):
            r = engine_res[idx]
            assert r.publication_number == pub
            assert abs(r.bm25_score - round(score, 4)) < 1e-4
            assert r.title == patents[pub]["title"]


def test_t18_top_20_patent_deduplication() -> None:
    """T18: Returned patent candidates contain no duplicate publication numbers."""
    engine = BM25SearchEngine()
    results = engine.search("soil moisture sensor", top_k_patents=20)
    pubs = [r.publication_number for r in results]
    assert len(pubs) == len(set(pubs))
    assert len(pubs) <= 20


def test_t19_complete_provenance_and_attributions() -> None:
    """T19: Search results carry complete provenance fields and official URLs."""
    engine = BM25SearchEngine()
    results = engine.search("soil moisture sensor", top_k_patents=5)
    assert len(results) > 0

    for r in results:
        assert r.publication_number.startswith("US")
        assert r.application_number is not None
        assert r.title != ""
        assert r.bm25_score > 0.0
        assert r.best_passage != ""
        assert r.best_section in {"TITLE", "ABSTRACT", "BACKGROUND", "DESCRIPTION"}
        assert r.chunk_id != ""
        assert r.internal_chunk_locator != ""
        assert r.source_document_locator is not None
        assert r.source_url.startswith(f"https://patents.google.com/patent/{r.publication_number}")
        assert len(r.inventors) > 0
        assert r.total_matching_patents > 0


def test_t20_total_matching_vs_displayed_count_separation() -> None:
    """T20: Explicitly distinguishes total_matching_patents from top-k displayed results."""
    engine = BM25SearchEngine()
    results_top5 = engine.search("soil moisture sensor", top_k_patents=5)
    results_all = engine.search("soil moisture sensor", top_k_patents=50)

    assert len(results_top5) == 5
    assert len(results_all) >= 8
    assert results_top5[0].total_matching_patents == len(results_all)
    assert results_all[0].total_matching_patents == len(results_all)


def test_t21_deterministic_search_results() -> None:
    """T21: Re-running identical query on identical index yields bitwise identical results."""
    engine1 = BM25SearchEngine()
    engine2 = BM25SearchEngine()

    res1 = engine1.search("series RLC circuit", top_k_patents=5)
    res2 = engine2.search("series RLC circuit", top_k_patents=5)

    assert len(res1) == len(res2)
    for r1, r2 in zip(res1, res2):
        assert r1.publication_number == r2.publication_number
        assert r1.bm25_score == r2.bm25_score
        assert r1.chunk_id == r2.chunk_id
        assert r1.title == r2.title


def test_t22_dynamic_scoring_no_hardcoding() -> None:
    """T22: Different queries yield distinct scores, rankings, and best evidence chunks."""
    engine = BM25SearchEngine()

    res_sensor = engine.search("soil moisture sensor", top_k_patents=5)
    res_rlc = engine.search("series RLC circuit", top_k_patents=5)
    res_gw = engine.search("remote monitoring gateway", top_k_patents=5)

    # Top patents must differ according to technical relevance
    assert res_sensor[0].publication_number in {"US11674944B2", "US9301461B2", "US9804113B2", "US8104498B2"}
    assert res_rlc[0].publication_number == "US9804113B2"      # Resonant RLC sensor
    assert res_gw[0].publication_number in {"US11064664B2", "US10085393B2", "US9468162B2", "US9241451B2"}

    assert res_sensor[0].bm25_score != res_rlc[0].bm25_score
    assert res_rlc[0].bm25_score != res_gw[0].bm25_score


def test_t23_corrupt_files_raise_explicit_errors(tmp_path: Path) -> None:
    """T23: Missing or malformed corpus files are not silently ignored."""
    corrupt_chunks = tmp_path / "corrupt_chunks.jsonl"
    corrupt_chunks.write_text("NOT A VALID JSON LINE\n", encoding="utf-8")

    with pytest.raises(Exception):
        BM25SearchEngine(chunks_path=corrupt_chunks)


def test_t24_streamlit_app_displays_official_titles_and_inventors() -> None:
    """T24: Streamlit UI renders official titles and inventor names correctly in search results."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Enter valid invention to unlock search UI
    at.text_input[0].input("Akıllı Sulama Sistemi")
    at.text_area[0].input("Su tasarrufu problemi")
    at.text_area[1].input("Sensör tabanlı vana kontrolü")
    at.text_area[2].input("Nem sensörü, Vana")
    at.text_area[3].input("Sensör okunur, vana tetiklenir")
    at.button[0].click().run()

    # Search for moisture sensor
    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("soil moisture sensor")

    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    results = at.session_state["search_results"]
    assert len(results) == 5

    # Verify top results have official titles and inventors
    for r in results:
        assert r["title"] != ""
        assert len(r["inventors"]) > 0

    # Verify erroneous titles are not present anywhere in page text
    for bad_title in [
        "Soil moisture sensor with integrated temperature sensing",
        "Cloud-based irrigation management system",
        "Soil moisture sensor using resonant frequency measurement",
    ]:
        assert not any(bad_title in m.value for m in at.markdown)


def test_t25_invention_change_clears_search_state() -> None:
    """T25: Modifying and saving the invention resets search_results and current_query."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 1. First invention
    at.text_input[0].input("Buluş A")
    at.text_area[0].input("Problem A")
    at.text_area[1].input("Çözüm A")
    at.text_area[2].input("Bileşen A")
    at.text_area[3].input("Adım A")
    at.button[0].click().run()

    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("soil moisture sensor")
    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    assert len(at.session_state["search_results"]) > 0
    assert at.session_state["current_query"] == "soil moisture sensor"

    # 2. Modify invention
    at.text_input[0].input("Buluş B (Değiştirildi)")
    at.button[0].click().run()

    assert at.session_state["search_results"] == []
    assert at.session_state["current_query"] == ""


def test_t26_ml_annotation_files_and_zero_synthetic_labels() -> None:
    """T26: Validates queries.csv and labeling_queue.csv; ensures 0 automated fake labels."""
    import csv
    queries_path = ROOT_DIR / "data" / "annotations" / "queries.csv"
    queue_path = ROOT_DIR / "data" / "annotations" / "labeling_queue.csv"
    ml_design_path = ROOT_DIR / "docs" / "ml_relevance_design.md"
    guide_path = ROOT_DIR / "docs" / "relevance_labeling_guide.md"

    assert queries_path.exists()
    assert queue_path.exists()
    assert ml_design_path.exists()
    assert guide_path.exists()

    with open(queries_path, mode="r", encoding="utf-8") as f:
        queries = list(csv.DictReader(f))
    assert len(queries) == 20
    assert any(q["query_id"] == "Q20" and q["source_type"] == "Negative Control" for q in queries)

    with open(queue_path, mode="r", encoding="utf-8") as f:
        queue = list(csv.DictReader(f))
    assert len(queue) >= 160

    # Ensure labels have valid format and metadata consistency
    eval_groups = set()
    for item in queue:
        assert item["human_relevance_label"] in {"", "0", "1", "2"}, f"Invalid label value: {item['human_relevance_label']}"
        if item["human_relevance_label"] != "":
            assert item["review_status"] == "REVIEWED", f"Reviewed pair {item['pair_id']} must have REVIEWED status"
            assert item["reviewer_id"] != ""
            assert item["reviewed_at"] != ""
        else:
            assert item["review_status"] == "PENDING_HUMAN_REVIEW"
        assert item["pair_id"] != ""
        eval_groups.add(item["evaluation_group_id"])

    assert len(eval_groups) >= 6
    assert "FAM_US_IRR_WIRELESS_01" in eval_groups
    assert "FAM_US_DRESSELHAUS_SOIL_01" in eval_groups
    assert "SINGLETON_US11457576B2" in eval_groups
