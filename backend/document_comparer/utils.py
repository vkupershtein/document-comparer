"""
Module with utility functions
"""

from collections import defaultdict
from typing import Dict, Iterator, List, Set, Tuple
from bisect import bisect_left, bisect_right, insort

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
        pos_space_before = text.rfind(" ", 0, pos)
        pos_space_after = text.find(" ", pos+1)
        if (text[pos_space_before+1:pos].isnumeric() 
                or text[pos+1:pos_space_after].isnumeric()):
            continue
        if (pos-2 > 0 and
                text[pos-2] != " " and
                text[pos-2] != "." and
                len(text[:pos].split()) > 1):
            return text[:pos]
    return text


def align_start(start, text):
    """
    Align start of the string to non-empty character
    """
    while text[start:start+1] == ' ':
        start += 1
    return start


def align_end(end, text):
    """
    Align end of the string to non-empty character
    """
    while text[end:end+1] == ' ':
        end -= 1
    return end

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences
    """
    pos = 0
    sentences = []
    while pos < len(text):
        while text[pos:pos+1] == ' ':
            pos += 1
        sentence = recognize_first_sentence(text[pos:])
        pos += len(sentence)
        if text[pos:pos+1] == '.':
            pos += 1
            sentence = sentence.strip() + "."
        sentences.append(sentence)
    return sentences


def split_texts_into_sentences(texts: Iterator[str]) -> Iterator[List[str]]:
    """
    Split texts into sentences with simple algo
    """
    for text in texts:
        yield split_into_sentences(text)


def get_outer_positions(arr: List[int], left: int, right: int):
    """
    Get outer positions in the array for two numbers
    """
    pos_left = left
    pos_right = right
    i = bisect_right(arr, left)
    if 0 < i < len(arr):
        pos_left = arr[i-1]
    j = bisect_left(arr, right)
    if 0 < j < len(arr):
        pos_right = arr[j]
    return pos_left, pos_right


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
    result = np.empty_like(arr)  # type: ignore
    if num > 0:
        result[:num] = fill_value
        result[num:] = arr[:-num]
    elif num < 0:
        result[num:] = fill_value
        result[:num] = arr[-num:]
    else:
        result[:] = arr
    return result


def merge_sentences(sentences: List[str],
                    sent_positions: Set[int]) -> List[str]:
    """
    Merge previously split paragraph in less paragraphs
    if neighbouring sentences are in the set
    """
    result = []
    temp = []
    sign = True

    for i, sentence in enumerate(sentences):
        if i in sent_positions:
            if not sign and temp:
                result.append(temp)
                temp = []
            temp.append(sentence)
            sign = True
        else:
            if sign and temp:
                result.append(temp)
                temp = []
            temp.append(sentence)
            sign = False
    if temp:
        result.append(temp)
    return result


def filter_self_contained(levels):
    """
    Join arrays that are self contained
    """
    borders = []
    ranges = []

    for idx, level in enumerate(levels):
        min_val = min(level)
        max_val = max(level)

        # Binary search start and end positions in border list
        start_pos = bisect_right(borders, min_val)
        end_pos = bisect_right(borders, max_val)

        # CASE: Completely outside existing ranges
        if start_pos == end_pos and start_pos % 2 == 0:
            # Insert new border
            insort(borders, min_val)
            insort(borders, max_val)
            ranges.append((min_val, max_val, level, idx))

        # CASE: Fully contains one or more existing ranges
        elif start_pos % 2 == 0 and end_pos % 2 == 0:
            # Determine contained ranges
            to_remove = []
            for i, (low, high, _, _) in enumerate(ranges):
                if min_val <= low and max_val >= high:
                    to_remove.append(i)

            if to_remove:
                # Remove borders for contained intervals
                for i in sorted(to_remove, reverse=True):
                    low, high, _, _ = ranges[i]
                    borders.remove(low)
                    borders.remove(high)
                    del ranges[i]

                # Add current interval
                insort(borders, min_val)
                insort(borders, max_val)
                ranges.append((min_val, max_val, level, idx))

        # CASE: Overlaps partially — skip
        else:
            continue

    return [(_idx, lvl) for _, _, lvl, _idx in sorted(ranges, key=lambda x: x[0])]
