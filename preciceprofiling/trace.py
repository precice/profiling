from preciceprofiling.common import Run
import orjson
import argparse
import sys


def makeTraceParser(add_help: bool = True):
    trace_help = "Transform profiling to the Trace Event Format."
    trace = argparse.ArgumentParser(description=trace_help, add_help=add_help)
    trace.add_argument(
        "profilingfile",
        type=str,
        nargs="?",
        default="profiling.json",
        help="The profiling file to process",
    )
    trace.add_argument(
        "-o", "--output", default="trace.json", help="The resulting trace file"
    )
    trace.add_argument(
        "-l", "--limit", type=int, metavar="n", help="Select the first n ranks"
    )
    trace.add_argument(
        "-r", "--rank", type=int, nargs="*", help="Select individual ranks"
    )
    return trace


def runTrace(ns):
    return traceCommand(ns.profilingfile, ns.output, ns.rank, ns.limit)


def traceCommand(profilingfile, outfile, rankfilter, limit):
    run = Run(profilingfile)
    selection = (
        set()
        .union(rankfilter if rankfilter else [])
        .union(range(limit) if limit else [])
    )
    traces = run.toTrace(selection)
    print(f"Writing to {outfile}")
    with open(outfile, "wb") as outfile:
        outfile.write(orjson.dumps(traces))
    return 0


def main():
    parser = makeTraceParser()
    ns = parser.parse_args()
    return runTrace(ns)


if __name__ == "__main__":
    sys.exit(main())
