"""
Module to test text splitter
"""
from document_comparer.utils import recognize_first_sentence

def test_sentence_recognition_normal():
    """
    Test sentence recognition in standard case
    """

    text = "Where to end the search. Default is to the end of the string"
    expected = "Where to end the search"

    assert recognize_first_sentence(text) == expected

def test_sentence_recognition_empty():
    """
    Test sentence recognition if empty text
    """

    text = ""
    expected = ""

    assert recognize_first_sentence(text) == expected

def test_sentence_recognition_complex():
    """
    Test sentence recognition in complex case
    """

    text = "Rack in the High-bay building containing, e.g. the Main Processing Unit (MPU). MPS Concentrators spread out along the PIP-II."
    expected = "Rack in the High-bay building containing, e.g. the Main Processing Unit (MPU)"

    assert recognize_first_sentence(text) == expected

def test_sentence_recognition_one_sentence():
    """
    Test sentence recognition if only one sentence
    """

    text = "Where to end the search."
    expected = "Where to end the search"

    assert recognize_first_sentence(text) == expected

def test_sentence_recognition_no_point():
    """
    Test sentence recognition if no point present
    """

    text = "Where to end the search"
    expected = "Where to end the search"

    assert recognize_first_sentence(text) == expected