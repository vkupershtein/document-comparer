"""
All API schemas
"""

from typing import List
from pydantic import BaseModel, Field

class CompareRequest(BaseModel):
    """
    Base arguments for compare
    """
    header_left: int = Field(default=0)
    footer_left: int = Field(default=0)
    size_weight_left: float = Field(default=0.8)
    header_right: int = Field(default=0)
    footer_right: int = Field(default=0)
    size_weight_right: float = Field(default=0.8)
    ratio_threshold: float = Field(default=0.5)
    length_threshold: int = Field(default=80)

class TaggedSubtext(BaseModel):
    """
    Tagged subtext model
    """
    tag: str
    subtext: str

class CompareResult(BaseModel):
    """
    Model for compare results
    """
    ratio: float
    type: str
    text_left_id: str
    text_left: str
    text_right_id: str
    text_right: str
    text_left_report: str | List[TaggedSubtext]
    text_right_report: str | List[TaggedSubtext]
    heading_number_left: str
    heading_text_left: str
    heading_number_right: str
    heading_text_right: str

class CompareResponse(BaseModel):
    """
    Compare response for API
    """
    comparison: List[CompareResult]
