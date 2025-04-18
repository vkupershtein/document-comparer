"""
Module to test merging of split paragraphs
"""

from document_comparer.utils import merge_sentences


def test_all_active():
    """
    Test case where all sentences are in sent_positions; should result in a single merged paragraph.
    """
    sentences = ["A", "B", "C"]
    sent_positions = {0, 1, 2}
    assert merge_sentences(sentences, sent_positions) == [["A", "B", "C"]]

def test_alternating():
    """
    Test alternating active/inactive sentences; each switch should start a new paragraph.
    """
    sentences = ["A", "B", "C", "D"]
    sent_positions = {0, 2}
    assert merge_sentences(sentences, sent_positions) == [["A"], ["B"], ["C"], ["D"]]

def test_grouped_active_then_inactive():
    """
    Test with grouped active sentences, followed by an inactive, then another active and inactive.
    """
    sentences = ["A", "B", "C", "D", "E"]
    sent_positions = {0, 1, 3}   
    assert merge_sentences(sentences, sent_positions) == [["A", "B"], ["C"], ["D"], ["E"]]

def test_empty_sentences():
    """
    Test edge case where the sentence list is empty; should return an empty result.
    """
    result = merge_sentences([], set())
    assert not result
