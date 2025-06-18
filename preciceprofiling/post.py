#! /usr/bin/env python3

import argparse
import sys

from preciceprofiling.analyze import runAnalyze, makeAnalyzeParser
from preciceprofiling.export import runExport, makeExportParser
from preciceprofiling.histogram import runHistogram, makeHistogramParser
from preciceprofiling.trace import runTrace, makeTraceParser


def main():
    parser = argparse.ArgumentParser(description="", epilog="")
    subparsers = parser.add_subparsers(
        title="commands",
        dest="cmd",
    )

    def add_subparser(name, parserFactory):
        parser = parserFactory(False)
        subparsers.add_parser(
            name,
            help=parser.description,
            description=parser.description,
            parents=[parser],
        )

    add_subparser("analyze", makeAnalyzeParser)
    add_subparser("trace", makeTraceParser)
    add_subparser("export", makeExportParser)
    add_subparser("histogram", makeHistogramParser)

    args = parser.parse_args()

    dispatcher = {
        "trace": runTrace,
        "export": runExport,
        "analyze": runAnalyze,
        "histogram": runHistogram,
    }

    def showHelp(ns):
        parser.print_help()
        return 1

    return dispatcher.get(args.cmd, showHelp)(args)


if __name__ == "__main__":
    sys.exit(main())
