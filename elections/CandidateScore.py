from .Candidate import Candidate

from dataclasses import dataclass
@dataclass(frozen=True)
class CandidateScore:
    candidate: Candidate
    score: float