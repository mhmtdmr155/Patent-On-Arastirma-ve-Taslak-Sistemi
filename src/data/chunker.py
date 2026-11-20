"""Section-Aware Passage Chunking Module (PAT-0205).

Splits patent documents into deterministic, section-aware passage chunks
preserving provenance, section labeling, and paragraph/sentence boundaries.
"""

from typing import Optional
import re
from src.data.schema import PatentChunk, PatentRecord


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences cleanly using punctuation heuristics."""
    # Split on period/question/exclamation followed by space and capital letter or end of string
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(])', text)
    return [s.strip() for s in raw_sentences if s.strip()]


def _chunk_text_block(
    text: str,
    publication_number: str,
    section: str,
    source_url: str,
    start_order: int = 1,
    target_min_words: int = 100,
    target_max_words: int = 300,
) -> list[PatentChunk]:
    """
    Split a continuous text block into paragraph- and sentence-aware chunks
    targeting 100-300 words without mixing sections or patents.
    """
    chunks: list[PatentChunk] = []
    if not text or not text.strip():
        return chunks

    # Split into paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    current_sentences: list[str] = []
    current_word_count = 0
    current_char_start = 0
    chunk_order = start_order

    def emit_chunk(sentences: list[str], char_start: int) -> PatentChunk:
        chunk_text = " ".join(sentences)
        w_count = len(chunk_text.split())
        c_end = char_start + len(chunk_text)
        locator = f"{section.lower()}_p{chunk_order}"
        c_id = f"{publication_number}_{section}_{chunk_order:04d}"
        doc_locator = f"section={section.lower()}"
        return PatentChunk(
            chunk_id=c_id,
            publication_number=publication_number,
            section=section,
            text=chunk_text,
            source_url=source_url,
            internal_chunk_locator=locator,
            source_document_locator=doc_locator,
            source_locator=locator,
            chunk_order=chunk_order,
            word_count=w_count,
            character_start=char_start,
            character_end=c_end,
        )

    for p in paragraphs:
        p_sentences = _split_into_sentences(p)
        if not p_sentences:
            p_sentences = [p]

        for s in p_sentences:
            s_words = len(s.split())
            if current_word_count + s_words > target_max_words and current_sentences:
                # Emit current accumulated chunk
                chunk = emit_chunk(current_sentences, current_char_start)
                chunks.append(chunk)
                current_char_start += len(chunk.text) + 1
                chunk_order += 1
                current_sentences = [s]
                current_word_count = s_words
            else:
                current_sentences.append(s)
                current_word_count += s_words

    if current_sentences:
        chunk = emit_chunk(current_sentences, current_char_start)
        chunks.append(chunk)

    return chunks


def chunk_patent_record(
    record: PatentRecord,
    target_min_words: int = 100,
    target_max_words: int = 300,
) -> list[PatentChunk]:
    """
    Partition a full patent record into structured, section-aware chunks.
    Covers: TITLE, ABSTRACT, BACKGROUND (if present), DESCRIPTION.
    """
    chunks: list[PatentChunk] = []
    pub = record.publication_number
    url = record.source_url

    order = 1

    # 1. TITLE
    if record.title and record.title.strip():
        t_text = record.title.strip()
        t_chunk = PatentChunk(
            chunk_id=f"{pub}_TITLE_{order:04d}",
            publication_number=pub,
            section="TITLE",
            text=t_text,
            source_url=url,
            internal_chunk_locator="title_p1",
            source_document_locator="section=title",
            source_locator="title_p1",
            chunk_order=order,
            word_count=len(t_text.split()),
            character_start=0,
            character_end=len(t_text),
        )
        chunks.append(t_chunk)
        order += 1

    # 2. ABSTRACT (Verbatim from source)
    if record.abstract and record.abstract.strip():
        abs_chunks = _chunk_text_block(
            record.abstract.strip(),
            pub,
            "ABSTRACT",
            url,
            start_order=order,
            target_min_words=target_min_words,
            target_max_words=target_max_words,
        )
        chunks.extend(abs_chunks)
        order += len(abs_chunks)

    # 3. BACKGROUND (Only if genuinely present in the source)
    if record.background and record.background.strip():
        bg_chunks = _chunk_text_block(
            record.background.strip(),
            pub,
            "BACKGROUND",
            url,
            start_order=order,
            target_min_words=target_min_words,
            target_max_words=target_max_words,
        )
        chunks.extend(bg_chunks)
        order += len(bg_chunks)

    # 4. DESCRIPTION
    if record.description and record.description.strip():
        # Exclude background snippet if it was separated, or chunk the body
        desc_text = record.description.strip()
        if record.background and record.background.strip() in desc_text:
            # Avoid duplicate background in description if already cleanly separated
            desc_text = desc_text.replace(record.background.strip(), "").strip()

        desc_chunks = _chunk_text_block(
            desc_text,
            pub,
            "DESCRIPTION",
            url,
            start_order=order,
            target_min_words=target_min_words,
            target_max_words=target_max_words,
        )
        chunks.extend(desc_chunks)
        order += len(desc_chunks)

    return chunks

