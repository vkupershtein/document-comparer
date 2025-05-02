"""
Module to test merge strategies
"""

from document_comparer.merge_strategies import (
    join_optimize_paragraph_matches,
    merge_matches_on_condition,
    unmatched_condition_no_id,
    matched_condition,
    unmatched_condition_with_id
)
from document_comparer.paragraph import Paragraph, ParagraphMatch


def paragraph(text, _id):
    """
    Helper to create Paragraph.
    """
    return Paragraph(text=text, id=_id)


def match(ratio, type_, pos, pos2, left=None, right=None):
    """
    Helper to create ParagraphMatch.
    """
    return ParagraphMatch(ratio=ratio, type=type_, position=pos, position_secondary=pos2,
                          paragraph_left=left, paragraph_right=right)


def test_join_optimize_paragraph_matches_basic_merge():
    """
    Test join_optimize_paragraph_matches correctly merges orphaned left-side paragraphs
    when joining improves the ratio.
    """
    data = [
        match(40, "changed", 0, 0, paragraph(
            "hi world", "1"), paragraph("hello great", "1")),
        match(0, "removed", 1, -1, paragraph("great", "2"), None),
        match(0, "removed", 2, -1, paragraph("day", "3"), None),
        match(0, "removed", 3, -1, paragraph("to be alive", "4"), None),
        match(30, "changed", 4, 1, paragraph("short", "5"),
              paragraph("be alive longer text", "2")),
    ]
    updated = join_optimize_paragraph_matches(data, True, True)

    assert len(updated) == 3
    assert updated[1].paragraph_left
    assert updated[1].paragraph_left.text == "day"
    assert updated[1].paragraph_right is None


def test_merge_on_zero_ratio_condition():
    """
    Test merge_matches_on_condition merges consecutive zero-ratio 'removed' ParagraphMatches.
    """
    data = [
        match(0, "removed", 0, -1, paragraph("orphan", "1"), None),
        match(0, "removed", 1, -1, paragraph("is", "2"), None),
        match(0, "removed", 2, -1, paragraph("safe", "3"), None),
        match(80, "changed", 3, 1, paragraph(
            "ok", "4"), paragraph("fine", "3")),
    ]
    merged = merge_matches_on_condition(data, unmatched_condition_no_id)
    assert len(merged) == 2
    assert merged[0].paragraph_left
    assert merged[0].paragraph_left.text == "orphan is safe"
    assert merged[0].paragraph_right is None


def test_merge_no_id_condition_removed_and_new_alternating():
    """
    Test merge_matches_on_condition merges consecutive zero-ratio 'removed' ParagraphMatches.
    """
    data = [
        match(0, "new", 3, 1, None, paragraph("fine", "3")),
        match(0, "new", 4, 1, None, paragraph("wonderful", "4")),
        match(0, "removed", 0, -1, paragraph("orphan", "1"), None),
        match(0, "removed", 1, -1, paragraph("is", "2"), None),
        match(0, "removed", 2, -1, paragraph("safe", "3"), None)
    ]
    merged = merge_matches_on_condition(data, unmatched_condition_no_id)
    assert len(merged) == 2
    assert merged[0].paragraph_right
    assert merged[0].paragraph_right.text == "fine wonderful"
    assert merged[0].paragraph_left is None
    assert merged[1].paragraph_left
    assert merged[1].paragraph_left.text == "orphan is safe"
    assert merged[1].paragraph_right is None    


def test_merge_on_unmatched_with_id_condition():
    """
    Test merge_matches_on_condition does not merges 
    consecutive 'removed' ParagraphMatches, because they have different ids
    """
    data = [
        match(0, "removed", 0, -1, paragraph("orphan", "1"), None),
        match(0, "removed", 1, -1, paragraph("is", "2"), None),
        match(0, "removed", 2, -1, paragraph("safe", "3"), None),
        match(80, "changed", 3, 1, paragraph(
            "ok", "4"), paragraph("fine", "3")),
    ]
    merged = merge_matches_on_condition(data, unmatched_condition_with_id)
    assert len(merged) == 4
    assert merged[0].paragraph_left
    assert merged[0].paragraph_left.text == "orphan"
    assert merged[0].paragraph_right is None


def test_merge_on_equality_condition_same_ids():
    """
    Test merge_matches_on_condition merges equal matches with the same paragraph IDs.
    """
    data = [
        match(100, "equal", 0, 0, paragraph(
            "same", "1"), paragraph("same", "1")),
        match(100, "equal", 1, 1, paragraph(
            "text", "1"), paragraph("text", "1")),
        match(100, "equal", 2, 2, paragraph(
            "again", "1"), paragraph("again", "1")),
        match(80, "changed", 3, 3, paragraph(
            "other", "2"), paragraph("text", "2")),
    ]
    merged = merge_matches_on_condition(data, matched_condition)
    assert len(merged) == 2
    assert merged[0].paragraph_left
    assert merged[0].paragraph_right
    assert merged[0].paragraph_left.text == "same text again"
    assert merged[0].paragraph_right.text == "same text again"


def test_merge_on_equality_condition_different_ids():
    """
    Test that equality_condition does not merge equal matches with different paragraph IDs.
    """
    data = [
        match(100, "equal", 0, 0, paragraph("A", "1"), paragraph("A", "1")),
        match(100, "equal", 1, 1, paragraph("B", "2"), paragraph("B", "2")),
    ]
    merged = merge_matches_on_condition(data, matched_condition)
    assert len(merged) == 2
    assert merged[0].paragraph_left
    assert merged[1].paragraph_left
    assert merged[0].paragraph_left.text == "A"
    assert merged[1].paragraph_left.text == "B"


def test_merge_on_same_id_and_type_condition():
    """
    Test merging on same_id_and_type_condition when paragraph IDs and types match.
    """
    data = [
        match(60, "changed", 0, 0, paragraph("A", "1"), paragraph("A", "1")),
        match(55, "changed", 1, 1, paragraph("B", "1"), paragraph("B", "1")),
        match(70, "changed", 2, 2, paragraph("C", "1"), paragraph("C", "1")),
        match(90, "changed", 3, 3, paragraph("D", "2"), paragraph("D", "2")),
    ]
    merged = merge_matches_on_condition(data, matched_condition)
    assert len(merged) == 2
    assert merged[0].paragraph_left
    assert merged[0].paragraph_right
    assert merged[0].paragraph_left.text == "A B C"
    assert merged[0].paragraph_right.text == "A B C"


def test_merge_empty_input():
    """
    Test merging behavior when input list is empty.
    Should return an empty list.
    """
    merged = merge_matches_on_condition([], unmatched_condition_with_id)
    assert not merged


def test_merge_single_element():
    """
    Test merging behavior when input list has a single ParagraphMatch.
    Should return the same list unmodified.
    """
    single = [
        match(0, "removed", 0, -1, paragraph("only", "1"), None)
    ]
    merged = merge_matches_on_condition(single, unmatched_condition_no_id)
    assert len(merged) == 1
    assert merged[0].paragraph_left
    assert merged[0].paragraph_left.text == "only"


def test_join_optimize_with_no_orphans():
    """
    Test join_optimize_paragraph_matches when all matches are fully paired.
    Should return the input list unchanged.
    """
    data = [
        match(100, "equal", 0, 0, paragraph(
            "All", "1"), paragraph("All", "1")),
        match(100, "equal", 1, 1, paragraph(
            "matched", "2"), paragraph("matched", "2")),
    ]
    result = join_optimize_paragraph_matches(data, True, True)
    assert result == data
