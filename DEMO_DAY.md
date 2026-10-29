# Demo Day guide — Alberto & Ian

Everything you will show is a real SUMO simulation steered by the real ATCS controllers. The 3D page only draws it.
Be ready to say that, because it is the point of the project.

## 0. Before the day (do this once, the day before)

1. `cd ~/3dATCS && ./setup.sh` — must end with "Setup complete".
2. `./run.sh test -m "not slow"` — everything should pass (about 5 minutes). Skipping this is fine; it is only reassurance.
3. `./run.sh benchmark --all` is optional: `results/benchmark_*.json` already hold measured numbers, and the page shows
   them immediately. Re-running regenerates them with a new timestamp (the numbers should be identical — they are deterministic).
4. **Rehearse the whole script below at least once on the presentation laptop and projector.**
5. Record a backup video (see §6): with the server running, `./run.sh record` (or Win+Alt+R / OBS).
6. Windows: use **Chrome or Edge, hardware acceleration ON** (Settings → System). Close other heavy apps.
7. Power: plugged in, "Best performance" mode, display scaling at 100–150 %.

## 1. Launch (2 minutes before)

```bash
cd ~/3dATCS
./run.sh                 # prints: 3dATCS: open http://localhost:8765/
```

Open **http://localhost:8765** in the Windows browser. Press **F** for full screen. The status pill should say **Ready**
and the dot beside it should be green. Leave the terminal visible on another screen (it prints the run lifecycle).

If you present from another computer on the same network: `./run.sh --host 0.0.0.0`, then browse to `http://<this-pc-ip>:8765`.

## 2. Controls cheat sheet

| Key | Action | Key | Action |
|---|---|---|---|
| Space | start / pause / resume | O / T / D | camera overview / top / driver |
| R | restart | H | hide the interface (clean view) |
| X | stop | P | measured results |
| 1 / 2 / 3 | Fixed / Queue-Based / Wait-Time (fresh run) | F | full screen |
| B | side-by-side Fixed vs ATCS | ? | shortcut list |

Mouse: drag = orbit, right-drag = pan, wheel = zoom. Speed buttons: 1×–50×.

## 3. Suggested presentation (≈ 7–8 minutes)

Default scenario is **Uneven traffic** (east–west heavy, north–south light): the clearest difference.

| # | What you do | What the audience sees | What to say |
|---|---|---|---|
| 1 | Show the page with nothing running. Press **O**; drag the camera a little. | The 3D intersection: four approaches, signals, crosswalks, N/E/S/W markers. | "We can't deploy our controller on a real junction, so we run it in SUMO — a standard traffic simulator — and visualise it in 3D. Every car and light you'll see is straight from SUMO." |
| 2 | Choose **Fixed timing**, speed **10×**, press **Space**. Watch ~90 simulated seconds. Point at the HUD. | Lights follow a fixed cycle; cars queue on the red side; the HUD shows "stopped / waiting" per direction growing. | "This is traditional timing: 42 s green each way no matter what. See the cars stacking on the red side while the other way may be empty." |
| 3 | Press **D** for a few seconds (driver view), then **O**. | Cars stopped at the line under a red head; they go when it turns green. | "Cars stop at red, go on green — this is SUMO's behaviour, not an animation." |
| 4 | Press **2** (Queue-Based). It starts a fresh run of the same scenario. | Clock resets to 0:00; same traffic; the signal board now shows ATCS. | "Same road, same cars (same random seed), but now the ATCS Queue-Based controller. It switches when the other side's queue is larger than ours, after at least 20 s of green." |
| 5 | Press **B** for **side-by-side** (Fixed left, ATCS right; it starts a fresh run by itself). Click **20×**. Let it run to ~5 simulated minutes. | Two simulations in lockstep: queues on the left are longer; the HUD shows stopped counts, waiting seconds, average wait. | "Left: traditional timing. Right: ATCS. Identical traffic. Look at the stopped counts and accumulated waiting." |
| 6 | Press **X**, then **P** (Results). | The measured table: avg wait, max wait, time loss, vehicles done, % vs Fixed. | "These come from a full simulated hour per controller, measured by SUMO: Queue-Based cut average waiting from 13.4 s to 6.1 s, about 55 % less. These are simulation results, not real-world measurements." |
| 7 | (optional) Choose **Rush hour** in the scenario box, open Results. | Adaptive is *not* better on average here. | "Honest result: when both roads are saturated there's little to gain; the adaptive controllers still cut the worst-case wait (52 s vs 59 s). That's in our original ATCS report too." |
| 8 | (optional) Press **3** for Wait-Time and run the same scenario. | Similar behaviour to Queue-Based. | "Wait-Time uses accumulated waiting seconds instead of queue length." |

