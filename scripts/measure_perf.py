"""Measure the running system: render FPS, simulation update rate, bridge latency, CPU and memory.

    python scripts/measure_perf.py [--gpu] [--compare] [--controller queue_based] [--scenario rush_hour]
                                   [--speed 10] [--sim-seconds 300] [--size 1920x1080] [--full-hour] [--out results/perf_x.json]

--gpu       use the NVIDIA GPU through WSL's D3D12 layer (default: SwiftShader software rendering)
--full-hour run the whole simulated hour at 50x and check the live run completes with every frame delivered
"""
import argparse, asyncio, datetime, json, os, platform, statistics, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from atcs3d import paths
from tests.browser_util import Browser
from tests.helpers import ServerProc

TICK = os.sysconf("SC_CLK_TCK")


def descendants(root):
    kids = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            stat = open(f"/proc/{pid}/stat").read()
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
            kids.setdefault(ppid, []).append(int(pid))
        except (OSError, IndexError, ValueError):
            pass
    out, todo = [], [root]
    while todo:
        p = todo.pop()
        out.append(p)
        todo += kids.get(p, [])
    return out


def cpu_rss(pids):
    ticks = rss = 0
    for p in pids:
        try:
            f = open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()
            ticks += int(f[11]) + int(f[12])
            for line in open(f"/proc/{p}/status"):
                if line.startswith("VmRSS"):
                    rss += int(line.split()[1])
        except (OSError, IndexError):
            pass
    return ticks / TICK, rss / 1024  # cpu seconds, MiB


def stats(xs):
    xs = sorted(xs)
    if not xs:
        return None
    return {"mean": round(statistics.mean(xs), 2), "min": round(xs[0], 2), "p5": round(xs[int(0.05 * (len(xs) - 1))], 2),
            "median": round(statistics.median(xs), 2), "p95": round(xs[int(0.95 * (len(xs) - 1))], 2), "max": round(xs[-1], 2), "n": len(xs)}


async def main(a):
    w, h = (int(v) for v in a.size.split("x"))
    controllers = ("fixed", a.controller) if a.compare else (a.controller,)
    with ServerProc(results_dir=os.path.join(paths.OUTPUT_DIR, "perf_results")) as srv:
        async with Browser(w, h, gpu=a.gpu) as b:
            pg = await b.open(srv.url, a.query)
            renderer = await b.gl_renderer()
            await b.start_run(controllers, a.scenario, 50 if a.full_hour else a.speed)
            target = None if a.full_hour else a.sim_seconds
            srv_pids = descendants(srv.proc.pid)
            me = os.getpid()
            chrome_pids = [p for p in descendants(me) if p != me]
            samples = {"fps": [], "srv_cpu": [], "chrome_cpu": [], "srv_rss": [], "chrome_rss": [], "veh": []}
            prev = (time.time(), cpu_rss(srv_pids)[0], cpu_rss(chrome_pids)[0])
            t_start = time.time()
            await asyncio.sleep(3)  # warm-up (shader compile, first frames)
            prev = (time.time(), cpu_rss(descendants(srv.proc.pid))[0], cpu_rss([p for p in descendants(me) if p != me])[0])
            while True:
                await asyncio.sleep(1.0)
                info = await pg.evaluate("({fps: window.__atcs.fps, status: window.__atcs.status, t: window.__atcs.lastFrame && window.__atcs.lastFrame.t,"
                                         " veh: window.__atcs.lastFrame ? window.__atcs.lastFrame.panes.reduce((s, p) => s + p.vehicles.length, 0) : 0})")
                now = time.time()
                sp, cp = descendants(srv.proc.pid), [p for p in descendants(me) if p != me]
                s_cpu, s_rss = cpu_rss(sp)
                c_cpu, c_rss = cpu_rss(cp)
                dt = now - prev[0]
                samples["srv_cpu"].append(100 * (s_cpu - prev[1]) / dt)
                samples["chrome_cpu"].append(100 * (c_cpu - prev[2]) / dt)
                samples["srv_rss"].append(s_rss); samples["chrome_rss"].append(c_rss)
                samples["fps"].append(info["fps"]); samples["veh"].append(info["veh"])
                prev = (now, s_cpu, c_cpu)
                if info["status"] == "ended" or (target and info["t"] is not None and info["t"] >= target):
                    break
                if time.time() - t_start > 400:
                    break
            final = await pg.evaluate("({status: window.__atcs.status, seq: window.__atcs.lastFrame.seq, t: window.__atcs.lastFrame.t, rx: window.__atcs.rxStats()})")
            perf = json.loads(await pg.evaluate("fetch('/api/perf').then(r => r.text())"))
            errors = list(b.errors)
    out = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "machine": {"cpu_cores": os.cpu_count(), "platform": platform.platform(), "webgl_renderer": renderer},
        "config": {"controllers": list(controllers), "scenario": a.scenario, "speed": 50 if a.full_hour else a.speed, "viewport": a.size,
                   "gpu": a.gpu, "full_hour": a.full_hour, "query": a.query},
        "render_fps": stats(samples["fps"]),
        "vehicles_on_screen": {"mean": round(statistics.mean(samples["veh"]), 1), "max": max(samples["veh"])},
        "frame_arrival_ms": {"mean": round(final["rx"]["meanInterArrivalMs"], 1), "expected": round(1000 / (50 if a.full_hour else a.speed), 1)},
        "bridge_server_to_browser_ms": round(final["rx"]["meanServerToClientMs"], 1),
        "worker_step_roundtrip_ms": perf["step_roundtrip_ms"],
        "frame_bytes": perf["frame_bytes"],
        "server_plus_sumo_cpu_pct_of_one_core": stats(samples["srv_cpu"]),
        "chromium_cpu_pct_of_one_core": stats(samples["chrome_cpu"]),
        "server_plus_sumo_rss_mib": stats(samples["srv_rss"]),
        "chromium_rss_mib": stats(samples["chrome_rss"]),
        "end": {"status": final["status"], "last_t": final["t"], "last_seq": final["seq"], "frames_received": final["rx"]["frames"],
                "no_frame_dropped": final["rx"]["frames"] == final["seq"] + 1},
        "browser_errors": errors,
    }
    print(json.dumps(out, indent=2))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(out, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", action="store_true"); ap.add_argument("--compare", action="store_true")
    ap.add_argument("--controller", default="queue_based"); ap.add_argument("--scenario", default="rush_hour")
    ap.add_argument("--speed", type=int, default=10); ap.add_argument("--sim-seconds", type=int, default=300)
    ap.add_argument("--size", default="1920x1080"); ap.add_argument("--full-hour", action="store_true"); ap.add_argument("--out"); ap.add_argument("--query", default="")
    asyncio.run(main(ap.parse_args()))
