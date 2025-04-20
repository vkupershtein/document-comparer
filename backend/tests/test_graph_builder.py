"""
Module to test heading pathway finder
"""

import pytest
from document_comparer.graph_builder import GraphBuilder, create_graph_builder


def test_find_best_path_in_sequence():
    """
    Test for best path in sequence
    """
    sequence = [("1", {}), ("1.1", {}), ("1.2", {}), ("2", {}), ("2.1", {})]
    graph_builder = GraphBuilder(sequence)

    best_path = graph_builder.find_best_path_in_sequence()
    best_values = [el.value for el in best_path]

    assert best_values == ["1", "1.1", "1.2", "2", "2.1"]


def test_find_best_path_tiebreak_by_range():
    """
    Find best path with tie break
    """
    sequence = [("1", {}), ("1.1", {}), ("x", {}), ("2", {}), ("2.1", {})]
    graph_builder = GraphBuilder(sequence)

    best_path = graph_builder.find_best_path_in_sequence()
    best_values = [el.value for el in best_path]

    assert best_values == ["1", "1.1", "2", "2.1"]


def test_infinite_recursion_case():
    """
    This test checks if the recursion occurs.    
    """

    sequence = [("1", {}), ("1.1", {}), ("1", {})]
    graph_builder = GraphBuilder(sequence)

    best_path = graph_builder.find_best_path_in_sequence()
    best_values = [el.value for el in best_path]

    assert best_values == ["1", "1.1"]


def test_possible_infinite_recursion_duplicate_like_entries():
    """
    Simulates a situation where identical elements reappear structurally,
    which might trick the visited system.
    """
    # All these have the same heading structure, slightly offset
    sequence = [("1", {}), ("1.1", {}), ("1.1", {}), ("1.1", {})]
    graph_builder = GraphBuilder(sequence)

    best_path = graph_builder.find_best_path_in_sequence()
    best_values = [el.value for el in best_path]

    # It may result in multiple "1.1" entries, depending on logic.
    # But it should not crash.
    assert best_values[0] == "1"
    assert all(v == "1.1" for v in best_values[1:])


def test_deeply_nested_heading_sequence():
    """
    Long nested sequence to stress-test recursion depth
    """
    sequence = [(f"1.{i}", {}) for i in range(100)]
    sequence.insert(0, ("1", {}))  # prepend base heading

    graph_builder = GraphBuilder(sequence)
    best_path = graph_builder.find_best_path_in_sequence()
    best_values = [el.value for el in best_path]

    assert best_values[0] == "1"
    assert best_values[-1] == "1.99"
    assert len(best_values) == 101


def test_deep_recursion_graph_building():
    """ 
    Create a large sequence of elements in increasing order 
    """
    value_key = 'heading'
    records = [{value_key: str(i)} for i in range(1000)]

    with pytest.raises(RecursionError):
        # This may raise a RecursionError if depth exceeds Python's limit
        gb = create_graph_builder(records, value_key)  # type: ignore
        gb.find_best_path_in_sequence()


def test_duplicate_headings():
    """
    Verify no infinite recursion occurs; best path might be empty or single element
    """
    value_key = 'heading'
    records: list[dict[str, str | int]] = [
        {value_key: '1'},
        {value_key: '1'},  # Same value, different position
        {value_key: '1'},
    ]

    gb = create_graph_builder(records, value_key)
    best_path = gb.find_best_path_in_sequence()

    assert len(best_path) <= 1  # Adjust based on expected behavior


def test_interleaved_headings():
    """
    Check if the best path is correctly determined without recursion issues
    """
    value_key = 'heading'
    records: list[dict[str, str | int]] = [
        {value_key: '1'},
        {value_key: '3'},
        {value_key: '2'},  # Lower than previous but higher than first
        {value_key: '4'},
    ]

    gb = create_graph_builder(records, value_key)
    best_path = gb.find_best_path_in_sequence()

    assert len(best_path) == 3  # Expected path: '1' -> '3' -> '4' or similar


def test_non_numeric_headings():
    """
    Verify paths are built correctly without infinite recursion
    """
    value_key = 'heading'
    records: list[dict[str, str | int]] = [
        {value_key: '1.a'},
        {value_key: '1.b'},
        {value_key: '1.a.1'},
    ]

    gb = create_graph_builder(records, value_key)
    best_path = gb.find_best_path_in_sequence()

    assert len(best_path) == 2

def test_single_element():
    """
    Single element sequence
    """
    value_key = 'heading'
    records: list[dict[str, str | int]] = [{value_key: '1'}]

    gb = create_graph_builder(records, value_key)
    best_path = gb.find_best_path_in_sequence()
    assert len(best_path) == 0

def test_empty_sequence():
    """
    Empy sequence
    """
    value_key = 'heading'
    records: list[dict[str, str | int]] = []

    gb = create_graph_builder(records, value_key)
    best_path = gb.find_best_path_in_sequence()
    assert len(best_path) == 0
