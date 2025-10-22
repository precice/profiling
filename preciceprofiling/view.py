from preciceprofiling.parsers import addInputArgument
from preciceprofiling.perfetto import open_in_perfetto
import argparse
import sys
import pathlib
import json


def makeViewParser(add_help: bool = True):
    view_help = "Open the trace in ui.perfetto.dev"
    view = argparse.ArgumentParser(description=view_help, add_help=add_help)
    view.add_argument(
        "pftrace",
        nargs="?",
        type=pathlib.Path,
        default=pathlib.Path("profiling.pftrace"),
        help="The perfetto trace file to view",
    )
    view.add_argument(
        "-c",
        "--commands",
        type=pathlib.Path,
        help="File to read startup commands from",
    )
    view.add_argument(
        "-i",
        "--isolate",
        type=int,
        nargs="+",
        help="Isolate ranks in new workspace",
    )
    return view


def runView(ns):
    return viewCommand(ns.pftrace, ns.commands, ns.isolate)


def viewCommand(tracefile, commandsFile, isolate):
    cmds = []
    if isolate:
        matcher = "|".join(map(str, isolate))
        WORKSPACE = "preCICE"
        cmds.append({"id": "dev.perfetto.CreateWorkspace", "args": [WORKSPACE]})
        cmds.append(
            {
                "id": "dev.perfetto.CopyTracksToWorkspaceByRegexWithAncestors",
                "args": [f".*Rank ({matcher})$", WORKSPACE, "path"],
            }
        )
        cmds.append({"id": "dev.perfetto.SwitchWorkspace", "args": [WORKSPACE]})
    if commandsFile:
        assert commandsFile.exists()
        cmds.extend(json.loads(commandsFile.read_bytes()))
    open_in_perfetto(tracefile, startupCommands=cmds)
    return 0


def main():
    parser = makeViewParser()
    ns = parser.parse_args()
    return runView(ns)


if __name__ == "__main__":
    sys.exit(main())
