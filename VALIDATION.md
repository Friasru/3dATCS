# Validation

All numbers here were produced on this machine (WSL2 Ubuntu 24.04, 4 cores, 11 GB RAM, NVIDIA GeForce RTX 5060 Laptop GPU,
SUMO 1.18.0) on 2026-10-28. Raw measurements are committed in `results/`. Reproduce the tests with `./run.sh test`.

**Prerequisite for the browser tests, `./run.sh record` and `./run.sh screenshots`:** a Chromium for Playwright. Install it
project-locally with `./run.sh install-browser` (about 170 MB into `.cache/`, git-ignored); on this laptop the tests reused a Chromium
already cached from another project. The demo itself (`./run.sh` plus any browser) needs none of this.

**Test status: 81 tests, all passing** in the final complete run (`./run.sh test -p no:cacheprovider --durations=8 -q`,
6 min 46 s, exit code 0), executed after the last code change. The tail of that run is reproduced in §7.

## 1. What was tested

| File | Tests | What it establishes |
|---|---:|---|
| `tests/test_source_integrity.py` | 19 | The 9 ATCS files we run (3 controllers + registry, runner, metrics, net, routes, sumocfg) are **byte-identical** to the originals (SHA-256 vs. recorded sums and vs. the original checkout, read-only), and the ATCS team's **own unit/integration tests pass against our copies**. |
| `tests/test_parity.py` | 5 | Driving a controller through the 3D bridge (3,600+ one-second steps with a snapshot every second) produces **exactly the same SUMO output as the original ATCS runner**: all 1,400 `tripinfo` records and all 3,600 `summary` steps equal, for Fixed, Queue-Based and Wait-Time. The runner reproduces ATCS's published numbers. |
| `tests/test_bridge.py` | 27 | Bridge frames equal an **independent** SUMO+controller recording made with plain TraCI getters (vehicle ids, positions to 1 cm, heading, speed, lane, signal string, 400 s × 3 controllers); runs are deterministic; all controllers get identical demand; yellow is always 3 s and phases cycle; Fixed is 42 s/3 s; adaptive green limits; adaptive controllers give the busier axis longer green; **no vehicle enters the junction on red** and the head shown for an approach is the link its cars use (full rush-hour × 3 controllers, ≈3,200 junction crossings each); cars wait at the stop line only when the signal says so; turning vehicles are reported correctly; live wait estimate within 0.1 s of the final figure; full-hour results equal the published ATCS figures; no stray processes. |
| `tests/test_server.py` | 14 | Run control over the real WebSocket protocol: frames start at t=0 and advance exactly 1.0 s; pause freezes the clock and resume continues at exactly t+1; restart gives a fresh run with no stale frames; stop reports partial results and leaves no SUMO processes; changing the controller explicitly ends the run; side-by-side is lockstep and the Fixed side is identical to a stand-alone Fixed run; unknown commands (e.g. `setPhase`) are rejected and cannot alter signals; last browser leaving pauses the run, a reconnect resumes it; pacing within ±15 % at 5× and 10×; cross-origin WebSocket refused; benchmark command; **a complete live simulated hour at 50× through the server ends naturally and its result equals the headless benchmark exactly.** |
| `tests/test_web.py` | 14 | Real Chromium + real server: page renders with no script errors; **works with every non-local request blocked** (offline); signal heads equal the SUMO signal state on every received frame (red, yellow and green all seen; axes never both green); after Pause, **each model sits where SUMO put its vehicle** (position, heading, one model per id, no extras); vehicles lie on their SUMO lane centre lines; while running, displayed positions equal the interpolation formula between two consecutive SUMO snapshots; all UI controls and keyboard shortcuts; side-by-side shows two correctly labelled panes; Results panel numbers equal the benchmark file; a page reload recovers the running simulation; **the Results panel opens by itself when a full simulated hour finishes (live, 50×)**. |
| `tests/test_results.py` | 2 | Committed benchmarks equal ATCS's published `results.json` for Fixed and Queue-Based in all four scenarios, and Wait-Time equals the ATCS README / tuning sweep. |

## 2. Controller comparison (SUMO, one simulated hour, seed 23423, step 1 s)

Same network, same demand file contents, same seed, same evaluation (`metrics.summarize` on SUMO `tripinfo`). Negative = less
than Fixed (better). From `results/benchmark_*.json` (SUMO 1.18.0, generated 2026-10-28).

