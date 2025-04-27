"""
Module for utility functions
that manipulate paragraphs
"""

from typing import List

from document_comparer.paragraph import Paragraph


def join_paragraphs(paragraphs: List[Paragraph]) -> Paragraph:
    """
    Join multiple paragraphs into one
    """
    assert len(paragraphs) > 0
    return Paragraph(text=" ".join([para.text for para in paragraphs]),
                        id=paragraphs[0].id,
                        payload=paragraphs[0].payload)


def sorted_paragraphs(paragraphs: List[Paragraph]) -> List[Paragraph]:
    """
    Sort paragraphs
    """
    return sorted(paragraphs,
                    key=lambda para: (para.payload["para_pos"], para.payload.get("sent_pos", 0)))
