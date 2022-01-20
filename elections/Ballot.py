from dataclasses import dataclass
from typing import List, Set
from .CandidateScore import CandidateScore
from .Candidate import Candidate

@dataclass
class Ballot:
    ordered_candidates: List[CandidateScore]

    def active_choice(self, active_candidates: Set[Candidate]) -> Candidate:
        for c in self.ordered_candidates:
            if c.candidate in active_candidates:
                return c.candidate
        return None