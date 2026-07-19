import sys, asyncio
sys.path.insert(0, r"C:\Users\samet\Desktop\Projeler\YouTube\web\backend")
from pipeline import generate_video
from pathlib import Path

async def n(c, s, m, p):
    print(f"  [{p}%] {s}: {m}", flush=True)

async def main():
    images = {}
    d = Path(r"C:\Users\samet\Desktop\Projeler\YouTube\output\images\ocean")
    for p in d.glob("*.png"):
        images[p.stem] = str(p)
    try:
        out = await generate_video("Ocean Animals", "cinematic", images, "test", n)
        print("OUTPUT:", out)
    except Exception as e:
        print("ERR:", e)

asyncio.run(main())
