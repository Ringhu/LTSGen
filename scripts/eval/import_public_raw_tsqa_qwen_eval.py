#!/usr/bin/env python3
"""Import packaged A100/Qwen Public Raw TSQA v4 evaluation results."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_DIR = (
    ROOT
    / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521/model_eval_20260521"
)
REQUIRED_FILES = ("prompt_report.json", "prompt_preview.jsonl", "predictions.jsonl", "metrics.json")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_safe_tar(tar: tarfile.TarFile) -> None:
    for member in tar.getmembers():
        name = member.name
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"unsafe tar member path: {name}")


def top_level_dir(tar: tarfile.TarFile) -> str:
    roots = {Path(member.name).parts[0] for member in tar.getmembers() if Path(member.name).parts}
    if len(roots) != 1:
        raise SystemExit(f"expected one top-level run directory in archive, got: {sorted(roots)}")
    return next(iter(roots))


def verify_run_dir(run_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (run_dir / name).is_file()]
    if missing:
        raise SystemExit(f"missing required files under {run_dir}: {missing}")


def copy_run_dir(source: Path, target: Path, *, overwrite: bool) -> None:
    if target.exists():
        if not overwrite:
            raise SystemExit(f"target exists; pass --overwrite to replace: {target}")
        shutil.rmtree(target)
    shutil.copytree(source, target)


def import_archive(source: Path, eval_dir: Path, *, overwrite: bool) -> Path:
    with tarfile.open(source, "r:*") as tar:
        ensure_safe_tar(tar)
        run_name = top_level_dir(tar)
        target = eval_dir / run_name
        if target.exists():
            if not overwrite:
                raise SystemExit(f"target exists; pass --overwrite to replace: {target}")
            shutil.rmtree(target)
        with tempfile.TemporaryDirectory(prefix="public_raw_tsqa_import_") as tmp:
            tmp_dir = Path(tmp)
            tar.extractall(tmp_dir)
            extracted = tmp_dir / run_name
            verify_run_dir(extracted)
            shutil.move(str(extracted), str(target))
    verify_run_dir(target)
    return target


def import_directory(source: Path, eval_dir: Path, *, overwrite: bool) -> Path:
    verify_run_dir(source)
    target = eval_dir / source.name
    if source.resolve() != target.resolve():
        copy_run_dir(source, target, overwrite=overwrite)
    verify_run_dir(target)
    return target


def run_python(args: list[str]) -> None:
    subprocess.run(["python3", *args], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", type=Path, help="A100 run directories or .tar.gz archives")
    parser.add_argument("--eval_dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip_compare", action="store_true")
    args = parser.parse_args()

    args.eval_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []
    for source in args.sources:
        source = source.expanduser()
        if not source.exists():
            raise SystemExit(f"missing source: {source}")
        if source.is_dir():
            run_dir = import_directory(source, args.eval_dir, overwrite=args.overwrite)
        else:
            run_dir = import_archive(source, args.eval_dir, overwrite=args.overwrite)
        run_python(
            [
                "scripts/eval/summarize_public_raw_tsqa_model_eval.py",
                "--predictions_jsonl",
                rel(run_dir / "predictions.jsonl"),
                "--out_json",
                rel(run_dir / "error_summary.json"),
                "--quiet",
            ]
        )
        imported.append(run_dir)

    if not args.skip_compare:
        run_python(["scripts/eval/compare_public_raw_tsqa_model_evals.py", "--eval_dir", rel(args.eval_dir)])

    for run_dir in imported:
        print(f"[imported] {rel(run_dir)}")


if __name__ == "__main__":
    main()
