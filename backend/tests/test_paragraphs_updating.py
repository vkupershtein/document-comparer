"""
Module to test paragraphs updating
"""
from document_comparer.paragraph import Paragraph
from document_comparer import TextMatcher


def test_paragraphs_update_normal():
    """
    Normal case for paragraphs updating
    """
    # pylint:disable=line-too-long
    text_left = "The sky turned a deep orange as the sun began to set. A warm breeze rustled the leaves on the trees. Birds chirped softly in the distance, preparing to settle in for the night."
    text_right = "The sky transformed into a glowing amber as twilight settled in. A soft wind stirred the branches of nearby trees. Birds chirped softly in the distance, preparing to settle in for the night."

    opcodes = TextMatcher.get_edit_operations(text_left, text_right)

    text_left_para = Paragraph(text=text_left, id="1")
    text_right_para = Paragraph(text=text_right, id="2")

    expected_left = [
        Paragraph(
            text='',
            id='1',
            payload={},
        ),
        Paragraph(
            text='The sky turned a deep orange as the sun began to set.',
            id='1',
            payload={},
        ),
        Paragraph(
            text='A warm breeze rustled the leaves on the trees. Birds '
            'chirped softly in the distance, preparing to settle in for the '
            'night.',
            id='1',
            payload={},
        ),
    ]
    expected_right = [
        Paragraph(
            text='',
            id='2',
            payload={},
        ),
        Paragraph(
            text='The sky transformed into a glowing amber as twilight settled in.',
            id='2',
            payload={},
        ),
        Paragraph(
            text='A soft wind stirred the branches of nearby trees. '
            'Birds chirped softly in the distance, preparing to settle in for '
            'the night.',
            id='2',
            payload={},
        ),
    ]

    segments_left, segments_right = TextMatcher.split_combined_text(text_left_para,
                                                                    text_right_para,
                                                                    opcodes, 10)

    assert segments_left == expected_left
    assert segments_right == expected_right


def test_paragraphs_update_added_sentences():
    """
    Case for paragraphs updating with added sentences
    """
    # pylint:disable=line-too-long
    text_left = "She placed the book on the windowsill and looked outside. Rain tapped gently against the glass. Everything seemed calm, almost dreamlike."
    text_right = "She placed the book on the windowsill and looked outside. Rain tapped gently against the glass. Everything seemed calm, almost dreamlike. She closed her eyes for a moment, listening to the rhythm of the rain. A faint smile crossed her face."

    opcodes = TextMatcher.get_edit_operations(text_left, text_right)

    text_left_para = Paragraph(text=text_left, id="1")
    text_right_para = Paragraph(text=text_right, id="2")

    expected_left = [
        Paragraph(
            text='She placed the book on the windowsill and looked outside. '
            'Rain tapped gently against the glass. '
            'Everything seemed calm, almost dreamlike.',
            id='1',
            payload={},
        ),
        Paragraph(
            text='',
            id='1',
            payload={},
        ),
    ]
    expected_right = [
        Paragraph(
            text='She placed the book on the windowsill and looked outside. '
            'Rain tapped gently against the glass. '
            'Everything seemed calm, almost dreamlike.',
            id='2',
            payload={},
        ),
        Paragraph(
            text='She closed her eyes for a moment, listening to the rhythm of the rain. '
            'A faint smile crossed her face.',
            id='2',
            payload={},
        ),
    ]

    segments_left, segments_right = TextMatcher.split_combined_text(text_left_para,
                                                                    text_right_para,
                                                                    opcodes, 10)

    assert segments_left == expected_left
    assert segments_right == expected_right


def test_paragraphs_update_complex():
    """
    Case for paragraphs updating complex
    """
    # pylint:disable=line-too-long
    text_left = "The dog barked excitedly when it saw the boy. He ran across the yard to greet his furry friend. They played fetch until the sun went down."
    text_right = "The dog let out a series of joyful barks when it spotted the boy. He dashed happily through the grassy yard to meet his furry friend. They played fetch until the sun went down."

    opcodes = TextMatcher.get_edit_operations(text_left, text_right)

    text_left_para = Paragraph(text=text_left, id="1")
    text_right_para = Paragraph(text=text_right, id="2")

    expected_left = [
        Paragraph(
            text='',
            id='1',
            payload={},
        ),
        Paragraph(
            text='The dog barked excitedly when it saw the boy.',
            id='1',
            payload={},
        ),
        Paragraph(
            text='He ran across the yard to greet his furry friend. They played fetch until the sun went down.',
            id='1',
            payload={},
        )
    ]
    expected_right = [
        Paragraph(
            text='',
            id='2',
            payload={},
        ),
        Paragraph(
            text='The dog let out a series of joyful barks when it spotted the boy.',
            id='2',
            payload={},
        ),
        Paragraph(
            text='He dashed happily through the grassy yard to meet his furry friend. They played fetch until the sun went down.',
            id='2',
            payload={},
        )
    ]

    segments_left, segments_right = TextMatcher.split_combined_text(text_left_para,
                                                                    text_right_para,
                                                                    opcodes, 10)

    assert segments_left == expected_left
    assert segments_right == expected_right
