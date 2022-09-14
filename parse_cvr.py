import json
import os.path as path
import pickle
import os
from typing import List

from elections.Ballot import Ballot
from elections.Candidate import Candidate
from elections.CandidateScore import CandidateScore
from elections.HeadToHeadElection import HeadToHeadElection
from elections.InstantRunoffElection import InstantRunoffElection, InstantRunoffResult
from elections.Party import NoParty
from elections.PluralityElection import PluralityResult

dir = "CVR_Export_20220908084311"


def pickle_sessions(ss, pickle_file):
    pickle.dump(ss, open(pickle_file, "wb"))


def load_pickled_sessions(count: int):
    pickle_file = f"full_results-{count}.p"
    if path.exists(pickle_file):
        print("loading cvr from pickle")
        return pickle.load(open(pickle_file, "rb"))
    else:
        print("loading cvr from json")
        cvr = json.load(open(f"{dir}/CvrExport.json", "r"))
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
        self.ambiguous_mattered = 0
        self.ambiguous_present = 0
        self.total_ambiguous = 0
        self.multiple_rankings = 0
        self.rank_skips = 0
        self.write_in_skipped = 0
        self.candidates = candidates
        self.candidates_by_id = candidates_by_id
        self.write_in_candidates = 0
        self.write_in_indices = set()
        self.write_in_densities = {}

    def add_marks(self, marks):
        seen_candidates = set()
        scores = []
        last_rank = 0

        # check if there is any ambiguous mark on the ballot
        ballot_contains_ambiguous = 0
        for m in marks:
            if m['IsAmbiguous']:
                ballot_contains_ambiguous = 1
                self.total_ambiguous += 1

            c = m['CandidateId']
            if self.candidates_by_id[c].name == 'Write-in':
                self.write_in_candidates += 1
                if m['WriteinDensity'] in self.write_in_densities:
                    self.write_in_densities[m['WriteinDensity']] += 1
                else:
                    self.write_in_densities[m['WriteinDensity']] = 1

        self.ambiguous_present += ballot_contains_ambiguous

        for m in marks:
            c, r = m['CandidateId'], m['Rank']
            if m['IsAmbiguous']:
                # this mark is ambiguous, mark density is low (< 25) it should be completely ignored.
                self.ambiguous_mattered += 1
                continue


            if c in seen_candidates:
                # this candidate has already been ranked, ignore the mark
                # keep parsing the ballot
                # this does not count as a skipped ranking, so update current rank.
                self.multiple_rankings += 1
                last_rank = r
                continue

            if r == last_rank:
                # ranked two different candidates at the same level.
                # peel off the conflicting candidate that has the same ranking
                # level.  Stop processing the ballot
                self.over_votes += 1
                scores.pop()
                break;

            if r == last_rank + 2:
                # skipped one rank, add this candidate and keep processing
                self.rank_skips += 1

            if r >= last_rank + 3:
                # skipped two or more rankings
                # ignore this ranking and stop processing the ballot
                self.rank_errors += 1
                break;

            last_rank = r
            seen_candidates.add(c)
            candidate = self.candidates_by_id[c]
            scores.append(CandidateScore(candidate, 100 - r))

        if len(scores) != 0:
            ballot = Ballot(scores)
            self.ballots.append(ballot)
        else:
            self.under_votes += 1

    def print_stat(self, prefix, count, explanation):
        print("%20s %7d %s" % (prefix, count, explanation))
    def run_elections(self):
        irv = InstantRunoffElection(self.ballots, set(self.candidates))
        h2h = HeadToHeadElection(self.ballots, set(self.candidates))
        print(f"{self.contest_id}:  {self.name}")
        self.print_stat("Valid Ballots",  len(self.ballots), "ballots with at least one ranking")
        self.print_stat("Over Votes",  self.over_votes, "multiple candidates at the same ranking level")
        self.print_stat("Ranking Errors",  self.rank_errors, "skipped two or more ranks")
        self.print_stat("Rank Skips",  self.rank_skips, "skipped one rank, but kept processing")
        self.print_stat("Multiple Rankings",  self.multiple_rankings, "single candidate ranked at multiple levels")
        self.print_stat("Ambiguous Mark",  self.ambiguous_present, "ballot had at least one ambiguous mark")
        self.print_stat("Ambiguous Mattered",  self.ambiguous_mattered, "ambiguous mark skipped during ballot processing")
        self.print_stat("Total Ambiguous",  self.ambiguous_mattered, "total ambiguous")
        self.print_stat("Write In Skipped",  self.write_in_skipped, "Skipped a write-in-candidate")
        self.print_stat("Write Candidates",  self.write_in_candidates, "detected a write-in-candidate")
        print("write_in_indices:  ", self.write_in_indices)
        print("write_in_densities:  ", self.write_in_densities)

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
        for card in session["Original"]["Cards"]:
            for contest in card["Contests"]:
                election_id = contest['Id']
                if election_id == 69:
                    if election_id not in elections:
                        elections[election_id] = Contest(election_id,
                                                         contests[election_id],
                                                         candidate_sets[election_id],
                                                         candidates_by_id)

                    elections[election_id].add_marks(contest['Marks'])

    return elections


def main():
    print("loading json")
    if not os.path.exists(dir):
        print (f"""
        no cast vote record files found at {dir}.  
        
        Download the cast vote records from https://www.elections.alaska.gov/election-results/e/?id=22sspg
        At the bottom of the page, there is a link to the download "Cast Vote Record (zip)".
        Download that file and unzip it (your browser may automatically unzip it.)
        place the root directory ./{dir} in the local directory.
        
        Alternately, you can change the variable 'dir' at the top of this file to point at the location of the ballots.
        
        """)
    contest_json = json.load(open(f"{dir}/ContestManifest.json", "r"))
    candidates_json = json.load(open(f"{dir}/CandidateManifest.json"))

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
    print(f"number of sessions: {len(sessions)}")
    elections = parse_all_cvr(sessions, contests, candidate_sets, candidates_by_id)
    for contest in elections.values():
        contest.run_elections()


main()
