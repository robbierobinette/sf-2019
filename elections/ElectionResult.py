from typing import List
from .Candidate import Candidate

class ElectionResult:
    def __init__(self, ordered_candidates: List[Candidate]):
        self.ordered_candidates = ordered_candidates
        self.is_tie = False

    def winner(self) -> Candidate:
        return self.ordered_candidates[0]
