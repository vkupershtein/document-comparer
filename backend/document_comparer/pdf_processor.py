"""
Module to process PDF files and extract paragraphs.
"""

from io import BufferedReader, BytesIO
from typing import List, Optional, Union

from internal.notifier import Notifier, ThresholdNotifier
import numpy as np
import pdfplumber as pdfp

from document_comparer.paragraph import Paragraph
from document_comparer.processor_protocol import DocumentProcessor

from .utils import get_heading_info, get_lower_values, get_upper_values, shift_elements


class PDFProcessor(DocumentProcessor):
    """Processes PDF files to extract structured paragraphs with heading detection."""

    def __init__(self,
                 file_object: Union[BufferedReader, BytesIO, str],
                 page_start: int = 0,
                 page_end: Optional[int] = None,
                 top_start: int = 0,
                 top: int = 0,
                 bottom: int = 0,
                 size_weight: float = 1.0,
                 threshold_notifier: ThresholdNotifier =
                 ThresholdNotifier(notifier=Notifier(None, None), lower=0, upper=0)):
        """Initialize PDFProcessor with a file object or path."""
        self.content = file_object
        self.page_start = page_start
        self.page_end = page_end
        self.top_start = top_start
        self.top = top
        self.bottom = bottom
        self.size_weight = size_weight
        self.notifier = threshold_notifier["notifier"]
        self.lower_threshold = threshold_notifier["lower"]
        self.upper_threshold = threshold_notifier["upper"]
        self.middle_threshold = (
            self.upper_threshold + self.lower_threshold) // 2
        self.threshold_notifier = threshold_notifier

    def extract_paragraphs(self) -> List[Paragraph]:
        """
        Extract paragraphs from PDF with layout-aware processing.

        Returns:
            List of processed paragraphs maintaining document structure
        """
        paragraphs: List[Paragraph] = []

        paged_document_words = self.extract_document_words()

        non_break_pages = self.get_non_break_pages(paged_document_words)

        for page_idx, words in enumerate(paged_document_words):
            # Split into preliminary paragraphs
            page_paragraphs = self._split_paragraphs_by_spacing(words)

            # Process paragraphs with heading detection
            self._process_page_paragraphs(
                page_paragraphs, paragraphs, page_idx, non_break_pages)

            self.notifier.loop_notify(page_idx, self.middle_threshold,
                                      self.upper_threshold, len(paged_document_words))

        return paragraphs

    def extract_document_words(self):
        """
        Extract document words with metadata
        """
        page_words = []
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
                page_words.append(words)

                self.notifier.loop_notify(page_idx, self.lower_threshold,
                                          self.middle_threshold, len(pages))

            return page_words

    def _split_paragraphs_by_spacing(
        self,
        words: List[dict]
    ) -> List[str]:
        """Split words into paragraphs based on vertical spacing."""
        paragraphs: List[str] = []
        current_para: List[str] = []
        prev_bottom = 0
        prev_size = 0

        for word in words:
            # Calculate spacing from previous line
            spacing = word["top"] - prev_bottom
            threshold = word["size"] * self.size_weight

            # Detect paragraph break
            if current_para and (spacing > threshold or
                                 (spacing < -threshold * 2 and word["size"] > prev_size * 0.75)):
                paragraphs.append(" ".join(current_para).strip())
                current_para = []

            current_para.append(word["text"])
            prev_bottom = word["bottom"]
            prev_size = word["size"]

        # Add final paragraph
        if current_para:
            paragraphs.append(" ".join(current_para).strip())

        return paragraphs

    def _process_page_paragraphs(
        self,
        page_paragraphs: List[str],
        document_paragraphs: List[Paragraph],
        page_idx: int,
        non_break_pages: List[int]
    ) -> None:
        """Process paragraphs from a single page with heading detection."""
        for idx, para in enumerate(page_paragraphs):
            if not para:
                continue  # Skip empty paragraphs

            page_non_break_condition = False

            if idx == 0 and page_idx in non_break_pages and len(document_paragraphs) != 0:
                current_head_condition = self._has_heading(para)
                prev_head_condition = self._has_heading(
                    document_paragraphs[-1].text)
                page_non_break_condition = not (
                    current_head_condition or prev_head_condition)

            # Handle first paragraph of page specially
            if page_non_break_condition:
                document_paragraphs[-1].text += " " + para
            else:
                para_pos = len(document_paragraphs)
                document_paragraphs.append(Paragraph(text=para,
                                                     id=str(para_pos),
                                                     payload={"para_pos": para_pos,
                                                              "page_number": str(page_idx+1)}))                

    def _has_heading(self, paragraph):
        """
        Check that paragraph has heading
        """
        heading_num, heading_text = get_heading_info(paragraph)
        return heading_num and heading_text

    def get_page_borders(self, paged_document_words):
        """
        Get borgers of each page
        """
        lefts = []
        tops = []
        rights = []
        bottoms = []
        for words in paged_document_words:
            lefts.append(words[0]['x0'] if len(words) > 0 else 0)
            tops.append(words[0]['top'] if len(words) > 0 else 0)
            rights.append(words[-1]['x1'] if len(words) > 0 else 0)
            bottoms.append(words[-1]['bottom'] if len(words) > 0 else 0)
        return tops, lefts, rights, bottoms

    def get_non_break_pages(self, paged_document_words):
        """
        Get page number where paragraphs can be merged
        """
        tops, lefts, rights, bottoms = self.get_page_borders(
            paged_document_words)
        normal_tops = get_lower_values(tops)
        normal_lefts = get_lower_values(lefts)
        normal_rights = shift_elements(get_upper_values(rights), 1, True)
        normal_bottoms = shift_elements(get_upper_values(bottoms), 1, True)
        result = []
        for top, left, right, bottom in zip(normal_tops, normal_lefts,
                                            normal_rights, normal_bottoms):
            result.append(top & left & right & bottom)
        return list(np.where(result)[0])
