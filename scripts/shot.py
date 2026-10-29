"""Visual check: render the page in the cached headless Chromium and save a screenshot.

    python scripts/shot.py out.png [controller=fixed] [sim_seconds=50] [camera] [compare_controller] [scenario] [speed]
"""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tests.browser_util import Browser


async def main(out, controller="fixed", wait=50, cam=None, compare=None, scenario=None, speed=10, w=1600, h=900):
    async with Browser(w, h) as b:
        pg = await b.open("http://127.0.0.1:8765")
        await b.start_run((controller, compare) if compare else (controller,), scenario, speed)
        await b.wait_sim_time(wait)
        if cam:
            await pg.click(f"#cams button[data-cam='{cam}']"); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=out)
        info = await pg.evaluate("({fps: window.__atcs.fps, p0: window.__atcs.pane(0), r: window.__atcs.renderer(), pill: document.querySelector('#status-pill').textContent})")
        print("pill:", info["pill"], "| fps(software GL):", round(info["fps"], 1), "| vehicles:", len(info["p0"]["vehicleIds"]),
              "| lights:", info["p0"]["signalColors"], "| draw calls:", info["r"]["calls"])
        print("errors:", b.errors)

a = sys.argv
asyncio.run(main(a[1], a[2] if len(a) > 2 else "fixed", float(a[3]) if len(a) > 3 else 50, a[4] if len(a) > 4 and a[4] != "-" else None,
                 a[5] if len(a) > 5 and a[5] != "-" else None, a[6] if len(a) > 6 and a[6] != "-" else None, int(a[7]) if len(a) > 7 else 10))
