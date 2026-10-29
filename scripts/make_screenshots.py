"""Capture the README/Demo-Day screenshots from the running page (GPU-rendered through WSL, 1920x1080)."""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tests.browser_util import Browser

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "images")


async def main():
    async with Browser(1920, 1080, gpu=True) as b:
        pg = await b.open("http://127.0.0.1:8765")
        print("renderer:", await b.gl_renderer())
        await b.start_run(("fixed",), "uneven", 20)
        await b.wait_sim_time(95)
        await pg.screenshot(path=f"{OUT}/01-fixed-overview.png")
        await pg.click("#cams button[data-cam='driver']"); await pg.wait_for_timeout(1800)
        await pg.screenshot(path=f"{OUT}/02-driver-view.png")
        await pg.click("#cams button[data-cam='top']"); await pg.wait_for_timeout(1800)
        await pg.screenshot(path=f"{OUT}/03-top-view.png")
        await b.start_run(("queue_based",), "uneven", 20)
        await b.wait_sim_time(95)
        await pg.click("#cams button[data-cam='overview']"); await pg.wait_for_timeout(1800)
        await pg.screenshot(path=f"{OUT}/04-queue-based-overview.png")
        await b.start_run(("fixed", "queue_based"), "uneven", 20)
        await b.wait_sim_time(120)
        await pg.screenshot(path=f"{OUT}/05-side-by-side.png")
        await pg.click("#btn-stop"); await pg.wait_for_function("window.__atcs.status === 'stopped'")
        await pg.click("#btn-results"); await pg.wait_for_selector("table.res"); await pg.wait_for_timeout(500)
        await pg.screenshot(path=f"{OUT}/06-results.png")
        print("errors:", b.errors)

asyncio.run(main())
