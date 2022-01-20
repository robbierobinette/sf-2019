from .Election import ElectionResult, Election, BallotIter, Ballot
from typing import List, Iterable, Union, Set
from .Candidate import Candidate
from .PluralityElection import PluralityElection, PluralityResult


class InstantRunoffResult(ElectionResult):
    def __init__(self, ordered_candidates: List[Candidate], rounds: List[PluralityResult]):
        super().__init__(ordered_candidates)
        self.rounds = rounds


class InstantRunoffElection(Election):
    def __init__(self, ballots: BallotIter, candidates: Set[Candidate]):
        super().__init__(ballots, candidates)

    def result(self) -> InstantRunoffResult:
        return self.compute_result()

    def compute_result(self) -> InstantRunoffResult:
        active_candidates = self.candidates.copy()
        rounds = []
        losers = []
        while len(active_candidates) > 1:
            plurality = PluralityElection(self.ballots, active_candidates)
            r = plurality.result()
            rounds.append(r)
            loser = r.ordered_candidates[-1]
            losers.append(loser)
            active_candidates.remove(loser)

        assert(len(active_candidates) == 1)
        losers += list(active_candidates)
        winners = list(reversed(losers))

        return InstantRunoffResult(winners, rounds)



