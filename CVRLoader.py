import json
import os
import os.path as path
import pickle
from typing import List

from elections.Candidate import Candidate
from elections.Party import NoParty
from Contest import Contest



# there is a lot of conflict between my terminology for elections and the JSON terminology
# used by Dominion. In particular, I use the class Election to refer to something which implements
# a voting rule to determine a winner from a set of ranked-choice ballots for that election.
# a 'Ballot' is an ordered list of candidate scores in a single election.
#
# There is also conflict between my class 'Contest' which mirrors json defined contests in the
# CVR files.  Sorry for the confusion.

class CVRLoader(object):
    def __init__(self, cvr_directory: str, max_sessions: int = 1000000000):
        self.cvr_directory = cvr_directory
        self.max_sessions = max_sessions
        self.sessions = None
        self.candidates_by_id = {}
        self.candidate_sets = {}
        self.contest_description_by_id = {}
        self.elections = {}

        self.load()

    @staticmethod
    def pickle_sessions(sessions: List[dict], pickle_file: str) -> None:
        pickle.dump(sessions, open(pickle_file, "wb"))

    def load_all_cvr_export_files(self, directory: str):
        cvr_export_files = [file for file in os.listdir(directory) if
                            file.startswith('CvrExport') and file.endswith('.json')]
        all_sessions = []
        for file in cvr_export_files:
            with open(f"{directory}/{file}") as f:
                data = json.load(f)
                all_sessions.extend(data.get('Sessions', []))

            # If the total number of sessions loaded is at least max_sessions, stop loading more files
            if len(all_sessions) >= self.max_sessions:
                break
        return all_sessions

    def load_sessions(self, cvr_dir) -> list[dict]:
        pickle_file = f"{cvr_dir}/results-{self.max_sessions}.pickle"
        if path.exists(pickle_file):
            print(f"loading cvr from pickle file: {pickle_file}")
            return pickle.load(open(pickle_file, "rb"))
        else:
            json_file = f"{cvr_dir}/CvrExport.json"
            if path.exists(json_file):
                print(f"loading cvr from json {json_file}")
                cvr = json.load(open(json_file, "r"))
                ss = cvr['Sessions'][0 : self.max_sessions]
            else:
                ss = self.load_all_cvr_export_files(cvr_dir)

            self.pickle_sessions(ss, pickle_file)
            return ss

    def parse_all_cvr(self, sessions, contests, candidate_sets, candidates_by_id):
        for session in sessions:
            for card in session["Original"]["Cards"]:
                for contest in card["Contests"]:
                    election_id = contest['Id']
                    if election_id not in self.elections:
                        self.elections[election_id] = Contest(election_id,
                                                         contests[election_id],
                                                         candidate_sets[election_id],
                                                         candidates_by_id)

                    self.elections[election_id].add_marks(contest['Marks'])

    def load(self):
        cvr_dir = self.cvr_directory
        print(f"loading json from {cvr_dir}")
        if not os.path.exists(f"{cvr_dir}/ContestManifest.json"):
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
        # create a map from the contest_id to the contest description
        for c in contest_json['List']:
            self.contest_description_by_id[c["Id"]] = c["Description"]

        # create a map of candidates by id
        # create a map of elections to a list of candidates for that election
        for c in candidates_json['List']:
            candidate = Candidate(c['Description'], NoParty)
            self.candidates_by_id[c['Id']] = candidate
            if c['ContestId'] in self.candidate_sets:
                self.candidate_sets[c['ContestId']].append(candidate)
            else:
                self.candidate_sets[c['ContestId']] = [candidate]

        # load all sessions
        self.sessions = self.load_sessions(cvr_dir)
        print(f"number of sessions: {len(self.sessions)}")

        print("creating contests")
        # create a 'Contest' for each election and parse the ballots.
        self.parse_all_cvr(self.sessions, self.contest_description_by_id, self.candidate_sets, self.candidates_by_id)
