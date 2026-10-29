# Technology research and decision

**Decision: Python state bridge + Three.js renderer in a browser.**

The requirement that decided it: *the existing Python ATCS controllers must run unmodified, in the loop, against SUMO,
and the 3D app must be launchable reliably and offline from this WSL-based setup.* A browser renderer fed by a Python
bridge satisfies that with the fewest moving parts; Unity and Godot would add a second runtime, a cross-OS link (WSL ↔
Windows), and tooling that cannot be installed or scripted here.

## Environment facts (inspected, not assumed)

| | |
|---|---|
| OS | WSL2 Ubuntu 24.04 on Windows 11, NVIDIA GeForce RTX 5060 Laptop GPU |
| SUMO | 1.18.0 (`sumo`, `sumo-gui` with OSG, `traci` + `sumolib` 1.18 via apt) |
| Python / Node | 3.12.3 / 20.20.2 |
| Unity, Godot | **not installed** (no editor, no hub, no licence) |
| Browser | none in WSL; Windows has Edge and Chrome; Playwright's Chromium is cached in `~/.cache/ms-playwright` |
| GPU from Linux side | Reachable from headless Chromium through ANGLE + Mesa `d3d12` (reported renderer: NVIDIA RTX 5060) |

## References inspected

Cloned shallowly into `research/` (git-ignored; only the commit pointers `research/*.COMMIT.txt` are kept).

### SUMO2Unity — `SimuTraffX-Lab/SUMO2Unity` (commit `4379205`)
- *What it is:* a Unity 6 project (324 MB) plus a Windows tool (`RequiredFiles/Sumo2UnityTool.exe`) that runs SUMO and
  exchanges vehicle and signal data with Unity.
- *Licence:* the README states code **MIT**, assets **CC-BY**. The clone has **no top-level `LICENSE` file**; the statement is in
  the README only, and the car models/assets are CC-BY (attribution required).
- *What we read:* `SimulationController.cs` receives JSON `{vehicle_id, position[3], angle, type, speeds}` per vehicle and
  `{junction_id, state}` for traffic lights; vehicles are updated every 0.1 s, **signals at most once per second**
  (`tlUpdateInterval = 1f`). Road networks are built inside the Unity editor by an editor window from the `.net.xml`.
  The Python file in the repo (`Sumo2UnityTool_combined.py`) is an 11-line header; the integration code we could actually
  inspect is the C# side inside the Unity project.
  It targets SUMO 1.22 and Unity `6000.0.53f1`, and is oriented to VR/driver-in-the-loop use.
- *Compatibility:* **rejected as a basis.** It would need Unity Hub + editor + Visual Studio (not installed, multi-GB, interactive
  licence sign-in), an editor-driven scene build that no setup script can reproduce, a Windows `.exe` that drives SUMO itself
  rather than our WSL Python controllers, and the Python/GUI half of the tool was not inspectable in the repo. Using it would mean
  re-plumbing our controllers into a different process model.
- *Reused:* the idea of a per-vehicle `{id, position, angle, type, speed}` record and per-junction signal-state string. **No code or assets copied.**

### SUMO-Web3D — `sidewalklabs/sumo-web3d` (commit `d89fe80`)
- *What it is:* Python TraCI server (aiohttp + websockets) plus a TypeScript/React/three.js client. The closest existing
  design to ours.
- *Licence:* **Eclipse Public License 2.0** (same as SUMO).
- *Maintenance:* the checked-out history ends in **Nov 2018** ("Fix for sumo 1.0.1"); yarn/webpack-era toolchain, old three.js typings.
- *What we read:* the server owns the TraCI loop and sends frame deltas (`creations/updates/removals`); the client builds the
  scene from the network and maps SUMO coordinates by flipping y (`z = bottom − y`).
