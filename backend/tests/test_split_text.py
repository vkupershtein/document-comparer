"""
Module to test text splitter
"""
from document_comparer.utils import recognize_first_sentence, split_into_sentences


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
    #pylint: disable=line-too-long
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


def test_split_text_into_sentences_normal():
    """
    Standard case for splitting
    """
    #pylint: disable=line-too-long
    text = "The document owner is responsible for maintaining document content, revisions, and updates." \
        + " An Owner is considered a “Checker” in Teamcenter workflow release when they are not the document Author."

    expected = ["The document owner is responsible for maintaining document content, revisions, and updates.",
                "An Owner is considered a “Checker” in Teamcenter workflow release when they are not the document Author."]

    sentences, positions = split_into_sentences(text)
    assert sentences == expected
    assert positions == [0, 91]


def test_split_text_into_sentences_one():
    """
    Standard case for splitting one sentence
    """
    text = "The document owner is responsible for maintaining document content, revisions, and updates"

    expected = [
        "The document owner is responsible for maintaining document content, revisions, and updates"]

    sentences, positions = split_into_sentences(text)
    assert sentences == expected
    assert positions == [0]


def test_split_text_into_sentences_one_with_point():
    """
    Standard case for splitting one sentence with point
    """
    text = "The document owner is responsible for maintaining document content, revisions, and updates."

    expected = [
        "The document owner is responsible for maintaining document content, revisions, and updates."]

    sentences, positions = split_into_sentences(text)
    assert sentences == expected
    assert positions == [0]


def test_split_text_complex():
    """
    Complex case for splitting into sentences
    """
    #pylint: disable=line-too-long
    text = "5.1.3. System Diagram The MPS consists of three functional layers as shown in Figure 5-1: " \
        + "1. Input layer, which provides signal interface to the individual machine elements or subsystems. " \
        + "2. Logic (permit) layer. This layer decides to either allow/maintain or inhibit the beam based on comparison of the input signals with parameters in the Beam Setup Database chosen by the Mode Controller." + \
        " 3. Output layer, containing drivers to the Beam Inhibiting Devices. The layers are FPGA-based and fully programmable."

    expected = ["5.1.3. System Diagram The MPS consists of three functional layers as shown in Figure 5-1: "
                + "1. Input layer, which provides signal interface to the individual machine elements or subsystems.",
                "2. Logic (permit) layer.", "This layer decides to either allow/maintain or inhibit the beam based on comparison of the input signals with parameters in the Beam Setup Database chosen by the Mode Controller.",
                "3. Output layer, containing drivers to the Beam Inhibiting Devices.", "The layers are FPGA-based and fully programmable."]

    sentences, positions = split_into_sentences(
        text)  # pylint: disable=unbalanced-tuple-unpacking
    assert sentences == expected
    assert positions == [0, 187, 212, 391, 459]
