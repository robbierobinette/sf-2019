import json
import os.path as path
import pickle
from typing import List

from elections.Ballot import Ballot
from elections.Candidate import Candidate
from elections.CandidateScore import CandidateScore
from elections.HeadToHeadElection import HeadToHeadElection
from elections.InstantRunoffElection import InstantRunoffElection, InstantRunoffResult
from elections.Party import NoParty
from elections.PluralityElection import PluralityResult


def pickle_sessions(ss, pickle_file):
    pickle.dump(ss, open(pickle_file, "wb"))


def load_pickled_sessions(count: int):
    pickle_file = f"full_results-{count}.p"
    if path.exists(pickle_file):
        print("loading cvr from pickle")
        return pickle.load(open(pickle_file, "rb"))
    else:
        print("loading cvr from json")
        cvr = json.load(open("cvr/CvrExport.json", "r"))
        ss = cvr['Sessions'][0:count]
        pickle_sessions(ss, pickle_file)
        return ss


class Contest:
    def __init__(self, contest_id: int, name: str, candidates: List[Candidate], candidates_by_id: {}):
        self.contest_id = contest_id
        self.name = name
        self.ballots = []
        self.over_votes = 0
        self.under_votes = 0
        self.rank_errors = 0
        self.candidates = candidates
        self.candidates_by_id = candidates_by_id

    def add_marks(self, marks):
        if len(marks) == 0:
            self.under_votes += 1
            return
        seen_candidates = set()
        scores = []
        current_rank = 0
        for m in marks:
            c, r = m['CandidateId'], m['Rank']
            if c in seen_candidates:
                self.over_votes += 1
                break;

            if r != current_rank + 1:
                self.rank_errors += 1
                break;

            current_rank = r
            seen_candidates.add(c)
            candidate = self.candidates_by_id[c]
            scores.append(CandidateScore(candidate, 100 - r))

        if len(scores) != 0:
            ballot = Ballot(scores)
            self.ballots.append(ballot)
        else:
            self.under_votes += 1

    def run_elections(self):
        irv = InstantRunoffElection(self.ballots, set(self.candidates))
        h2h = HeadToHeadElection(self.ballots, set(self.candidates))
        print(f"{self.contest_id}:  {self.name}")
        print(f"Valid Ballots: {len(self.ballots)}, Over Votes {self.over_votes}, Under Votes {self.under_votes}, Ranking Errors {self.rank_errors}")
        print(f"irvWinner {irv.result().winner().name}")
        print(f"h2hWinner {h2h.result().winner().name}")
        self.print_irv_result(irv.result())
        print("h2h Matrix:")
        h2h.result().print_matrix()

    def print_plurality(self, plurality_result: PluralityResult):
        for c in plurality_result.ordered_candidates:
            print("%30s %7d" % (c.name, plurality_result.vote_totals[c]))

    def print_irv_result(self, irv_result: InstantRunoffResult):
        c = 0
        for round in irv_result.rounds:
            c += 1
            print(f"irvRound: {c}")
            self.print_plurality(round)


def parse_all_cvr(sessions, contests, candidate_sets, candidates_by_id):
    elections = {}
    for session in sessions:
        for contest in session["Original"]["Contests"]:
            election_id = contest['Id']

            if election_id not in elections:
                elections[election_id] = Contest(election_id,
                                                 contests[election_id],
                                                 candidate_sets[election_id],
                                                 candidates_by_id)

            elections[election_id].add_marks(contest['Marks'])

    return elections


def main():
    print("loading json")
    contest_json = json.load(open("cvr/ContestManifest.json", "r"))
    candidates_json = json.load(open("cvr/CandidateManifest.json"))

    print("composing meta data")
    contests = {}
    for c in contest_json['List']:
        contests[c["Id"]] = c["Description"]

    candidates_by_id = {}
    candidate_sets = {}
    for c in candidates_json['List']:
        candidate = Candidate(c['Description'], NoParty)
        candidates_by_id[c['Id']] = candidate
        if c['ContestId'] in candidate_sets:
            candidate_sets[c['ContestId']].append(candidate)
        else:
            candidate_sets[c['ContestId']] = [candidate]

    sessions = load_pickled_sessions(1000000)
    elections = parse_all_cvr(sessions, contests, candidate_sets, candidates_by_id)
    for contest in elections.values():
        contest.run_elections()


main()
