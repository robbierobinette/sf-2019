from .Election import *
from .ElectionResult import ElectionResult


class PluralityResult(ElectionResult):
    def __init__(self, ordered_candidates: List[Candidate], vote_totals: {}):
        super().__init__(ordered_candidates)
        self.vote_totals = vote_totals

    def print(self):
        for c in self.ordered_candidates:
            print(f"{c.name} {self.vote_totals[c]}")
        print("")


class PluralityElection(Election):
    def __init__(self, ballots: BallotIter, active_candidates: Set[Candidate]):
        super().__init__(ballots, active_candidates)
        self.vote_totals = {}
        for c in active_candidates:
            self.vote_totals[c] = 0

        self.active_candidates = active_candidates
        self.ordered_candidates: List[Candidate] = self.compute_results()

    def compute_results(self) -> List[Candidate]:
        for b in self.ballots:
            w = b.active_choice(self.active_candidates)
            if w:
                self.vote_totals[w] += 1

        c_list = list(self.vote_totals.items())
        c_list.sort(key=lambda p: p[1], reverse=True)
        return list(map(lambda p: p[0], c_list))

    def result(self) -> PluralityResult:
        return PluralityResult(self.ordered_candidates, self.vote_totals)
