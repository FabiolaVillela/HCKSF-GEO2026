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
OUTPUT_DIR = ROOT / "docs" / "gifs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

async def capture_element(ws, selector, msg_id, second_selector=None):
    # Compute absolute page coordinates without scrolling
    js = f'''(() => {{
        window.scrollTo(0, 0);
        const el1 = document.querySelector("{selector}");
        if (!el1) return null;
        const r1 = el1.getBoundingClientRect();
        let top = r1.top, bottom = r1.bottom, left = r1.left, right = r1.right;
        if ("{second_selector or ''}") {{
            const el2 = document.querySelector("{second_selector}");
            if (el2) {{
                const r2 = el2.getBoundingClientRect();
                top = Math.min(top, r2.top);
                bottom = Math.max(bottom, r2.bottom);
                left = Math.min(left, r2.left);
                right = Math.max(right, r2.right);
            }}
        }}
        return {{
            x: Math.round(left),
            y: Math.round(top),
            width: Math.round(right - left),
            height: Math.round(bottom - top)
        }};
    }})()'''
    res = await cdp_call(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True}, msg_id)
    rect = res.get("result", {}).get("value")
    if not rect or rect["width"] <= 0 or rect["height"] <= 0:
        return None
        
    shot = await cdp_call(ws, "Page.captureScreenshot", {
        "format": "png",
        "clip": {"x": rect["x"], "y": rect["y"], "width": rect["width"], "height": rect["height"], "scale": 1},
        "captureBeyondViewport": True
    }, msg_id)
    return Image.open(io.BytesIO(base64.b64decode(shot["data"])))

def save_gif(images, output_path, duration=110, loop=0, target_width=840):
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
    durations[-1] = max(1000, duration * 8) # Pause on final frame

    processed[0].save(
        output_path,
        save_all=True,
        append_images=processed[1:],
        duration=durations,
        loop=loop,
        optimize=False
    )
    print(f"Created {output_path.name} ({len(processed)} frames, {os.path.getsize(output_path)/1024:.1f} KB, size {target_width}x{target_height})")

