import asyncio
import base64
import io
import json
import math
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from PIL import Image
import websockets

ROOT = Path(__file__).resolve().parents[1]
GIFS_DIR = ROOT / "docs" / "gifs"
GIFS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9229
URL = "http://127.0.0.1:8503/"

# Level isometric base: pitch by -55 deg around X (apex points straight up, level horizon)
pitch = -math.radians(52)
q_iso_base = [math.cos(pitch/2), math.sin(pitch/2), 0, 0]

def mul_q(a, b):
    return [
        a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],
        a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],
        a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],
        a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]
    ]

def get_iso_q(yaw_deg):
    yaw = math.radians(yaw_deg)
    q_yaw = [math.cos(yaw/2), 0, 0, math.sin(yaw/2)]
    return mul_q(q_iso_base, q_yaw)

def get_plan_q(yaw_deg):
    yaw = math.radians(yaw_deg)
    return [math.cos(yaw/2), 0, 0, math.sin(yaw/2)]

async def cdp_call(ws, method, params=None, msg_id=[1]):
    mid = msg_id[0]
    msg_id[0] += 1
    req = {"id": mid, "method": method, "params": params or {}}
    await ws.send(json.dumps(req))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == mid:
            return resp.get("result", {})

async def capture_frame(ws, msg_id):
    res = await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            window.scrollTo(0, 0);
            const t = document.querySelector('.timeline-card').getBoundingClientRect();
            const v = document.querySelector('.viewport-card').getBoundingClientRect();
            return {
                x: Math.round(t.left),
                y: Math.round(t.top),
                width: Math.round(Math.max(t.width, v.width)),
                height: Math.round(v.bottom - t.top)
            };
        })()''',
        "returnByValue": True
    }, msg_id)
    rect = res.get("result", {}).get("value")
    if not rect or rect["width"] <= 0 or rect["height"] <= 0:
        return None
        
    shot = await cdp_call(ws, "Page.captureScreenshot", {
        "format": "png",
        "clip": {"x": rect["x"], "y": rect["y"], "width": rect["width"], "height": rect["height"], "scale": 1},
        "captureBeyondViewport": True
    }, msg_id)
    return Image.open(io.BytesIO(base64.b64decode(shot["data"])))

def save_gif(images, output_path, duration=110, target_width=840):
    if not images:
        print(f"No frames for {output_path}")
        return
    processed = []
    w, h = images[0].size
    if target_width and w > target_width:
        ratio = target_width / float(w)
        target_height = int(float(h) * ratio)
    else:
        target_width, target_height = w, h

    for im in images:
        rgb_im = im.convert("RGB").resize((target_width, target_height), Image.Resampling.LANCZOS)
        paletted = rgb_im.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        processed.append(paletted)

    durations = [duration] * len(processed)
    durations[0] = 500  # Pause on first frame
    durations[-1] = 1600 # Pause on completed dome

    processed[0].save(
        output_path,
        save_all=True,
        append_images=processed[1:],
        duration=durations,
        loop=0,
        optimize=False
    )
    print(f"Generated {output_path.name}: {len(processed)} frames, {os.path.getsize(output_path)/1024:.1f} KB, {target_width}x{target_height}")

async def record_progression(ws, msg_id, mode="iso", output_file="domestage_progress_100pct.gif"):
    print(f"\nRecording {mode.upper()} progression up to 100%...")
    # Hide panels except timeline and viewport
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            document.querySelector('header').style.display = 'none';
            document.querySelector('.controls-grid').style.display = 'none';
            document.querySelector('.new-bars-card').style.display = 'none';
            document.getElementById('precompute-card').style.display = 'none';
            document.querySelector('.metrics-grid').style.display = 'none';
            document.querySelector('.viz-options-strip').style.display = 'none';
            document.getElementById('aisc-controls').style.display = 'none';
            document.getElementById('show-dimensions').checked = false;
            document.getElementById('show-deformation').checked = false;
            document.getElementById('show-reactions').checked = false;
            document.getElementById('show-aisc').checked = false;
            window.scrollTo(0, 0);
        })()'''
    }, msg_id)
    await asyncio.sleep(0.4)

    # Initial camera setup
    initial_yaw = 25 if mode == "iso" else 0
    init_q = get_iso_q(initial_yaw) if mode == "iso" else get_plan_q(0)
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": f'''(() => {{
            window.simulator.setCameraQ({json.dumps(init_q)});
            window.simulator.draw();
        }})()'''
    }, msg_id)

    frames = []

    # Wait for all stages to be in memory
    for _ in range(40):
        res = await cdp_call(ws, "Runtime.evaluate", {
            "expression": "window.simulator ? window.simulator.getCalculated().size : 0",
            "returnByValue": True
        }, msg_id)
        if res.get("result", {}).get("value", 0) >= 135:
            break
        await asyncio.sleep(0.2)

    # Stages from 0 to 135 (100%)
    # 24 smoothly spaced stages covering all rings
    stages = [0, 5, 10, 16, 22, 28, 35, 42, 50, 58, 66, 74, 82, 90, 98, 106, 114, 120, 126, 130, 133, 135]
    print(f"Phase 1: Progressing across {len(stages)} stages to 100%...")
    for s in stages:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f'''(() => {{
                const r = window.simulator.getCalculated().get({s});
                if (r) window.simulator.applyStage({s}, r);
            }})()'''
        }, msg_id)
        await asyncio.sleep(0.04)
        im = await capture_frame(ws, msg_id)
        if im: frames.append(im)

    # Extra frame at 100%
    if frames: frames.append(frames[-1])

    # Phase 2: Smooth Level Turntable Rotation at 100% (Zero tilt, pure horizontal rotation)
    print("Phase 2: Turntable rotation at 100% completion (Zero tilt)...")
    steps = 14
    for i in range(1, steps + 1):
        yaw = initial_yaw + (i * 360.0 / steps)
        q_step = get_iso_q(yaw) if mode == "iso" else get_plan_q(i * 360.0 / steps)
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f'''(() => {{
                window.simulator.setCameraQ({json.dumps(q_step)});
                window.simulator.draw();
            }})()'''
        }, msg_id)
        await asyncio.sleep(0.04)
        im = await capture_frame(ws, msg_id)
        if im: frames.append(im)

    save_gif(frames, GIFS_DIR / output_file, duration=115, target_width=840)

async def main():
    print("Launching headless Chrome on port 9229...")
    proc = subprocess.Popen([
        CHROME_BIN,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        "--remote-allow-origins=*",
        "--window-size=1200,950",
        URL
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    try:
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
        tab = [t for t in tabs if t.get("type") == "page"][0]
        
        async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=50*1024*1024) as ws:
            msg_id = [1]
            await cdp_call(ws, "Page.enable", {}, msg_id)
            await asyncio.sleep(1.0)
            
            # 1. Clean Level Isometric 100% progression (Primary)
            await record_progression(ws, msg_id, mode="iso", output_file="domestage_app_demo.gif")
            
            # 2. Pure Vista en Planta (Top-down) 100% progression
            await record_progression(ws, msg_id, mode="plan", output_file="domestage_plan_view_100pct.gif")

    finally:
        proc.terminate()
        proc.wait()
        print("Chrome stopped.")

if __name__ == '__main__':
    asyncio.run(main())
