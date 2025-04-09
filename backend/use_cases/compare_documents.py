"""
Use case to compare to documents
"""

from io import BufferedReader, BytesIO
import logging
from typing import BinaryIO, Union
from fastapi import HTTPException
from document_comparer.graph_builder import create_graph_builder, set_best_path
from document_comparer.text_matcher import TextMatcher
from document_comparer.pdf_processor import PDFProcessor
from schemas import CompareRequest

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def compare_documents(left_file: Union[BufferedReader, BytesIO, str, BinaryIO], 
                      right_file: Union[BufferedReader, BytesIO, str, BinaryIO], 
                      args: CompareRequest, mode:str="html"):
    """
    Compare documents and get comparison report
    """
    try:
        logger.info("Split pdf into paragraphs")
        left_paragraphs = PDFProcessor(left_file, # type: ignore
                                       top=args.header_left, 
                                       bottom=args.footer_left, 
                                       size_weight=args.size_weight_left).extract_paragraphs()
        right_paragraphs = PDFProcessor(right_file, # type: ignore
                                        top=args.header_right, 
                                        bottom=args.footer_right, 
                                        size_weight=args.size_weight_right).extract_paragraphs()
        logger.info("Make comparison")
        comparison = TextMatcher(left_paragraphs, 
                                right_paragraphs, 
                                args.ratio_threshold, 
                                args.length_threshold).generate_comparison(mode)
        
        logger.info("Update headings")
        left_heading_sequence = create_graph_builder(comparison, "heading_number_left").find_best_path_in_sequence()
        set_best_path(comparison, left_heading_sequence, "heading_number_left", "heading_text_left")

        right_heading_sequence = create_graph_builder(comparison, "heading_number_right").find_best_path_in_sequence()
        set_best_path(comparison, right_heading_sequence, "heading_number_right", "heading_text_right")

        return comparison
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")    

