"""
Module for utility functions
that manipulate paragraphs
"""

from typing import List, Sequence

from document_comparer.paragraph import Paragraph


def join_paragraphs(paragraphs: Sequence[Paragraph|None]) -> Paragraph:
    """
    Join multiple paragraphs into one
    """
    assert len(paragraphs) > 0
    paragraph_id = paragraphs[0].id if paragraphs[0] else ""
    paragraph_payload = paragraphs[0].payload if paragraphs[0] else {}
    return Paragraph(text=" ".join([para.text for para in paragraphs if para]),
                        id=paragraph_id,
                        payload=paragraph_payload)


def sorted_paragraphs(paragraphs: List[Paragraph]) -> List[Paragraph]:
    """
    Sort paragraphs
    """
    return sorted(paragraphs,
                    key=lambda para: (para.payload["para_pos"], para.payload.get("sent_pos", 0)))
