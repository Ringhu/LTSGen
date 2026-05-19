#!/usr/bin/env python3
"""Check remote GPU access for the natural-QCC cross-domain smoke run."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_OUT = BASE / "natural_qcc_remote_gpu_access_check_20260520.json"

PROFILES = {
    "a100": {
        "ssh_target": "a100",
        "remote_root": "/cluster/home/user1/hulining/LTSGEN",
        "python": "/cluster/home/user1/anaconda3/envs/opentslm/bin/python3",
    },
    "3090": {
        "ssh_target": "3090",
        "remote_root": "/cluster/home/hulining/LTSGEN",
        "python": "/cluster/home/hulining/anaconda3/envs/opentslm/bin/python3",
    },
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def local_git_head() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def remote_probe_script(remote_root: str, python_path: str) -> str:
    return f"""set -euo pipefail
echo "hostname=$(hostname)"
echo "root_exists=$(test -d {remote_root!r} && echo 1 || echo 0)"
if test -d {remote_root!r}; then
  cd {remote_root!r}
  echo "git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo missing)"
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || echo missing)"
  echo "python_exists=$(test -x {python_path!r} && echo 1 || echo 0)"
  if test -x {python_path!r}; then
    {python_path!r} - <<'PY'
import importlib.util
import json

mods = {{name: importlib.util.find_spec(name) is not None for name in ("torch", "transformers", "peft")}}
print("python_modules_json=" + json.dumps(mods, sort_keys=True))
try:
    import torch

    print("torch_cuda_available=" + str(bool(torch.cuda.is_available())).lower())
    print("torch_cuda_device_count=" + str(torch.cuda.device_count() if torch.cuda.is_available() else 0))
except Exception as exc:  # noqa: BLE001
    print("torch_error=" + repr(exc))
PY
  fi
  nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader 2>/dev/null | sed 's/^/gpu=/' || true
fi
"""


def parse_remote_stdout(stdout: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {"gpus": []}
    for line in stdout.splitlines():
        if not line.strip() or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "gpu":
            parsed["gpus"].append(value)
        elif key == "python_modules_json":
            try:
                parsed[key] = json.loads(value)
            except json.JSONDecodeError:
                parsed[key] = value
        elif key in {"root_exists", "python_exists"}:
            parsed[key] = value == "1"
        elif key == "torch_cuda_available":
            parsed[key] = value == "true"
        elif key == "torch_cuda_device_count":
            try:
                parsed[key] = int(value)
            except ValueError:
                parsed[key] = value
        else:
            parsed[key] = value
    return parsed


def check_profile(profile: str, *, timeout: int, branch: str) -> dict[str, Any]:
    cfg = PROFILES[profile]
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={timeout}",
        cfg["ssh_target"],
        "bash",
        "-s",
    ]
    script = remote_probe_script(cfg["remote_root"], cfg["python"])
    proc = subprocess.run(cmd, input=script, text=True, capture_output=True, check=False, timeout=timeout + 20)
    parsed = parse_remote_stdout(proc.stdout)
    reachable = proc.returncode == 0
    access_pass = bool(
        reachable
        and parsed.get("root_exists")
        and parsed.get("python_exists")
        and parsed.get("torch_cuda_available")
        and parsed.get("torch_cuda_device_count", 0)
    )
    return {
        "profile": profile,
        "ssh_target": cfg["ssh_target"],
        "remote_root": cfg["remote_root"],
        "python": cfg["python"],
        "expected_branch": branch,
        "returncode": proc.returncode,
        "reachable": reachable,
        "access_pass": access_pass,
        "parsed": parsed,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Natural QCC Remote GPU Access Check（2026-05-20）",
        "",
        f"- local head: `{report['local_head']}`",
        f"- any access pass: `{report['any_access_pass']}`",
        "",
        "| profile | reachable | access pass | root | cuda | devices | stderr |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report["profiles"]:
        parsed = item.get("parsed") or {}
        stderr = (item.get("stderr_tail") or "").strip().replace("\n", " ")[:120]
        lines.append(
            f"| `{item['profile']}` | `{item['reachable']}` | `{item['access_pass']}` | "
            f"`{parsed.get('root_exists')}` | `{parsed.get('torch_cuda_available')}` | "
            f"`{parsed.get('torch_cuda_device_count')}` | `{stderr}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This check is a blocker diagnostic only. It does not run training and must not be treated as generated-caption QA evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", nargs="+", default=["a100", "3090"], choices=sorted(PROFILES))
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument("--branch", default="codex/question-repair-20260519-ready")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    profiles = [check_profile(profile, timeout=args.timeout, branch=args.branch) for profile in args.profiles]
    report = {
        "local_head": local_git_head(),
        "branch": args.branch,
        "profiles": profiles,
        "any_access_pass": any(item["access_pass"] for item in profiles),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["any_access_pass"] else 1)


if __name__ == "__main__":
    main()
