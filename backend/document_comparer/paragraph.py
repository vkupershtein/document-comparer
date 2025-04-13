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
