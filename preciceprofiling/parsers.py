import argparse


def addUnitArgument(parser):
    parser.add_argument(
        "-u",
        "--unit",
        choices=["h", "m", "s", "ms", "us"],
        default="us",
        help="The duration unit to use",
    )


def addInputArgument(parser):
    parser.add_argument(
        "profilingfile",
        nargs="?",
        type=str,
        default="profiling.json",
        help="The profiling file to process",
    )


def makeAnalyzeParser(add_help: bool = True):
    analyze_help = """Analyze profiling data of a given solver.
    Event durations are displayed in the unit of choice.
    Parallel solvers show events of the primary rank next to the secondary ranks spending the least and most time in advance of preCICE.
    """
    analyze = argparse.ArgumentParser(description=analyze_help, add_help=add_help)
    analyze.add_argument("participant", type=str, help="The participant to analyze")
    addInputArgument(analyze)
    addUnitArgument(analyze)
    analyze.add_argument(
        "-e",
        "--event",
        nargs="?",
        type=str,
        default="advance",
        help="The event used to determine the most expensive and cheapest rank.",
    )
    analyze.add_argument("-o", "--output", help="Write the result to CSV file")

    return analyze


def makeHistogramParser(add_help: bool = True):
    histogram_help = """Plots the duration distribution of a single event of a given solver.
    Event durations are displayed in the unit of choice.
    """
    histogram = argparse.ArgumentParser(description=histogram_help, add_help=add_help)
    histogram.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write to file instead of displaying the plot",
    )
    histogram.add_argument(
        "-r", "--rank", type=int, default=None, help="Display only the given rank"
    )

    def try_int(s):
        try:
            return int(s)
        except:
            return s

    histogram.add_argument(
        "-b",
        "--bins",
        type=try_int,
        default="fd",
        help="Number of bins or strategy. Must be a valid argument to numpy.histogram_bin_edges",
    )
    histogram.add_argument("participant", type=str, help="The participant to analyze")
    histogram.add_argument("event", type=str, help="The event to analyze")
    addInputArgument(histogram)
    addUnitArgument(histogram)
    return histogram


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


def makeExportParser(add_help: bool = True):
    export_help = "Export the profiling data as a CSV file."
    export = argparse.ArgumentParser(description=export_help, add_help=add_help)
    addInputArgument(export)
    addUnitArgument(export)
    export.add_argument(
        "-o",
        "--output",
        type=str,
        default="profiling.csv",
        help="The CSV file to export to.",
    )
    return export
