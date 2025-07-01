import pathlib
import pytest
import tempfile
import subprocess
import polars as pl


def get_cases():
    casesdir = pathlib.Path(__file__).parent / "cases"
    return [e for e in casesdir.iterdir() if e.is_dir()]


def run_case(case: pathlib.Path, cwd: pathlib.Path):
    print("--- Merge")
    subprocess.run(["precice-profiling-merge", str(case)], check=True, cwd=cwd)
    assert (cwd / "profiling.json").exists()

    print("--- Export")
    subprocess.run(["precice-profiling-export"], check=True, cwd=cwd)
    assert (cwd / "profiling.csv").exists()

    print("--- Trace")
    subprocess.run(["precice-profiling-trace"], check=True, cwd=cwd)
    assert (cwd / "trace.json").exists()

    participants = (
        pl.read_csv(cwd / "profiling.csv").get_column("participant").unique().to_list()
    )
    for i, part in enumerate(participants):
        print(f"--- Analyze {part}")
        out = cwd / f"analyze-{i}.csv"
        subprocess.run(
            ["precice-profiling-analyze", "-o", str(out), part], check=True, cwd=cwd
        )
        assert out.exists()


def truncate_case_files(case: pathlib.Path, tmp: pathlib.Path):
    for file in case.iterdir():
        print(f"Truncating {file}")
        content = file.read_text()
        truncated = content.removesuffix("\n").removesuffix("]}")
        with open(tmp / file.name, "w") as f:
            f.write(truncated)


@pytest.mark.parametrize("case", get_cases())
def test_case(case: pathlib.Path):
    print(f"Testing case: {case}")

    with tempfile.TemporaryDirectory() as tmp:
        cwd = pathlib.Path(tmp)
        run_case(case, cwd)


@pytest.mark.parametrize("case", get_cases())
def test_truncated_case(case: pathlib.Path):
    print(f"Testing case: {case}")

    with tempfile.TemporaryDirectory() as tmp:
        cwd = pathlib.Path(tmp)
        truncate_case_files(case, cwd)
        run_case(cwd, cwd)
