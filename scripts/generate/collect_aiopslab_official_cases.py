#!/usr/bin/env python3
"""Collect official AIOpsLab telemetry cases on the 3090 LoopBench deployment.

This script is intended to run inside:

    /cluster/home/hulining/projects/loopbench-ts/aiopslab

It uses AIOpsLab's own problem classes and Prometheus observer, then writes a
case manifest plus metrics CSV files. It avoids the known noisy atexit double
recover path by not using Orchestrator.init_problem; instead it instantiates the
problem directly and handles deploy/fault/workload/metrics/cleanup explicitly.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


CASE_PLAN = {
    "port_misconfig_user": {
        "problem_id": "k8s_target_port-misconfig-mitigation-1",
        "fault_family": "port_misconfig",
        "faulty_service": "user-service",
        "app": "social-network",
    },
    "port_misconfig_text": {
        "problem_id": "k8s_target_port-misconfig-mitigation-2",
        "fault_family": "port_misconfig",
        "faulty_service": "text-service",
        "app": "social-network",
    },
    "port_misconfig_post_storage": {
        "problem_id": "k8s_target_port-misconfig-mitigation-3",
        "fault_family": "port_misconfig",
        "faulty_service": "post-storage-service",
        "app": "social-network",
    },
    "revoke_auth_geo": {
        "problem_id": "revoke_auth_mongodb-mitigation-1",
        "fault_family": "revoke_auth",
        "faulty_service": "mongodb-geo",
        "app": "hotel-reservation",
    },
    "revoke_auth_rate": {
        "problem_id": "revoke_auth_mongodb-mitigation-2",
        "fault_family": "revoke_auth",
        "faulty_service": "mongodb-rate",
        "app": "hotel-reservation",
    },
    "scale_pod_zero_user": {
        "problem_id": "scale_pod_zero_social_net-mitigation-1",
        "fault_family": "scale_pod_zero",
        "faulty_service": "user-service",
        "app": "social-network",
    },
}


@dataclass(frozen=True)
class CaseSpec:
    case_key: str
    problem_id: str
    fault_family: str
    faulty_service: str
    app: str
    seed: int

    @property
    def case_id(self) -> str:
        return f"{self.fault_family}_seed{self.seed}_{self.faulty_service}"


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def cleanup_cluster() -> dict[str, Any]:
    """Best-effort cleanup for workload residue shared by AIOpsLab cases."""
    commands = [
        ["kubectl", "delete", "job", "wrk2-job", "-n", "default", "--ignore-not-found=true"],
        ["kubectl", "delete", "job", "wrk2-job", "-n", "test-social-network", "--ignore-not-found=true"],
        ["kubectl", "delete", "job", "wrk2-job", "-n", "test-hotel-reservation", "--ignore-not-found=true"],
    ]
    out = []
    for cmd in commands:
        try:
            proc = _run(cmd, timeout=30)
            out.append({"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        except Exception as exc:  # noqa: BLE001
            out.append({"cmd": cmd, "error": repr(exc)})
    return {"commands": out}


def make_problem(spec: CaseSpec) -> Any:
    if spec.problem_id.startswith("k8s_target_port-misconfig"):
        from aiopslab.orchestrator.problems.k8s_target_port_misconfig import (
            K8STargetPortMisconfigMitigation,
        )

        return K8STargetPortMisconfigMitigation(faulty_service=spec.faulty_service)
    if spec.problem_id.startswith("revoke_auth_mongodb"):
        from aiopslab.orchestrator.problems.revoke_auth import MongoDBRevokeAuthMitigation

        return MongoDBRevokeAuthMitigation(faulty_service=spec.faulty_service)
    if spec.problem_id.startswith("scale_pod_zero_social_net"):
        from aiopslab.orchestrator.problems.scale_pod import ScalePodSocialNetMitigation

        return ScalePodSocialNetMitigation()
    raise ValueError(f"Unsupported AIOpsLab problem: {spec.problem_id}")


def collect_metrics(case_dir: Path, start_time: datetime, end_time: datetime) -> dict[str, Any]:
    from aiopslab.observer import observe as observe_mod
    from aiopslab.observer.observe import collect_metrics as collect_metrics_fn

    orig_root = observe_mod.root_path
    observe_mod.root_path = case_dir
    try:
        collect_metrics_fn(start_time=start_time, end_time=end_time)
    finally:
        observe_mod.root_path = orig_root
    csv_files = sorted(str(path) for path in (case_dir / "metrics_output").rglob("*.csv"))
    return {"csv_count": len(csv_files), "csv_files": csv_files[:200]}


def run_case(spec: CaseSpec, outdir: Path, post_fault_wait_s: int, logger: Callable[[str], None]) -> dict[str, Any]:
    case_dir = outdir / spec.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    logger(f"[{spec.case_id}] start problem={spec.problem_id}")

    problem = make_problem(spec)
    status = "ok"
    error = ""
    fault_start = None
    metrics_end = None
    metrics_info: dict[str, Any] = {}
    cleanup_info: dict[str, Any] = {}

    try:
        try:
            problem.app.delete()
        except Exception as exc:  # noqa: BLE001
            logger(f"[{spec.case_id}] pre-delete warning: {exc!r}")
        problem.app.deploy()
        logger(f"[{spec.case_id}] app deployed namespace={problem.namespace}")

        fault_start = datetime.now(timezone.utc)
        problem.inject_fault()
        logger(f"[{spec.case_id}] fault injected; starting workload")
        try:
            problem.start_workload()
        except Exception as exc:  # noqa: BLE001
            logger(f"[{spec.case_id}] workload warning: {exc!r}")

        logger(f"[{spec.case_id}] waiting {post_fault_wait_s}s for telemetry")
        time.sleep(post_fault_wait_s)
        metrics_end = datetime.now(timezone.utc)
        metrics_info = collect_metrics(
            case_dir,
            start_time=fault_start - timedelta(seconds=min(60, post_fault_wait_s)),
            end_time=metrics_end,
        )
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        error = repr(exc)
        logger(f"[{spec.case_id}] FAILED: {error}")
    finally:
        try:
            problem.recover_fault()
        except Exception as exc:  # noqa: BLE001
            logger(f"[{spec.case_id}] recover warning: {exc!r}")
        try:
            problem.app.cleanup()
        except Exception as exc:  # noqa: BLE001
            logger(f"[{spec.case_id}] app cleanup warning: {exc!r}")
        cleanup_info = cleanup_cluster()

    finished = datetime.now(timezone.utc)
    manifest = {
        "case_id": spec.case_id,
        "case_key": spec.case_key,
        "problem_id": spec.problem_id,
        "fault_family": spec.fault_family,
        "faulty_service": spec.faulty_service,
        "app": spec.app,
        "seed": spec.seed,
        "fault_start_utc": _iso_utc(fault_start or started),
        "metrics_end_utc": _iso_utc(metrics_end or finished),
        "metrics_dir": str(case_dir / "metrics_output"),
        "metrics_info": metrics_info,
        "cleanup_info": cleanup_info,
        "wall_s": round((finished - started).total_seconds(), 3),
        "status": status,
        "error": error,
    }
    (case_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger(f"[{spec.case_id}] done status={status} csv={metrics_info.get('csv_count', 0)}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--case_keys", nargs="+", default=["port_misconfig_user"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--post_fault_wait_s", type=int, default=30)
    parser.add_argument("--skip_existing", action="store_true")
    args = parser.parse_args()

    unknown = sorted(set(args.case_keys) - set(CASE_PLAN))
    if unknown:
        raise ValueError(f"Unknown case keys: {unknown}; available={sorted(CASE_PLAN)}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / "driver.log"
    log_f = log_path.open("a", encoding="utf-8", buffering=1)

    def logger(message: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
        print(line, flush=True)
        log_f.write(line + "\n")

    logger(f"=== collect_aiopslab_official_cases outdir={outdir}")
    manifests: list[dict[str, Any]] = []
    for case_key in args.case_keys:
        base = CASE_PLAN[case_key]
        for seed in args.seeds:
            spec = CaseSpec(case_key=case_key, seed=seed, **base)
            if args.skip_existing and (outdir / spec.case_id / "manifest.json").exists():
                logger(f"[skip] {spec.case_id}")
                continue
            manifests.append(run_case(spec, outdir, args.post_fault_wait_s, logger))
            time.sleep(10)

    index_path = outdir / "index.json"
    previous = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    index_path.write_text(json.dumps(previous + manifests, indent=2), encoding="utf-8")
    logger(f"=== done cases={len(manifests)}")
    log_f.close()


if __name__ == "__main__":
    if Path.cwd().name != "aiopslab":
        print("warning: expected to run from the AIOpsLab repository root", file=sys.stderr)
    main()
