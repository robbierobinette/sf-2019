#!venv/bin/python3
from CVRLoader import CVRLoader
from Contest import Contest
from elections.DiversityRunoff import *
from elections.InstantRunoffElection import InstantRunoffElection
from elections.HeadToHeadElection import HeadToHeadElection
from argparse import ArgumentParser


def analyze_election(contest: Contest, diversity_threshold=.035, diversity_depth=2, debug=False):
    print(f"\n\n\nDiagnostics for Diversity Runoff for {contest.name} id {contest.contest_id}")
    diversity_runoff = DiversityRunoffElection(contest.ballots,
                                               set(contest.candidates),
                                               diversity_threshold=diversity_threshold,
                                               diversity_depth=diversity_depth,
                                               debug=debug)
    print(f"{contest.name} Diversity Runoff Winner: {diversity_runoff.result().winner().name}")
    head_to_head = HeadToHeadElection(contest.ballots, set(contest.candidates))

    print("\n\nCondorcet Pairwise Comparisons")
    head_to_head.result().print_matrix()




# parse the input arguments.
# three arguments are accepted:
#   the directory containing the CVR files
# the diversity_threshold (default .035)
# the diversity_depth (default 2)
# and a debug flag (default False)

def main():

    # parse the input arguments.
    argparse = ArgumentParser()
    argparse.add_argument("--dir", help="Directory containing the CVR files", default="CVR_Export")
    argparse.add_argument("-t", "--diversity_threshold", help="Diversity threshold", type=float, default=.035)
    argparse.add_argument("-d", "--diversity_depth", help="Diversity depth", type=int, default=2)
    argparse.add_argument("--debug", action="store_true", help="Debug flag", default=False)
    args = argparse.parse_args()



    cvr = CVRLoader(args.dir, 10 * 1000 * 1000)
    print(f"loaded {len(cvr.elections)} elections")
    for contest in [c for c in cvr.elections.values() if len(c.ballots) > 0]:
        analyze_election(contest, args.diversity_threshold, args.diversity_depth, args.debug)

main()
