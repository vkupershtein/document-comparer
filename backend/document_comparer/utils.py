"""
Module with utility functions
"""

from typing import Tuple

from document_comparer.constants import HEADING_PATTERN


def get_heading_info(text: str) -> Tuple[str, str]:
    """
    Extract heading info from text
    """
    m = HEADING_PATTERN.match(text)
    if m:
        head_number, head_text = m.groups()           
        return head_number, head_text 
    return "", ""