| Scenario (EW / NS veh/h) | Controller | Vehicles done | Avg wait (s) | Max wait (s) | Avg time loss (s) | Avg wait vs Fixed | Time loss vs Fixed |
|---|---|---:|---:|---:|---:|---:|---:|
| Uneven traffic (500 / 200) | Fixed | 1400 | 13.39 | 46 | 23.35 | baseline | baseline |
|  | Queue-Based | 1400 | 6.07 | 25 | 15.11 | −54.7% | −35.3% |
|  | Wait-Time | 1400 | 6.18 | 25 | 15.35 | −53.9% | −34.3% |
| Balanced traffic (300 / 300) | Fixed | 1200 | 13.37 | 46 | 22.42 | baseline | baseline |
|  | Queue-Based | 1200 | 6.21 | 21 | 14.78 | −53.5% | −34.1% |
|  | Wait-Time | 1200 | 5.11 | 24 | 13.10 | −61.8% | −41.6% |
| North-south heavy (200 / 600) | Fixed | 1600 | 14.80 | 46 | 25.66 | baseline | baseline |
|  | Queue-Based | 1600 | 6.01 | 25 | 15.59 | −59.4% | −39.3% |
|  | Wait-Time | 1600 | 6.50 | 25 | 16.27 | −56.1% | −36.6% |
| Rush hour (900 / 700) | Fixed | 3200 | 18.06 | 59 | 32.77 | baseline | baseline |
|  | Queue-Based | 3200 | 18.26 | 52 | 36.93 | **+1.1%** | **+12.7%** |
|  | Wait-Time | 3200 | 19.48 | 56 | 38.56 | **+7.9%** | **+17.7%** |

**Parity with the original ATCS baseline:** Fixed and Queue-Based equal `results/results.json` of the original repository to
the last printed digit for all four scenarios (`test_results.py`); Wait-Time equals the ATCS README (held-out time loss
16.27 s, max wait 25 s) and its tuning sweep (best row: 15.35 / 38.56 / 13.10, mean 22.34). Nothing differs, so there are no
intentional differences to report.

**The ATCS project's own caveat is reproduced:** in saturated rush-hour traffic neither adaptive controller beats Fixed on
average waiting time or time loss (they do reduce the worst-case wait: 52 s and 56 s vs. 59 s). The demo shows this
honestly (Results panel, scenario "Rush hour").

### What the controllers actually do (measured from the frames; the controllers were not modified)

These observations come from phase lengths in the streamed frames and are offered for the team's Q&A preparation:

| Demand (EW / NS) | Controller | East–west green: mean / max | North–south green: mean / max |
|---|---|---:|---:|
| 500 / 200 | Fixed | 42 / 42 | 42 / 42 |
| 500 / 200 | Queue-Based | 21.2 / 25 | 21.0 / 22 |
| 500 / 200 | Wait-Time | 21.0 / 21 | 21.0 / 21 |
| 1100 / 100 (diagnostic) | Queue-Based | 27.1 / 38 | 21.0 / 21 |
| 1100 / 100 (diagnostic) | Wait-Time | 26.2 / 35 | 21.0 / 21 |

- Under the ATCS scenarios the adaptive controllers mostly alternate at about the 20 s minimum green (21 observed seconds,
  because the controller notices the phase one step late). Much of their advantage over Fixed in these scenarios therefore
  comes from shorter cycles than the 42 s Fixed greens. They do stretch the busy road's green when demand is lopsided
  (diagnostic 1100/100 case, tested), and keep the quiet road short.
- The maximum-green caps (60 s Queue-Based, 45 s Wait-Time) were **not reached in any full simulation we ran** (largest
  observed green: 38 s). They are covered by the ATCS unit tests (also run here), not by a full-simulation test.
- A possible reason adaptive control does not win at rush hour: with both roads busy it flips at the minimum green and
  spends 3 s of yellow per ≈24 s phase (12.5 %) against 3 s per 45 s (6.7 %) for Fixed. This is an arithmetic observation,
  not something we tested as a cause.

## 3. Measured performance

Tool: `scripts/measure_perf.py` (headless Chromium driven by Playwright; CPU/memory from `/proc`, sampled once a second,
3 s warm-up excluded). "GPU" = real NVIDIA GPU reached through WSL's Mesa D3D12 layer; "software" = SwiftShader.
Scenario "Rush hour" (the most vehicles), 10× speed unless noted.

