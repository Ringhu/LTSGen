from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.remote.check_natural_qcc_remote_gpu_access import check_profile, parse_remote_stdout


class CheckNaturalQccRemoteGpuAccessTest(unittest.TestCase):
    def test_parse_remote_stdout(self):
        stdout = "\n".join(
            [
                "hostname=gpu-host",
                "root_exists=1",
                "git_branch=codex/question-repair-20260519-ready",
                "git_head=abc123",
                "python_exists=1",
                'python_modules_json={"peft": true, "torch": true, "transformers": true}',
                "torch_cuda_available=true",
                "torch_cuda_device_count=2",
                "gpu=0, NVIDIA A100-SXM4-80GB, 81920 MiB",
                "gpu=1, NVIDIA A100-SXM4-80GB, 81920 MiB",
            ]
        )

        parsed = parse_remote_stdout(stdout)

        self.assertEqual(parsed["hostname"], "gpu-host")
        self.assertTrue(parsed["root_exists"])
        self.assertTrue(parsed["python_exists"])
        self.assertEqual(parsed["python_modules_json"]["torch"], True)
        self.assertTrue(parsed["torch_cuda_available"])
        self.assertEqual(parsed["torch_cuda_device_count"], 2)
        self.assertEqual(len(parsed["gpus"]), 2)

    def test_check_profile_requires_cuda(self):
        fake_proc = SimpleNamespace(
            returncode=0,
            stdout="\n".join(
                [
                    "hostname=gpu-host",
                    "root_exists=1",
                    "python_exists=1",
                    "torch_cuda_available=false",
                    "torch_cuda_device_count=0",
                ]
            ),
            stderr="",
        )

        with patch("scripts.remote.check_natural_qcc_remote_gpu_access.subprocess.run", return_value=fake_proc):
            result = check_profile("a100", timeout=1, branch="codex/question-repair-20260519-ready")

        self.assertTrue(result["reachable"])
        self.assertFalse(result["access_pass"])

    def test_check_profile_passes_when_repo_python_and_cuda_exist(self):
        fake_proc = SimpleNamespace(
            returncode=0,
            stdout="\n".join(
                [
                    "hostname=gpu-host",
                    "root_exists=1",
                    "python_exists=1",
                    "torch_cuda_available=true",
                    "torch_cuda_device_count=1",
                    "gpu=0, NVIDIA RTX 3090, 24576 MiB",
                ]
            ),
            stderr="",
        )

        with patch("scripts.remote.check_natural_qcc_remote_gpu_access.subprocess.run", return_value=fake_proc):
            result = check_profile("3090", timeout=1, branch="codex/question-repair-20260519-ready")

        self.assertTrue(result["reachable"])
        self.assertTrue(result["access_pass"])
        self.assertEqual(result["parsed"]["torch_cuda_device_count"], 1)


if __name__ == "__main__":
    unittest.main()
