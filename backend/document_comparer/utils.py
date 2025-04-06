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
        return head_number, recognize_first_sentence(head_text) 
    return "", ""

def recognize_first_sentence(text):
    """
    Recognize first sentence in a text
    """
    pos = 0
    while pos != -1:
        pos = text.find(".", pos+1)
        if pos-2 > 0 and text[pos-2] != " " and text[pos-2] != ".":
            return text[:pos]
    return text