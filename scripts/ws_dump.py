"""Bridge check without a browser: connect to the WebSocket, start a run, print what the renderer would receive.

    python scripts/ws_dump.py [controller] [seconds_of_sim_time] [speed]
"""
import asyncio
import json
import sys

import aiohttp


async def main(controller="fixed", until=75, speed=20, url="http://127.0.0.1:8765/ws"):
    async with aiohttp.ClientSession() as s, s.ws_connect(url) as ws:
        async def send(**m):
            await ws.send_str(json.dumps(m))

        await send(cmd="select", controllers=[controller], scenario="uneven")
        await send(cmd="speed", value=speed)
        await send(cmd="start")
        run_id = None
        async for m in ws:
            msg = json.loads(m.data)
            t = msg["type"]
            if t == "hello":
                print("hello: net edges", len(msg["net"]["edges"]), "approaches", [a["lane"] for a in msg["net"]["approaches"]])
            elif t == "state":
                print("state:", msg["status"], msg["controllers"], msg["scenario"]["key"], "run", msg["run_id"], "speed", msg["speed"])
                if msg["status"] == "running":
                    run_id = msg["run_id"]
            elif t == "frame" and msg["run_id"] == run_id:
                p = msg["panes"][0]
                if int(msg["t"]) % 15 == 0:
                    print(f"frame seq={msg['seq']:>3} t={msg['t']:>5} veh={len(p['vehicles']):>2} tls={p['tls']['state']} "
                          f"phase={p['tls']['phase']} elapsed={p['tls']['elapsed']}")
                if msg["t"] >= until:
                    await send(cmd="stop")
            elif t == "result":
                print("result:", json.dumps(msg["panes"]))
                break
            elif t == "error":
                print("ERROR", msg["message"])
                break


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main(a[0] if a else "fixed", float(a[1]) if len(a) > 1 else 75, int(a[2]) if len(a) > 2 else 20))
