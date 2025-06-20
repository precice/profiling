from preciceprofiling.common import Run, ns_to_unit_factor
import polars as pl
from preciceprofiling.parsers import addInputArgument, addUnitArgument
import argparse
import sys


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


def printWide(df):
    from itertools import repeat

    def makeLabel(eventName):
        if "_GLOBAL" in eventName:
            return "total"

        indentation = "  "

        if "/" not in eventName:
            return indentation + eventName
        parts = eventName.split("/")
        return indentation * len(parts) + parts[-1]

    df: pl.DataFrame = (
        df.sort("eid")
        .with_columns(pl.col("eid").map_elements(makeLabel, return_dtype=pl.String))
        .rename({"eid": "name"})
    )

    blocksize = 6
    assert len(df.columns) % blocksize == 1

    headerFmts = []
    bodyFmts = []
    colWidths = []
    for col in df.iter_columns():
        headerWidth = len(col.name.encode())

        def fmt(d):
            if col.dtype == pl.Float32 or col.dtype == pl.Float64:
                return len(f"{d:.2f}")
            else:
                return len(f"{d}")

        width = col.map_elements(fmt, return_dtype=pl.Int64).max()
        width = max(width, headerWidth)
        colWidths.append(width)
        sw = str(width)

        headerFmts.append("{:<" + sw + "}")

        if col.dtype == pl.Float32 or col.dtype == pl.Float64:
            bodyFmts.append("{:>" + sw + ".2f}")
        elif col.dtype == pl.String:
            bodyFmts.append("{:<" + sw + "}")
        else:
            bodyFmts.append("{:>" + sw + "}")

    headerFmt = ""
    hline = ""
    bodyFmt = ""

    for col, (h, b, w) in enumerate(zip(headerFmts, bodyFmts, colWidths)):
        if col % blocksize == 1:
            headerFmt += " │ "
        else:
            headerFmt += " "
        headerFmt += h

        if col % blocksize == 1:
            hline += "─┼─"
        else:
            hline += " "

        hline += "─" * w

        if col % blocksize == 1:
            bodyFmt += " │ "
        else:
            bodyFmt += " "
        bodyFmt += b

    print(headerFmt.format(*(df.columns)))
    print(hline)
    for row in df.iter_rows():
        print(
            bodyFmt.format(
                *map(lambda e: float("nan") if e is None else e, row)
            ).replace("nan", "   ")
        )


def runAnalyze(ns):
    return analyzeCommand(
        ns.profilingfile, ns.participant, ns.event, ns.output, ns.unit
    )


def analyzeCommand(profilingfile, participant, event, outfile=None, unit="us"):
    run = Run(profilingfile)
    df = run.toDataFrame()

    participants = set(df.get_column("participant").unique())
    assert (
        participant in participants
    ), f"Given participant {participant} doesn't exist. Known: " + ", ".join(
        participants
    )

    print(f"Output timing are in {unit}.")

    # Filter by participant
    # Convert duration to requested unit
    dur_factor = 1000 * ns_to_unit_factor(unit)
    df = (
        df.filter(pl.col("participant") == participant)
        .drop("participant")
        .with_columns(
            (pl.col("dur") * dur_factor),
            (pl.col("dur") / pl.col("dur").max().over(["rank"]) * 100).alias("rel"),
        )
    )

    ranks = df.select("rank").unique()

    if len(ranks) == 1:
        joined = (
            df.group_by("eid")
            .agg(
                pl.sum("dur").alias("sum"),
                pl.sum("rel").alias("%"),
                pl.count("dur").alias("count"),
                pl.mean("dur").alias("mean"),
                pl.min("dur").alias("min"),
                pl.max("dur").alias("max"),
            )
            .sort("eid")
        )
    else:
        ldf = df.lazy()
        rankAdvance = (
            ldf.filter((pl.col("eid") == event) & (pl.col("rank") > 0))
            .group_by("rank")
            .agg(pl.col("dur").sum())
            .sort("dur")
            .collect()
        )
        minSecRank = rankAdvance.select(pl.first("rank")).item()
        maxSecRank = rankAdvance.select(pl.last("rank")).item()

        if minSecRank is None or maxSecRank is None:
            ranksToPrint = (0,)
            print(
                "Selection only contains the primary rank 0 as event isn't available on secondary ranks."
            )
        elif minSecRank == maxSecRank:
            ranksToPrint = (0, minSecRank)
            print(
                f"Selection contains the primary rank 0 and secondary rank {minSecRank}."
            )
        else:
            ranksToPrint = (0, minSecRank, maxSecRank)
            print(
                f"Selection contains the primary rank 0, the cheapest secondary rank {minSecRank}, and the most expensive secondary rank {maxSecRank}."
            )

        ldf = df.lazy()
        joined = (
            pl.concat(
                [
                    (
                        ldf.filter(pl.col("rank") == rank)
                        .group_by("eid")
                        .agg(
                            pl.sum("dur").alias(f"R{rank}:sum"),
                            pl.sum("rel").alias(f"R{rank}:%"),
                            pl.count("dur").alias(f"R{rank}:count"),
                            pl.mean("dur").alias(f"R{rank}:mean"),
                            pl.min("dur").alias(f"R{rank}:min"),
                            pl.max("dur").alias(f"R{rank}:max"),
                        )
                    )
                    for rank in ranksToPrint
                ],
                how="align",
            )
            .sort("eid")
            .collect()
        )

    printWide(joined)

    if outfile:
        print(f"Writing to {outfile}")
        joined.write_csv(outfile)

    return 0


def main():
    parser = makeAnalyzeParser()
    ns = parser.parse_args()
    return runAnalyze(ns)


if __name__ == "__main__":
    sys.exit(main())
