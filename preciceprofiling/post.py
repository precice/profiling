#! /usr/bin/env python3

import argparse
import sys

from preciceprofiling.analyze import analyzeCommand
from preciceprofiling.export import exportCommand
from preciceprofiling.histogram import histogramCommand
from preciceprofiling.trace import traceCommand

from preciceprofiling.parsers import (
    makeTraceParser,
    makeExportParser,
    makeAnalyzeParser,
    makeHistogramParser,
)


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
