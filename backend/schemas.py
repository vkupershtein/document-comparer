"""
All API schemas
"""

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
