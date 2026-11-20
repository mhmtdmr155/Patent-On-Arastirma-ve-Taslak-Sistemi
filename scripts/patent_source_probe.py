"""Patent Kaynak Yoklama, Metadata Çıkarım ve Pipeline Betiği (PAT-0201 Pilot).

Standart kütüphane tabanlı, güvenli ve hız sınırlarına uyumlu patent doğrulama ve
veri mühendisliği aracı.
"""

import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.error
import urllib.request

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Güvenlik ve Ağ Sınırları (PAT-0201)
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024  # 2 MB tekil indirme sınırı
MAX_TOTAL_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB toplam indirme sınırı
REQUEST_TIMEOUT_SECONDS = 15
POLITE_DELAY_SECONDS = 1.0

PILOT_PATENTS = [
    "US11457576B2",
    "US11674944B2",
    "US8671969B2",
    "US12144295B1",
    "US11064664B2",
    "US9241451B2",
    "US7836910B2",
    "US9804113B2",
]


def fetch_patent_html(publication_number: str) -> tuple[bool, str, dict[str, str]]:
    """
    Belirtilen yayın numarasına ait kamuya açık patent sayfasını çeker.
    Maksimum 2 MB boyut sınırına ve zaman aşımına uyar.
    """
    clean_pub = publication_number.strip().upper().replace(" ", "").replace("/", "").replace(",", "")
    url = f"https://patents.google.com/patent/{clean_pub}/en"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                return False, f"Boyut sınırı aşıldı ({content_length} bayt > 2 MB)", {"url": url}

            raw_bytes = resp.read(MAX_DOWNLOAD_BYTES + 1)
            if len(raw_bytes) > MAX_DOWNLOAD_BYTES:
                return False, f"Boyut sınırı aşıldı (> {MAX_DOWNLOAD_BYTES} bayt, kesilme riski)", {"url": url}

            encoding = resp.headers.get_content_charset() or "utf-8"
            html_text = raw_bytes.decode(encoding, errors="replace")
            return True, html_text, {"url": url, "bytes_read": str(len(raw_bytes))}
    except urllib.error.HTTPError as e:
        return False, f"HTTP Hatası {e.code}: {e.reason}", {"url": url}
    except urllib.error.URLError as e:
        return False, f"Ağ Bağlantı Hatası: {e.reason}", {"url": url}
    except Exception as e:
        return False, f"Beklenmeyen Hata: {str(e)}", {"url": url}


