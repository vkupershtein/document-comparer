"""
Module with utility functions
"""

from typing import List, Tuple

import numpy as np

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


def split_into_sentences(text) -> Tuple[List, List]:
    """
    Split text into sentences
    """
    pos = 0
    sentences = []
    positions = []
    while pos < len(text):
        sentence = recognize_first_sentence(text[pos:])
        positions.append(pos)
        pos += len(sentence)
        if text[pos:pos+1] == '.':
            pos += 1
            sentence = sentence.strip() + "."
        sentences.append(sentence)
    return sentences, positions


def min_max_scale(arr):
    """
    Scale array values between 0 and 1
    depending on minimum and maximum
    """
    arr = np.array(arr)
    arr = (arr - arr.min()) / (arr.max() - arr.min())
    return arr


def get_lower_values(arr, lower=0.1):
    """
    Scale array and get values lower the threshold
    """
    scaled_array = min_max_scale(arr)
    return np.where(scaled_array < lower, True, False)


def get_upper_values(arr, upper=0.9):
    """
    Scale array and get values upper the threshold
    """
    scaled_array = min_max_scale(arr)
    return np.where(scaled_array > upper, True, False)


def shift_elements(arr, num, fill_value):
    """
    Shift elements with predefined step and fill value
    """
    result = np.empty_like(arr)
    if num > 0:
        result[:num] = fill_value
        result[num:] = arr[:-num]
    elif num < 0:
        result[num:] = fill_value
        result[:num] = arr[-num:]
    else:
        result[:] = arr
    return result
