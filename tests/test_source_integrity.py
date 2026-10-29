"""The ATCS controllers and SUMO inputs we run must be exactly the originals.

Two checks: the copies match the checksums recorded at copy time, and (when the original checkout is on this
machine) they still match the original files. The original is only ever *read* here.
"""
import hashlib
import os
import subprocess
import sys

import pytest

from atcs3d import paths

ORIGINAL_SIM = os.path.expanduser("~/ATCS-Adaptive-Traffic-Control-System/simulation")
CONTROLLER_FILES = [
    "controllers/__init__.py",
    "controllers/fixed.py",
    "controllers/queue_based.py",
    "controllers/wait_time.py",
]
SIM_FILES = CONTROLLER_FILES + ["runner.py", "metrics.py", "baseline.sumocfg", "routes.rou.xml", "intersection_final.net.xml"]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def recorded():
    out = {}
    with open(os.path.join(paths.ATCS_SOURCE, "SHA256SUMS")) as f:
        for line in f:
            digest, name = line.split(None, 1)
            out[name.strip().removeprefix("./")] = digest
    return out


@pytest.mark.parametrize("name", SIM_FILES)
def test_copy_matches_recorded_checksum(name):
    assert sha(os.path.join(paths.ATCS_SOURCE, name)) == recorded()[name]


@pytest.mark.skipif(not os.path.isdir(ORIGINAL_SIM), reason="original ATCS checkout not on this machine")
@pytest.mark.parametrize("name", SIM_FILES)
def test_copy_matches_original_repository(name):
    assert sha(os.path.join(paths.ATCS_SOURCE, name)) == sha(os.path.join(ORIGINAL_SIM, name))


def test_original_atcs_unit_tests_pass_against_the_copies():
    """The ATCS team's own controller/metrics/route/integration tests, run on our copies (writes only to atcs_source/output)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=paths.ATCS_SOURCE, capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert " passed" in proc.stdout