| Configuration | Render FPS mean / 5th pct / min | Vehicles on screen mean / max |
|---|---|---|
| **GPU, 1920×1080, single view**, Queue-Based | **60.0 / 60.0 / 60.0** (display cap) | 42 / 48 |
| **GPU, 1920×1080, side-by-side** | **57.3 / 52.0 / 51.2** | 88 / 102 |
| **GPU, 1920×1080, full simulated hour at 50×** (uneven) | 60.0 / 60.0 / 60.0 | 17 / 22 |
| Software GL, 1280×720, single | 9.2 / 7.9 / 7.9 | 40 / 46 |
| Software GL, 1280×720, `?shadows=0&dpr=1` | 15.0 / 14.3 / 14.3 | 40 / 46 |

| Pipeline metric | Single view (10×) | Side-by-side (10×) | Full hour (50×) |
|---|---:|---:|---:|
| Frames arrive every (expected) | 99.6 ms (100) | 99.6 ms (100) | 20.0 ms (20) |
| Server → browser latency (same machine) | 1.0 ms | 1.2 ms | 0.6 ms |
| Worker step round trip (SUMO step + controller + snapshot), mean / max | 3.07 / 5.19 ms | 3.14 / 5.68 ms | 2.21 / 5.00 ms |
| Frame size, mean | 5.3 KB | 10.9 KB | 2.6 KB |
| Server + SUMO CPU (% of one core) | 3.0 | 5.2 | 2.1 |
| Server + SUMO memory | 90 MiB | 141 MiB | 89 MiB |
| Chromium CPU (% of one core) / memory | 66 % / 1.25 GiB | 77 % / 1.32 GiB | 50 % / 1.28 GiB |

**End-to-end reliability:** a complete simulated hour through the live server at 50× with the GPU-rendered page attached
ran to its natural end at t = 3,643 s; the page received **3,644 of 3,644 frames** (none dropped), no browser errors,
status "ended". A separate slow test (`test_results_panel_opens_by_itself_when_a_run_finishes`) checks that the Results panel
opens by itself at the natural end, and the slow server test checks that the live result equals the headless benchmark
exactly. Every test that starts a run also ends it, and the process-leak checks (a scan of `/proc` for `sim_worker`/`sumo`
after the bridge tests and after the server tests) find nothing left behind.

**Vehicle synchronisation stability:** every received frame is a complete snapshot reconciled by vehicle id; in the tests
the rendered id set equalled SUMO's id set on every checked frame and positions matched to < 0.01 m when settled.

**Caveats:** GPU numbers are for headless Chromium on WSL through Mesa D3D12 (an OpenGL-on-D3D12 translation), which is a
different path from native Windows Chrome/Edge; native numbers were **not measured**. A 60.0 FPS result means the display
cap was reached, not the maximum capability. The "software" rows show what a machine with no GPU acceleration would get.

## 4. Verification of specific requirements

| Requirement | Evidence |
|---|---|
| Fixed / Queue-Based / Wait-Time behave as originally implemented | Byte-identical sources; original unit tests pass on the copies; bridge output equals the original runner's, record by record. |
| Min/max green and yellow respected | `test_yellow_is_always_three_seconds…`, `test_*_green_limits` (limits read from the ATCS modules, not copied); max-green logic is in the ATCS unit tests. |
| Renderer never changes signal decisions | There is no such command; unknown commands are rejected (`test_unknown_commands…`); the page tests only observe. |
| Vehicle ids match SUMO | `test_frames_equal_independent_sumo_recording`, `test_paused_scene_is_exactly_the_last_sumo_frame`. |
| Coordinates, headings | Exact model position/yaw check against SUMO frames; vehicles on lane centre lines. |
| Signal colours match | `test_signal_heads_always_show_the_sumo_signal_state`, `test_no_vehicle_enters_the_junction_on_red…`. |
| Stop / resume at red / green | `test_vehicles_wait_at_the_line_only_because_of_the_signal` (cars stop ≈1.0 m before the line, which is where the drawn stop line is). |
| Spawn / despawn correct | Frame id sets equal SUMO's each step; arrivals counted. |
| Time consistent | Clock shows `traci.simulation.getTime()`; pause test. |
| Start, pause, resume, restart, stop, controller & scenario selection, clean shutdown | `test_server.py`, `test_web.py::test_ui_controls…`, process-leak checks. |
| Fair comparison | Same demand file generator, seed and step; determinism and identical-demand tests. |
| Roads align with trajectories | Road meshes are built from SUMO lane shapes; vehicle-on-lane test. |
| Camera overview usable | Overview/Top/Driver presets; screenshots in `docs/images/` (checked from screenshots only; not yet by a person on a projector). |

