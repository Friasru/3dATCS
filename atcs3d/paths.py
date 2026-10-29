"""Filesystem locations. Everything this project writes goes under ROOT (never into the original ATCS repo)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATCS_SOURCE = os.path.join(ROOT, "atcs_source")  # verbatim copy of the original ATCS simulation/ files
WEB_DIR = os.path.join(ROOT, "web")
OUTPUT_DIR = os.path.join(ROOT, "output")  # transient SUMO output (git-ignored)
RESULTS_DIR = os.environ.get("ATCS3D_RESULTS_DIR") or os.path.join(ROOT, "results")  # committed snapshot of benchmark results

NET_FILE = os.path.join(ATCS_SOURCE, "intersection_final.net.xml")
SUMOCFG = os.path.join(ATCS_SOURCE, "baseline.sumocfg")
TLS_ID = "A0"  # same junction id the original runner controls


def use_atcs_source():
    """Make the verbatim ATCS modules (controllers, runner, metrics) importable."""
    if ATCS_SOURCE not in sys.path:
        sys.path.insert(0, ATCS_SOURCE)
