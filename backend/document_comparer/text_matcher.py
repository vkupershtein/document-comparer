"""
Module to match collections of texts
"""

from difflib import SequenceMatcher
from typing import List, Literal, Tuple, Callable, Any

from rapidfuzz import fuzz
import numpy as np
from scipy.optimize import linear_sum_assignment

from document_comparer.constants import JUNK_PATTERN
from document_comparer.paragraph import Paragraph

from .utils import align_end, align_start, get_heading_info, get_outer_positions, split_into_sentences


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
    def find_optimal_matches(cls, score_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find optimal matches for score matrix
        """
        row_idx, col_idx = linear_sum_assignment(score_matrix, maximize=True)
        return row_idx, col_idx

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

    @classmethod
    def split_combined_text(cls, text_left: Paragraph, text_right: Paragraph,
                            opcodes: List[Tuple[Literal['replace', 'delete', 'insert', 'equal'],
                                                int, int, int, int]],
                            length_threshold: float) -> Tuple[List[Paragraph], List[Paragraph]]:
        """
        Split matched texts based on opcodes and sentence boundaries.
        """
        segments_left: List[Paragraph] = []
        segments_right: List[Paragraph] = []
        current_left_index = 0
        current_right_index = 0

        _, split_pos_left = split_into_sentences(text_left.text)
        _, split_pos_right = split_into_sentences(text_right.text)
        split_pos_left.append(len(text_left.text))
        split_pos_right.append(len(text_right.text))

        for tag, left_start, left_end, right_start, right_end in opcodes:
            if ((tag == "delete" and left_end - left_start > length_threshold)
                    or (tag == "insert" and right_end - right_start > length_threshold)):
                left_start = align_start(left_start, text_left.text)
                left_end = align_end(left_end, text_left.text)
                right_start = align_start(right_start, text_right.text)
                right_end = align_end(right_end, text_right.text)

                left_start, left_end = get_outer_positions(
                    split_pos_left, left_start, left_end)
                right_start, right_end = get_outer_positions(
                    split_pos_right, right_start, right_end)

                # Append any text between previous index and new start
                if current_left_index <= left_start and current_right_index <= right_start:
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
        if current_left_index < len(text_left.text):
            segments_left.append(Paragraph(text=text_left.text[current_left_index:].strip(),
                                           id=text_left.id,
                                           payload=text_left.payload))
        if current_right_index < len(text_right.text):
            segments_right.append(Paragraph(text=text_right.text[current_right_index:].strip(),
                                            id=text_right.id,
                                            payload=text_right.payload))
        return segments_left, segments_right

    @classmethod
    def calculate_score_matrix(cls, texts_left: List[Paragraph], texts_right: List[Paragraph]) -> np.ndarray:
        """
        Calculate score matrix based on fuzzy matching ratio for two lists of texts
        """
        score_matrix = np.zeros((len(texts_left), len(texts_right)))
        for i, text1 in enumerate(texts_left):
            for j, text2 in enumerate(texts_right):
                score_matrix[i][j] = fuzz.ratio(text1.text, text2.text)
        return score_matrix

    @classmethod
    def compute_optimal_matches(cls, texts_left: List[Paragraph],
                                texts_right: List[Paragraph],
                                ratio_threshold: float) -> List[Tuple[int, Paragraph, int, Paragraph, float]]:
        """
        Compute optimal matches using score matrix and Hungarian algorithm.
        Only return matches exceeding the ratio threshold.
        """
        score_matrix = cls.calculate_score_matrix(texts_left, texts_right)
        row_idx, col_idx = cls.find_optimal_matches(score_matrix)
        return [(i, texts_left[i], j, texts_right[j], score_matrix[i][j])
                for i, j in zip(row_idx, col_idx)
                if score_matrix[i][j] > ratio_threshold]  # type: ignore

    def _update_segment(self, texts: List[Paragraph], pos: int, new_segments: List[Paragraph]) -> List[Paragraph]:
        """
        Helper to update list of texts at given position with new segments.
        """
        return texts[:pos] + new_segments + texts[pos + 1:]

    def _attempt_merge(self, idx: int, text_obj: Paragraph,
                       match_positions: List[int],
                       optimal_matches: List[Tuple[int, Paragraph, int, Paragraph, float]],
                       merge_index: int, opposing_index: int) -> bool:
        """
        Helper to try merging a text with its closest neighbour based on fuzzy ratio improvement.
        For left texts use merge_index=1 (updating text_left) and opposing_index=3 (reference text_right);
        for right texts use merge_index=3 and opposing_index=1.
        Returns True if merge occurred.
        """
        step_options = [-1, 1]
        best_diff = 0
        best_merge = None

        for step in step_options:
            neighbor_idx = self.find_closest_match(match_positions, idx, step)
            if neighbor_idx == -1:
                continue
            neighbor_match = optimal_matches[neighbor_idx]
            neighbour_para = neighbor_match[merge_index]
            neighbour_para_oppose = neighbor_match[opposing_index]
            if not (isinstance(neighbour_para, Paragraph)
                    and isinstance(neighbour_para_oppose, Paragraph)):
                continue
            # Calculate updated ratios based on merge direction
            if step == -1:
                merged_text = neighbour_para.text + \
                    ' ' + text_obj.text
            else:
                merged_text = text_obj.text + ' ' + \
                    neighbour_para.text
            updated_ratio = fuzz.ratio(
                merged_text, neighbour_para_oppose.text)
            diff = updated_ratio - neighbor_match[4]
            if diff > best_diff:
                best_diff = diff
                best_merge = (neighbor_idx, step)
        if best_diff > 0 and best_merge:
            neighbor_idx, step = best_merge
            neighbor_match = optimal_matches[neighbor_idx]
            neighbour_para = neighbor_match[merge_index]
            if not isinstance(neighbour_para, Paragraph):
                return False
            if step == -1:
                neighbour_para.text += ' ' + \
                    text_obj.text
            else:
                neighbour_para.text = text_obj.text + \
                    ' ' + neighbour_para.text
            return True
        return False

    def update_try_merge(self):
        """
        Update texts by trying to merge with neighbours using improved matching ratios.
        Uses a helper (_attempt_merge) for common merge logic.
        """
        optimal_matches = self.compute_optimal_matches(
            self.texts_left, self.texts_right, self.ratio_threshold)
        # Extract positions from optimal matches for easier lookup
        match_positions_left = [match[0] for match in optimal_matches]
        match_positions_right = [match[2] for match in optimal_matches]

        texts_left_indices = list(range(len(self.texts_left)))
        texts_right_indices = list(range(len(self.texts_right)))
        # Remove indices already matched optimally
        for pos_left, _, pos_right, _, _ in optimal_matches:
            texts_left_indices.remove(pos_left)
            texts_right_indices.remove(pos_right)

        left_indices_to_remove = []
        # Attempt merging for left side texts
        for idx in texts_left_indices:
            text_left = self.texts_left[idx]
            if self._attempt_merge(idx, text_left, match_positions_left, optimal_matches,
                                   merge_index=1, opposing_index=3):
                left_indices_to_remove.append(idx)
        for idx in sorted(left_indices_to_remove, reverse=True):
            self.texts_left.pop(idx)

        right_indices_to_remove = []
        # Attempt merging for right side texts using symmetric logic
        for idx in texts_right_indices:
            text_right = self.texts_right[idx]
            if self._attempt_merge(idx, text_right, match_positions_right, optimal_matches,
                                   merge_index=3, opposing_index=1):
                right_indices_to_remove.append(idx)
        for idx in sorted(right_indices_to_remove, reverse=True):
            self.texts_right.pop(idx)

    def update_texts_combined(self):
        """
        Update texts using optimal matching and opcodes
        to split combined texts based on sentence boundaries.
        """
        optimal_matches = self.compute_optimal_matches(
            self.texts_left, self.texts_right, self.ratio_threshold)
        # Unpack positions and texts from optimal matches
        positions_left = [match[0] for match in optimal_matches]
        matched_texts_left = [match[1] for match in optimal_matches]
        positions_right = [match[2] for match in optimal_matches]
        matched_texts_right = [match[3] for match in optimal_matches]
        match_tags = self.get_match_tags(
            matched_texts_left, matched_texts_right)

        # Process in reverse order to avoid list index shifts
        for j, opcodes in enumerate(reversed(match_tags)):
            pos = len(match_tags) - 1 - j
            left_position = positions_left[pos]
            right_position = positions_right[pos]
            updated_left, updated_right = self.split_combined_text(
                matched_texts_left[pos],
                matched_texts_right[pos],
                opcodes,
                self.length_threshold
            )
            self.texts_left = self._update_segment(
                self.texts_left, left_position, updated_left)
            self.texts_right = self._update_segment(
                self.texts_right, right_position, updated_right)

        # Remove any texts that are empty
        self.texts_left = [t for t in self.texts_left if t.text.strip()]
        self.texts_right = [t for t in self.texts_right if t.text.strip()]

    def generate_comparison(self, mode: str = "html"):
        """
        Generate comparison object        
        """
        # Run the splitting phase twice
        self.update_texts_combined()
        self.update_texts_combined()
        self.update_try_merge()
        optimal_matches = self.compute_optimal_matches(
            self.texts_left, self.texts_right, self.ratio_threshold)

        comparison_obj = []
        texts_left_indices = list(range(len(self.texts_left)))
        texts_right_indices = list(range(len(self.texts_right)))

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
                "position": pos_left,
                "position_secondary": pos_right,
                "heading_number_left": heading_number_left,
                "heading_text_left": heading_text_left,
                "heading_number_right": heading_number_right,
                "heading_text_right": heading_text_right
            }
            comparison_obj.append(item)
            texts_left_indices.remove(pos_left)
            texts_right_indices.remove(pos_right)

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
        match_positions_right = [match[2]
                                 for match in optimal_matches] if optimal_matches else []
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
                "position": pos_left,
                "position_secondary": pos_right,
                "heading_number_left": "",
                "heading_text_left": "",
                "heading_number_right": heading_number_right,
                "heading_text_right": heading_text_right
            }
            comparison_obj.append(item)

        return comparison_obj
