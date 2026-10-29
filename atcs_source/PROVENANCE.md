# Provenance of the files in `atcs_source/`

Everything in this directory (except this file and `SHA256SUMS`) is a **verbatim, unmodified copy**
of files from the original ATCS project, which is read-only for 3dATCS.

| Item | Value |
|---|---|
| Source repository | https://github.com/Friasru/ATCS-Adaptive-Traffic-Control-System |
| Source commit | `83f909d00ffc22d6089849d23f3a96479f8fbeab` (`main`, "Merge pull request #13 from Friasru/ian/home-controllers") |
| Source directory | `simulation/` |
| Authors | Alberto Frias (`Friasru`), Ian Aviles (`IanAvi15`) — see the original README "Team" section |
| Copied on | 2026-10-28 |

The files were copied with `cp` (read access to the original only) and verified byte-for-byte with `cmp`.
`SHA256SUMS` records the checksums of the copies. `tests/test_source_integrity.py` re-compares them against
the original checkout when it is present on disk (read-only), and against `SHA256SUMS` otherwise.

**Do not edit these files.** If the ATCS team changes a controller, re-copy it and update this file and `SHA256SUMS`.
All adaptation (running the controllers inside the 3D bridge) lives in `atcs3d/`, never here.

## What is copied

| File | Role |
|---|---|
| `controllers/{__init__,fixed,queue_based,wait_time}.py` | The three ATCS controllers (authoritative signal logic) |
| `runner.py` | Original headless run loop; used here as the **reference** in parity tests |
| `metrics.py` | Original tripinfo summariser (`summarize`) — used unchanged for the comparison numbers |
| `intersection_final.net.xml`, `routes.rou.xml`, `baseline.sumocfg` | SUMO network and the original configuration |
| `tests/*`, `pytest.ini` | The original controller / metrics / route / integration tests, run against the copies |

`tests/` and `runner.py` write to `atcs_source/output/` (git-ignored) — never to the original repository.
