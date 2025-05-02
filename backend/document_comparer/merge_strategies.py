"""
Module for different merge strategies
"""
from typing import Callable, List

from rapidfuzz import fuzz

from document_comparer.paragraph_utils import join_paragraphs
from document_comparer.paragraph import Paragraph, ParagraphMatch


def join_optimize_paragraph_matches(matches: List[ParagraphMatch],
                                    do_left_side: bool, do_right_side: bool) -> List[ParagraphMatch]:
    """
    Merge both sides considering ratio optimization
    """
    if do_left_side:
        updated_matches = _join_optimize_text_pairs_side(matches, side="left")
    else:
        updated_matches = matches
    if do_right_side:
        return _join_optimize_text_pairs_side(updated_matches, side="right")

    return updated_matches


def merge_matches_on_condition(matches: List[ParagraphMatch],
                               condition: Callable[[ParagraphMatch,
                                                    ParagraphMatch | None], bool]) -> List[ParagraphMatch]:
    """
    Merge on condition
    """
    merged: List[ParagraphMatch] = []
    prev_match = None
    buffer_matches: List[ParagraphMatch] = []
    for current_match in matches:
        if not condition(current_match, prev_match) and buffer_matches:
            merged.append(_join_matches(buffer_matches))
            buffer_matches = []
        buffer_matches.append(current_match)
        prev_match = current_match
    if buffer_matches:
        merged.append(_join_matches(buffer_matches))

    return merged


def unmatched_condition_no_id(current_match: ParagraphMatch,
                         prev_match: ParagraphMatch | None = None) -> bool:
    """
    Condition based on zero ratio and same type
    """
    if current_match.type not in ["removed", "new"]:
        return False

    if prev_match and prev_match.type != current_match.type:
        return False

    return True

def unmatched_condition_with_id(current_match: ParagraphMatch,
                               prev_match: ParagraphMatch | None = None) -> bool:
    """
    Condition based on ratio and paragraph ids
    """
    if current_match.type not in ["removed", "new"]:
        return False

    if prev_match and prev_match.type != current_match.type:
        return False

    if (prev_match and prev_match.paragraph_left
            and current_match.paragraph_left
            and prev_match.paragraph_left.id != current_match.paragraph_left.id):
        return False

    if (prev_match and prev_match.paragraph_right
            and current_match.paragraph_right
            and prev_match.paragraph_right.id != current_match.paragraph_right.id):
        return False

    return True

def matched_condition(current_match: ParagraphMatch,
                       prev_match: ParagraphMatch | None = None) -> bool:
    """
    Condition based on match of two paragraphs (equal or with changes) and same ids
    """
    if current_match.type not in ["equal", "changed"]:
        return False

    if prev_match and prev_match.type != current_match.type:
        return False

    if (prev_match and prev_match.paragraph_left
            and current_match.paragraph_left
            and prev_match.paragraph_left.id != current_match.paragraph_left.id):
        return False

    if (prev_match and prev_match.paragraph_right
            and current_match.paragraph_right
            and prev_match.paragraph_right.id != current_match.paragraph_right.id):
        return False

    return True


def _check_item_for_join(pairs: List[ParagraphMatch], position, side="left", direction=1):
    """
    Check previous or next item in the pairs list for join
    """
    assert side in ["left", "right"]
    assert direction in [-1, 1]
    orig_attr = "paragraph_left" if side == "left" else "paragraph_right"
    compare_attr = "paragraph_right" if side == "left" else "paragraph_left"
    end_pos = len(pairs) if direction > 0 else -1
    joined_para = Paragraph("", "")
    base_para: Paragraph = getattr(pairs[position], orig_attr)
    for idx in range(position+direction, end_pos, direction):
        para_orig: Paragraph | None = getattr(pairs[idx], orig_attr)
        if para_orig is None:
            continue
        para_compare: Paragraph | None = getattr(pairs[idx], compare_attr)
        if para_compare is None:
            return idx, 0, joined_para
        joined_text = base_para.text + " " + \
            para_orig.text if direction > 0 else para_orig.text + \
            " " + base_para.text
        updated_ratio = fuzz.ratio(joined_text, para_compare.text)
        return idx, updated_ratio - pairs[idx].ratio, Paragraph(id=para_compare.id,
                                                                text=joined_text,
                                                                payload=para_compare.payload)
    return -1, 0, joined_para


def _join_optimize_text_pairs_side(pairs, side="left") -> List[ParagraphMatch]:
    """
    Join one side with ratio optimization
    """
    updated_pairs = pairs[:]
    assert side in ["left", "right"]
    compare_attr = "paragraph_right" if side == "left" else "paragraph_left"
    indices_to_delete = []
    for pos, _ in enumerate(updated_pairs):
        if getattr(updated_pairs[pos], compare_attr) is not None:
            continue
        idx_next, ratio_diff_next, joined_para_next = _check_item_for_join(
            updated_pairs, pos, side, 1)
        idx_prev, ratio_diff_prev, joined_para_prev = _check_item_for_join(
            updated_pairs, pos, side, -1)
        if ratio_diff_next > 0 or ratio_diff_prev > 0:
            indices_to_delete.append(pos)
            if ratio_diff_next > 0 and ratio_diff_next > ratio_diff_prev:
                para_compare = getattr(updated_pairs[idx_next], compare_attr)
                para_left = joined_para_next if side == "left" else para_compare
                para_right = joined_para_next if side == "right" else para_compare
                updated_pairs[idx_next].ratio = updated_pairs[idx_next].ratio + \
                    ratio_diff_next
                updated_pairs[idx_next].paragraph_left = para_left
                updated_pairs[idx_next].paragraph_right = para_right
            elif ratio_diff_prev > 0 and ratio_diff_prev > ratio_diff_next:
                para_compare = getattr(updated_pairs[idx_prev], compare_attr)
                para_left = joined_para_prev if side == "left" else para_compare
                para_right = joined_para_prev if side == "right" else para_compare
                updated_pairs[idx_prev].ratio = updated_pairs[idx_next].ratio + \
                    ratio_diff_next
                updated_pairs[idx_prev].paragraph_left = para_left
                updated_pairs[idx_prev].paragraph_right = para_right
    for idx in reversed(indices_to_delete):
        updated_pairs.pop(idx)
    return updated_pairs


def _join_matches(matches: List[ParagraphMatch]) -> ParagraphMatch:
    """
    Join matches into one
    """
    assert len(matches) > 0
    paragraph_left = join_paragraphs(
        [match.paragraph_left for match in matches])
    paragraph_right = join_paragraphs(
        [match.paragraph_right for match in matches])
    if not paragraph_left.text:
        paragraph_left = None
    if not paragraph_right.text:
        paragraph_right = None

    return ParagraphMatch(ratio=matches[0].ratio,
                          type=matches[0].type,
                          position=matches[0].position,
                          position_secondary=matches[0].position_secondary,
                          paragraph_left=paragraph_left,
                          paragraph_right=paragraph_right)
