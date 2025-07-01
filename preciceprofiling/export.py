from preciceprofiling.common import Run
from preciceprofiling.parsers import addInputArgument, addUnitArgument
import argparse
import sys


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


def runExport(ns):
    return exportCommand(ns.profilingfile, ns.output, ns.unit)


def exportCommand(profilingfile, outfile, unit):
    run = Run(profilingfile)
    print(f"Writing to {outfile}")
    run.toExportDataFrame(unit).write_csv(outfile)
    return 0


def main():
    parser = makeExportParser()
    ns = parser.parse_args()
    return runExport(ns)


if __name__ == "__main__":
    sys.exit(main())
