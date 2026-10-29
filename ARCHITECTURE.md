# Architecture

```
┌────────────────────┐   TraCI    ┌───────────────┐   JSON lines   ┌─────────────────────────┐   WebSocket   ┌──────────────────────┐
│ ATCS controller    │◄──────────►│ SUMO (sumo)   │                │ State bridge            │──────────────►│ 3D renderer          │
│ (atcs_source/      │ setPhase   │ authoritative │                │ atcs3d/session.py       │  full frames  │ web/ (Three.js)      │
│  controllers/*.py) │ getters    │ simulation    │                │ atcs3d/server.py        │◄──────────────│ + HUD + controls     │
└─────────▲──────────┘            └───────▲───────┘                └───────────▲─────────────┘   commands    └──────────────────────┘
          └───────── one process per simulation: atcs3d/sim_worker.py ─────────┘
```

**Rule of the whole design:** information flows left to right. The renderer *consumes* simulation state. The only things
it can send back are run-control commands (select / start / pause / resume / stop / restart / speed / benchmark). There is
no command that touches a signal, a vehicle or a controller, and the server rejects unknown commands
(`tests/test_server.py::test_unknown_commands_are_rejected_and_cannot_touch_signals`).

## Layer 1 — ATCS controllers (`atcs_source/`)

Verbatim copies of `FixedController`, `QueueBasedController` and `WaitTimeController` from the original ATCS repository
(commit `83f909d`, see `atcs_source/PROVENANCE.md`). They are imported and called exactly as the ATCS runner calls them;
nothing in this project reimplements, wraps or tunes their logic. Their rules (read from the source):

| Controller | Rule |
|---|---|
| Fixed | Does nothing; SUMO runs the programme from the network file: N-S green 42 s, yellow 3 s, E-W green 42 s, yellow 3 s. |
| Queue-Based | Holds a green (`setPhaseDuration(1000)`) and, once `now − phase_start ≥ MIN_GREEN (20 s)`, switches to yellow when the other group's stopped-vehicle count `≥` the current group's `+ SWITCH_MARGIN (2)`, or when `MAX_GREEN (60 s)` has elapsed and anyone is queued on the other group. Queue = sum of `lane.getLastStepHaltingNumber`. |
| Wait-Time | Same structure; compares accumulated waiting time (`lane.getWaitingTime`) with `MIN_GREEN 20 s`, `MAX_GREEN 45 s`, `SWITCH_MARGIN 0` (strictly greater switches; ties keep the green). |

The 3 s yellow after a forced switch is SUMO's own next phase in the programme.

## Layer 2 — SUMO + TraCI (`atcs3d/sim_worker.py`)

One **worker process** = one SUMO instance + one controller. It runs the ATCS loop in the ATCS order:

```python
traci.simulationStep()
snapshot = read_state()          # read-only TraCI getters (added by this project)
controller.step(traci.simulation.getTime())
```

- Step length stays at SUMO's default **1.0 s**, which the controllers were tuned for. Seed is fixed at SUMO's default
  (23423), passed explicitly.
- The signal state is read **before** `controller.step`. SUMO applies a signal switch at the start of a step, so this is the
  state that governed the vehicle movement just reported; reading it after the controller call would show adaptive
  switches one second early compared to the fixed programme.
- Vehicles are read with TraCI subscriptions (position, heading, speed, lane, current waiting time, route, size).
- Demand files are written by the ATCS `runner.write_routes`, so all controllers get byte-identical demand.
- Separate processes mean: a crash is contained, a SUMO child can always be killed with its worker's process group, the
  controllers' module-global `traci` connection is never shared, and side-by-side is simply two workers.
- Protocol: JSON lines on stdin/stdout (`start`, `step`, `finish`, `stop`). stdout is protected at the file-descriptor
  level so stray prints from SUMO/traci can never corrupt it.

**Not duplicated anywhere else:** vehicle motion, car-following, junction conflicts and every signal decision are SUMO /
the ATCS controller. The renderer has no physics and no signal logic.

## Layer 3 — State bridge (`atcs3d/session.py`, `atcs3d/server.py`)

`Hub` owns the run state machine (`idle → starting → running ⇄ paused → ended | stopped`) and one active `Run`
(1 pane for single view, 2 for side-by-side).

A **frame** is a complete snapshot, never a delta:

```jsonc
{ "type":"frame", "run_id":7, "seq":42, "t":42.0, "srv_ms":1761684000123,
  "panes":[{ "controller":"queue_based", "t":42.0,
     "vehicles":[{"id":"f_we.12","x":181.3,"y":198.4,"a":90.0,"v":9.1,"lane":"left0A0_0","w":0.0,"route":"west_east","len":5.0,"wid":1.8}],
     "tls":{"state":"rrrrGGggrrrrGGgg","phase":2,"elapsed":14.0},
     "lanes":{"left0A0_0":{"halt":2,"wait":9.0,"count":3}, ...},      // the controllers' own inputs
     "groups":[{"phase":0,"halt":0,"wait":0.0},{"phase":2,"halt":2,"wait":9.0}],
     "counts":{"departed":21,"arrived":9,"in_network":12},
     "live":{"avg_wait":5.1,"max_wait":14.0} }] }                      // running estimate, see below
```

