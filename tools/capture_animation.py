"""
Capture demo-animation.html as an animated GIF using Playwright.
Run: python3 tools/capture_animation.py
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
import io

ASSETS = Path(__file__).parent.parent / "assets"
HTML_FILE = ASSETS / "demo-animation.html"
GIF_OUT = ASSETS / "demo-animation.gif"

# Animation cycle is ~10s. Capture one cycle without interfering.
# Each iteration = sleep(0.25) + ~0.08s screenshot overhead ≈ 0.33s/frame
# 28 frames × 0.33s = 9.2s — safely within one cycle
FRAME_COUNT = 28
INTERVAL_MS = 250
VIEWPORT = {"width": 860, "height": 760}


def capture():
    frames = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(f"file://{HTML_FILE.resolve()}")

        # Wait for initial render, then start capturing immediately.
        # No style injection — original CSS fits all content (confirmed).
        # No reload override — we capture one natural cycle.
        time.sleep(0.3)

        for i in range(FRAME_COUNT):
            png = page.screenshot(type="png")
            img = Image.open(io.BytesIO(png)).convert("RGB")
            img = img.resize((640, 572), Image.LANCZOS)
            frames.append(img)
            time.sleep(INTERVAL_MS / 1000)

        browser.close()

    # Build a global palette from all frames combined, then map every frame to it.
    # This is required for PIL animated GIF to avoid identical-frame artifacts.
    combined = Image.new("RGB", (frames[0].width, frames[0].height * len(frames)))
    for i, f in enumerate(frames):
        combined.paste(f, (0, i * frames[0].height))
    global_q = combined.quantize(colors=128, method=Image.Quantize.FASTOCTREE)

    palette_frames = []
    for frame in frames:
        pf = frame.quantize(palette=global_q, dither=Image.Dither.NONE)
        palette_frames.append(pf)

    palette_frames[0].save(
        GIF_OUT,
        save_all=True,
        append_images=palette_frames[1:],
        loop=0,
        duration=INTERVAL_MS,
        optimize=False,
    )
    print(f"Saved {GIF_OUT}  ({GIF_OUT.stat().st_size // 1024} KB, {len(palette_frames)} frames)")


if __name__ == "__main__":
    capture()
