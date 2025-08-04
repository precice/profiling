# preCICE profiling tools

## Workflow

1. _Optional_ Enable `<profiling mode="all"/>` in the preCICE configuration of your case to get the profiling information.
2. Run the preCICE simulation.
3. Run `precice-profiling-merge` to combine all emitted profiling files of the simulation into a single `profiling.db` file.
4. Analyze the solvers:
    * Use `precice-profiling-analyze` to get a breakdown of an individual solver.
    * Use `precice-profiling-trace` to visualize the data.
    * Use `precice-profiling-export` to export the data as CSV to import in other software.


## Tools

### merge

Merges profiling files emitted by each rank of each participant into a single easily portable file.
Creates a `profiling.db` by default.

### export

Transforms all events to a tabular format and exports the result as a CSV format.
The columns `Participant`, and `Rank` can be used to filter the dataset to extract individual participants or specific ranks.

Reads `profiling.db` and creates `profiling.csv` by default.

### trace

Transforms all events to the [Google Trace Format](https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU) which can be visualized by tools such as `about::tracing` in Chromium based browsers or [perfetto.dev](https://ui.perfetto.dev/).

Reads `profiling.db` and creates `trace.json` by default.

### analyze

Analyzes a given solver and returns a table of all timings including some statistics based on their duration.

Reads `profiling.db` by default.

## HPC users

HPC users or users of locked down clusters without easy access to pip can download the [`merge` command](https://raw.githubusercontent.com/precice/profiling/refs/heads/main/preciceprofiling/merge.py) as a standalone file and run it without installing additional dependencies.

```console
wget -O precice-profiling-merge https://raw.githubusercontent.com/precice/profiling/refs/heads/main/preciceprofiling/merge.py
chmod +x precice-profiling-merge
```

## Licensing

This repository contains modified part of the the `precice-profiling` script, which is part of the preCICE library (precice/precice `tools/profiling/precice-profiling`) and licensed under the LGPv3 license.
The two copyright holders David Schneider (@davidscn david.schneider@ipvs.uni-stuttgart.de) and Frédéric Simonis (@fsimonis frederic.simonis@ipvs.uni-stuttgart.de) decided on 23. June 2025 15:00 CET to rerelease the content of the `precice-profiling` script in this repository under the MIT license.
