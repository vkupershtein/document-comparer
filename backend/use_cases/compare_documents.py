"""
Use case to compare to documents
"""

from io import BufferedReader, BytesIO
import logging
from typing import BinaryIO, Union
from use_cases.processor_factory import create_document_processor
from document_comparer.graph_builder import create_graph_builder, set_best_path
from document_comparer.text_matcher import TextMatcher
from internal.schemas import CompareRequest, CompareRequestSingle
from internal.notifier import Notifier

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def compare_documents(left_file: Union[BufferedReader, BytesIO, str, BinaryIO],
                      left_file_type: str,
                      right_file: Union[BufferedReader, BytesIO, str, BinaryIO],
                      right_file_type: str,
                      args: CompareRequest,
                      notifier: Notifier,
                      mode: str = "html"):
    """
    Compare documents and get comparison report
    """
    logger.info("Split pdf into paragraphs")
    left_paragraphs = create_document_processor(left_file,
                                                CompareRequestSingle(header=args.header_left,
                                                                     footer=args.footer_left,
                                                                     size_weight=args.size_weight_left,
                                                                     text_column=args.text_column_left,
                                                                     id_column=args.id_column_left),
                                                left_file_type).extract_paragraphs()
    notifier.notify(25)
    right_paragraphs = create_document_processor(right_file,
                                                 CompareRequestSingle(header=args.header_right,
                                                                      footer=args.footer_right,
                                                                      size_weight=args.size_weight_right,
                                                                      text_column=args.text_column_right,
                                                                      id_column=args.id_column_right),
                                                 right_file_type).extract_paragraphs()
    notifier.notify(40)
    logger.info("Make comparison")
    comparison = TextMatcher(left_paragraphs,
                             right_paragraphs,
                             args.ratio_threshold,
                             args.length_threshold,
                             notifier).generate_comparison(mode)

    logger.info("Update headings")
    left_heading_sequence = create_graph_builder(
        comparison, "heading_number_left").find_best_path_in_sequence()
    set_best_path(comparison, left_heading_sequence,
                  "heading_number_left", "heading_text_left")

    right_heading_sequence = create_graph_builder(
        comparison, "heading_number_right").find_best_path_in_sequence()
    set_best_path(comparison, right_heading_sequence,
                  "heading_number_right", "heading_text_right")
    notifier.notify(99)

    return comparison
