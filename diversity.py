#!venv/bin/python3
from CVRLoader import CVRLoader
from Contest import Contest
from elections.DiversityRunoff import *


def analyze_election(contest: Contest):
    print(f"{contest.name} id {contest.contest_id}")
    diversity_runoff = DiversityRunoffElection(contest.ballots,
                                               set(contest.candidates),
                                               diversity_threshold=.10,
                                               diversity_depth=1000,
                                               debug=True)
    print(f"{contest.name} winner: {diversity_runoff.result().winner().name}")


def main():
    cvr = CVRLoader("CVR_Export", 10 * 1000 * 1000)
    print(f"loaded {len(cvr.elections)} elections")
    for contest in [c for c in cvr.elections.values() if len(c.ballots) > 0]:
        analyze_election(contest)


main()