Timing guide: at 50× a full simulated hour plays in about 75 s (it opens the Results panel by itself when it finishes) —
a good option if you want the *live* hour result rather than the stored benchmark. At 20× it takes about 3 minutes.

### Numbers you can quote (deterministic, from `results/benchmark_uneven.json`)

| Uneven 500/200, one simulated hour | Fixed | Queue-Based | Wait-Time |
|---|---:|---:|---:|
| Avg wait | 13.39 s | 6.07 s | 6.18 s |
| Max wait | 46 s | 25 s | 25 s |
| Avg time loss | 23.35 s | 15.11 s | 15.35 s |
| Vehicles completed | 1400 | 1400 | 1400 |

A concrete moment: at simulated **t = 120 s** in the side-by-side, Fixed has 11 cars stopped with 156 s of accumulated
waiting; Queue-Based has 7 stopped with 74 s. (Same traffic, same instant.)

## 4. Questions you may get

- **Is this real traffic?** No. It is a SUMO simulation of the ATCS test scenarios. We compare controllers *within* SUMO.
- **Did you change the controllers for the demo?** No. They are byte-identical copies of the ATCS ones (checksums are
  tested) and the same Python code runs them. The 3D page cannot change a signal — it has no such command.
- **Is the 3D a separate simulation?** No. SUMO is the only simulator. The page receives each simulated second and smooths
  between seconds; at rest it is exactly SUMO's positions (tested).
- **Why does the adaptive controller win in light traffic?** In our data the adaptive greens are mostly at their 20 s
  minimum, whereas the fixed programme holds 42 s: shorter waits on the red side. Under lopsided demand the busy road's
  green stretches (we saw up to 38 s), while the quiet road stays near the minimum. We did not tune anything for this demo.
- **Why isn't it better at rush hour?** Both roads are always busy, so the adaptive controllers alternate at the minimum
  green and pay the 3 s yellow more often than Fixed does. It lowers the worst-case wait, not the average.
- **Why no turning cars or pedestrians?** The ATCS test scenarios are straight-through only. The crosswalks are scenery.
- **Why one second per frame?** SUMO's default step, which the controllers were tuned for; we interpolate for smoothness.

## 5. Recovery procedures (in order of escalation)

| Problem | Fix |
|---|---|
| A run looks odd / you want to start over | Press **R** (restart). Takes ~1 s. |
| Browser tab froze or was closed | Re-open `http://localhost:8765`. The page rebuilds itself; a run that was going **resumes**. (If nobody is connected the run auto-pauses; after 2 minutes it stops.) |
| Page is slow / stutters (weak GPU or no hardware acceleration) | Reload with `http://localhost:8765/?shadows=0&dpr=1`. |
| "Starting SUMO…" never finishes, or an error toast appears | Press **X**, then Space. If it repeats: Ctrl+C in the terminal, run `./run.sh` again (each worker and its SUMO are killed with the server). |
| Port busy ("address already in use") | `./run.sh --port 9001` and browse to that port. |
| Stray simulation processes | `pgrep -af "atcs3d.sim_worker"`; stop them with `pkill -f atcs3d.sim_worker`. |
| Nothing at all loads on Windows | In WSL run `curl localhost:8765/api/health` — it should print `{"ok": true}`. If so, try `http://127.0.0.1:8765`, or restart WSL with `wsl --shutdown` from Windows. |
| Results table empty | `./run.sh benchmark --all` (~10 s), then press **P** again. |

## 6. Backup plan if the simulator or laptop fails

Have these ready, in this order:

1. **Recorded demo video** — with the server running, `./run.sh record` records a 2-minute demo (Fixed, Queue-Based, side-by-side,
   results) from the real page to `output/backup_demo.webm` (about 60 MB); or screen-record a rehearsal with Win+Alt+R. Copy it to a USB stick and the cloud.
2. **Screenshots** in `docs/images/` (overview, driver view, top view, side-by-side, results table).
3. **SUMO's own viewer** on any machine with SUMO: `cd atcs_source && python3 runner.py queue_based --gui` (the original ATCS
   runner). It shows 2D traffic and signals, without our 3D view or comparison panel.
4. **The numbers**: the table in §3 and `results/benchmark_*.json` — explain the result from the slides even with no screen.

## 7. After the demo

Press **X**, then Ctrl+C in the terminal. `pgrep -af sumo` should show nothing.
