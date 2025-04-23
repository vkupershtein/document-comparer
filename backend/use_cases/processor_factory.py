"""
Module to create file processor
"""

from io import BufferedReader, BytesIO
from typing import BinaryIO, Union

from fastapi import UploadFile
from internal.notifier import ThresholdNotifier
from internal.schemas import CompareRequestSingle
from document_comparer.pdf_processor import PDFProcessor
from document_comparer.excel_processor import ExcelProcessor


def create_document_processor(file_object: Union[BufferedReader, BytesIO, str, BinaryIO],
                              args: CompareRequestSingle, mode: str,
                              threshold_notifier: ThresholdNotifier):
    """
    Create document processor: PDF or Excel
    """
    if mode == 'excel' and args.text_column:
        return ExcelProcessor(file_object,  # type: ignore
                              args.text_column,
                              args.id_column)
    elif mode == 'pdf':
        return PDFProcessor(file_object, top=args.header,  # type: ignore
                            bottom=args.footer,
                            size_weight=args.size_weight,
                            threshold_notifier=threshold_notifier)
    raise ValueError('Processing mode should be either "excel" or "pdf"')


def detect_file_type(upload_file: UploadFile) -> str:
    """
    Detect file type xlsx or pdf by content type
    """
    content_type = upload_file.content_type
    if content_type == "application/pdf":
        return "pdf"
    if content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.ms-excel"]:
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
