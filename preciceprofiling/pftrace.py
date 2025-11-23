from preciceprofiling.common import Run
import argparse
import sys
import pathlib
from preciceprofiling.parsers import addInputArgument


def makePFTraceParser(add_help: bool = True):
    trace_help = "Transform profiling to the perfetto trace."
    trace = argparse.ArgumentParser(description=trace_help, add_help=add_help)
    addInputArgument(trace)
    trace.add_argument(
        "-o",
        "--output",
        default="profiling.pftrace",
        type=pathlib.Path,
        help="The resulting perfetto trace file",
    )
    return trace


def runPFTrace(ns):
    return pftraceCommand(ns.profilingfile, ns.output)


def pftraceCommand(profilingfile, outfile):
    run = Run(profilingfile)
    print(f"Building perfetto trace")
    trace = run.toPFTrace()
    print(f"Writing to {outfile}")
    outfile.write_bytes(trace)
    return 0


def main():
    parser = makePFTraceParser()
    ns = parser.parse_args()
    return runPFTrace(ns)


if __name__ == "__main__":
    sys.exit(main())
