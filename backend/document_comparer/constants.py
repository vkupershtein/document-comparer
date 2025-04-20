"""
Module with global contants
"""
import re

HEADING_PATTERN = re.compile(r"^((?:[1-9]{1}\d*\.*)+\d*)\s*([A-Z0-9][A-Za-z]+.*)")
JUNK_PATTERN = re.compile(r'[-|_|\*\s]')
HARD_RECURSION_ITER_LIMIT = 150000
