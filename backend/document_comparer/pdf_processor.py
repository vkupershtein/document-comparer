"""
Module to process pdf files
"""

from io import BufferedReader, BytesIO
from typing import Union

import pdfplumber as pdfp

from .utils import get_heading_info

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
                first_paragraph = True                
                for word in page_words:
                    line_diff = word["top"] - prev_bottom
                    prev_bottom = word["bottom"]
                    if line_diff > size_weight * word["size"] and len(paragraph_words) > 0:
                        paragraph_text = " ".join(paragraph_words).strip()
                        append_text = True
                        if first_paragraph:
                            heading_number, heading_text = get_heading_info(paragraph_text)
                            if len(paragraphs) > 0 and not (heading_number and heading_text):
                                append_text = False
                        if append_text:
                            paragraphs.append(paragraph_text)
                        else:                                
                            paragraphs[-1] = paragraphs[-1] + " " + paragraph_text                                
                        paragraph_words = []
                        first_paragraph = False
                    paragraph_words.append(word["text"])
                paragraphs.append(" ".join(paragraph_words).strip())
                paragraph_words = []            
            return paragraphs
