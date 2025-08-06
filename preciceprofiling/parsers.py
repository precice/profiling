import pathlib


def addUnitArgument(parser):
    parser.add_argument(
        "-u",
        "--unit",
        choices=["h", "m", "s", "ms", "us"],
        default="us",
        help="The duration unit to use",
    )


def addInputArgument(parser):
    parser.add_argument(
        "profilingfile",
        nargs="?",
        type=pathlib.Path,
        default=pathlib.Path("profiling.db"),
        help="The profiling file to process",
    )
