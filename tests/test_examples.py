import pathlib
import pytest
import tempfile
import polars as pl

from preciceprofiling.merge import mergeCommand
from preciceprofiling.analyze import analyzeCommand
from preciceprofiling.export import exportCommand
from preciceprofiling.trace import traceCommand


def get_cases():
    casesdir = pathlib.Path(__file__).parent / "cases"
    return [e for e in casesdir.iterdir() if e.is_dir()]


def get_json_cases():
    return [case for case in get_cases() if case.name.endswith("-json")]


def run_case(case: pathlib.Path, cwd: pathlib.Path, useDir: bool):
    profiling = cwd / "profiling.db"
    export = cwd / "profiling.csv"
    trace = cwd / "trace.json"
    unit = "us"

    mergeInputs = (
        [case]
        if useDir
        else list(case.glob("*-*-*.json")) + list(case.glob("*-*-*.txt"))
    )

    print("--- Merge")
    assert mergeCommand(mergeInputs, profiling, True) == 0
    assert profiling.exists()

    print("--- Export")
    assert exportCommand(profiling, export, unit) == 0
    assert export.exists()

    print("--- Trace")
    assert traceCommand(profiling, trace, unit, None, False) == 0
    assert trace.exists()

    participants = (
        pl.read_csv(cwd / "profiling.csv").get_column("participant").unique().to_list()
    )
    for i, part in enumerate(participants):
        print(f"--- Analyze {part}")
        out = cwd / f"analyze-{i}.csv"
        assert analyzeCommand(profiling, part, "advance", out, unit) == 0
        assert out.exists()


def truncate_case_files(case: pathlib.Path, tmp: pathlib.Path):
    for file in case.glob("*-*-*.json"):
        print(f"Truncating {file}")
        content = file.read_text()
        truncated = content.removesuffix("\n").removesuffix("]}")
        with open(tmp / file.name, "w") as f:
            f.write(truncated)


@pytest.mark.parametrize("case", get_cases())
@pytest.mark.parametrize("useDir", [True, False])
def test_case(case: pathlib.Path, useDir: bool):
    print(f"Testing case: {case}")

    with tempfile.TemporaryDirectory() as tmp:
        cwd = pathlib.Path(tmp)
        run_case(case, cwd, useDir)


@pytest.mark.parametrize("case", get_json_cases())
@pytest.mark.parametrize("useDir", [True, False])
def test_truncated_case(case: pathlib.Path, useDir: bool):
    print(f'Testing case: {case} {"dir" if useDir else "files"}')

    with tempfile.TemporaryDirectory() as tmp:
        cwd = pathlib.Path(tmp)
        truncate_case_files(case, cwd)
        run_case(cwd, cwd, useDir)
