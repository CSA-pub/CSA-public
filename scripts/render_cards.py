#!/usr/bin/env python3
"""
CSA card images (`CSA-public`), drawn as SVG and rendered with headless Microsoft Edge:

    og-image-v2.png           1200x630  social card (og:image, twitter:image, Product JSON-LD,
                              webmanifest, catalyst/sponsor pages) and the Stripe product image
    assets/kaggle-cover.png   1200x600  Kaggle cover + README banner

The cards carry no counts on purpose: counts move with every monthly edition, and an image
sits outside the count-claim checks. The one figure kept, 0 cross-molecule merges, is the
csa-poc precision gate: an edition that breaks it never ships. The timeline is illustrative
and shows readouts only (the v1 calendar is protocol readouts).

`_headers` serves /*.png as immutable for a year, so a changed social card needs a NEW file name
(update every reference, and list the old path in functions/_middleware.js RETIRED_FILES). The
Kaggle cover is not linked from any page, so it is redrawn in place.

Needs Windows with Edge and numpy (no Pillow): the screenshot is median-cut to 256 colours and
written as an indexed PNG.

Usage:
    python scripts/render_cards.py            # writes both files
    python scripts/render_cards.py --keep     # also keeps the intermediate HTML/PNG in .cards-build/
"""
import argparse
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

BG, TEAL, AXIS, PILL, WHITE, GREY = "#0c1817", "#2bb3a8", "#0f6e6a", "#0f1f1e", "#eaf3f1", "#8fa6a2"
SANS = "'Segoe UI', system-ui, sans-serif"
MONO = "Consolas, 'Cascadia Mono', monospace"

HOST = "csa.dataengineered.io"
MONTHS = ["JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR", "MAY"]
MARKERS = {2: "READOUT", 5: "READOUT", 8: "READOUT"}  # month index -> event label
CHIPS = ["linked to the listed ticker", "source URL on every row", "0 cross-molecule merges"]


def timeline(y=417):
    out = [f'<line x1="70" y1="{y}" x2="1130" y2="{y}" stroke="{AXIS}" stroke-width="3"/>']
    for i, month in enumerate(MONTHS):
        x = 120 + 96 * i
        out.append(f'<text x="{x}" y="{y + 38}" text-anchor="middle" font-family="{MONO}" font-size="12" '
                   f'letter-spacing="1" fill="{GREY}">{month}</text>')
        if i in MARKERS:
            out.append(f'<line x1="{x}" y1="{y - 56}" x2="{x}" y2="{y - 10}" stroke="{TEAL}" stroke-width="2"/>'
                       f'<circle cx="{x}" cy="{y}" r="15" fill="{TEAL}" fill-opacity="0.18"/>'
                       f'<circle cx="{x}" cy="{y}" r="8.5" fill="{TEAL}" stroke="{WHITE}" stroke-width="2"/>'
                       f'<text x="{x}" y="{y - 68}" text-anchor="middle" font-family="{MONO}" font-size="14" '
                       f'font-weight="700" fill="{TEAL}">{MARKERS[i]}</text>')
        else:
            out.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{GREY}"/>')
    return "".join(out)


def chips(y=533):
    out, x, gap = [], 40, 20
    w = (1160 - 40 - gap * (len(CHIPS) - 1)) / len(CHIPS)
    for label in CHIPS:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="40" rx="13" fill="{PILL}" stroke="{AXIS}" '
                   f'stroke-width="1.5"/>'
                   f'<text x="{x + w / 2}" y="{y + 26}" text-anchor="middle" font-family="{MONO}" font-size="16" '
                   f'fill="{WHITE}">{label}</text>')
        x += w + gap
    return "".join(out)


def card_body():
    """Everything on the 1200x630 card except the background."""
    return f"""
  <rect x="70" y="73" width="58" height="4" fill="{TEAL}"/>
  <text x="138" y="80" font-family="{MONO}" font-size="14" letter-spacing="1" fill="{GREY}">DATAENGINEERED</text>
  <text x="1130" y="80" text-anchor="end" font-family="{MONO}" font-size="16" fill="{GREY}">{HOST}</text>
  <text x="68" y="162" font-family="{SANS}" font-size="84" font-weight="700" fill="{WHITE}">CSA</text>
  <text x="72" y="209" font-family="{SANS}" font-size="35" font-weight="700" fill="{TEAL}">Clinical-Stage</text>
  <text x="72" y="248" font-family="{SANS}" font-size="35" font-weight="700" fill="{WHITE}">Asset Intelligence</text>
  <text x="72" y="294" font-family="{SANS}" font-size="21" fill="{WHITE}" xml:space="preserve">A forward catalyst calendar  \u2014  clinical trials  \u00d7  FDA  \u00d7  SEC,</text>
  <text x="72" y="321" font-family="{SANS}" font-size="21" fill="{GREY}">linked to the drug asset and the listed sponsor.</text>
  {timeline()}
  {chips()}"""


