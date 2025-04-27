"""
Module to match collections of texts
"""

from difflib import SequenceMatcher
from typing import List, Tuple, Callable, Any

from document_comparer.optimal_assignment import compute_optimal_matches
from document_comparer.constants import JUNK_PATTERN
from document_comparer.paragraph import Paragraph
from document_comparer.paragraph_merger import ParagraphMerger
from document_comparer.paragraph_utils import sorted_paragraphs
from document_comparer.utils import get_heading_info, split_into_sentences
from internal.constants import COMPLETE_SECOND, COMPLETE_SPLIT
from internal.notifier import Notifier

COMPLETE_MIDDLE = (COMPLETE_SPLIT + COMPLETE_SECOND) // 2


class TextMatcher:
    """
    Class to optimally match two lists of texts
    """

    def __init__(self, texts_left: List[Paragraph],
                 texts_right: List[Paragraph],
                 ratio_threshold: float,
                 length_threshold: int,
                 notifier: Notifier = Notifier(None, None)):
        """
        Constructor of text matcher instance
        """
        self.texts_left: List[Paragraph] = texts_left
        self.texts_right: List[Paragraph] = texts_right
        self.ratio_threshold = ratio_threshold * 100
        self.update_ratio_threshold = 90.0
        self.length_threshold = length_threshold
        self.notifier = notifier

    def find_closest_match(self, match_positions: List[int], text_position: int, step: int) -> int:
        """
        Find the index of the closest match given a list of match positions.
        Returns -1 if no valid match is found.
        """
        if step == 0:
            return -1
        limit_position = min(
            match_positions) if step < 0 else max(match_positions)
        match_positions_set = set(match_positions)
        current_position = text_position
        while current_position not in match_positions_set:
            current_position += step
            if (step < 0 and current_position < limit_position) or (step > 0 and current_position > limit_position):
                return -1
        return match_positions.index(current_position)

    @classmethod
    def get_edit_operations(cls, text_left: str, text_right: str, junk: Any = None):
        """
        Get edit operations using SequenceMatcher
        """
        matcher = SequenceMatcher(junk, text_left, text_right)
        return matcher.get_opcodes()

    @classmethod
    def is_changed(cls, tag: str, subtext_left: str, subtext_right: str) -> bool:
        """
        Determine if text was changed (ignoring junk)
        """
        if tag == 'equal':
            return False
        clean_left = JUNK_PATTERN.sub('', subtext_left)
        clean_right = JUNK_PATTERN.sub('', subtext_right)
        return clean_left != clean_right

    @classmethod
    def _get_report(cls, text_left: str, text_right: str,
                    formatter: Callable[[str, str, str, bool], Tuple[Any, Any, bool]]) -> Tuple[Any, Any, bool]:
        """
        Private helper that runs over the edit operations and formats reports.
        The formatter callback is responsible for processing one opcode.
        """
        opcodes = cls.get_edit_operations(
            text_left, text_right, lambda x: x == " ")
        report_left = []
        report_right = []
        changed = False
        for tag, i1, i2, j1, j2 in opcodes:
            sub_left = text_left[i1:i2]
            sub_right = text_right[j1:j2]
            if not (sub_left.strip() or sub_right.strip()):
                continue
            # Determine if the text has changed
            sub_changed = cls.is_changed(tag, sub_left, sub_right)
            # When content is visually the same, treat as equal
            if tag != 'equal' and not sub_changed:
                tag = 'equal'
            left_part, right_part, sub_changed = formatter(
                tag, sub_left, sub_right, sub_changed)
            report_left.append(left_part)
            report_right.append(right_part)
            changed = changed or sub_changed
        return report_left, report_right, changed

    @classmethod
    def _html_formatter(cls, tag: str, sub_left: str, sub_right: str,
                        sub_changed: bool) -> Tuple[str, str, bool]:
        """
        Formatter for HTML reporting
        """
        if tag == "delete":
            sub_left = f'<span style="color: #FF3131;text-decoration: line-through;">{sub_left}</span>'
        elif tag == "replace":
            sub_left = f'<span style="color: #FFBF00;">{sub_left}</span>'
            sub_right = f'<span style="color: #FFBF00;">{sub_right}</span>'
        elif tag == "insert":
            sub_right = f'<span style="color: #50C878;">{sub_right}</span>'
        return sub_left, sub_right, sub_changed

    @classmethod
    def _json_formatter(cls, tag: str, sub_left: str, sub_right: str,
                        sub_changed: bool) -> Tuple[dict, dict, bool]:
        """
        Formatter for JSON reporting
        """
        return {"tag": tag, "subtext": sub_left}, {"tag": tag, "subtext": sub_right}, sub_changed

    @classmethod
    def get_match_html_report(cls, text_left: str, text_right: str) -> Tuple[str, str, bool]:
        """
        Get match report with HTML tags
        """
        report_left, report_right, changed = cls._get_report(
            text_left, text_right, cls._html_formatter)
        return "".join(report_left), "".join(report_right), changed

    @classmethod
    def get_match_json_report(cls, text_left: str, text_right: str) -> Tuple[List[dict], List[dict], bool]:
        """
        Get match report as JSON
        """
        return cls._get_report(text_left, text_right, cls._json_formatter)

    @classmethod
    def get_match_tags(cls, matched_texts_left: List[Paragraph],
                       matched_texts_right: List[Paragraph]):
        """
        Get match tags (or opcodes) for each pair
        """
        return [cls.get_edit_operations(l.text, r.text)
                for l, r in zip(matched_texts_left, matched_texts_right)]

    def _update_segment(self, texts: List[Paragraph], pos: int, new_segments: List[Paragraph]) -> List[Paragraph]:
        """
        Helper to update list of texts at given position with new segments.
        """
        return texts[:pos] + new_segments + texts[pos + 1:]

    def get_unmatched_texts_indices(self, match_positions_left: List[int],
                                    match_positions_right: List[int]):
        """
        Get indices of the unmatched texts. 
        These are texts that were potentially removed or added
        """
        texts_left_indices = list(range(len(self.texts_left)))
        texts_right_indices = list(range(len(self.texts_right)))
        # Remove indices already matched optimally
        for pos_left, pos_right in zip(match_positions_left, match_positions_right):
            texts_left_indices.remove(pos_left)
            texts_right_indices.remove(pos_right)
        return texts_left_indices, texts_right_indices

    @classmethod
    def split_paragraph(cls, para: Paragraph) -> List[Paragraph]:
        """
        Split paragraph into sentence paragraphs
        """
        texts, _ = split_into_sentences(para.text)
        return [Paragraph(text=text, id=para.id, payload={**para.payload, "sent_pos": i})
                for i, text in enumerate(texts)]    

    def update_merge_paragraphs(self):
        """
        Update paragraphs by merging neighbours based on matches

        Delegates the actual merging to the ParagraphMerger class
        """
        merger = ParagraphMerger(notifier=self.notifier)        

        updated_paragraphs_left, updated_paragraphs_right = merger.merge_paragraph_pipeline(self.texts_left,
                                                                                    self.texts_right,
                                                                                    self.update_ratio_threshold)

        self.texts_left = sorted_paragraphs(updated_paragraphs_left)
        self.texts_right = sorted_paragraphs(updated_paragraphs_right)

    def update_split_paragraphs(self):
        """
        Update paragraphs by splitting into sentences those that were unmatched        
        """
        optimal_matches = compute_optimal_matches(
            self.texts_left, self.texts_right, self.update_ratio_threshold)
        # Extract positions from optimal matches for easier lookup
        match_positions_left = [match[0] for match in optimal_matches]
        updated_paragraphs_left = [match[1] for match in optimal_matches]
        match_positions_right = [match[2] for match in optimal_matches]
        updated_paragraphs_right = [match[3] for match in optimal_matches]

        texts_left_indices, texts_right_indices = self.get_unmatched_texts_indices(
            match_positions_left, match_positions_right
        )

        for para in updated_paragraphs_left:
            para.payload["sent_pos"] = 0

        for para in updated_paragraphs_right:
            para.payload["sent_pos"] = 0

        for i, idx_left in enumerate(texts_left_indices):
            para = self.texts_left[idx_left]
            updated_paragraphs_left += self.split_paragraph(para)
            self.notifier.loop_notify(i, COMPLETE_SECOND, COMPLETE_MIDDLE,
                                      len(texts_left_indices))

        for i, idx_right in enumerate(texts_right_indices):
            para = self.texts_right[idx_right]
            updated_paragraphs_right += self.split_paragraph(para)
            self.notifier.loop_notify(i, COMPLETE_MIDDLE, 
                                      COMPLETE_SPLIT, len(texts_right_indices))

        self.texts_left = sorted_paragraphs(updated_paragraphs_left)
        self.texts_right = sorted_paragraphs(updated_paragraphs_right)

    def generate_comparison(self, mode: str = "html"):
        """
        Generate comparison object        
        """
        # Run the splitting phase twice
        self.update_split_paragraphs()
        self.update_merge_paragraphs()
        optimal_matches = compute_optimal_matches(
            self.texts_left, self.texts_right, self.ratio_threshold)

        match_positions_left = [match[0] for match in optimal_matches]
        match_positions_right = [match[2] for match in optimal_matches]

        texts_left_indices, texts_right_indices = self.get_unmatched_texts_indices(
            match_positions_left, match_positions_right
        )

        comparison_obj = []

        # Select reporting method based on mode
        report_method: Callable[[str, str], Tuple[Any, Any, bool]] = (
            self.get_match_html_report if mode == "html" else self.get_match_json_report
        )

        for pos_left, text_left, pos_right, text_right, ratio in optimal_matches:
            heading_number_left, heading_text_left = get_heading_info(
                text_left.text)
            heading_number_right, heading_text_right = get_heading_info(
                text_right.text)
            report_left, report_right, changed = report_method(
                text_left.text, text_right.text)
            item = {
                "ratio": round(ratio / 100, 4) if changed else 1.0,
                "type": "changed" if changed else "same",
                "text_left_id": text_left.id,
                "text_left": text_left.text,
                "text_right_id": text_right.id,
                "text_right": text_right.text,
                "text_left_report": report_left,
                "text_right_report": report_right,
                "page_number_left": text_left.payload.get("page_number", ""),
                "page_number_right": text_right.payload.get("page_number", ""),
                "position": pos_left,
                "position_secondary": pos_right,
                "heading_number_left": heading_number_left,
                "heading_text_left": heading_text_left,
                "heading_number_right": heading_number_right,
                "heading_text_right": heading_text_right
            }
            comparison_obj.append(item)

        # Process texts that were removed
        for idx in texts_left_indices:
            text_left = self.texts_left[idx]
            heading_number_left, heading_text_left = get_heading_info(
                text_left.text)
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
                "page_number_left": text_left.payload.get("page_number", ""),
                "page_number_right": "",
                "position": idx,
                "position_secondary": 0,
                "heading_number_left": heading_number_left,
                "heading_text_left": heading_text_left,
                "heading_number_right": "",
                "heading_text_right": ""
            }
            comparison_obj.append(item)

        # Process texts that are new on the right side.
        # We use the last match in optimal_matches to position the new text nearby.
        for idx in texts_right_indices:
            text_right = self.texts_right[idx]
            heading_number_right, heading_text_right = get_heading_info(
                text_right.text)
            _, report_right, _ = report_method("", text_right.text)
            # For new texts, we use the closest match (if any) to assign a position.
            closest_match_index = self.find_closest_match(
                match_positions_right, idx, -1) if match_positions_right else -1
            if closest_match_index != -1:
                pos_left = optimal_matches[closest_match_index][0]
                pos_right = optimal_matches[closest_match_index][2]
            else:
                pos_left = pos_right = 0
            item = {
                "ratio": 0,
                "type": "new",
                "text_left_id": "",
                "text_left": "",
                "text_right_id": text_right.id,
                "text_right": text_right.text,
                "text_left_report": "",
                "text_right_report": report_right,
                "page_number_left": "",
                "page_number_right": text_right.payload.get("page_number", ""),                
                "position": pos_left,
                "position_secondary": pos_right,
                "heading_number_left": "",
                "heading_text_left": "",
                "heading_number_right": heading_number_right,
                "heading_text_right": heading_text_right
            }
            comparison_obj.append(item)

        return comparison_obj
