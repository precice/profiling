import csv
from preciceprofiling.common import Run


def exportCommand(profilingfile, outfile, unit):
    run = Run(profilingfile)
    dataFields = run.allDataFields()
    fieldnames = [
        "participant",
        "rank",
        "size",
        "event",
        "timestamp",
        "duration",
    ] + dataFields
    print(f"Writing to {outfile}")
    with open(outfile, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)
        writer.writerows(run.toExportList(unit, dataFields))
    return 0
