"""
Module to test outer positions
"""

from document_comparer.utils import get_outer_positions


def test_outer_positions_standard():
    """
    Test standard case
    """

    arr = [1, 7, 9, 13, 16]
    left = 6
    right = 15

    expected = (1, 16)

    assert get_outer_positions(arr, left, right) == expected


def test_outer_positions_edge():
    """
    Test edge case
    """

    arr = [1, 7, 9, 13, 16]
    left = 0
    right = 20

    expected = (0, 20)

    assert get_outer_positions(arr, left, right) == expected


def test_outer_positions_inside():
    """
    Test inside case
    """

    arr = [1, 7, 9, 13, 16]
    left = 10
    right = 13

    expected = (9, 13)

    assert get_outer_positions(arr, left, right) == expected


def test_outer_positions_full_inside():
    """
    Test full inside case
    """

    arr = [1, 7, 9, 13, 16]
    left = 10
    right = 12

    expected = (9, 13)

    assert get_outer_positions(arr, left, right) == expected

def test_outer_positions_first_last():
    """
    Test case with first and last
    """

    arr = [1, 7, 9, 13, 16]
    left = 1
    right = 16

    expected = (1, 16)

    assert get_outer_positions(arr, left, right) == expected

def test_outer_positions_both_after():
    """
    Test case with both values after the last
    """

    arr = [1, 7, 9, 13, 16]
    left = 17
    right = 19

    expected = (17, 19)

    assert get_outer_positions(arr, left, right) == expected

def test_outer_positions_both_before():
    """
    Test case with both values before the first
    """

    arr = [5, 7, 9, 13, 16]
    left = 2
    right = 4

    expected = (2, 4)

    assert get_outer_positions(arr, left, right) == expected
