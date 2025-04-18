"""
Module for optimal assignment
"""

from typing import List, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment
from rapidfuzz import fuzz

from document_comparer.paragraph import Paragraph


def find_optimal_matches(score_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find optimal matches for score matrix
    """
    row_idx, col_idx = linear_sum_assignment(score_matrix, maximize=True)
    return row_idx, col_idx


def calculate_score_matrix(texts_left: List[Paragraph], texts_right: List[Paragraph]) -> np.ndarray:
    """
    Calculate score matrix based on fuzzy matching ratio for two lists of texts
    """
    score_matrix = np.zeros((len(texts_left), len(texts_right)))
    for i, text1 in enumerate(texts_left):
        for j, text2 in enumerate(texts_right):
            score_matrix[i][j] = fuzz.ratio(text1.text, text2.text)
    return score_matrix


def compute_optimal_matches(texts_left: List[Paragraph],
                            texts_right: List[Paragraph],
                            ratio_threshold: float) -> List[Tuple[int, Paragraph, int, Paragraph, float]]:
    """
    Compute optimal matches using score matrix and Hungarian algorithm.
    Only return matches exceeding the ratio threshold.
    """
    score_matrix = calculate_score_matrix(texts_left, texts_right)
    row_idx, col_idx = find_optimal_matches(score_matrix)
    return [(i, texts_left[i], j, texts_right[j], score_matrix[i][j])
            for i, j in zip(row_idx, col_idx)
            if score_matrix[i][j] > ratio_threshold]  # type: ignore
