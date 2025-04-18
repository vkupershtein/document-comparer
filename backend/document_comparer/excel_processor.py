"""
Module to process Excel files
and extract paragraphs from them
"""

from io import BufferedReader, BytesIO
from typing import List, Union

import pandas as pd
from document_comparer.paragraph import Paragraph
from document_comparer.processor_protocol import DocumentProcessor


class ExcelProcessor(DocumentProcessor):
    """
    Exctracting paragraphs from excel file
    """

    def __init__(self,
                 file_object: Union[BufferedReader, BytesIO, str],
                 text_column: str,
                 id_column: str | None = None):
        self.text_column = text_column
        self.id_column = id_column
        self.dataframe = pd.read_excel(file_object)
        self.dataframe = self.dataframe[self.dataframe[self.text_column].notna(
        )]

    def extract_paragraphs(self) -> List[Paragraph]:
        """
        Extract paragraphs from excel file with metadata
        """
        return [Paragraph(text=record[self.text_column],
                          id=record[self.id_column] if self.id_column else str(
                              i),
                          payload={key: value for key, value in record.items()
                                   # type: ignore
                                   if key not in [self.text_column, self.id_column]} | {"para_pos": i})
                for i, record in enumerate(self.dataframe.to_dict("records"))]
