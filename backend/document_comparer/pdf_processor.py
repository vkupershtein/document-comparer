"""
Module to process PDF files and extract paragraphs.
"""

from io import BufferedReader, BytesIO
from itertools import chain
import math
from typing import Dict, List, Optional, Tuple, Union

from internal.notifier import Notifier, ThresholdNotifier
import numpy as np
import pdfplumber as pdfp

from document_comparer.paragraph import Paragraph
from document_comparer.processor_protocol import DocumentProcessor

from .utils import (filter_self_contained,
                    get_heading_info,
                    get_lower_values,
                    get_upper_values,
                    shift_elements)


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
        Extract all paragraphs from the PDF document
        """
        tables_paragraphs, page_table_borders = self.extract_table_info()
        text_paragraphs = self.extract_text_paragraphs(page_table_borders)

        paragraphs = sorted(tables_paragraphs + text_paragraphs,
                            key=lambda x: (x.payload["page_number"], x.payload["coord"]))
        for i, para in enumerate(paragraphs):
            para.id = str(i)
            para.payload["para_pos"] = i
        return paragraphs

    def extract_text_paragraphs(self, page_table_borders: Dict[int, List[Tuple[int, int]]]) -> List[Paragraph]:
        """
        Extract paragraphs from PDF with layout-aware processing.

        Returns:
            List of processed paragraphs maintaining document structure
        """
        paragraphs: List[Paragraph] = []

        paged_document_words = self.extract_document_words()

        non_break_pages = self.get_non_break_pages(paged_document_words)

        for page_idx, words in enumerate(paged_document_words):
            table_borders = page_table_borders.get(page_idx)
            # Split into preliminary paragraphs
            page_paragraphs, page_paragraphs_coords = self._split_paragraphs_by_spacing(
                words, table_borders)
            # Process paragraphs with heading detection
            self._process_page_paragraphs(
                page_paragraphs, page_paragraphs_coords, paragraphs, page_idx, non_break_pages)

            self.notifier.loop_notify(page_idx, self.middle_threshold,
                                      self.upper_threshold, len(paged_document_words))

        return paragraphs

    def extract_table_info(self) -> Tuple[List[Paragraph], Dict[int, List[Tuple[int, int]]]]:
        """
        Extract table paragraphs and table zones on each page
        """
        tables, tables_lines, pages_indices = self.extract_table_rows()
        page_table_borders = self._get_page_table_borders(
            tables_lines, pages_indices)
        tables_paragraphs: List[Paragraph] = []
        for table_id, (table, table_lines, page_idx) in enumerate(zip(tables, tables_lines, pages_indices)):
            tables_paragraphs += self._make_table_paragraphs(
                table, table_lines, page_idx, table_id)
        return tables_paragraphs, page_table_borders

    def extract_table_rows(self):
        """
        Extract table rows from pdf file
        """
        with pdfp.open(self.content) as pdf:
            pages = pdf.pages
            tables: List[List[List[str | None]]] = []
            tables_lines: List[List[int]] = []
            pages_indices: List[int] = []
            for page_idx, page in enumerate(pages):
                content_area = (0, self.top, page.width,
                                page.height-self.bottom)
                cropped_page = page.crop(content_area)
                finder = cropped_page.debug_tablefinder()
                x_min, x_max, y_min, y_max = -math.inf, +math.inf, -math.inf, +math.inf
                for edge in finder.get_edges():
                    if 'pts' not in edge:
                        continue
                    x_coord, y_coord = zip(*edge['pts'])
                    x_min = min(list(x_coord) + [x_min])
                    x_max = max(list(x_coord) + [x_max])
                    y_min = min(list(y_coord) + [y_min])
                    y_max = max(list(y_coord) + [y_max])
                page_table_lines = []
                for tb in finder.tables:
                    y_rows_levels = np.sort(np.unique(list(chain(*[[row.bbox[1], row.bbox[3]]
                                                                   for row in tb.rows])))).tolist()
                    x_columns_levels = np.sort(np.unique(list(chain(*[[column.bbox[0], column.bbox[2]]
                                                                      for column in tb.columns])))).tolist()
                    page_table_lines.append({
                        "explicit_horizontal_lines": y_rows_levels,
                        "explicit_vertical_lines": x_columns_levels
                    })

                table_ll = [tbl['explicit_horizontal_lines']
                            for tbl in page_table_lines]
                page_table_lines = [page_table_lines[res[0]]
                                    for res in filter_self_contained(table_ll)]

                if not page_table_lines:
                    continue

                if -math.inf < x_min < min(page_table_lines[0]["explicit_vertical_lines"]):
                    page_table_lines[0]["explicit_vertical_lines"].insert(
                        0, x_min)
                if -math.inf < y_min < min(page_table_lines[0]["explicit_horizontal_lines"]):
                    page_table_lines[0]["explicit_horizontal_lines"].insert(
                        0, y_min)
                if math.inf < x_max > max(page_table_lines[-1]["explicit_vertical_lines"]):
                    page_table_lines[-1]["explicit_vertical_lines"].append(
                        x_max)
                if math.inf < y_max > max(page_table_lines[-1]["explicit_horizontal_lines"]):
                    page_table_lines[-1]["explicit_horizontal_lines"].append(
                        y_max)

                for table_lines in page_table_lines:
                    table = page.extract_table(table_settings={
                        "vertical_strategy": "explicit",
                        "horizontal_strategy": "explicit",
                        "explicit_vertical_lines": table_lines["explicit_vertical_lines"],
                        "explicit_horizontal_lines": table_lines["explicit_horizontal_lines"]
                    })
                    if table:
                        tables.append(table)
                        tables_lines.append(
                            table_lines["explicit_horizontal_lines"])
                        pages_indices.append(page_idx)
            return tables, tables_lines, pages_indices

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

    @classmethod
    def _get_page_table_borders(cls,
                                tables_lines: List[List[int]],
                                pages_indices: List[int]) -> Dict[int, List[Tuple[int, int]]]:
        """
        Make a list of table zones for each page hat has tables
        """
        page_table_borders: Dict[int, List[Tuple[int, int]]] = {}
        for table_lines, page_idx in zip(tables_lines, pages_indices):
            page_table_borders.setdefault(page_idx, []).append(
                (table_lines[0], table_lines[-1]))
        return page_table_borders

    @classmethod
    def _make_table_paragraphs(cls, table: List[List[str | None]],
                               table_lines: List[int],
                               page_idx: int, table_id: int) -> List[Paragraph]:
        """
        Make table paragraphs from table
        """
        table_paragraphs: List[Paragraph] = []
        for row, coord in zip(table, table_lines[1:]):
            para_text = ' '.join([cell for cell in row if cell]).replace(
                '\n', ' ').strip()
            if not para_text:
                continue
            table_paragraphs.append(
                Paragraph(text=para_text,
                          id=str(table_id),
                          payload={
                              "page_number": page_idx+1,
                              "coord": coord
                          }
                          )
            )
        return table_paragraphs

    def _split_paragraphs_by_spacing(
        self,
        words: List[dict],
        table_borders: List[Tuple[int, int]] | None
    ) -> Tuple[List[str], List[float]]:
        """Split words into paragraphs based on vertical spacing."""
        paragraphs: List[str] = []
        current_para: List[str] = []
        prev_bottom = 0
        prev_size = 0

        paragraphs_coords: List[float] = []

        for word in words:
            if table_borders and any(border[0]-1 < word["bottom"] < border[1]+1 for border in table_borders):
                continue
            # Calculate spacing from previous line
            spacing = word["top"] - prev_bottom
            threshold = word["size"] * self.size_weight

            # Detect paragraph break
            if current_para and (spacing > threshold or
                                 (spacing < -threshold * 2 and word["size"] > prev_size * 0.75)):
                paragraphs.append(" ".join(current_para).strip())
                paragraphs_coords.append(prev_bottom)
                current_para = []

            current_para.append(word["text"])
            prev_bottom = word["bottom"]
            prev_size = word["size"]

        # Add final paragraph
        if current_para:
            paragraphs.append(" ".join(current_para).strip())
            paragraphs_coords.append(prev_bottom)

        assert len(paragraphs) == len(paragraphs_coords)

        return paragraphs, paragraphs_coords

    def _process_page_paragraphs(
        self,
        page_paragraphs: List[str],
        page_paragraphs_coords: List[float],
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
                document_paragraphs.append(
                    Paragraph(text=para,
                              id=str(para_pos),
                              payload={
                                  "para_pos": para_pos,
                                  "page_number": page_idx+1,
                                  "coord": page_paragraphs_coords[idx]
                              }
                              )
                )

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
