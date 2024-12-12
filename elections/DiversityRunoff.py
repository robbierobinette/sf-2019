from collections import defaultdict
from typing import List, Set

from .Candidate import Candidate
from .Election import ElectionResult, Election, BallotIter


class DiversityScore:
    def __init__(self, candidate: Candidate, ballot_orders: int, first_place_votes: int):
        self.candidate = candidate
        self.ballot_orders = ballot_orders
        self.first_place_votes = first_place_votes

    def __lt__(self, other):
        if self.ballot_orders != other.ballot_orders:
            return self.ballot_orders > other.ballot_orders
        else:
            return self.first_place_votes > other.first_place_votes


class DiversityRound:
    def __init__(self, diversity_scores: List[DiversityScore], total_votes: int) -> None:
        self.diversity_scores = diversity_scores
        self.total_votes = total_votes


class DiversityRunoffResult(ElectionResult):
    def __init__(self, ordered_candidates: List[Candidate], rounds: List[DiversityRound]):
        super().__init__(ordered_candidates)
        self.rounds = rounds


class DiversityRunoffElection(Election):
    def __init__(self, ballots: BallotIter,
                 candidates: Set[Candidate],
                 diversity_threshold: float = .10,
                 diversity_depth: int = 1000,
                 debug = False):
        super().__init__(ballots, candidates)
        self.diversity_threshold = diversity_threshold
        self.diversity_depth = diversity_depth
        self.debug = debug
        if len(self.ballots) > 0:
            self._result = self.compute_result()
        else:
            self._result = None
            print("No ballots")

    def result(self) -> DiversityRunoffResult:
        return self._result

    # find the number of different ballot orders with this candidate as the first candidate.
    # limit the ballot orders to the currently active candidates.

    def join_names(self, ordered_candidates: List[Candidate]) -> str:
        return '; '.join(candidate.name.split(",")[0] for candidate in ordered_candidates)

    def compute_diversity(self, active_candidates: Set[Candidate]) -> List[DiversityScore]:
        ballot_orders = defaultdict(dict)
        ranked_counts = defaultdict(int)
        all_ordered_names = set()

        num_active_ballots = 0
        for b in self.ballots:
            candidates = [c.candidate for c in b.ordered_candidates if c.candidate in active_candidates]
            if len(candidates) > 0:
                num_active_ballots += 1

        for ballot in self.ballots:
            ordered_candidates = [c.candidate for c in ballot.ordered_candidates if c.candidate in active_candidates]
            # do not include bullet votes in the diversity_count
            # candidates should not be judged by the percentage of their bullet votes.
            # Certainly not rewarded for them.
            if len(ordered_candidates) > 0:
                first_choice = ordered_candidates[0]


                # if ordered candidates lists all but one of the active_candidates, then last place is implied.
                # Add that.
                if len(ordered_candidates) == len(active_candidates) - 1:
                    ordered_candidates_set = set(ordered_candidates)
                    missing_candidate = active_candidates - ordered_candidates_set
                    if missing_candidate:
                        ordered_candidates.append(missing_candidate.pop())

                ordered_candidates = ordered_candidates[0:self.diversity_depth]
                ordered_names = self.join_names(ordered_candidates)
                all_ordered_names.add(ordered_names)
                if ordered_names not in ranked_counts:
                    ranked_counts[ordered_names] = len(ordered_candidates)

                if first_choice not in ballot_orders:
                    ballot_orders[first_choice] = defaultdict(int)

                ballot_orders[first_choice][ordered_names] += 1

        diversity_scores = []

        # find the maximum length of any ballot order for any first choice in ballot_orders{}
        # to do this, I need to flatten the array of array's of keys. into a


        max_ballot_order_len = max(len(ballot_order) for ballot_order in all_ordered_names)

        for first_choice in ballot_orders.keys():

            # sum of vote counts for each ballot order for this first_choice
            first_place_votes = sum(ballot_orders[first_choice].values())
            # count the ballot_orders that exceed the threshold for diversity for this first choice.
            diversity_threshold_count = 0
            for ballot_order, count in sorted(ballot_orders[first_choice].items(), key=lambda x: x[1], reverse=True):
                pct = count / num_active_ballots
                if pct > self.diversity_threshold and ranked_counts[ballot_order] > 1:
                    diversity_threshold_count += 1
                if self.debug:
                    # print the ballot_order and set the length to the maximum length of any ballot_order
                    print(f"{ballot_order:<{max_ballot_order_len}} "
                          f"count {count:6d} "
                          f"pct {pct * 100:5.2f} "
                          f"dtc {diversity_threshold_count:2d}")

            diversity_scores.append(DiversityScore(first_choice, diversity_threshold_count, first_place_votes))

        return sorted(diversity_scores)

    def compute_result(self) -> DiversityRunoffResult:
        active_candidates = self.candidates.copy()

        # remove a candidate whose name matches "WriteIn" from active_candidates
        active_candidates = {candidate for candidate in active_candidates if "Write-in" not in candidate.name}

        rounds: List[DiversityRound] = []
        winner = None
        if len(active_candidates) == 1:
            winner = active_candidates.pop()

        while not winner and len(active_candidates) > 1:
            diversity_scores = self.compute_diversity(active_candidates)

            if self.debug:
                print("diversity scores: ")
                for ds in diversity_scores:
                    print("\t%-30s ballot_orders %2d first place votes %6d" % (
                    ds.candidate.name, ds.ballot_orders, ds.first_place_votes))

            total_votes = sum(d.first_place_votes for d in diversity_scores)

            # check to see if any candidate exceeds 50%
            for ds in diversity_scores:
                if ds.first_place_votes / total_votes > .5:
                    winner = ds.candidate
                    print("%-30s wins with %.2f%% of the vote" % (winner.name, ds.first_place_votes / total_votes * 100))
                    break

            # remove the ast place diversity score from the race.
            last_place: DiversityScore = diversity_scores[-1]
            if self.debug and not winner:
                print(
                    f"last place is %-30s " % last_place.candidate.name +
                    f"diversity %2d " % last_place.ballot_orders +
                    f"votes %6d / %5.2f%%" %  (last_place.first_place_votes, last_place.first_place_votes / total_votes * 100))
            active_candidates.remove(diversity_scores[-1].candidate)

            rounds.append(DiversityRound(diversity_scores, total_votes))

        return DiversityRunoffResult([winner], rounds)