- *Compatibility:* **not forked.** It launches its own SUMO and has no hook for running externally defined controllers in
  the loop, and the toolchain is outdated. We adopted two ideas — the browser as a pure viewer fed by a Python TraCI
  server, and reconciling vehicles by id — and wrote our own code. **No code copied.** We send full snapshots rather than
  deltas because they are simpler to reason about and tiny here (≈2–11 KB per frame).

### Found by search only (not cloned or inspected in depth)
- BME Traffic Lab, `BMEAutomatedDrive/SUMO-Unity3D-connection`: Python TCP server between SUMO and Unity 3D (asks for citation).
- `zhiweiyang0227/SUMO-Unity-VR-traffic-simulation`: Unity ↔ SUMO through a C# TraCI port (CodingConnected), VR/e-scooter.
- No Godot-specific SUMO/TraCI integration or addon turned up in a web search.

## Options compared

Scores are our judgement from the evidence above (● good · ◐ partial · ○ poor).

| Criterion | A. Unity + SUMO | B. Three.js + SUMO (chosen) | C. Godot + SUMO | D. `sumo-gui` (+ OSG) |
|---|---|---|---|---|
| 1. Technical compatibility with unmodified Python controllers in the loop | ◐ needs a bridge from Python to a C# runtime | ● bridge is Python; controllers untouched | ◐ same bridge need; no existing addon found | ● ATCS runner already supports `--gui` |
| 2. Integration difficulty | ○ editor-driven scene, C# receiver, WSL↔Windows link | ● one Python process + static web files | ◐ GDScript/C# receiver to write; Godot not installed | ● none |
| 3. Visual quality | ● highest ceiling | ● good (PBR lighting, shadows, labels); not photoreal | ● good | ○ SUMO's 2D / basic OSG view |
| 4. Performance | ● | ● measured 60 fps (display cap) with ~45 vehicles on the RTX GPU; 57 fps side-by-side | ● | ● |
| 5. Stability | ◐ editor/version sensitivity | ● plain web stack, no native build | ◐ | ● |
| 6. Hardware requirements | ◐ heavy install | ● any browser; GPU strongly recommended (software GL ≈ 9–15 fps) | ◐ | ● |
| 7. Offline presentation readiness | ◐ build/export step, Windows-side tooling | ● vendored three.js, no CDN, tested with all external requests blocked | ◐ export step | ● |
| 8. Licence compatibility | ◐ MIT code + CC-BY assets; Unity licence | ● three.js MIT; SUMO used as an external program | ● MIT | ● EPL-2.0 (SUMO) |
| 9. Maintenance status of references | ● SUMO2Unity active (Sep 2026) | ◐ sumo-web3d is stale (2018), so we depend on no code from it | ○ none found | ● SUMO |
| 10. Time to a working, verified prototype | ○ days (install + scene + bridge) | ● same day | ◐ | ● but no comparison UI |

**Why not simply Unity because it looks more realistic?** A Demo Day demonstration fails on reliability, not on texture
quality. Unity would put an unscriptable editor step and a second OS in the critical path of something that must start
reliably on the day, and its extra realism does not change what the audience needs to see: cars queueing at red, lights
changing, and the fixed-vs-adaptive difference.

**Fallback (Option D):** the original ATCS runner can open SUMO's own viewer: `cd atcs_source && python3 runner.py queue_based --gui`.
It is documented in `DEMO_DAY.md` as the last-resort backup.

## Dependencies recorded

| Component | Version | Licence | Use |
|---|---|---|---|
| SUMO (system package) | 1.18.0 | EPL-2.0 | external program (not redistributed) |
| `traci`, `sumolib` (system) | 1.18.0 | EPL-2.0 | Python client libraries |
| three.js (+ `OrbitControls`, `RoundedBoxGeometry`, `BufferGeometryUtils`) | 0.170.0 | MIT | vendored in `web/vendor/three/` |
| aiohttp | ≥ 3.9 | Apache-2.0 | server (installed in `.venv`) |
| pytest, playwright | dev only | MIT / Apache-2.0 | tests, screenshots |
