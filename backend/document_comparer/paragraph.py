"""
Module for paragraph class
"""

from dataclasses import field, dataclass
from typing import Any


@dataclass
class Paragraph:
    """
    Paragraph class with fields for text, id and other attributes
    """
    text: str
    id: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParagraphMatch:
    """
    Match of two paragraphs
    """
    ratio: float
    type: str
    position: int
    position_secondary: int
    paragraph_left: Paragraph | None
    paragraph_right: Paragraph | None