Guarantees (each is tested):

| Requirement | How |
|---|---|
| Authoritative timestamps | `t` is `traci.simulation.getTime()`; the browser clock shows it, never its own. |
| Stable ids, no duplicates | Vehicle ids are SUMO's. The renderer keys models by id and reconciles against every frame. |
| Insert / remove | A frame lists exactly the vehicles in the network; a missing id is removed. |
| No stale state after restart | Every start bumps `run_id`; frames carry it; the browser drops frames of an older run; the server announces the new run before its first frame. |
| Pause | The server stops asking the worker to step. Simulation time itself stops. Resume continues at exactly `t+1`. |
| Pacing | Wall-clock scheduler, `speed` simulated seconds per real second, no burst catch-up after a stall. |
| Lockstep | Both panes of a side-by-side run are stepped together each tick and travel in one message; their `t` is always equal. |
| Race-free connect | A browser is registered and given `hello` + the current state/frame/results with no `await` in between; every send to a connection goes through that connection's lock, so ordering equals call order. The page also buffers anything that arrives before `hello`. |
| Nobody watching | When the last browser leaves, the run auto-pauses; a reconnect within 120 s resumes it, after that the run is stopped and SUMO freed. |
| Clean shutdown | Stop / restart / server exit kill the worker's process group (worker + SUMO). A worker also exits when its stdin closes. |

`live.avg_wait` is a running estimate (seconds a vehicle spent below 0.1 m/s, counted from the second after insertion); the
authoritative figures always come from SUMO's `tripinfo` via the ATCS `metrics.summarize` when a run ends or in the
benchmark. At the end of a full run the estimate agrees with tripinfo to within 0.1 s (tested).

### Benchmark (`atcs3d/benchmark.py`)

Runs `finish` (the pure ATCS loop, no snapshots) for the three controllers in parallel worker processes — about 2 s per
simulated hour each — and stores `results/benchmark_<scenario>.json` with scenario, seed, SUMO version, source commit and
timestamp. "Improvement vs Fixed" is `(fixed − controller) / fixed × 100`, the same definition as the ATCS compare API.

## Layer 4 — 3D renderer (`web/`)

| File | Responsibility |
|---|---|
| `js/net.js` | WebSocket client with reconnect. |
| `js/main.js` | Wiring, render loop (one WebGL renderer, one viewport per pane), keyboard shortcuts, read-only test hooks. |
| `js/world.js` | Static scene generated from the network JSON: asphalt from lane shapes, junction polygon, markings, zebra crossings, sidewalks, buildings, trees; `SignalRig` (mast + three-lamp head per approach). |
| `js/vehicles.js` | One model per SUMO id; places it from a pair of snapshots (see below). |
| `js/view.js` | Scene, camera, orbit controls, presets, frame playout, DOM labels (compass, queue badges). |
| `js/ui.js` | Controls, per-pane HUD, results table. UI state is only ever set from server messages. |

### Coordinates

SUMO: x east, y north, heading in degrees clockwise from north. three.js: x east, y up, z south. The world is centred on
the junction: `X = x − 200`, `Z = −(y − 200)`. Models point along +X; `yaw = 90° − heading`. TraCI reports the
**front-bumper** position, so a model's centre is half a vehicle length behind it along the heading. All of this is
verified against SUMO frames in `tests/test_web.py::test_paused_scene_is_exactly_the_last_sumo_frame`.

### Smoothing without changing the truth

Snapshots arrive once per simulated second. For each draw the page interpolates between the two newest snapshots:

`position = (1−u)·previous + u·current`, with `u` from the wall-clock time since the current snapshot arrived
(one snapshot of delay). A vehicle that appeared this step is back-extrapolated along its heading; one that left carries
on along its heading until the next snapshot. When `u = 1` (always, after Pause) every vehicle is exactly at its SUMO
position. The inputs and `u` of every draw are recorded, and `test_interpolation_is_exactly_a_blend_of_two_consecutive_sumo_positions`
checks the displayed positions against that formula.

Signal heads change as the interpolation toward a new snapshot begins, because that snapshot's state is what governed
that second of movement.

### Signal heads ↔ lanes

The head of each approach shows the state SUMO reports for that lane's **straight-ahead link** (found from the network's
`connection linkIndex` entries, not from phase numbers). `test_no_vehicle_enters_the_junction_on_red_and_head_mapping_is_right`
checks over a full hour, for every vehicle that crosses a stop line, that the head for its approach displays the link it
used and that it was never red.

## Extending

- **New scenario:** add a `Scenario(...)` in `atcs3d/scenarios.py` (demand per axis). The route file is produced by the ATCS writer.
- **New controller:** it must exist in `atcs_source/controllers/CONTROLLERS`; add its title in `scenarios.CONTROLLERS`.
- **Different network:** replace `atcs_source/intersection_final.net.xml` (and the TLS id in `paths.py`). The renderer builds
  from lane shapes and signal links, but the signal rig assumes one traffic-light junction with one lane per approach.
