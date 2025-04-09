"""
Module for file processor protocol
"""

from typing import List, Protocol

from document_comparer.paragraph import Paragraph

class DocumentProcessor(Protocol):
    """
    Protocol for document processor
    that can extract paragraphs
    """
    def extract_paragraphs(self) -> List[Paragraph]:  ...    