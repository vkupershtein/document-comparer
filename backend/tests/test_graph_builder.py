"""
Module to test heading pathway finder
"""

from document_comparer.graph_builder import GraphBuilder  # Adjust import path

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
