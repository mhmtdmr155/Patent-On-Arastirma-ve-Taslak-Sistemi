"""Patent Family, Classification, and Duplicate Resolution Module (PAT-0206, PAT-0207, PAT-0450-D01).

Manages genuine patent continuation relationships, priority lineages, family groupings,
and duplicate detection based strictly on documented source evidence to prevent
data leakage in downstream ML tasks.
"""

from typing import Any
from src.data.schema import PatentRecord


# Documented, strictly verified multi-patent family relationship lineages in active corpus
VERIFIED_PILOT_FAMILIES = {
    "FAMILY_DRESSELHAUS_MOISTURE_SENSOR": {
        "family_id": "FAM_US_DRESSELHAUS_SOIL_01",
        "description": "Soil moisture sensor and controller (Capacitance probe and valve interrupter)",
        "google_patents_family_id": "36615521",
        "assignee": "Rain Bird Corp",
        "members": ["US7836910B2", "US8104498B2", "US8671969B2"],
        "lineage_notes": (
            "US8671969B2 (App 13/336,709) is an explicit continuation of US Pat. No. 8,104,498, "
            "which is a continuation of US Pat. No. 7,836,910 (App 11/097,061, Dresselhaus et al.). "
            "All originate from common parent application Ser. No. 11/027,355 and share Google Patents family ID 36615521."
        ),
        "relationships": [
            ("US8104498B2", "US7836910B2", "continuation_of", "US8104498B2 (App 11/097,061) is a continuation of US7836910B2"),
            ("US7836910B2", "US8104498B2", "has_continuation", "US8104498B2 (App 11/097,061) is a continuation of US7836910B2"),
            ("US8671969B2", "US8104498B2", "continuation_of", "US8671969B2 (App 13/336,709) is a continuation of US8104498B2"),
            ("US8104498B2", "US8671969B2", "has_continuation", "US8671969B2 (App 13/336,709) is a continuation of US8104498B2"),
            ("US8671969B2", "US7836910B2", "family_member", "Shared parent application Ser. No. 11/027,355 and Google Patents family ID 36615521"),
            ("US7836910B2", "US8671969B2", "family_member", "Shared parent application Ser. No. 11/027,355 and Google Patents family ID 36615521"),
        ],
    },
    "FAMILY_IRRIGATION_CONTROL_WIRELESS": {
        "family_id": "FAM_US_IRR_WIRELESS_01",
        "description": "Methods and systems for irrigation control (Wireless monitoring nodes & server)",
        "google_patents_family_id": "41495413",
        "assignee": "Rain Bird Corp",
        "members": ["US8849461B2", "US9241451B2", "US10716269B2", "US11064664B2"],
        "lineage_notes": (
            "Direct continuous continuation lineage of Ersavas, Pekol & Bodur (Rain Bird Corp) "
            "originating from TR 2008/05998 and US 12/537,772: US8849461B2 (App 13/844,248) -> "
            "US9241451B2 (App 14/466,469) -> US10716269B2 (App 16/452,397 via US10362739) -> "
            "US11064664B2 (App 16/933,594)."
        ),
        "relationships": [
            ("US9241451B2", "US8849461B2", "continuation_of", "US9241451B2 (App 14/466,469) is a continuation of US8849461B2 (App 13/844,248)"),
            ("US8849461B2", "US9241451B2", "has_continuation", "US9241451B2 (App 14/466,469) is a continuation of US8849461B2 (App 13/844,248)"),
            ("US10716269B2", "US9241451B2", "continuation_lineage", "US10716269B2 (App 16/452,397) is a continuation of US10362739, which is a continuation of US9241451B2 (App 14/466,469)"),
            ("US9241451B2", "US10716269B2", "continuation_lineage", "US10716269B2 (App 16/452,397) is a continuation of US10362739, which is a continuation of US9241451B2 (App 14/466,469)"),
            ("US11064664B2", "US10716269B2", "continuation_of", "US11064664B2 (App 16/933,594) is a continuation of US10716269B2 (App 16/452,397)"),
            ("US10716269B2", "US11064664B2", "has_continuation", "US11064664B2 (App 16/933,594) is a continuation of US10716269B2 (App 16/452,397)"),
            ("US11064664B2", "US8849461B2", "family_member", "Common Ersavas wireless irrigation lineage and shared priority TR 2008/05998"),
            ("US8849461B2", "US11064664B2", "family_member", "Common Ersavas wireless irrigation lineage and shared priority TR 2008/05998"),
            ("US10716269B2", "US8849461B2", "family_member", "Common Ersavas wireless irrigation lineage and shared priority TR 2008/05998"),
            ("US8849461B2", "US10716269B2", "family_member", "Common Ersavas wireless irrigation lineage and shared priority TR 2008/05998"),
            ("US11064664B2", "US9241451B2", "family_member", "Common Ersavas wireless irrigation lineage and shared priority TR 2008/05998"),
            ("US9241451B2", "US11064664B2", "family_member", "Common Ersavas wireless irrigation lineage and shared priority TR 2008/05998"),
        ],
    },
    "FAMILY_ACCLIMA_TDR_MOISTURE": {
        "family_id": "FAM_US_ACCLIMA_TDR_01",
        "description": "Acclima TDR and impedance soil moisture and conductivity sensors",
        "google_patents_family_id": "25483224_31999113",
        "assignee": "Technical Development Consultants Inc",
        "members": ["US6657443B2", "US6831468B2"],
        "lineage_notes": (
            "US6831468B2 (App 10/659,645) is an explicit Continuation-In-Part of US Pat. No. 6,657,443 "
            "(App 09/945,528) to Anderson et al. for determining soil moisture content and conductivity."
        ),
        "relationships": [
            ("US6831468B2", "US6657443B2", "continuation_in_part_of", "US6831468B2 (App 10/659,645) is an explicit Continuation-In-Part of US6657443B2 (App 09/945,528)"),
            ("US6657443B2", "US6831468B2", "has_continuation_in_part", "US6831468B2 (App 10/659,645) is an explicit Continuation-In-Part of US6657443B2 (App 09/945,528)"),
        ],
    },
}