def og_card():
    return 1200, 630, f'<rect width="1200" height="630" fill="{BG}"/>{card_body()}'


def kaggle_cover():
    # the same card 30 px shorter: everything moves up 15 px
    return 1200, 600, f'<rect width="1200" height="600" fill="{BG}"/><g transform="translate(0 -15)">{card_body()}</g>'


def render(width, height, body, html_path, png_path, profile):
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;background:" + BG + "}</style>"
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>', encoding="utf-8")
    subprocess.run([str(EDGE), "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--disable-gpu", f"--user-data-dir={profile}", f"--window-size={width},{height}",
                    f"--screenshot={png_path}", html_path.as_uri()], check=True, capture_output=True)
    # msedge.exe hands off to a browser process and returns before the screenshot is written
    deadline, last = time.time() + 60, -1
    while time.time() < deadline:
        size = png_path.stat().st_size if png_path.exists() else -1
        if size > 0 and size == last:
            return
        last = size
        time.sleep(1)
    raise SystemExit(f"Edge wrote no screenshot to {png_path}")


def read_rgb(path):
    """RGB(A) 8-bit PNG -> HxWx3 array (Edge writes filter types 0-4)."""
    data = path.read_bytes()
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    assert depth == 8 and ctype in (2, 6), (depth, ctype)
    ch = 3 if ctype == 2 else 4
    raw, stride = zlib.decompress(idat), w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    for y in range(h):
        f, line = raw[y * (stride + 1)], np.frombuffer(raw, np.uint8, stride, y * (stride + 1) + 1).astype(np.int32)
        if f in (0, 2):
            cur = line if f == 0 else (line + prev) & 255
        else:
            cur = np.zeros(stride, np.int32)
            for x in range(stride):
                a = cur[x - ch] if x >= ch else 0
                b, c = prev[x], (prev[x - ch] if x >= ch else 0)
                if f == 1:
                    p = a
                elif f == 3:
                    p = (a + b) // 2
                else:
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    p = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                cur[x] = (line[x] + p) & 255
        out[y], prev = cur, cur
    return out.reshape(h, w, ch)[:, :, :3]


def write_indexed(path, rgb, colors=256):
    """Median-cut to <=256 colours, nearest-colour mapping, indexed PNG at zlib level 9."""
    h, w, _ = rgb.shape
    px = rgb.reshape(-1, 3).astype(np.int32)
    uniq, inv = np.unique(px, axis=0, return_inverse=True)
    weights = np.bincount(inv.reshape(-1), minlength=len(uniq))
    boxes = [np.arange(len(uniq))]
    while len(boxes) < colors:
        spans = [(np.ptp(uniq[b], 0).max() if len(b) > 1 else -1) for b in boxes]
        i = int(np.argmax(spans))
        if spans[i] <= 0:
            break
        box = boxes.pop(i)
        c = int(np.ptp(uniq[box], 0).argmax())
        box = box[np.argsort(uniq[box, c], kind="stable")]
        cum = np.cumsum(weights[box])
        cut = int(np.clip(np.searchsorted(cum, cum[-1] / 2), 1, len(box) - 1))
        boxes += [box[:cut], box[cut:]]
    palette = np.array([np.average(uniq[b], 0, weights[b]) for b in boxes]).round().astype(np.int32)
    nearest = np.empty(len(uniq), np.int64)
    for s in range(0, len(uniq), 2048):
        nearest[s:s + 2048] = ((uniq[s:s + 2048, None] - palette[None]) ** 2).sum(-1).argmin(1)
    index = nearest[inv.reshape(-1)].reshape(h, w).astype(np.uint8)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    raw = b"".join(b"\x00" + row.tobytes() for row in index)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
                     + chunk(b"PLTE", palette.astype(np.uint8).tobytes())
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--keep", action="store_true", help="keep the intermediate files in .cards-build/")
    args = ap.parse_args()
    build = Path(tempfile.mkdtemp(prefix="csa-cards-"))
    try:
        for name, (w, h, body), target in [("og", og_card(), ROOT / "og-image-v2.png"),
                                           ("kaggle", kaggle_cover(), ROOT / "assets" / "kaggle-cover.png")]:
            shot = build / f"{name}.png"
            render(w, h, body, build / f"{name}.html", shot, build / "profile")
            rgb = read_rgb(shot)
            assert rgb.shape[:2] == (h, w), (name, rgb.shape)
            write_indexed(target, rgb)
            print(f"{target.relative_to(ROOT).as_posix()}: {w}x{h}, {target.stat().st_size:,} bytes")
        if args.keep:
            keep = ROOT / ".cards-build"
            shutil.rmtree(keep, ignore_errors=True)
            shutil.copytree(build, keep, ignore=shutil.ignore_patterns("profile"))
    finally:
        shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    main()
