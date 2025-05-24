"""
Module to match collections of texts
"""

import logging
from typing import List, Tuple, Callable, Any

from Levenshtein import opcodes as match_opcodes

from document_comparer.merge_strategies import (join_optimize_paragraph_matches,
                                                matched_condition,
                                                merge_matches_on_condition,
                                                unmatched_condition_no_id,
                                                unmatched_condition_with_id)
from document_comparer.optimal_assignment import compute_optimal_matches
from document_comparer.constants import JUNK_PATTERN
from document_comparer.paragraph import Paragraph, ParagraphMatch
from document_comparer.paragraph_utils import sorted_paragraphs
from document_comparer.utils import (
    define_lang_model, split_texts_into_sentences_lib, split_texts_into_sentences)
from internal.constants import COMPLETE_MERGE, COMPLETE_SECOND, COMPLETE_SPLIT
from internal.notifier import Notifier

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

COMPLETE_MIDDLE = (COMPLETE_SPLIT + COMPLETE_SECOND) // 2


class TextMatcher:
    """
    Class to optimally match two lists of texts
    """

    def __init__(self, texts_left: List[Paragraph],
                 texts_right: List[Paragraph],
                 ratio_threshold: float,
                 length_threshold: int,
                 file_type_left: str = "pdf",
                 file_type_right: str = "pdf",
                 notifier: Notifier = Notifier(None, None)):
        """
        Constructor of text matcher instance
        """
        self.texts_left: List[Paragraph] = texts_left
        self.texts_right: List[Paragraph] = texts_right
        self.ratio_threshold = ratio_threshold * 100
        self.update_ratio_threshold = 99.0
        self.length_threshold = length_threshold
        self.file_type_left = file_type_left
        self.file_type_right = file_type_right
        self.notifier = notifier
        self.nlp_model = define_lang_model(
            [para.text for para in texts_left + texts_right])
        logger.info('Using NLP model: %s', 
                    self.nlp_model.lang if self.nlp_model else 'no model')        

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
    def get_edit_operations(cls, text_left: str, text_right: str):
        """
        Get edit operations using Levenshtein
        """
        return match_opcodes(text_left, text_right)

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
    def get_subchanges(cls, text_left: str, text_right: str, opcodes=None) -> List[bool]:
        """
        Get subchanges in texts
        """
        if opcodes is None:
            opcodes = cls.get_edit_operations(text_left, text_right)
        subchanges = []
        for tag, i1, i2, j1, j2 in opcodes:
            sub_left = text_left[i1:i2]
            sub_right = text_right[j1:j2]
            if not (sub_left.strip() or sub_right.strip()):
                subchanges.append(False)
            # Determine if the text has changed
            sub_changed = cls.is_changed(tag, sub_left, sub_right)
            subchanges.append(sub_changed)
        return subchanges

    @classmethod
    def is_fully_changed(cls, text_left: str, text_right: str):
        """
        Check if text is fully changed
        """
        subchanges = cls.get_subchanges(text_left, text_right)
        return any(subchanges)

    @classmethod
    def _get_report(cls, text_left: str, text_right: str,
                    formatter: Callable[[str, str, str], Tuple[Any, Any]]) -> Tuple[Any, Any]:
        """
        Private helper that runs over the edit operations and formats reports.
        The formatter callback is responsible for processing one opcode.
        """
        opcodes = cls.get_edit_operations(text_left, text_right)
        report_left = []
        report_right = []
        subchanges = cls.get_subchanges(text_left, text_right, opcodes)
        for (tag, i1, i2, j1, j2), sub_changed in zip(opcodes, subchanges):
            sub_left = text_left[i1:i2]
            sub_right = text_right[j1:j2]
            if not (sub_left.strip() or sub_right.strip()):
                continue
            # When content is visually the same, treat as equal
            if tag != 'equal' and not sub_changed:
                tag = 'equal'
            left_part, right_part = formatter(tag, sub_left, sub_right)
            report_left.append(left_part)
            report_right.append(right_part)
        return report_left, report_right

    @classmethod
    def _html_formatter(cls, tag: str, sub_left: str, sub_right: str) -> Tuple[str, str]:
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
        return sub_left, sub_right

    @classmethod
    def _json_formatter(cls, tag: str, sub_left: str,
                        sub_right: str) -> Tuple[dict, dict]:
        """
        Formatter for JSON reporting
        """
        return {"tag": tag, "subtext": sub_left}, {"tag": tag, "subtext": sub_right}

    @classmethod
    def get_match_html_report(cls, text_left: str, text_right: str) -> Tuple[str, str]:
        """
        Get match report with HTML tags
        """
        report_left, report_right = cls._get_report(
            text_left, text_right, cls._html_formatter)
        return "".join(report_left), "".join(report_right)

    @classmethod
    def get_match_json_report(cls, text_left: str, text_right: str) -> Tuple[List[dict], List[dict]]:
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

    def split_paragraphs(self, paragraphs: List[Paragraph]) -> List[Paragraph]:
        """
        Split paragraph into sentence paragraphs
        """
        para_it = (para.text for para in paragraphs)
        updated_paragraphs: List[Paragraph] = []
        if self.nlp_model is not None:            
            texts_it = split_texts_into_sentences_lib(para_it, self.nlp_model)
        else:
            texts_it = split_texts_into_sentences(para_it)
        for para, texts in zip(paragraphs, texts_it):
            updated_paragraphs += [Paragraph(text=text, id=para.id, payload={**para.payload, "sent_pos": i})
                                   for i, text in enumerate(texts)]
        return updated_paragraphs

    def update_merge_paragraphs(self):
        """
        Update paragraphs by merging neighbours based on matches

        Merging is delegated to various merging strategies
        """
        paragraph_matches: List[ParagraphMatch] = self.make_paragraph_matches(
            False)
        self.notifier.notify(
            COMPLETE_SPLIT + (COMPLETE_MERGE - COMPLETE_SPLIT) / 4)
        paragraph_matches = join_optimize_paragraph_matches(paragraph_matches,
                                                            self.file_type_left == "pdf",
                                                            self.file_type_right == "pdf")
        self.notifier.notify(
            COMPLETE_SPLIT + (COMPLETE_MERGE - COMPLETE_SPLIT) / 2)
        paragraph_matches = merge_matches_on_condition(
            paragraph_matches, matched_condition)
        self.notifier.notify(COMPLETE_SPLIT + 3 *
                             (COMPLETE_MERGE - COMPLETE_SPLIT) / 4)
        if self.file_type_left == 'pdf' and self.file_type_right == "pdf":
            paragraph_matches = merge_matches_on_condition(paragraph_matches,
                                                           unmatched_condition_no_id)
        else:
            paragraph_matches = merge_matches_on_condition(paragraph_matches,
                                                           unmatched_condition_with_id)

        self.texts_left = [para_match.paragraph_left for para_match in paragraph_matches
                           if para_match.paragraph_left]

        self.texts_right = [para_match.paragraph_right for para_match in paragraph_matches
                            if para_match.paragraph_right]
        self.notifier.notify(COMPLETE_MERGE)

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

        updated_paragraphs_left += self.split_paragraphs([self.texts_left[idx_left]
                                                          for idx_left in texts_left_indices])
        self.notifier.notify(COMPLETE_MIDDLE)

        updated_paragraphs_right += self.split_paragraphs([self.texts_right[idx_right]
                                                           for idx_right in texts_right_indices])
        self.notifier.notify(COMPLETE_SPLIT)

        self.texts_left = sorted_paragraphs(updated_paragraphs_left)
        self.texts_right = sorted_paragraphs(updated_paragraphs_right)

    def make_paragraph_matches(self, is_final: bool = False) -> List[ParagraphMatch]:
        """
        Match paragraph with right order
        """
        threshold = self.ratio_threshold if is_final else self.update_ratio_threshold
        optimal_matches = compute_optimal_matches(
            self.texts_left, self.texts_right, threshold,
            consider_partial=is_final)

        match_positions_left = [match[0] for match in optimal_matches]
        match_positions_right = [match[2] for match in optimal_matches]

        texts_left_indices, texts_right_indices = self.get_unmatched_texts_indices(
            match_positions_left, match_positions_right
        )

        result = []

        for pos_left, text_left, pos_right, text_right, ratio in optimal_matches:
            changed = self.is_fully_changed(text_left.text, text_right.text)
            item = ParagraphMatch(ratio=ratio if changed else 100,
                                  type="changed" if changed else "equal",
                                  position=pos_left,
                                  position_secondary=pos_right,
                                  paragraph_left=text_left,
                                  paragraph_right=text_right)
            result.append(item)

        for idx in texts_left_indices:
            text_left = self.texts_left[idx]
            item = ParagraphMatch(ratio=0,
                                  type="removed",
                                  position=idx,
                                  position_secondary=0,
                                  paragraph_left=text_left,
                                  paragraph_right=None)
            result.append(item)

        for idx in texts_right_indices:
            text_right = self.texts_right[idx]
            closest_match_index = self.find_closest_match(
                match_positions_right, idx, -1) if match_positions_right else -1
            if closest_match_index != -1:
                pos_left = optimal_matches[closest_match_index][0]
                pos_right = optimal_matches[closest_match_index][2]
            else:
                pos_left = pos_right = 0
            item = ParagraphMatch(ratio=0,
                                  type="new",
                                  position=pos_left,
                                  position_secondary=pos_right,
                                  paragraph_left=None,
                                  paragraph_right=text_right)
            result.append(item)

        return sorted(result, key=lambda x: (x.position, x.position_secondary))

    def generate_comparison(self, mode: str = "html"):
        """
        Generate comparison object        
        """
        # Run the splitting phase twice
        self.update_split_paragraphs()
        self.update_merge_paragraphs()

        paragraph_matches: List[ParagraphMatch] = self.make_paragraph_matches(
            True)

        comparison_obj = []

        # Select reporting method based on mode
        report_method: Callable[[str, str], Tuple[Any, Any]] = (
            self.get_match_html_report if mode == "html" else self.get_match_json_report
        )

        for match_item in paragraph_matches:
            paragraph_left = (match_item.paragraph_left
                              if match_item.paragraph_left
                              else Paragraph("", ""))
            paragraph_right = (match_item.paragraph_right
                               if match_item.paragraph_right
                               else Paragraph("", ""))
            report_left, report_right = report_method(
                paragraph_left.text, paragraph_right.text)
            item = {
                "ratio": round(match_item.ratio / 100, 4),
                "type": match_item.type,
                "text_left_id": match_item.paragraph_left.id if match_item.paragraph_left else "",
                "text_left": paragraph_left.text,
                "text_right_id": match_item.paragraph_right.id if match_item.paragraph_right else "",
                "text_right": paragraph_right.text,
                "text_left_report": report_left,
                "text_right_report": report_right,
                "page_number_left": str(paragraph_left.payload.get("page_number", "")),
                "page_number_right": str(paragraph_right.payload.get("page_number", ""))
            }
            comparison_obj.append(item)

        return comparison_obj
