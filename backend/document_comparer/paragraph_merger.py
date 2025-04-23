"""
Module containing paragraph merging functionality
"""
from dataclasses import field, dataclass
from typing import Dict, List, Tuple, Optional

from document_comparer.optimal_assignment import compute_optimal_matches
from document_comparer.paragraph import Paragraph
from internal.constants import COMPLETE_MERGE, COMPLETE_SPLIT
from internal.notifier import Notifier


@dataclass
class ParagraphMerger:
    """
    Class responsible for merging paragraphs based on matching patterns
    """
    notifier: Notifier
    merged_paragraphs_left: List[Paragraph] = field(default_factory=list)
    merged_paragraphs_right: List[Paragraph] = field(default_factory=list)

    # Temporary collections for paragraphs being merged
    temp_paragraphs_left: List[Paragraph] = field(default_factory=list)
    temp_paragraphs_right: List[Paragraph] = field(default_factory=list)

    # Tracking current paragraph positions
    current_para_left: int = -1
    current_para_right: int = -1

    # Flags for tracking match sequences
    sign_left: bool = True
    sign_right: bool = True

    def merge_paragraphs(self,
                         texts_left: List[Paragraph],
                         texts_right: List[Paragraph],
                         ratio_threshold: float) -> Tuple[List[Paragraph], List[Paragraph]]:
        """
        Merge neighboring paragraphs based on matching patterns

        Returns:
            Tuple containing the merged left and right paragraph collections
        """
        # Step 1: Compute optimal matches and create lookup maps
        matched_paragraphs: List[Tuple[Paragraph, Paragraph]
                                 ] = self._compute_and_get_matched_paragraphs(texts_left,
                                                                              texts_right,
                                                                              ratio_threshold)
        left_lookup_map, right_lookup_map = self._make_lookup_map_for_matches(
            matched_paragraphs)

        # Step 2: Initialize processing stacks and result collections
        left_texts_stack: List[Paragraph] = list(
            reversed(texts_left.copy()))
        right_texts_stack: List[Paragraph] = list(
            reversed(texts_right.copy()))

        max_loop_length = max(len(left_texts_stack), len(right_texts_stack))
        # Step 3: Process paragraphs until all are consumed
        while left_texts_stack or right_texts_stack:
            # Get next paragraphs from stacks if available
            left_para: Optional[Paragraph] = left_texts_stack.pop(
            ) if left_texts_stack else None
            right_para: Optional[Paragraph] = right_texts_stack.pop(
            ) if right_texts_stack else None

            # Process the current paragraph pair
            self._process_paragraph_pair(
                left_para, right_para,
                left_texts_stack, right_texts_stack,
                left_lookup_map, right_lookup_map
            )

            iteration = max_loop_length - max(len(left_texts_stack),
                                              len(right_texts_stack))
            self.notifier.loop_notify(iteration, COMPLETE_SPLIT, 
                                      COMPLETE_MERGE, max_loop_length)

        # Step 4: Handle any remaining paragraphs in temporary collections
        self._finalize_merge_results()

        # Step 5: Return the merged collections
        return self.merged_paragraphs_left, self.merged_paragraphs_right

    def _compute_and_get_matched_paragraphs(self,
                                            texts_left,
                                            texts_right,
                                            ratio_threshold) -> List[Tuple[Paragraph, Paragraph]]:
        """
        Compute optimal matches and extract matched paragraphs
        """
        optimal_matches = compute_optimal_matches(texts_left,
                                                  texts_right,
                                                  ratio_threshold)
        # Extract matched paragraphs for easier lookup
        return [(match[1], match[3]) for match in optimal_matches]

    @staticmethod
    def _make_lookup_map_for_matches(matched_paragraphs: List[Tuple[Paragraph, Paragraph]]) \
            -> Tuple[Dict[Tuple[int, int], Tuple[int, int]], Dict[Tuple[int, int], Tuple[int, int]]]:
        """
        Make a look up maps for matched paragraphs
        """
        left_lookup_map: Dict[Tuple[int, int], Tuple[int, int]] = {}
        right_lookup_map: Dict[Tuple[int, int], Tuple[int, int]] = {}

        for paragraph_left, paragraph_right in matched_paragraphs:
            unique_id_left = paragraph_left.payload["para_pos"], paragraph_left.payload["sent_pos"]
            unique_id_right = paragraph_right.payload["para_pos"], paragraph_right.payload["sent_pos"]
            left_lookup_map[unique_id_left] = unique_id_right
            right_lookup_map[unique_id_right] = unique_id_left

        return left_lookup_map, right_lookup_map

    def _process_paragraph_pair(
        self,
        left_para: Optional[Paragraph],
        right_para: Optional[Paragraph],
        left_texts_stack: List[Paragraph],
        right_texts_stack: List[Paragraph],
        left_lookup_map: Dict[Tuple[int, int], Tuple[int, int]],
        right_lookup_map: Dict[Tuple[int, int], Tuple[int, int]]
    ) -> None:
        """
        Process a pair of paragraphs from left and right collections
        """
        # Find potential matches for current paragraphs
        matched_right_para: Optional[Tuple[int, int]] = self._find_match_for_left_para(
            left_para, left_lookup_map)
        matched_left_para: Optional[Tuple[int, int]] = self._find_match_for_right_para(
            right_para, right_lookup_map)

        # Check if current paragraphs form a direct match
        is_match: bool = self._is_direct_match(right_para, matched_right_para)

        # Check if paragraphs are from the same position in their respective documents
        same_para_pos: bool = self._is_same_paragraph_position(
            left_para, right_para, self.current_para_left, self.current_para_right)

        # Update current paragraph positions
        if left_para:
            self.current_para_left = left_para.payload["para_pos"]
        if right_para:
            self.current_para_right = right_para.payload["para_pos"]

        # Handle direct matches
        if left_para and right_para and is_match:
            self._handle_direct_match(
                left_para, right_para, same_para_pos)
            return

        # Handle cross-matching paragraphs
        if left_para and matched_left_para and right_para and matched_right_para:
            self._handle_cross_match(left_para, right_para,
                                     left_texts_stack,
                                     right_texts_stack,
                                     matched_left_para,
                                     matched_right_para)
            return

        # Handle one-sided matches
        if left_para and right_para and matched_right_para:
            self._handle_left_match(
                left_para, right_para, left_texts_stack)
        elif left_para and right_para and matched_left_para:
            self._handle_right_match(
                left_para, right_para, right_texts_stack)
        else:
            self._handle_no_match(left_para, right_para)

        # Mark that we're no longer in a matching sequence
        self.sign_left = False
        self.sign_right = False

    @staticmethod
    def _find_match_for_left_para(
        left_para: Optional[Paragraph],
        left_lookup_map: Dict[Tuple[int, int], Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        """Find the matching right paragraph for a left paragraph"""
        if not left_para:
            return None
        left_para_pos: int = left_para.payload["para_pos"]
        left_sent_pos: int = left_para.payload["sent_pos"]
        return left_lookup_map.get((left_para_pos, left_sent_pos))

    @staticmethod
    def _find_match_for_right_para(
        right_para: Optional[Paragraph],
        right_lookup_map: Dict[Tuple[int, int], Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        """Find the matching left paragraph for a right paragraph"""
        if not right_para:
            return None
        right_para_pos: int = right_para.payload["para_pos"]
        right_sent_pos: int = right_para.payload["sent_pos"]
        return right_lookup_map.get((right_para_pos, right_sent_pos))

    @staticmethod
    def _is_direct_match(
        right_para: Optional[Paragraph],
        matched_right_para: Optional[Tuple[int, int]]
    ) -> bool:
        """Check if right paragraph matches its expected match"""
        if not (right_para and matched_right_para):
            return False
        return (matched_right_para[0] == right_para.payload["para_pos"] and
                matched_right_para[1] == right_para.payload["sent_pos"])

    @staticmethod
    def _is_same_paragraph_position(
        left_para: Optional[Paragraph],
        right_para: Optional[Paragraph],
        current_para_left: int,
        current_para_right: int
    ) -> bool:
        """Check if paragraphs are from the same position in their documents"""
        if not (left_para and right_para):
            return False
        return (current_para_left == left_para.payload["para_pos"] and
                current_para_right == right_para.payload["para_pos"])

    def _handle_direct_match(
        self,
        left_para: Paragraph,
        right_para: Paragraph,
        same_para_pos: bool
    ) -> None:
        """Handle case where paragraphs directly match"""
        # If we have temp paragraphs and we're not continuing in the same paragraph,
        # append them to results
        if self.temp_paragraphs_left and not (same_para_pos and self.sign_left):
            self._flush_left()

        if self.temp_paragraphs_right and not (same_para_pos and self.sign_left):
            self._flush_right()

        # Add current paragraphs to temp collections
        self.temp_paragraphs_left.append(left_para)
        self.temp_paragraphs_right.append(right_para)

        # Mark that we're in a matching sequence
        self.sign_left = True
        self.sign_right = True

    def _handle_cross_match(
        self,
        left_para: Paragraph,
        right_para: Paragraph,
        left_texts_stack: List[Paragraph],
        right_texts_stack: List[Paragraph],
        match_left_para: Tuple[int, int],
        match_right_para: Tuple[int, int]
    ) -> None:
        """Handle case where paragraphs have cross matches"""
        # Put paragraphs back on stacks to process later
        self._cross_insert_stack(left_texts_stack,
                                 right_texts_stack,
                                 left_para,
                                 right_para,
                                 match_left_para,
                                 match_right_para)

        # Finalize any accumulated temp paragraphs
        if self.temp_paragraphs_left:
            self._flush_left()

        if self.temp_paragraphs_right:
            self._flush_right()

    def _handle_left_match(
        self,
        left_para: Paragraph,
        right_para: Paragraph,
        left_texts_stack: List[Paragraph]
    ) -> None:
        """Handle case where left paragraph has a match but right doesn't"""
        left_texts_stack.append(left_para)
        if self.temp_paragraphs_right and self.sign_right:
            self._flush_right()
        self.temp_paragraphs_right.append(right_para)

    def _handle_right_match(
        self,
        left_para: Paragraph,
        right_para: Paragraph,
        right_texts_stack: List[Paragraph]
    ) -> None:
        """Handle case where right paragraph has a match but left doesn't"""
        right_texts_stack.append(right_para)
        if self.temp_paragraphs_left and self.sign_left:
            self._flush_left()
        self.temp_paragraphs_left.append(left_para)

    def _handle_no_match(
        self,
        left_para: Optional[Paragraph],
        right_para: Optional[Paragraph]
    ) -> None:
        """Handle case where neither paragraph has a match"""
        if self.temp_paragraphs_left and self.sign_left:
            self._flush_left()

        if self.temp_paragraphs_right and self.sign_right:
            self._flush_right()

        if left_para:
            self.temp_paragraphs_left.append(left_para)
        if right_para:
            self.temp_paragraphs_right.append(right_para)

    def _finalize_merge_results(self) -> None:
        """Finalize any remaining temporary paragraphs"""
        if self.temp_paragraphs_left:
            self._flush_left()

        if self.temp_paragraphs_right:
            self._flush_right()

    @staticmethod
    def _join_paragraphs(paragraphs: List[Paragraph]) -> Paragraph:
        """
        Join multiple paragraphs into one
        """
        assert len(paragraphs) > 0
        return Paragraph(text=" ".join([para.text for para in paragraphs]),
                         id=paragraphs[0].id,
                         payload=paragraphs[0].payload)

    @classmethod
    def _cross_insert_stack(cls, left_stack: List[Paragraph],
                            right_stack: List[Paragraph],
                            left_para: Paragraph,
                            right_para: Paragraph,
                            matched_left_para: Tuple[int, int],
                            matched_right_para: Tuple[int, int]):
        """
        Return paragraphs to both stacks to align them with the matches
        """
        left_index = cls._index_paragraph(right_stack, matched_right_para)
        right_index = cls._index_paragraph(left_stack, matched_left_para)

        left_index = left_index - len(left_stack)
        right_index = right_index - len(right_stack)

        if left_index >= right_index:
            if left_index < 0:
                left_stack.insert(
                    left_index, left_para)
            else:
                left_stack.append(left_para)
            if right_index + 1 < 0:
                right_stack.insert(right_index+1, right_para)
            else:
                right_stack.append(right_para)
        else:
            if right_index < 1:
                right_stack.insert(right_index, right_para)
            else:
                right_stack.append(right_para)
            if left_index + 1 < 0:
                left_stack.insert(left_index+1, left_para)
            else:
                left_stack.append(left_para)

    @staticmethod
    def _index_paragraph(stack: List[Paragraph], matched_para: Tuple[int, int]) -> int:
        """
        Find matched paragraph in the stack
        """
        pos = len(stack)-1
        for para in reversed(stack):
            if para.payload["para_pos"] == matched_para[0] and para.payload["sent_pos"] == matched_para[1]:
                return pos
            pos -= 1
        raise ValueError(f'{matched_para} not in the list')

    def _flush_left(self):
        """
        Flush left side to the resulting paragraphs list
        """
        self.merged_paragraphs_left.append(
            self._join_paragraphs(self.temp_paragraphs_left))
        self.temp_paragraphs_left = []

    def _flush_right(self):
        """
        Flush right side to the resulting paragraphs list
        """
        self.merged_paragraphs_right.append(
            self._join_paragraphs(self.temp_paragraphs_right))
        self.temp_paragraphs_right = []
