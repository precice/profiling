from preciceprofiling.common import Run, ns_to_unit_factor
import matplotlib.pyplot as plt
import polars as pl
import argparse
import sys
from preciceprofiling.parsers import addInputArgument, addUnitArgument


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


def runHistogram(ns):
    return histogramCommand(
        ns.profilingfile,
        ns.output,
        ns.participant,
        ns.event,
        ns.rank,
        ns.bins,
        ns.unit,
    )


def histogramCommand(profilingfile, outfile, participant, event, rank, bins, unit="us"):
    run = Run(profilingfile)

    # Check user input
    assert (
        participant in run.participants()
    ), f"Given participant {participant} doesn't exist."
    assert event in run.events(), f"Given event {event} doesn't exist."

    df = run.toDataFrame(participant=participant, event=event)

    if not rank is None:
        assert df.select(
            pl.col("rank").is_in([rank]).any()
        ).item(), f"Given rank {rank} doesn't exist."

    # Filter by participant and event
    filter = (pl.col("participant") == participant) & (pl.col("eid") == event)
    # Optionally filter by rank
    if not rank is None:
        filter = filter & (pl.col("rank") == rank)

    # duration scaling factor
    dur_factor = 1000 * ns_to_unit_factor(unit)

    # Query durations
    durations = df.filter(filter).select(pl.col("dur") * dur_factor)

    ranks = df["rank"].unique()
    rankDesc = (
        "ranks: " + ",".join(map(str, ranks))
        if len(ranks) < 5
        else f"{len(ranks)} ranks"
    )

    fig, ax = plt.subplots(figsize=(14, 7), tight_layout=True)
    ax.set_title(f'Histogram of event "{event}" on {participant} ({rankDesc})')
    ax.set_xlabel(f"Duration [{unit}]")
    ax.set_ylabel("Occurrence")
    hist_data = ax.hist(durations, bins=bins, histtype="barstacked", align="mid")
    ax.bar_label(hist_data[2])
    binborders = hist_data[1]
    ax.set_xticks(binborders, labels=[f"{d:,.2f}" for d in binborders], rotation=90)
    ax.set_xlim(left=min(binborders), right=max(binborders))
    ax.grid(axis="x")

    if outfile:
        print(f"Writing to {outfile}")
        plt.savefig(outfile)
    else:
        plt.show()

    return 0


def main():
    parser = makeHistogramParser()
    ns = parser.parse_args()
    return runHistogram(ns)


if __name__ == "__main__":
    sys.exit(main())
