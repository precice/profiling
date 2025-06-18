#! /usr/bin/env python3

import argparse
import sys

from preciceprofiling.common import (
    histogramCommand,
    exportCommand,
    analyzeCommand,
    traceCommand,
)


def main():
    parser = argparse.ArgumentParser(description="", epilog="")
    subparsers = parser.add_subparsers(
        title="commands",
        dest="cmd",
    )
    # parser.add_argument("-v", "--verbose", help="Print verbose output")
    parser.add_argument(
        "-u",
        "--unit",
        choices=["h", "m", "s", "ms", "us"],
        default="us",
        help="The duration unit to use",
    )

    analyze_help = """Analyze profiling data of a given solver.
    Event durations are displayed in the unit of choice.
    Parallel solvers show events of the primary rank next to the secondary ranks spending the least and most time in advance of preCICE.
    """
    analyze = subparsers.add_parser(
        "analyze", help=analyze_help.splitlines()[0], description=analyze_help
    )
    analyze.add_argument("participant", type=str, help="The participant to analyze")
    analyze.add_argument(
        "profilingfile",
        nargs="?",
        type=str,
        default="profiling.json",
        help="The profiling file to process",
    )
    analyze.add_argument(
        "-e",
        "--event",
        nargs="?",
        type=str,
        default="advance",
        help="The event used to determine the most expensive and cheapest rank.",
    )
    analyze.add_argument("-o", "--output", help="Write the result to CSV file")

    def try_int(s):
        try:
            return int(s)
        except:
            return s

    histogram_help = """Plots the duration distribution of a single event of a given solver.
    Event durations are displayed in the unit of choice.
    """
    histogram = subparsers.add_parser(
        "histogram", help=histogram_help.splitlines()[0], description=histogram_help
    )
    histogram.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write to file instead of displaying the plot",
    )
    histogram.add_argument(
        "-r", "--rank", type=int, default=None, help="Display only the given rank"
    )
    histogram.add_argument(
        "-b",
        "--bins",
        type=try_int,
        default="fd",
        help="Number of bins or strategy. Must be a valid argument to numpy.histogram_bin_edges",
    )
    histogram.add_argument("participant", type=str, help="The participant to analyze")
    histogram.add_argument("event", type=str, help="The event to analyze")
    histogram.add_argument(
        "profilingfile",
        nargs="?",
        type=str,
        default="profiling.json",
        help="The profiling file to process",
    )

    trace_help = "Transform profiling to the Trace Event Format."
    trace = subparsers.add_parser(
        "trace", help=trace_help.splitlines()[0], description=trace_help
    )
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

    export_help = "Export the profiling data as a CSV file."
    export = subparsers.add_parser(
        "export", help=export_help.splitlines()[0], description=export_help
    )
    export.add_argument(
        "profilingfile",
        nargs="?",
        type=str,
        default="profiling.json",
        help="The profiling files to process",
    )
    export.add_argument(
        "-o",
        "--output",
        type=str,
        default="profiling.csv",
        help="The CSV file to export to.",
    )

    args = parser.parse_args()

    dispatcher = {
        "trace": lambda ns: traceCommand(
            ns.profilingfile, ns.output, ns.rank, ns.limit
        ),
        "export": lambda ns: exportCommand(ns.profilingfile, ns.output, ns.unit),
        "analyze": lambda ns: analyzeCommand(
            ns.profilingfile, ns.participant, ns.event, ns.output, ns.unit
        ),
        "histogram": lambda ns: histogramCommand(
            ns.profilingfile,
            ns.output,
            ns.participant,
            ns.event,
            ns.rank,
            ns.bins,
            ns.unit,
        ),
    }

    def showHelp(ns):
        parser.print_help()
        return 1

    return dispatcher.get(args.cmd, showHelp)(args)


if __name__ == "__main__":
    sys.exit(main())