def populate_family_links(records: list[PatentRecord]) -> None:
    """
    Populate bidirectional family and continuation links on patent records
    based strictly on verified source textual evidence and priority lineage.
    Never creates synthetic or artificial links between unrelated portfolio patents.
    """
    record_map = {r.publication_number: r for r in records}

    # Clear any stale links first
    for r in records:
        r.family_links = []

    for fam_key, fam_info in VERIFIED_PILOT_FAMILIES.items():
        fam_id = fam_info["family_id"]
        for src_pub, tgt_pub, rel_type, evidence in fam_info.get("relationships", []):
            if src_pub in record_map and tgt_pub in record_map:
                src_rec = record_map[src_pub]
                existing_targets = [l["related_publication"] for l in src_rec.family_links]
                if tgt_pub not in existing_targets:
                    src_rec.family_links.append({
                        "family_id": fam_id,
                        "related_publication": tgt_pub,
                        "relationship_type": rel_type,
                        "source_evidence": evidence,
                    })


def check_for_duplicates(records: list[PatentRecord]) -> tuple[bool, list[str]]:
    """
    Check for duplicate publication numbers in the corpus.
    Returns (has_duplicates, list_of_duplicate_pub_numbers).
    """
    seen: set[str] = set()
    duplicates: list[str] = []

    for r in records:
        pub = r.publication_number.strip().upper()
        if pub in seen:
            duplicates.append(pub)
        else:
            seen.add(pub)

    return (len(duplicates) > 0, duplicates)


def separate_domain_and_patent_cpcs(
    patent_cpcs: list[str],
    domain_target_cpcs: list[str],
) -> dict[str, list[str]]:
    """
    Explicitly partition the patent's actual CPC codes from the domain target CPCs
    to prevent indiscriminate cross-contamination of metadata.
    """
    p_set = set(patent_cpcs)
    d_set = set(domain_target_cpcs)

    overlapping = sorted(list(p_set.intersection(d_set)))
    patent_specific = sorted(list(p_set.difference(d_set)))

    return {
        "patent_actual_cpcs": sorted(list(p_set)),
        "domain_target_cpcs": sorted(list(d_set)),
        "overlapping_cpcs": overlapping,
        "patent_specific_cpcs": patent_specific,
    }
