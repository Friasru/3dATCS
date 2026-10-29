"""Running a controller through the 3D bridge must give *exactly* the same SUMO result as the ATCS runner.

If the snapshotting perturbed the simulation, or the controller were not the original one, tripinfo/summary would
differ. Both are compared trip-by-trip and step-by-step against a run of the verbatim `atcs_source/runner.py`.
"""
import asyncio
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from atcs3d import paths, scenarios
from atcs3d.worker_client import WorkerClient

CONTROLLERS = list(scenarios.CONTROLLERS)


def attrs(path, tag, drop=()):
    return [{k: v for k, v in e.attrib.items() if k not in drop} for e in ET.parse(path).getroot().iter(tag)]


@pytest.fixture(scope="module")
def reference():
    """Run the verbatim ATCS runner (uneven 500/200) once per controller. Output stays in atcs_source/output."""
    out = {}
    for c in CONTROLLERS:
        tag = f"parity_ref_{c}"
        subprocess.run([sys.executable, "runner.py", c, "--tag", tag], cwd=paths.ATCS_SOURCE, check=True,
                       capture_output=True, timeout=300)
        out[c] = (os.path.join(paths.ATCS_SOURCE, "output", f"tripinfo_{tag}.xml"),
                  os.path.join(paths.ATCS_SOURCE, "output", f"summary_{tag}.xml"))
    return out


async def run_via_bridge(controller, scenario, tag):
    """Step the worker one second at a time, exactly as the live server does, until SUMO says it is done."""
    w = await WorkerClient(tag).spawn()
    frames = 0
    try:
        await w.request({"cmd": "start", "controller": controller, "scenario": scenario, "tag": tag, "run_id": 1})
        while True:
            f = await w.request({"cmd": "step"})
            frames += 1
            if f.get("ended"):
                break
        res = await w.request({"cmd": "stop"})
    finally:
        await w.kill()
    return res, frames


@pytest.mark.parametrize("controller", CONTROLLERS)
def test_bridge_run_identical_to_atcs_runner(controller, reference):
    tag = f"parity_bridge_{controller}"
    res, frames = asyncio.run(run_via_bridge(controller, {"ew": 500, "ns": 200}, tag))
    ref_trip, ref_sum = reference[controller]
    my_trip = os.path.join(paths.OUTPUT_DIR, tag, "tripinfo.xml")
    my_sum = os.path.join(paths.OUTPUT_DIR, tag, "summary.xml")

    ref_trips, my_trips = attrs(ref_trip, "tripinfo"), attrs(my_trip, "tripinfo")
    assert len(my_trips) == len(ref_trips) == 1400
    assert my_trips == ref_trips  # every vehicle: same depart, arrival, duration, waitingTime, timeLoss...
    # every simulated second: same halting/running/etc. ("duration" is SUMO's wall-clock compute time per step)
    assert attrs(my_sum, "step", drop=("duration",)) == attrs(ref_sum, "step", drop=("duration",))
    assert frames > 3600


def test_published_atcs_numbers_reproduced(reference):
    """The reference itself reproduces the numbers ATCS published for this scenario (results/results.json)."""
    sys.path.insert(0, paths.ATCS_SOURCE)
    import metrics

    fixed = metrics.summarize(reference["fixed"][0])
    queue = metrics.summarize(reference["queue_based"][0])
    assert fixed["vehicles_completed"] == 1400
    assert round(fixed["avg_wait_s"], 2) == 13.39 and fixed["max_wait_s"] == 46.0 and round(fixed["avg_time_loss_s"], 2) == 23.35
    assert round(queue["avg_wait_s"], 2) == 6.07 and queue["max_wait_s"] == 25.0 and round(queue["avg_time_loss_s"], 2) == 15.11


def test_explicit_seed_equals_sumo_default():
    assert scenarios.SEED == 23423  # SUMO's built-in default seed, which the ATCS runner relies on
