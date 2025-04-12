"""
Module to process PDF files and extract paragraphs.
"""

from io import BufferedReader, BytesIO
from typing import List, Optional, Union

import pdfplumber as pdfp

from document_comparer.paragraph import Paragraph
from document_comparer.processor_protocol import DocumentProcessor

from .utils import get_heading_info


class PDFProcessor(DocumentProcessor):
    """Processes PDF files to extract structured paragraphs with heading detection."""

    def __init__(self,
                 file_object: Union[BufferedReader, BytesIO, str],
                 page_start: int = 0,
                 page_end: Optional[int] = None,
                 top_start: int = 0,
                 top: int = 0,
                 bottom: int = 0,
                 size_weight: float = 1.0
                 ):
        """Initialize PDFProcessor with a file object or path."""
        self.content = file_object
        self.page_start = page_start
        self.page_end = page_end
        self.top_start = top_start
        self.top = top
        self.bottom = bottom
        self.size_weight = size_weight

    def extract_paragraphs(self) -> List[Paragraph]:
        """
        Extract paragraphs from PDF with layout-aware processing.

        Returns:
            List of processed paragraphs maintaining document structure
        """
        paragraphs: List[Paragraph] = []

        with pdfp.open(self.content) as pdf:
            pages = pdf.pages[self.page_start:self.page_end]

            for page_idx, page in enumerate(pages):
                is_first_page = page_idx == 0
                crop_top = self.top_start if is_first_page else self.top

                # Crop page to content area
                content_area = (0, crop_top, page.width,
                                page.height - self.bottom)
                cropped_page = page.crop(content_area)

                # Extract words with font size information
                words = cropped_page.extract_words(extra_attrs=["size"])

                # Split into preliminary paragraphs
                page_paragraphs = self._split_paragraphs_by_spacing(words)

                # Process paragraphs with heading detection
                self._process_page_paragraphs(page_paragraphs, paragraphs)

        return paragraphs

    def _split_paragraphs_by_spacing(
        self,
        words: List[dict]
    ) -> List[str]:
        """Split words into paragraphs based on vertical spacing."""
        paragraphs: List[str] = []
        current_para: List[str] = []
        prev_bottom = 0

        for word in words:
            # Calculate spacing from previous line
            spacing = word["top"] - prev_bottom
            threshold = word["size"] * self.size_weight

            # Detect paragraph break
            if current_para and (spacing > threshold or spacing < -threshold * 2):
                paragraphs.append(" ".join(current_para).strip())
                current_para = []

            current_para.append(word["text"])
            prev_bottom = word["bottom"]

        # Add final paragraph
        if current_para:
            paragraphs.append(" ".join(current_para).strip())

        return paragraphs

    def _process_page_paragraphs(
        self,
        page_paragraphs: List[str],
        document_paragraphs: List[Paragraph]
    ) -> None:
        """Process paragraphs from a single page with heading detection."""
        for idx, para in enumerate(page_paragraphs):
            if not para:
                continue  # Skip empty paragraphs

            # Handle first paragraph of page specially
            if idx == 0:
                self._merge_with_previous(para, document_paragraphs)
            else:
                document_paragraphs.append(Paragraph(text=para,
                                                     id=str(len(document_paragraphs))))

    def _merge_with_previous(
        self,
        paragraph: str,
        document_paragraphs: List[Paragraph]
    ) -> None:
        """Merge paragraph with previous content if not a valid heading."""
        heading_num, heading_text = get_heading_info(paragraph)

        prev_heading_num, prev_heading_text = "", ""

        if len(document_paragraphs) != 0:
            prev_heading_num, prev_heading_text = get_heading_info(
                document_paragraphs[-1].text)

        if (heading_num and heading_text) or (prev_heading_num and prev_heading_text) or len(document_paragraphs) == 0:
            document_paragraphs.append(Paragraph(text=paragraph,
                                                 id=str(len(document_paragraphs))))
        else:
            # Merge with previous paragraph
            document_paragraphs[-1].text += " " + paragraph
