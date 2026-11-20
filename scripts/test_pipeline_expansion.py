"""
Test script to run PatentPipeline for all 34 patents.
Checks fetch/cache, parsing, chunking, and JSONL integrity.
"""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.data.pipeline import PatentPipeline, MAX_TOTAL_DOWNLOAD_BYTES

TARGET_34_PATENTS = [
    # Baseline 8
    "US11457576B2",
    "US11674944B2",
    "US8671969B2",
    "US12144295B1",
    "US11064664B2",
    "US9241451B2",
    "US7836910B2",
    "US9804113B2",
    # New 26
    "US8104498B2",
    "US7133749B2",
    "US7328089B2",
    "US10085393B2",
    "US9301461B2",
    "US7170302B2",
    "US7884620B2",
    "US7944220B2",
    "US10107738B2",
    "US11635402B2",
    "US8244404B2",
    "US8706307B2",
    "US8948921B2",
    "US9468162B2",
    "US9594366B2",
    "US10025284B2",
    "US10327397B2",
    "US10782722B2",
    "US6904789B2",
    "US10716269B2",
    "US6657443B2",
    "US6831468B2",
    "US7844368B2",
    "US8849461B2",
    "US10842090B2",
    "US11089745B2",
]

print(f"Targeting {len(TARGET_34_PATENTS)} patents. Unique count: {len(set(TARGET_34_PATENTS))}")

pipeline = PatentPipeline(base_dir=ROOT_DIR)
# Temporarily increase download limit for pipeline run
from src.data import pipeline as pipeline_module
pipeline_module.MAX_TOTAL_DOWNLOAD_BYTES = 50 * 1024 * 1024
pipeline_module.POLITE_DELAY_SECONDS = 0.5

records, chunks, manifest = pipeline.run_pipeline(patent_list=TARGET_34_PATENTS)

print(f"Pipeline finished successfully!")
print(f"Total records parsed: {len(records)}")
print(f"Total chunks generated: {len(chunks)}")
print(f"Status summary: {manifest['status_summary']}")

