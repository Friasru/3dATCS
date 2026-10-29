"""Record a ~2-minute backup demo video of the real page (GPU-rendered) to output/backup_demo.webm.

Needs the server running (./run.sh). Sequence: Fixed -> Queue-Based -> side-by-side -> measured results.
    python scripts/record_backup_video.py [--url http://127.0.0.1:8765] [--size 1920x1080]
"""
import argparse, asyncio, glob, os, shutil, sys
# Playwright needs its own small ffmpeg build to write video; setup keeps it project-local (see ./run.sh record).
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache", "ms-playwright"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tests.browser_util import Browser

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


async def main(url, size):
    w, h = (int(v) for v in size.split("x"))
    vdir = os.path.join(ROOT, "output", "video_tmp")
    shutil.rmtree(vdir, ignore_errors=True)
    async with Browser(w, h, gpu=True, video_dir=vdir) as b:
        pg = await b.open(url)
        await pg.wait_for_timeout(3000)  # idle overview
        await b.start_run(("fixed",), "uneven", 10)
        await pg.wait_for_timeout(28000)
        await pg.click("#cams button[data-cam='driver']"); await pg.wait_for_timeout(7000)
        await pg.click("#cams button[data-cam='overview']"); await pg.wait_for_timeout(2000)
        await b.start_run(("queue_based",), "uneven", 10)
        await pg.wait_for_timeout(28000)
        await b.start_run(("fixed", "queue_based"), "uneven", 20)
        await pg.wait_for_timeout(40000)
        await pg.click("#btn-stop"); await pg.wait_for_timeout(800)
        await pg.click("#btn-results"); await pg.wait_for_timeout(9000)
        print("browser errors:", b.errors)
    vids = glob.glob(os.path.join(vdir, "*.webm"))
    out = os.path.join(ROOT, "output", "backup_demo.webm")
    shutil.move(vids[0], out)
    shutil.rmtree(vdir, ignore_errors=True)
    print(f"wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB)")


ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:8765"); ap.add_argument("--size", default="1920x1080")
a = ap.parse_args()
asyncio.run(main(a.url, a.size))
