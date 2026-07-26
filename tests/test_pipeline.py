from pathlib import Path

from open_dmrv.pipeline import run_synthetic_pipeline


def test_pipeline_outputs(tmp_path: Path) -> None:
    paths = run_synthetic_pipeline(tmp_path, "config.yml")
    assert all(path.exists() for path in paths.values())
