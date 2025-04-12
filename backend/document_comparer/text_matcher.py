"""
Module to match collections of texts
"""

from difflib import SequenceMatcher
import re
from typing import List, Tuple

from rapidfuzz import fuzz
import numpy as np
from scipy.optimize import linear_sum_assignment

from document_comparer.constants import JUNK_PATTERN
from document_comparer.paragraph import Paragraph

from .utils import get_heading_info

class TextMatcher:
    """
    Class to optimally match two lists of texts
    """

    def __init__(self, texts_left: List[Paragraph], 
                 texts_right: List[Paragraph], 
                 ratio_threshold: float, 
                 length_threshold: int):
        """
        Constructor of text matcher instance
        """
        self.texts_left: List[Paragraph] = texts_left
        self.texts_right: List[Paragraph] = texts_right
        self.ratio_threshold = ratio_threshold * 100
        self.length_threshold = length_threshold

    @classmethod
    def find_optimal_matches(cls, score_matrix):
        """
        Find optimal matches for score matrix
        """
        row_idx, col_idx = linear_sum_assignment(score_matrix, maximize=True)

        return row_idx, col_idx
    
    @classmethod
    def get_edit_operations(cls, text_left: str, text_right: str, junk=None):
        """
        Get edit operations
        """
        matcher = SequenceMatcher(junk, text_left, text_right)
        return matcher.get_opcodes()
    
    @classmethod
    def is_changed(cls, tag, subtext_left: str, subtext_right: str) -> bool:
        if tag == 'equal':
            return False
        cleaned_subtext_left = JUNK_PATTERN.sub('', subtext_left)
        cleaned_subtext_right = JUNK_PATTERN.sub('', subtext_right)
        return cleaned_subtext_left != cleaned_subtext_right 
    
    @classmethod
    def get_match_html_report(cls, text_left: str, text_right: str):
        """
        Get match report with HTML tags
        """
        opcodes = cls.get_edit_operations(text_left, text_right, lambda x: x == " ")
        report_left = []
        report_right = []
        changed = False
        for tag, i1, i2, j1, j2 in opcodes:
            subtext_left = text_left[i1:i2]
            subtext_right = text_right[j1:j2]
            if not (subtext_left.strip() or subtext_right.strip()):
                continue
            subtext_changed = cls.is_changed(tag, subtext_left, subtext_right)
            if tag != 'equal' and not subtext_changed:
                tag = 'equal'            
            if tag == "delete":                
                subtext_left = f'<span style="color: #FF3131;text-decoration: line-through;">{subtext_left}</span>'
            elif tag == "replace":               
                subtext_left = f'<span style="color: #FFBF00;">{subtext_left}</span>'
                subtext_right = f'<span style="color: #FFBF00;">{subtext_right}</span>'
            elif tag == "insert":
                subtext_right = f'<span style="color: #50C878;">{subtext_right}</span>'
            report_left.append(subtext_left)
            report_right.append(subtext_right)
            changed = changed or subtext_changed
        return "".join(report_left), "".join(report_right), changed
    
    @classmethod
    def get_match_json_report(cls, text_left: str, text_right: str):
        """
        Get match report with HTML tags
        """
        opcodes = cls.get_edit_operations(text_left, text_right, lambda x: x == " ")
        report_left = []
        report_right = []
        changed = False
        for tag, i1, i2, j1, j2 in opcodes:
            subtext_left = text_left[i1:i2]
            subtext_right = text_right[j1:j2]
            if not (subtext_left.strip() or subtext_right.strip()):
                continue
            subtext_changed = cls.is_changed(tag, subtext_left, subtext_right)
            if tag != 'equal' and not subtext_changed:
                tag = 'equal'                       
            report_left.append({"tag": tag, "subtext": subtext_left})
            report_right.append({"tag": tag, "subtext": subtext_right})
            changed = changed or subtext_changed
        return report_left, report_right, changed 
        
    
    @classmethod
    def get_match_tags(cls, matched_texts_left: List[Paragraph], 
                       matched_texts_right: List[Paragraph]):
        """
        Get match tags (or opcodes) from SequenceMatcher
        """
        all_opcodes = []
        for text_left, text_right in zip(matched_texts_left, matched_texts_right):            
            all_opcodes.append(cls.get_edit_operations(text_left.text, text_right.text))
        return all_opcodes

    @classmethod
    def find_closest_match(cls, match_positions: List[int], text_position: int, step: int) -> int:
        """
        Find closest match to text if position is known
        """   
        if step == 0:
            return -1
        limit_position = min(match_positions) if step < 0 else max(match_positions)
        match_positions_set = set(match_positions)
        current_position = text_position
        while current_position not in match_positions_set:
            current_position += step
            limit_condition = current_position < limit_position if step < 0 else current_position > limit_position
            if limit_condition:
                return -1
        return match_positions.index(current_position)
  
    @classmethod
    def split_combined_text(cls, text_left: Paragraph, text_right: Paragraph,
                             positions: List[Tuple[str, int, int, int, int]], 
                             length_threshold: float) -> Tuple[List[Paragraph], List[Paragraph]]:
        """
        Split matched texts
        """
        segments_left: List[Paragraph] = []
        segments_right: List[Paragraph] = []
        current_left_index = 0
        current_right_index = 0

        first = True

        for tag, left_start, left_end, right_start, right_end in positions:
            if ((tag == "delete" and left_end-left_start > length_threshold) 
                    or (tag == "insert" and right_end-right_start > length_threshold)):                
                if not first:
                    segments_left.append(Paragraph(text=text_left.text[current_left_index:left_start].strip(), 
                                                   id=text_left.id,
                                                   payload=text_left.payload))
                    segments_right.append(Paragraph(text=text_right.text[current_right_index:right_start].strip(), 
                                                    id=text_right.id,
                                                   payload=text_right.payload))
                segments_left.append(Paragraph(text=text_left.text[left_start:left_end].strip(), 
                                               id=text_left.id,
                                               payload=text_left.payload))
                segments_right.append(Paragraph(text=text_right.text[right_start:right_end].strip(), 
                                                id=text_right.id,
                                                payload=text_right.payload))                
                current_left_index = left_end            
                current_right_index = right_end
            first = False
        if current_left_index < len(text_left.text):
            segments_left.append(Paragraph(text=text_left.text[current_left_index:].strip(), id=text_left.id,
                                                   payload=text_left.payload))
        if current_right_index < len(text_right.text):
            segments_right.append(Paragraph(text=text_right.text[current_right_index:].strip(), id=text_right.id,
                                                   payload=text_right.payload))                                
        return segments_left, segments_right 

    @classmethod
    def calculate_score_matrix(cls, texts_left: List[Paragraph], texts_right: List[Paragraph]):
        """
        Calculate score matrix for two lists of texts
        """
        score_matrix = np.zeros((len(texts_left), len(texts_right)))

        for i, text1 in enumerate(texts_left):
            for j, text2 in enumerate(texts_right):
                score_matrix[i][j] = fuzz.ratio(text1.text, text2.text)

        return score_matrix
    
    @classmethod
    def compute_optimal_matches(cls, texts_left: List[Paragraph], 
                                texts_right: List[Paragraph], 
                                ratio_threshold) -> List[Tuple[int, Paragraph, int, Paragraph, float]]:
        """
        Compute optimal matches algorithm
        """
        score_matrix = cls.calculate_score_matrix(texts_left, texts_right)
        row_idx, col_idx = cls.find_optimal_matches(score_matrix)
        return [(i, texts_left[i], j, texts_right[j], score_matrix[i][j]) 
                                for i, j in zip(row_idx, col_idx) 
                                if score_matrix[i][j] > ratio_threshold]     # type: ignore
                
    def update_texts_combined(self):
        """
        Update texts using optimal matching 
        and match tags
        """
        optimal_matches = self.compute_optimal_matches(self.texts_left, 
                                                       self.texts_right, 
                                                       self.ratio_threshold)
        positions_left, matched_texts_left, positions_right, matched_texts_right, _ = zip(*optimal_matches)
        match_tags = self.get_match_tags(matched_texts_left, matched_texts_right) # type: ignore

        tags_length = len(match_tags)

        for i, opcodes in enumerate(reversed(match_tags), 1):

            j = tags_length - i

            left_position = positions_left[j]
            right_position = positions_right[j]

            updated_texts_left, updated_texts_right = self.split_combined_text(matched_texts_left[j],
                                                                               matched_texts_right[j],
                                                                               opcodes,
                                                                               self.length_threshold)
            self.texts_left = (self.texts_left[:left_position] 
                               + updated_texts_left 
                               + self.texts_left[left_position+1:])         

            self.texts_right = (self.texts_right[:right_position] 
                                + updated_texts_right 
                                + self.texts_right[right_position+1:])
                       
        self.texts_left = [text for text in self.texts_left if len(text.text) > 0]
        self.texts_right = [text for text in self.texts_right if len(text.text) > 0]             

    def generate_comparison(self, mode:str="html"):
        """
        Generate comparison object
        """
        self.update_texts_combined()
        self.update_texts_combined()
        optimal_matches = self.compute_optimal_matches(self.texts_left, 
                                                       self.texts_right, 
                                                       self.ratio_threshold)
        
        comparison_obj = []

        texts_left_indices = list(range(len(self.texts_left)))
        texts_right_indices = list(range(len(self.texts_right)))

        report_method = self.get_match_html_report if mode == "html" else self.get_match_json_report

        for position_left, text_left, position_right, text_right, ratio in optimal_matches:            
            heading_number_left, heading_text_left = get_heading_info(text_left.text)
            heading_number_right, heading_text_right = get_heading_info(text_right.text)           
            report_left, report_right, changed = report_method(text_left.text, text_right.text)            
            item = {
                "ratio": float(round(ratio/100, 4)),
                "type": "changed" if changed else "same",
                "text_left_id": text_left.id,
                "text_left": text_left.text,
                "text_right_id": text_right.id,
                "text_right": text_right.text,                 
                "text_left_report": report_left,
                "text_right_report": report_right,
                "position": int(position_left),
                "position_secondary": int(position_right),
                "heading_number_left": heading_number_left,
                "heading_text_left": heading_text_left,
                "heading_number_right": heading_number_right,
                "heading_text_right": heading_text_right                
            }

            comparison_obj.append(item)
            texts_left_indices.remove(position_left)
            texts_right_indices.remove(position_right)
        
        for idx_left in texts_left_indices:
            text_left = self.texts_left[idx_left]
            heading_number_left, heading_text_left = get_heading_info(text_left.text)
            report_left, _, _ = report_method(text_left.text, "")
            item = {
                "ratio": 0,
                "type": "removed",
                "text_left_id": text_left.id,
                "text_left": text_left.text,
                "text_right_id": "",
                "text_right": "",                
                "text_left_report": report_left,
                "text_right_report": "",
                "position": int(idx_left),
                "position_secondary": 0,
                "heading_number_left": heading_number_left,
                "heading_text_left": heading_text_left,
                "heading_number_right": "",
                "heading_text_right": ""                                                
            }

            comparison_obj.append(item)

        _, _, match_positions_right, _, _ = zip(*optimal_matches)        

        for idx_right in texts_right_indices:
            text_right = self.texts_right[idx_right]
            heading_number_right, heading_text_right = get_heading_info(text_right.text) 
            _, report_right, _ = report_method("", text_right.text)
            closest_match_index = self.find_closest_match(match_positions_right, idx_right, -1) # type: ignore
            closest_match = optimal_matches[closest_match_index]
            item = {
                "ratio": 0,
                "type": "new",
                "text_left_id": "",
                "text_left": "",
                "text_right_id": text_right.id,                
                "text_right": text_right.text,
                "text_left_report": "",                
                "text_right_report": report_right,
                "position": int(closest_match[0]),
                "position_secondary": int(closest_match[2]),
                "heading_number_left": "",
                "heading_text_left": "",                 
                "heading_number_right": heading_number_right,
                "heading_text_right": heading_text_right                               
            }

            comparison_obj.append(item)        
        
        return comparison_obj   

    