async def record_assembly(ws, msg_id):
    print("Recording GIF 1: Assembly Progression...")
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            window.scrollTo(0,0);
            document.getElementById('show-deformation').checked = false;
            document.getElementById('show-reactions').checked = false;
            document.getElementById('show-aisc').checked = false;
            if (window.AISCView) window.AISCView.update();
            window.simulator.draw();
        })()'''
    }, msg_id)
    
    stages = [0, 2, 4, 6, 8, 10, 13, 16, 19, 22, 26, 30, 34, 38, 42, 46, 50, 54, 57, 60]
    frames = []
    for s in stages:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f"window.simulator.setStage({s})"
        }, msg_id)
        await asyncio.sleep(0.06)
        im = await capture_element(ws, ".viewport-card", msg_id)
        if im:
            frames.append(im)
    save_gif(frames, OUTPUT_DIR / "1_assembly_progress.gif", duration=120, target_width=840)

async def record_deformation(ws, msg_id):
    print("Recording GIF 2: Amplified Deflection & Reactions...")
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            window.scrollTo(0,0);
            window.simulator.setStage(50);
            document.getElementById('show-deformation').checked = false;
            document.getElementById('show-reactions').checked = false;
            document.getElementById('show-aisc').checked = false;
            updateDeformation();
            updateReactions();
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.1)
    frames = []
    # 1. Undeformed frame
    im = await capture_element(ws, ".viewport-card", msg_id)
    if im:
        for _ in range(2): frames.append(im)
    
    # 2. Step through deformation factors
    factors = [15, 30, 45, 60, 75, 90, 100]
    for fac in factors:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f'''(() => {{
                document.getElementById('show-deformation').checked = true;
                document.getElementById('deformation-factor').value = {fac};
                document.getElementById('deformation-factor-num').value = {fac};
                updateDeformation();
                window.simulator.draw();
            }})()'''
        }, msg_id)
        await asyncio.sleep(0.06)
        im = await capture_element(ws, ".viewport-card", msg_id)
        if im: frames.append(im)
        
    # 3. Add reactions
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            document.getElementById('show-reactions').checked = true;
            updateReactions();
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.08)
    for _ in range(3):
        im = await capture_element(ws, ".viewport-card", msg_id)
        if im: frames.append(im)
        
    save_gif(frames, OUTPUT_DIR / "2_amplified_deformation.gif", duration=160, target_width=840)

async def record_charts(ws, msg_id):
    print("Recording GIF 3: Progress Curves & Stability...")
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            window.scrollTo(0,0);
            document.getElementById('btn-charts').click();
        })()'''
    }, msg_id)
    print("Waiting for /api/progress calculations...")
    await asyncio.sleep(2.0)
    
    frames = []
    stages = [0, 4, 8, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    for s in stages:
        await cdp_call(ws, "Runtime.evaluate", {
            "expression": f"window.simulator.setStage({s})"
        }, msg_id)
        await asyncio.sleep(0.06)
        im = await capture_element(ws, "#charts-card", msg_id)
        if im: frames.append(im)
        
    save_gif(frames, OUTPUT_DIR / "3_progress_charts.gif", duration=140, target_width=840)

async def record_aisc(ws, msg_id):
    print("Recording GIF 4: AISC 360-22 LRFD Checks & Member Verification...")
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            window.scrollTo(0,0);
            window.simulator.setStage(60);
            document.getElementById('show-deformation').checked = false;
            document.getElementById('show-reactions').checked = false;
            document.getElementById('show-aisc').checked = false;
            updateDeformation();
            updateReactions();
            if (window.AISCView) window.AISCView.update();
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.1)
    frames = []
    
    # 1. Base view without AISC
    im = await capture_element(ws, ".viewport-card", msg_id, ".inspector-card")
    if im:
        for _ in range(2): frames.append(im)
    
    # 2. Select steel grade ASTM A500 Gr C and turn on AISC
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            document.getElementById('design-grade').value = 'a500-21-c';
            document.getElementById('show-aisc').checked = true;
            window.AISCView.update();
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.5)
    
    im = await capture_element(ws, ".viewport-card", msg_id, ".inspector-card")
    if im:
        for _ in range(2): frames.append(im)
        
    # 3. Select bar #12 to show governing equation H1-1a in inspector
    await cdp_call(ws, "Runtime.evaluate", {
        "expression": '''(() => {
            const sel = document.getElementById('element-select');
            sel.value = 'b12';
            sel.dispatchEvent(new Event('change'));
            window.simulator.draw();
        })()'''
    }, msg_id)
    await asyncio.sleep(0.2)
    
    im = await capture_element(ws, ".viewport-card", msg_id, ".inspector-card")
    if im:
        for _ in range(4): frames.append(im)
        
    save_gif(frames, OUTPUT_DIR / "4_aisc_check.gif", duration=250, target_width=840)

async def main():
    print("Launching headless Chrome on port 9229...")
    proc = subprocess.Popen([
        CHROME_BIN,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        "--remote-allow-origins=*",
        "--window-size=1280,1800",
        URL
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    
    try:
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
        tab = [t for t in tabs if t.get("type") == "page"][0]
        ws_url = tab["webSocketDebuggerUrl"]
        
        async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
            msg_id = [1]
            await cdp_call(ws, "Page.enable", {}, msg_id)
            await asyncio.sleep(1.0)
            
            await record_assembly(ws, msg_id)
            await record_deformation(ws, msg_id)
            await record_charts(ws, msg_id)
            await record_aisc(ws, msg_id)
            
            print("\n==========================================")
            print("All 4 animated GIFs successfully generated!")
            print("==========================================")
            for g in sorted(OUTPUT_DIR.glob("*.gif")):
                print(f" - {g.name}: {os.path.getsize(g)/1024:.1f} KB")

    finally:
        proc.terminate()
        proc.wait()
        print("Chrome stopped.")

if __name__ == '__main__':
    asyncio.run(main())