def parse_patent_metadata(html_content: str, publication_number: str, source_url: str) -> dict[str, Any]:
    """
    Çekilen HTML içeriğinden patent metadata alanlarını güvenle ayrıştırır.
    Bilinmeyen veya bulunamayan alanlar NULL (None) olarak bırakılır.
    Resmi abstract metnini kaynaktan birebir (verbatim) alır, LLM ile yeniden yazmaz.
    """
    record: dict[str, Any] = {
        "source_name": "Google Patents Public HTML Mirror",
        "source_url": source_url,
        "publication_number": publication_number,
        "application_number": None,
        "grant_number": None,
        "title": None,
        "filing_date": None,
        "publication_date": None,
        "abstract": None,
        "technical_summary": None,
        "description_available": False,
        "background_available": False,
        "cpc_codes": [],
        "ipc_codes": [],
        "document_language": "en",
        "technical_domain": "Smart Irrigation and Soil Moisture Monitoring",
        "retrieved_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "verification_status": "FAILED",
        "missing_fields": [],
    }

    # 1. Başlık (DC.title)
    title_match = re.search(r'<meta\s+name=["\']DC\.title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    if title_match:
        raw_title = html.unescape(title_match.group(1)).strip()
        record["title"] = " ".join(raw_title.split())
    else:
        record["missing_fields"].append("title")

    # 2. Başvuru Numarası (Application Number)
    app_meta = re.search(r'itemprop=["\']applicationNumber["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    if not app_meta:
        app_meta = re.search(r'<dd[^>]*itemprop=["\']applicationNumber["\'][^>]*>([^<]+)</dd>', html_content, re.IGNORECASE)

    if app_meta:
        record["application_number"] = app_meta.group(1).strip()
    else:
        app_alt = re.search(r'data-application-number=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if app_alt:
            record["application_number"] = app_alt.group(1).strip()
        else:
            app_text = re.search(r'Application\s+([A-Z]{2}\s*\d{2}/\d{3},?\d{3})', html_content, re.IGNORECASE)
            if app_text:
                record["application_number"] = app_text.group(1).strip().replace(" ", "")
            else:
                record["missing_fields"].append("application_number")

    # 3. Başvuru Tarihi (Filing Date / dateSubmitted)
    filing_match = re.search(r'<meta\s+name=["\']DC\.date["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']dateSubmitted["\']', html_content, re.IGNORECASE)
    if filing_match:
        record["filing_date"] = filing_match.group(1).strip()
    else:
        record["missing_fields"].append("filing_date")

    # 4. Yayın / Tescil Tarihi (Publication / Issue Date)
    issue_match = re.search(r'<meta\s+name=["\']DC\.date["\']\s+content=["\']([^"\']+)["\']\s+scheme=["\']issue["\']', html_content, re.IGNORECASE)
    if issue_match:
        record["publication_date"] = issue_match.group(1).strip()
        if publication_number.endswith("B1") or publication_number.endswith("B2"):
            record["grant_number"] = publication_number
    else:
        record["missing_fields"].append("publication_date")

    # 5. Özet (Abstract / DC.description - Kaynaktan Verbatim)
    abstract_match = re.search(r'<meta\s+name=["\']DC\.description["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    if abstract_match:
        raw_abstract = html.unescape(abstract_match.group(1)).strip()
        record["abstract"] = " ".join(raw_abstract.split())
    else:
        sec_abs = re.search(r'<section[^>]*itemprop=["\']abstract["\'][^>]*>(.*?)</section>', html_content, re.IGNORECASE | re.DOTALL)
        if sec_abs:
            clean_abs = re.sub(r'<[^>]+>', ' ', sec_abs.group(1))
            record["abstract"] = " ".join(html.unescape(clean_abs).split())
        else:
            record["missing_fields"].append("abstract")

    # 6. Açıklama ve Arka Plan Varlığı (Description / Background)
    if '<section itemprop="description"' in html_content or 'itemprop="description"' in html_content:
        record["description_available"] = True
    if 'background' in html_content.lower() and record["description_available"]:
        record["background_available"] = True

    # 7. CPC / IPC Sınıflandırma Kodları
    cpc_matches = re.findall(r'itemprop=["\']Code["\']>([A-H]\d{2}[A-Z]\d+/\d+)<', html_content)
    if cpc_matches:
        record["cpc_codes"] = list(dict.fromkeys(cpc_matches))[:8]
    else:
        meta_cpc = re.findall(r'[A-H]\d{2}[A-Z]\s*\d+/\d+', html_content)
        if meta_cpc:
            record["cpc_codes"] = list(dict.fromkeys([c.replace(" ", "") for c in meta_cpc]))[:8]

    # Durum değerlendirmesi
    if record["title"] and record["publication_number"]:
        record["verification_status"] = "VERIFIED"
    else:
        record["verification_status"] = "FAILED"

    return record


def probe_single_patent(publication_number: str) -> dict[str, Any]:
    """Tek bir patent için indirme ve ayrıştırma işlemini uçtan uca yürütür."""
    clean_pub = publication_number.strip().upper().replace(" ", "").replace("/", "").replace(",", "")
    success, result_content, info = fetch_patent_html(clean_pub)

    if not success:
        return {
            "source_name": "Google Patents Public HTML Mirror",
            "source_url": info.get("url", ""),
            "publication_number": clean_pub,
            "application_number": None,
            "title": None,
            "verification_status": "FAILED",
            "error_message": result_content,
            "missing_fields": ["all"],
        }

    metadata = parse_patent_metadata(result_content, clean_pub, info.get("url", ""))
    return metadata


def probe_patent_batch(pub_list: list[str]) -> list[dict[str, Any]]:
    """Verilen patent listesini nezaket gecikmesiyle tarar."""
    results: list[dict[str, Any]] = []
    for pub in pub_list:
        record = probe_single_patent(pub)
        results.append(record)
        time.sleep(POLITE_DELAY_SECONDS)
    return results


def main():
    parser = argparse.ArgumentParser(description="Patent Kaynak Yoklama ve Veri Pipeline Aracı (PAT-0201)")
    parser.add_argument("--run-pipeline", action="store_true", help="Uçtan uca veri pipeline'ını çalıştır (data/processed/ üretir)")
    parser.add_argument("--patents", nargs="*", default=PILOT_PATENTS, help="Taranacak patent listesi")
    args = parser.parse_args()

    if args.run_pipeline:
        # Import pipeline dynamically
        from src.data.pipeline import PatentPipeline
        pipeline = PatentPipeline()
        records, chunks, manifest = pipeline.run_pipeline(args.patents)
        print(f"Pipeline tamamlandı: {len(records)} patent, {len(chunks)} chunk.")
    else:
        print(f"Yoklama başlatılıyor ({len(args.patents)} patent)...")
        results = probe_patent_batch(args.patents[:4])
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
