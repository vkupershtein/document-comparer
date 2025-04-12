"""
Module with global contants
"""
import re

HEADING_PATTERN = re.compile(r"^(?:((?:[1-9]+\.)*[1-9]+\.*)\s*([A-Z0-9].+))")
JUNK_PATTERN = re.compile(r'[-|_|\*\s]')