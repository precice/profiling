from preciceprofiling.common import Run
import ujson


def traceCommand(profilingfile, outfile, rankfilter, limit):
    run = Run(profilingfile)
    selection = (
        set()
        .union(rankfilter if rankfilter else [])
        .union(range(limit) if limit else [])
    )
    traces = run.toTrace(selection)
    print(f"Writing to {outfile}")
    with open(outfile, "w") as outfile:
        ujson.dump(traces, outfile)
    return 0
