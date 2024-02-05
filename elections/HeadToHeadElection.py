from typing import List, Set, Tuple

from .Candidate import Candidate
from .Election import Election, BallotIter
from .ElectionResult import ElectionResult
import numpy as np


class HeadToHeadResult(ElectionResult):
    def __init__(self, ordered_candidates: List[Candidate], result_matrix: np.array, indices: {}, is_tie: bool):
        super().__init__(ordered_candidates)
        self.result_matrix: np.array = result_matrix
        self.is_tie: bool = is_tie
        self.candidate_to_index  = indices
        self.index_to_candidate = {}
        for k, v in indices.items():
            self.index_to_candidate[v] = k

    def print_matrix(self, count = 4):
        for c1 in self.ordered_candidates[0:count]:
            ci1 = self.candidate_to_index[c1]
            print(f"results for {c1.name}:")
            for c2 in self.ordered_candidates[0:count]:
                ci2 = self.candidate_to_index[c2]
                if ci1 != ci2:
                    v1 = self.result_matrix[ci1, ci2]
                    v2 = self.result_matrix[ci2, ci1]
                    t = v1 + v2
                    print("%30s %7d %5.2f%% %30s %7d %5.2f%% % 7d" % (c1.name, v1, 100 * v1 / t, c2.name, v2, 100 * v2 / t, v1 - v2))
            print("")

class HeadToHeadElection(Election):
    def __init__(self, ballots: BallotIter, candidates: Set[Candidate]):
        super().__init__(ballots, candidates)
        self.candidate_list = list(self.candidates)
        self.indices = {}
        for i in range(len(self.candidate_list)):
            self.indices[self.candidate_list[i]] = i

        self.result_matrix = self.compute_matrix()

    def result(self) -> HeadToHeadResult:
        oc = self.minimax(self.candidates)
        return HeadToHeadResult(oc, self.result_matrix, self.indices, self.check_for_tie(self.candidates))

    def compute_matrix(self) -> np.array:
        n_candidates = len(self.candidates)
        results = np.zeros([n_candidates, n_candidates])
        for b in self.ballots:
            not_seen: Set[Candidate] = self.candidates.copy()
            for cs1 in b.ordered_candidates:
                c1 = cs1.candidate
                if c1 not in not_seen:
                    print(f"{c1.name} is not in not_seen")
                    for c in not_seen:
                        print(f"not_seen: {c.name}")

                    for c in self.candidates:
                        print(f"candidates: {c.name}")

                    for cs in b.ordered_candidates:
                        print(f"ballot.ordered_candidates: {cs.candidate.name}")

                not_seen.remove(c1)
                row_i = self.indices[c1]
                for c2 in not_seen:
                    col_i = self.indices[c2]
                    results[row_i, col_i] += 1

        return results

    # returns votes for c1 - votes for c2
    def delta(self, c1: Candidate, c2: Candidate) -> float:
        r = self.indices[c1]
        c = self.indices[c2]
        return self.result_matrix[r, c] - self.result_matrix[c, r]

    def max_loss(self, candidate: Candidate, active_candidates: Set[Candidate]) -> float:
        opponents = active_candidates.copy()
        opponents.remove(candidate)

        losses = [-self.delta(candidate, c2) for c2 in opponents]
        return max(losses)

    def check_for_tie(self, active_candidates: Set[Candidate]) -> bool:
        for r in range(self.result_matrix.shape[0]):
            has_loss = False
            for c in range(self.result_matrix.shape[1]):
                if self.result_matrix[r, c] - self.result_matrix[c, r] < 0:
                    has_loss = True
            if not has_loss:
                return False
        return True

    def minimax(self, active_candidates: Set[Candidate]) -> List[Candidate]:
        if len(active_candidates) == 1:
            return list(active_candidates)

        ac = active_candidates.copy()
        max_losses: List[Tuple[Candidate, float]] = [(ci, self.max_loss(ci, ac)) for ci in ac]

        max_losses.sort(key=lambda x: x[1])

        winner = max_losses[0][0]
        ac.remove(winner)
        return [winner] + self.minimax(ac)
