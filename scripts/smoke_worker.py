"""Smoke test: drive one sim_worker, print a few frames, check the process is cleaned up."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from atcs3d.worker_client import WorkerClient  # noqa: E402


async def main(controller):
    w = await WorkerClient(f"smoke_{controller}").spawn()
    r = await w.request({"cmd": "start", "controller": controller, "scenario": {"ew": 500, "ns": 200},
                         "tag": f"smoke_{controller}", "run_id": 1})
    print("started: sumo_pid", r["sumo_pid"], "t0", r["frame"]["t"], "tls", r["frame"]["tls"], "groups", r["groups"])
    for i in range(1, 61):
        f = await w.request({"cmd": "step"})
        if i in (1, 5, 20, 30, 45, 60):
            print(f"t={f['t']:>5} veh={len(f['vehicles']):>2} tls={f['tls']['state']} ph={f['tls']['phase']} "
                  f"el={f['tls']['elapsed']} counts={f['counts']} groups={f['groups']}")
    if f["vehicles"]:
        print("sample vehicle:", f["vehicles"][0])
    res = await w.stop()
    print("stop ->", res)
    print("worker alive after stop:", w.alive)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "queue_based"))