## 5. Remaining problems and limitations

1. **Native Windows browser performance not measured** (see caveat above). Test it on the demo laptop; fallbacks are in `DEMO_DAY.md`.
2. **Chromium only.** Edge and Chrome share the engine; Firefox and Safari were not tried.
3. **Turning vehicles and pedestrians do not appear** in the ATCS scenarios. Turning is covered at bridge level
   (diagnostic route file) but not in the browser; turning paths are drawn as straight chords between 1 Hz samples (a few
   decimetres off the true arc mid-turn). Crosswalks are decoration.
4. **One second of display latency** by design: positions are interpolated between the two newest SUMO snapshots.
5. **No human visual QA yet.** Geometry and mapping are checked numerically and by screenshots; someone on the team should
   look at the projector output once.
6. **The "avg wait so far" figure is an estimate** (matches SUMO's tripinfo for 98 % of vehicles, final average within 0.1 s);
   authoritative figures come from tripinfo at the end of a run and from the benchmark.
7. **No long soak test** beyond one simulated hour live and repeated short cycles.
   Two tests are wall-clock sensitive and could flake on a heavily loaded machine: `test_pacing_matches_the_selected_speed`
   (±15 %) and `test_last_browser_leaving_pauses_and_a_quick_reconnect_resumes` (2 s absence).
8. Single-active-run server, no authentication; bound to `127.0.0.1` by default; cross-origin WebSockets refused.
9. The XML network file is parsed with Python's standard library; it is the trusted vendored file, not user input.
10. `research/` holds ~240 MB of reference clones (git-ignored). Delete the folder if you do not need it; the notes are in `RESEARCH.md`.

## 6. Problems found and fixed during development (for the record)

| Found by | Problem | Fix |
|---|---|---|
| Visual check | Camera blocked by tall buildings; top view rotated 45°. | Height capped by distance; camera offset. |
| Tests (`test_server`) | A reconnecting browser could receive a broadcast **before `hello`** (server race); the page would drop it. | Atomic attach + per-connection send lock on the server; early-message buffer in the page. |
| Tests | Controller change ended a run without telling clients. | Server announces `stopped` and the partial result. |
| Tests | Live "avg wait" estimate was ≈1 s per vehicle too high (counted the insertion step). | Skip the insertion step; now matches SUMO for 98 % of vehicles. |
| Review of failure modes | An orphaned run kept simulating after the browser closed. | Auto-pause when nobody is connected; resume on reconnect; stop after 2 min. |
| Performance run | ~900 draw calls per frame (≈45 FPS on GPU). | Merged each car to 2 meshes; now 60 FPS. |

## 7. Final run

Executed after the last code change (`./run.sh test -p no:cacheprovider --durations=8 -q`); output tail, unedited:

```
........................................................................ [ 88%]
.........                                                                [100%]
============================= slowest 8 durations ==============================
75.50s call     tests/test_web.py::test_results_panel_opens_by_itself_when_a_run_finishes
74.30s call     tests/test_server.py::test_a_live_run_to_the_natural_end_reports_the_same_numbers_as_the_benchmark
11.46s call     tests/test_web.py::test_interpolation_is_exactly_a_blend_of_two_consecutive_sumo_positions
11.12s setup    tests/test_bridge.py::test_yellow_is_always_three_seconds_and_phases_cycle[fixed]
10.49s call     tests/test_web.py::test_signal_heads_always_show_the_sumo_signal_state[fixed]
10.37s call     tests/test_web.py::test_signal_heads_always_show_the_sumo_signal_state[queue_based]
9.27s call     tests/test_bridge.py::test_adaptive_controllers_give_the_busier_axis_longer_green[wait_time]
9.23s call     tests/test_web.py::test_scenario_selection_changes_the_run_and_labels
81 passed in 406.57s (0:06:46)
```

Not covered by any test (stated plainly): native Windows Chrome/Edge frame rate; a person looking at the projector output;
Firefox/Safari; turning traffic in the browser; runs longer than one simulated hour.
