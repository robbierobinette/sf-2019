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
from collections import defaultdict


def pickle_sessions(ss, pickle_file):
    pickle.dump(ss, open(pickle_file, "wb"))


def load_all_cvr_export_files(directory, max_sessions=100000):
    cvr_export_files = [file for file in os.listdir(directory) if
                        file.startswith('CvrExport') and file.endswith('.json')]
    all_sessions = []
    for file in cvr_export_files:
        with open(f"{directory}/{file}") as f:
            data = json.load(f)
            all_sessions.extend(data.get('Sessions', []))

        # If the total number of sessions loaded is at least max_sessions, stop loading more files
        if len(all_sessions) >= max_sessions:
            break
    return all_sessions


def load_sessions(cvr_dir, max_sessions: int)-> List[dict]:
    pickle_file = f"{cvr_dir}/results-{max_sessions}.p"
    if path.exists(pickle_file):
        print(f"loading cvr from pickle file: {pickle_file}")
        return pickle.load(open(pickle_file, "rb"))
    else:
        json_file = f"{cvr_dir}/CvrExport.json"
        if path.exists(json_file):
            print(f"loading cvr from json {json_file}")
            cvr = json.load(open(json_file, "r"))
            ss = cvr['Sessions'][0:max_sessions]
        else:
            ss = load_all_cvr_export_files(cvr_dir, max_sessions)

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
        self.write_in_densities = defaultdict(int)
        self.is_ranked_choice = False

    def fill_third(self, names):
        if len(names) != 2:
            return names

        all_candidates = set(["Begich", "Peltola", "Palin"])
        for c in names:
            all_candidates.remove(c)

        return names + list(all_candidates)

    def last_name(self, candidate: Candidate) -> str:
        return candidate.name.split(" ")[0].split(",")[0]

    def show_diversity_count(self):
        if not self.is_ranked_choice:
            return
        candidates = {}

        print(f"Contest_id: {self.contest_id} name: {self.name}")
        all_candidates = set([self.last_name(c) for c in self.candidates if c.name != "Write-in"])
        for ballot in self.ballots:
            ordered_names = [self.last_name(c.candidate) for c in ballot.ordered_candidates
                             if c.candidate.name != 'Write-in']
            if len(ordered_names) > 0:

                # if they have specified all but one candidate, the final candidate is implied last.
                # add that so that it does not create a distinct ballot order.
                if len(ordered_names) == len(all_candidates) - 1:
                    ordered_names.append(list(set(all_candidates) - set(ordered_names))[0])

                primary_candidate = ordered_names[0]
                ballot_order = ", ".join(ordered_names[0:2])
                if primary_candidate not in candidates.keys():
                    candidates[primary_candidate] = defaultdict(int)
                candidates[primary_candidate][ballot_order] += 1

        votes_by_candidate = {}
        for c in candidates.keys():
            votes_by_candidate[c] = sum(candidates[c].values())
        total_votes = sum(votes_by_candidate.values())
        ordered_candidates = [a for a, b in sorted(votes_by_candidate.items(), key = lambda x:x[1], reverse=True)]

        for candidate in ordered_candidates:
            first_place_votes = sum(candidates[candidate].values())
            print("Candidate: %s total first place votes: %d  %.2f%%" % (candidate, first_place_votes, first_place_votes / total_votes * 100))
            diversity = 0
            for ballot_order, ballot_order_count in sorted(candidates[candidate].items(), key=lambda x: x[1], reverse = True):
                if ballot_order_count / first_place_votes > .1:
                    diversity += 1
                print("\t%-30s %6d %5.2f%% %s" % (candidate, ballot_order_count, ballot_order_count / first_place_votes * 100, ballot_order))
            print("\tdiversity %2d" % diversity)
            print("")

    def print_ballots(self):
        counts = defaultdict(int)

        for ballot in self.ballots:
            filtered_ballots = [c.candidate.name.split(" ")[0].split(",")[0] for c in ballot.ordered_candidates if
                                c.candidate.name != 'Write-in']
            if len(filtered_ballots) == 3:
                filtered_ballots = filtered_ballots[0:2]
            filtered_ballots = self.fill_third(filtered_ballots)
            names = ", ".join(filtered_ballots)
            if names == "":
                names = "Write-in only"
            if names not in counts:
                counts[names] = 1
            else:
                counts[names] += 1

        # All ballot orders
        print("All ballot orders: ")
        print(f"{len(self.ballots)} ballots")
        for names in sorted(counts.keys()):
            print("%30s %7d" % (names, counts[names]))

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
            if c in self.candidates_by_id and self.candidates_by_id[c].name == 'Write-in':
                self.write_in_candidates += 1
                self.write_in_densities[m['MarkDensity']] += 1

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
            if c not in self.candidates_by_id:
                self.candidates_by_id[c] = Candidate(f"unknown-candidate-{c}", NoParty)

            candidate = self.candidates_by_id[c]
            scores.append(CandidateScore(candidate, 100 - r))

        if len(scores) != 0:
            ballot = Ballot(scores)
            self.ballots.append(ballot)
            if len(ballot.ordered_candidates) > 1:
                self.is_ranked_choice = True
        else:
            self.under_votes += 1

    def print_stat(self, prefix, count, explanation):
        print("%20s %7d %s" % (prefix, count, explanation))

    def run_elections(self):
        irv = InstantRunoffElection(self.ballots, set(self.candidates))
        h2h = HeadToHeadElection(self.ballots, set(self.candidates))
        print(f"{self.contest_id}:  {self.name}")
        self.print_stat("Valid Ballots", len(self.ballots), "ballots with at least one ranking")
        self.print_stat("Over Votes", self.over_votes, "multiple candidates at the same ranking level")
        self.print_stat("Ranking Errors", self.rank_errors, "skipped two or more ranks")
        self.print_stat("Rank Skips", self.rank_skips, "skipped one rank, but kept processing")
        self.print_stat("Multiple Rankings", self.multiple_rankings, "single candidate ranked at multiple levels")
        self.print_stat("Ambiguous Mark", self.ambiguous_present, "ballot had at least one ambiguous mark")
        self.print_stat("Ambiguous Mattered", self.ambiguous_mattered,
                        "ambiguous mark skipped during ballot processing")
        self.print_stat("Total Ambiguous", self.ambiguous_mattered, "total ambiguous")
        self.print_stat("Under Votes", self.under_votes, "No valid rankings after processing")

        # print("write_in_indices:  ", self.write_in_indices)
        # print("write_in_densities:  ", self.write_in_densities)

        print(f"irvWinner {irv.result().winner().name}")
        print(f"h2hWinner {h2h.result().winner().name}")
        self.print_irv_result(irv.result())
        print("h2h Matrix:")
        h2h.result().print_matrix(5)

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
                # if election_id == 69:
                if election_id not in elections:
                    elections[election_id] = Contest(election_id,
                                                     contests[election_id],
                                                     candidate_sets[election_id],
                                                     candidates_by_id)

                elections[election_id].add_marks(contest['Marks'])

    return elections


def main():
    # cvr_dir = "CVR_Export_20220908084311"
    cvr_dir = "CVR_Export"

    print(f"loading json from {cvr_dir}")
    if not os.path.exists(cvr_dir):
        print(f"""
        no cast vote record files found at {cvr_dir}.  
        
        Download the cast vote records from https://www.elections.alaska.gov/election-results/e/?id=22sspg
        At the bottom of the page, there is a link to the download "Cast Vote Record (zip)".
        Download that file and unzip it (your browser may automatically unzip it.)
        place the root directory ./{cvr_dir} in the local directory.
        
        Alternately, you can change the variable 'cvr_dir' at the top of main() to point at the location of the ballots.
        
        """)
    contest_json = json.load(open(f"{cvr_dir}/ContestManifest.json", "r"))
    candidates_json = json.load(open(f"{cvr_dir}/CandidateManifest.json"))

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

    sessions = load_sessions(cvr_dir, 1000 * 1000 * 1000)
    print(f"number of sessions: {len(sessions)}")
    elections = parse_all_cvr(sessions, contests, candidate_sets, candidates_by_id)
    for contest in elections.values():
        contest.run_elections()
        # contest.print_ballots()
        # contest.show_diversity_count()


main()
