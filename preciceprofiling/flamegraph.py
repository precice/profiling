from preciceprofiling.common import Run, ns_to_unit_factor
from preciceprofiling.parsers import addInputArgument, addUnitArgument
import polars as pl
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import argparse


def makeFlamegraphParser(add_help: bool = True):
    flamegraph_help = """Plots the hierarchical duration data of a solver as a flamegraph plot.
    Event durations are displayed in the unit of choice.
    Parallel solvers show one plot for the primary rank and a combined plot for all secondary ranks.
    """
    parser = argparse.ArgumentParser(description=flamegraph_help, add_help=add_help)
    parser.add_argument("participant", type=str, help="The participant to analyze")
    addInputArgument(parser)
    addUnitArgument(parser)
    return parser


def runFlamegraph(ns):
    return flamegraphCommand(ns.profilingfile, ns.participant, ns.unit)


def flamegraphCommand(profilingfile, participant, unit="us"):
    run = Run(profilingfile)

    participants = run.participants()
    assert (
        participant in participants
    ), f"Given participant {participant} unknown. Known participants are {', '.join(participants)}"

    df = run.toDataFrame(participant=participant)
    print(f"Output timing are in {unit}.")

    def toParent(eid):
        if eid == "_GLOBAL":
            return ""
        if "/" not in eid:
            return "_GLOBAL"
        return eid.rpartition("/")[0]

    def toLabel(eid):
        if eid == "_GLOBAL":
            return participant
        return eid.rpartition("/")[2]

    # Filter by participant
    # Convert duration to requested unit
    dur_factor = 1000 * ns_to_unit_factor(unit)
    df = (
        df.filter(pl.col("participant") == participant)
        .drop("participant")
        .with_columns(
            pl.col("dur") * dur_factor,
            pl.col("eid")
            .map_elements(toParent, return_dtype=pl.String)
            .alias("parent"),
            pl.col("eid").map_elements(toLabel, return_dtype=pl.String).alias("label"),
        )
    )

    primary = (
        df.filter(pl.col("rank") == 0)
        .group_by("eid", "parent", "label")
        .agg(pl.sum("dur"))
        .sort("eid")
    )

    hovertemplate = (
        "<b>%{label}</b><br><i>%{id}</i><br>%{value}"
        + unit
        + "<br>%{percentParent:.1%} of parent<br>%{percentRoot:.1%} of total"
    )

    primaryPlot = go.Icicle(
        labels=primary["label"].to_list(),
        ids=primary["eid"].to_list(),
        parents=primary["parent"].to_list(),
        values=primary["dur"].to_list(),
        branchvalues="total",
        tiling=dict(orientation="v", flip="y"),
        root_color="lightgrey",
        hovertemplate=hovertemplate,
        textinfo="label+percent root",
    )

    if len(df.select("rank").unique()) == 1:

        fig = go.Figure(primaryPlot)
        fig.update_layout(title=participant)
        fig.show()
        return 0

    secondary = (
        df.filter(pl.col("rank") > 0)
        .group_by("eid", "parent", "label")
        .agg(pl.sum("dur"))
        .sort("eid")
    )

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "domain"}, {"type": "domain"}]],
        subplot_titles=[f"Primary of {participant}", f"Secondaries of {participant}"],
    )
    fig.add_trace(primaryPlot, row=1, col=1)
    fig.add_trace(
        go.Icicle(
            labels=secondary["label"].to_list(),
            ids=secondary["eid"].to_list(),
            parents=secondary["parent"].to_list(),
            values=secondary["dur"].to_list(),
            branchvalues="total",
            tiling=dict(orientation="v", flip="y"),
            root_color="lightgrey",
            hovertemplate=hovertemplate,
            textinfo="label+percent root",
        ),
        row=1,
        col=2,
    )
    fig.show()
    return 0


def main():
    parser = makeFlamegraphParser()
    ns = parser.parse_args()
    return runFlamegraph(ns)


if __name__ == "__main__":
    sys.exit(main())
