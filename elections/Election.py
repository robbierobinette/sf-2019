from .ElectionResult import ElectionResult
from .Ballot import Ballot
from typing import List, Iterable, Union, Set
from .Candidate import Candidate

BallotIter = Union[Iterable[Ballot], List[Ballot]]


class Election:
    def __init__(self, ballots: List[Ballot], candidates: Set[Candidate]):
        self.ballots = ballots
        self.candidates = candidates

    def result(self) -> ElectionResult:
        pass
