"""
Module to process PDF files and extract paragraphs.
"""

from io import BufferedReader, BytesIO
from typing import List, Optional, Union

import pdfplumber as pdfp

from .utils import get_heading_info


class PDFProcessor:
    """Processes PDF files to extract structured paragraphs with heading detection."""

    def __init__(self, file_object: Union[BufferedReader, BytesIO, str]):
        """Initialize PDFProcessor with a file object or path."""
        self.content = file_object

    def extract_paragraphs(
        self,
        page_start: int = 0,
        page_end: Optional[int] = None,
        top_start: int = 0,
        top: int = 0,
        bottom: int = 0,
        size_weight: float = 1.0
    ) -> List[str]:
        """
        Extract paragraphs from PDF with layout-aware processing.
        
        Args:
            page_start: Starting page index (0-based)
            page_end: Ending page index (exclusive)
            top_start: Top crop margin for first page
            top: Top crop margin for subsequent pages
            bottom: Bottom crop margin for all pages
            size_weight: Multiplier for font size when detecting paragraph breaks
            
        Returns:
            List of processed paragraphs maintaining document structure
        """
        paragraphs: List[str] = []
        
        with pdfp.open(self.content) as pdf:
            pages = pdf.pages[page_start:page_end]
            
            for page_idx, page in enumerate(pages):
                is_first_page = page_idx == 0
                crop_top = top_start if is_first_page else top
                
                # Crop page to content area
                content_area = (0, crop_top, page.width, page.height - bottom)
                cropped_page = page.crop(content_area)
                
                # Extract words with font size information
                words = cropped_page.extract_words(extra_attrs=["size"])
                
                # Split into preliminary paragraphs
                page_paragraphs = self._split_paragraphs_by_spacing(
                    words, 
                    size_weight
                )
                
                # Process paragraphs with heading detection
                self._process_page_paragraphs(page_paragraphs, paragraphs)

        return paragraphs

    def _split_paragraphs_by_spacing(
        self,
        words: List[dict],
        size_weight: float
    ) -> List[str]:
        """Split words into paragraphs based on vertical spacing."""
        paragraphs: List[str] = []
        current_para: List[str] = []
        prev_bottom = 0

        for word in words:
            # Calculate spacing from previous line
            spacing = word["top"] - prev_bottom
            threshold = word["size"] * size_weight

            # Detect paragraph break
            if current_para and spacing > threshold:
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
        document_paragraphs: List[str]
    ) -> None:
        """Process paragraphs from a single page with heading detection."""
        for idx, para in enumerate(page_paragraphs):
            if not para:
                continue  # Skip empty paragraphs

            # Handle first paragraph of page specially
            if idx == 0:
                self._merge_with_previous(para, document_paragraphs)
            else:
                document_paragraphs.append(para)

    def _merge_with_previous(
        self,
        paragraph: str,
        document_paragraphs: List[str]
    ) -> None:
        """Merge paragraph with previous content if not a valid heading."""
        heading_num, heading_text = get_heading_info(paragraph)
        
        if heading_num and heading_text:
            document_paragraphs.append(paragraph)
        elif document_paragraphs:
            # Merge with previous paragraph
            document_paragraphs[-1] += " " + paragraph
        else:
            # First paragraph in document
            document_paragraphs.append(paragraph)