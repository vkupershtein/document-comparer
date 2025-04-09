"""
Module for paragraph class
"""

from dataclasses import field, dataclass
from typing import Any

@dataclass
class Paragraph:
    text: str
    id: str
    payload: dict[str, Any] = field(default_factory=dict)

