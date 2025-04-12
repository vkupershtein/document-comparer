"""
Module to create file processor
"""

from io import BufferedReader, BytesIO
from typing import BinaryIO, Union

from fastapi import UploadFile
from schemas import CompareRequestSingle
from document_comparer.pdf_processor import PDFProcessor
from document_comparer.excel_processor import ExcelProcessor


def create_document_processor(file_object: Union[BufferedReader, BytesIO, str, BinaryIO], 
                              args: CompareRequestSingle, mode: str):
    if mode == 'excel' and args.text_column:
        return ExcelProcessor(file_object, args.text_column, args.id_column) # type: ignore
    elif mode == 'pdf':
        return PDFProcessor(file_object, top=args.header,  # type: ignore
                                       bottom=args.footer, 
                                       size_weight=args.size_weight)
    raise ValueError('Processing mode should be either "excel" or "pdf"')

def detect_file_type(upload_file: UploadFile) -> str:
    content_type = upload_file.content_type
    if content_type == "application/pdf":
        return "pdf"
    elif content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        return "excel"
    return "unknown"

def detect_file_type_on_name(filename: str) -> str:
    """
    Detect file type on file name
    """
    try:
        pos = filename.rfind('.')
        extension = filename[pos+1:]
        if extension == 'xlsx':
            return 'excel'
        elif extension == 'pdf':
            return 'pdf'
        return 'unknown'
    except ValueError as ex:
        raise ValueError('File must have "xlsx" or "pdf" type') from ex