import asyncio
import base64
import io
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from PIL import Image
import websockets

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_GIF = ROOT / "docs" / "gifs" / "domestage_app_demo.gif"
OUTPUT_GIF.parent.mkdir(parents=True, exist_ok=True)

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9229
URL = "http://127.0.0.1:8503/"

async def cdp_call(ws, method, params=None, msg_id=[1]):
    mid = msg_id[0]
    msg_id[0] += 1
    req = {"id": mid, "method": method, "params": params or {}}
    await ws.send(json.dumps(req))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == mid:
            return resp.get("result", {})

async def capture_demo_frame(ws, msg_id):
    res = await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            window.scrollTo(0, 0);
            const p = document.getElementById('precompute-card').getBoundingClientRect();
            const v = document.querySelector('.viewport-card').getBoundingClientRect();
            return {
                x: Math.round(p.left),
                y: Math.round(p.top),
                width: Math.round(Math.max(p.width, v.width)),
                height: Math.round(v.bottom - p.top)
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
        print("No frames to save!")
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
    # Give key moments longer duration
    durations[0] = 500  # Initial state
    durations[4] = 600  # Ready state
    durations[-1] = 1600 # Final orbit pause

    processed[0].save(
        output_path,
        save_all=True,
        append_images=processed[1:],
        duration=durations,
        loop=0,
        optimize=False
    )
    print(f"\n=======================================================")
    print(f"Generated {output_path.name}")
    print(f"Frames: {len(processed)}, Size: {os.path.getsize(output_path)/1024:.1f} KB, Res: {target_width}x{target_height}")
    print(f"=======================================================\n")

async def record_full_demo(ws, msg_id):
    print("Setting up clean showcase layout...")
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            document.querySelector('header').style.display = 'none';
            document.querySelector('.controls-grid').style.display = 'none';
            document.querySelector('.new-bars-card').style.display = 'none';
            document.querySelector('.metrics-grid').style.display = 'none';
            document.querySelector('.viz-options-strip').style.display = 'none';
            document.getElementById('aisc-controls').style.display = 'none';
            window.scrollTo(0, 0);
        })()'''
    }, msg_id)
    await asyncio.sleep(0.5)

    frames = []

    # --- ACT 1: Precomputation Progress Bar ("Barrita de calculando") ---
    print("Act 1: Recording calculation preload bar...")
    # Simulate the preload progression visually
    stages_to_show = [
        (0, "0 / 136 (0%)", "0%", "Precalculating all stages for instant 60 FPS motion…", "CALCULATING…", False),
        (28, "28 / 136 (21%)", "21%", "Precalculating stage 28 of 136…", "CALCULATING…", False),
        (65, "65 / 136 (48%)", "48%", "Precalculating stage 65 of 136…", "CALCULATING…", False),
        (105, "105 / 136 (77%)", "77%", "Precalculating stage 105 of 136…", "CALCULATING…", False),
        (136, "136 / 136 (100%)", "100%", "All 136 stages precalculated in memory · Fluid 60 FPS motion active", "READY / 60 FPS", True),
    ]
    for count, count_txt, pct_txt, label_txt, badge_txt, complete in stages_to_show:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f'''(() => {{
                const card = document.getElementById('precompute-card');
                if ({str(complete).lower()}) {{
                    card.classList.add('complete');
                    document.getElementById('precompute-spinner').textContent = '✓';
                    document.getElementById('precompute-badge').className = 'badge badge-stable';
                }} else {{
                    card.classList.remove('complete');
                    document.getElementById('precompute-spinner').textContent = '⚡';
                    document.getElementById('precompute-badge').className = 'badge badge-pending';
                }}
                document.getElementById('precompute-count').textContent = "{count_txt}";
                document.getElementById('precompute-fill').style.width = "{pct_txt}";
                document.getElementById('precompute-label').textContent = "{label_txt}";
                document.getElementById('precompute-badge').textContent = "{badge_txt}";
            }})()'''
        }, msg_id)
        await asyncio.sleep(0.04)
        im = await capture_demo_frame(ws, msg_id)
        if im: frames.append(im)

    # Wait for all real stages in memory
    print("Waiting for all stages in memory...")
    for _ in range(30):
        res = await cdp_call(ws, "Runtime.evaluate", {
            "expression": "window.simulator ? window.simulator.getCalculated().size : 0",
            "returnByValue": True
        }, msg_id)
        calc_size = res.get("result", {}).get("value", 0)
        if calc_size >= 130:
            break
        await asyncio.sleep(0.2)

    # --- ACT 2: Smooth 60 FPS Progressive Assembly Scrubbing ---
    print("Act 2: Scrubbing 60 FPS assembly timeline...")
    assembly_stages = [0, 8, 18, 30, 44, 58, 72, 86, 100, 112, 122, 130, 135]
    for s in assembly_stages:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f'''(() => {{
                const r = window.simulator.getCalculated().get({s});
                if (r) window.simulator.applyStage({s}, r);
            }})()'''
        }, msg_id)
        await asyncio.sleep(0.05)
        im = await capture_demo_frame(ws, msg_id)
        if im: frames.append(im)

    # --- ACT 3: Amplified Nodal Deflection & 3D Reaction Vectors ---
    print("Act 3: Amplified deflection & reaction vectors...")
    # Stay at stage 120 (significant cantilever sag)
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            const r = window.simulator.getCalculated().get(120);
            if (r) window.simulator.applyStage(120, r);
            document.getElementById('show-deformation').checked = false;
            document.getElementById('show-reactions').checked = false;
            document.getElementById('show-aisc').checked = false;
            updateDeformation(); updateReactions(); window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.06)
    im = await capture_demo_frame(ws, msg_id)
    if im: frames.append(im)

    # Ramp deformation
    for factor in [25, 60, 100]:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f'''(() => {{
                document.getElementById('show-deformation').checked = true;
                document.getElementById('deformation-factor').value = {factor};
                document.getElementById('deformation-factor-num').value = {factor};
                updateDeformation(); window.simulator.draw();
            }})()'''
        }, msg_id)
        await asyncio.sleep(0.06)
        im = await capture_demo_frame(ws, msg_id)
        if im: frames.append(im)

    # Show support reaction vectors
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            document.getElementById('show-reactions').checked = true;
            updateReactions(); window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.08)
    for _ in range(2):
        im = await capture_demo_frame(ws, msg_id)
        if im: frames.append(im)

    # --- ACT 4: ANSI/AISC 360-22 LRFD Checks & Utilization Colors ---
    print("Act 4: AISC 360-22 LRFD member checks & graduated colors...")
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            document.getElementById('show-deformation').checked = false;
            document.getElementById('show-reactions').checked = false;
            document.getElementById('show-aisc').checked = true;
            document.getElementById('design-grade').value = 'a500-21-c';
            if (window.AISCView) window.AISCView.update();
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.3)
    im = await capture_demo_frame(ws, msg_id)
    if im: frames.append(im)

    # Select critical member #24
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            const sel = document.getElementById('element-select');
            if (sel) {
                sel.value = 'b24';
                sel.dispatchEvent(new Event('change'));
            }
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.1)
    for _ in range(2):
        im = await capture_demo_frame(ws, msg_id)
        if im: frames.append(im)

    # --- ACT 5: 3D Camera Orbit ---
    print("Act 5: Orbiting 3D camera...")
    for _ in range(8):
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": "window.simulator.orbit(14, 3);"
        }, msg_id)
        await asyncio.sleep(0.05)
        im = await capture_demo_frame(ws, msg_id)
        if im: frames.append(im)

    save_gif(frames, OUTPUT_GIF, duration=120, target_width=840)

async def main():
    print("Launching headless Chrome for full demo recording...")
    proc = subprocess.Popen([
        CHROME_BIN,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        "--remote-allow-origins=*",
        "--window-size=1280,1200",
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
            await record_full_demo(ws, msg_id)
    finally:
        proc.terminate()
        proc.wait()
        print("Chrome stopped.")

if __name__ == '__main__':
    asyncio.run(main())
