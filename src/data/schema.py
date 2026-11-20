"""Standard Patent Data Schema (PAT-0202).

Defines the unified schema for patent metadata, verbatim source texts,
patent families, and section-aware chunk representations.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class VerificationStatus(str, Enum):
    """Defined verification status levels based on strict evidence."""
    METADATA_VERIFIED = "METADATA_VERIFIED"
    ABSTRACT_VERIFIED = "ABSTRACT_VERIFIED"
    FULL_TEXT_VERIFIED = "FULL_TEXT_VERIFIED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass
class PatentRecord:
    """Canonical representation of a single patent document."""
    schema_version: str = "1.0"
    publication_number: str = ""
    application_number: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None  # MUST be verbatim from source
    technical_summary: Optional[str] = None  # Separate commentary, NEVER mixed with abstract
    description: Optional[str] = None
    background: Optional[str] = None
    technical_domain: str = "Smart Irrigation and Soil Moisture Monitoring"
    language: str = "en"
    cpc_codes: list[str] = field(default_factory=list)  # Patent's actual CPCs
    ipc_codes: list[str] = field(default_factory=list)  # Patent's actual IPCs
    inventors: list[str] = field(default_factory=list)  # Patent's verified inventors
    assignee: Optional[str] = None  # Official assignee / applicant
    filing_date: Optional[str] = None
    publication_date: Optional[str] = None
    source_name: str = "Google Patents Public HTML Mirror"
    source_url: str = ""
    retrieved_at: str = ""
    verification_status: str = VerificationStatus.PARTIAL.value
    missing_fields: list[str] = field(default_factory=list)
    family_links: list[dict[str, Any]] = field(default_factory=list)
    raw_source_sha256: str = ""
    source_family_id: Optional[str] = None
    family_verification_status: str = "UNVERIFIED"
    evaluation_group_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary."""
        return asdict(self)


@dataclass
class PatentChunk:
    """Passage chunk with strict provenance and section awareness (PAT-0205 / PAT-0301)."""
    chunk_id: str  # Deterministic: e.g. f"{publication_number}_{section}_{chunk_order:04d}"
    publication_number: str
    section: str  # "TITLE", "ABSTRACT", "BACKGROUND", "DESCRIPTION"
    text: str
    source_url: str
    internal_chunk_locator: str  # Project internal locator e.g. f"{section.lower()}_chunk_{chunk_order:04d}"
    source_document_locator: Optional[str] = None  # Official doc section e.g. "section#description"
    source_locator: str = ""  # Backward compatibility field
    chunk_order: int = 1
    word_count: int = 0
    character_start: int = 0
    character_end: int = 0

    def __post_init__(self):
        if not self.source_locator:
            self.source_locator = self.internal_chunk_locator

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass to dictionary."""
        return asdict(self)


def validate_patent_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate a patent record against the schema rules.
    Returns (is_valid, list of errors).
    """
    errors: list[str] = []

    pub = record.get("publication_number")
    if not pub or not isinstance(pub, str) or len(pub.strip()) < 5:
        errors.append("Invalid or missing publication_number")

    app = record.get("application_number")
    if not app:
        errors.append("Missing application_number")
    elif app == pub:
        errors.append("application_number must not equal publication_number")

    title = record.get("title")
    if not title or not isinstance(title, str) or len(title.strip()) < 3:
        errors.append("Invalid or missing title")

    status = record.get("verification_status")
    valid_statuses = {s.value for s in VerificationStatus}
    if status not in valid_statuses:
        errors.append(f"Invalid verification_status: {status}. Expected one of {valid_statuses}")

    # Integrity rules
    if status == VerificationStatus.FULL_TEXT_VERIFIED.value:
        desc = record.get("description")
        if not desc or len(desc.strip()) < 50:
            errors.append("FULL_TEXT_VERIFIED requires non-empty description (at least 50 characters)")
        abs_text = record.get("abstract")
        if not abs_text or len(abs_text.strip()) < 20:
            errors.append("FULL_TEXT_VERIFIED requires non-empty abstract")

    if status == VerificationStatus.ABSTRACT_VERIFIED.value:
        abs_text = record.get("abstract")
        if not abs_text or len(abs_text.strip()) < 20:
            errors.append("ABSTRACT_VERIFIED requires non-empty abstract")

    return (len(errors) == 0, errors)

