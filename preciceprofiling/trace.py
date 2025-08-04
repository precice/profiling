from preciceprofiling.common import Run
import orjson
import argparse
import sys
import pathlib
from preciceprofiling.perfetto import open_in_perfetto
from preciceprofiling.parsers import addInputArgument


def makeTraceParser(add_help: bool = True):
    trace_help = "Transform profiling to the Trace Event Format."
    trace = argparse.ArgumentParser(description=trace_help, add_help=add_help)
    addInputArgument(trace)
    trace.add_argument(
        "-o",
        "--output",
        default="trace.json",
        type=pathlib.Path,
        help="The resulting trace file",
    )
    trace.add_argument(
        "-w",
        "--web",
        action="store_true",
        help="Open resulting trace in ui.perfetto.dev",
    )
    trace.add_argument(
        "-l", "--limit", type=int, metavar="n", help="Select the first n ranks"
    )
    trace.add_argument(
        "-r", "--rank", type=int, nargs="*", help="Select individual ranks"
    )
    return trace


def runTrace(ns):
    return traceCommand(ns.profilingfile, ns.output, ns.rank, ns.limit, ns.web)


def traceCommand(profilingfile, outfile, rankfilter, limit, web):
    run = Run(profilingfile)
    selection = (
        set()
        .union(rankfilter if rankfilter else [])
        .union(range(limit) if limit else [])
    )
    traces = run.toTrace(selection)
    print(f"Writing to {outfile}")
    outfile.write_bytes(orjson.dumps(traces))

    if web:
        open_in_perfetto(outfile)
    return 0


def main():
    parser = makeTraceParser()
    ns = parser.parse_args()
    return runTrace(ns)


if __name__ == "__main__":
    sys.exit(main())
