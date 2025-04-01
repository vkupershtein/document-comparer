"""
Module to process pdf files
"""

from io import BufferedReader, BytesIO
from typing import Union

import pdfplumber as pdfp

class PDFProcessor:
    """
    Class processes PDF objects
    """     
    def __init__(self, file_object: Union[BufferedReader, BytesIO, str]):
        """
        Construct PDFProcessor instance
        """
        self.content = file_object

    def extract_paragraphs(self, page_start=0, page_end=None, top_start=0, top=0, bottom=0, size_weight=1.0):        
        with pdfp.open(self.content) as reader:
            paragraphs = []
            paragraph_words = []
            first = True
            for page in reader.pages[page_start:page_end]:
                current_top = top
                if first:
                    current_top = top_start
                first = False
                page = page.crop((0, current_top, page.width, page.height-bottom))
                page_words = page.extract_words(extra_attrs=["size"])
                prev_bottom = 0
                first_word = True
                for word in page_words:
                    line_diff = word["top"] - prev_bottom
                    prev_bottom = word["bottom"]
                    if line_diff > size_weight * word["size"] and len(paragraph_words) > 0 and not first_word:                        
                        paragraphs.append(" ".join(paragraph_words))
                        paragraph_words = []
                    paragraph_words.append(word["text"])
                    first_word = False
            paragraphs.append(" ".join(paragraph_words))
            return paragraphs
