#!/usr/bin/env python3
"""
Convert a manually downloaded NYC Subway route bullet into a flattened PNG.

Workflow:
  1. Run the script. If the raw icon is missing, it prints the Wikimedia URL.
  2. Download the file (save as icons/<ROUTE>.png by default).
  3. Run the script again to crop/scale/flatten into icons/<ROUTE>_black.png.
"""

import argparse
import hashlib
import struct
import sys
import urllib.parse
import zlib
from pathlib import Path
from typing import List, Tuple

COMMONS_BASE = "https://upload.wikimedia.org/wikipedia/commons"
FILENAME_TEMPLATE = "NYCS-bull-trans-{route}.svg"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BPP = 4  # RGBA


def build_download_url(route: str, size: int) -> str:
    filename = FILENAME_TEMPLATE.format(route=route)
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()
    encoded = urllib.parse.quote(filename)
    return (
        f"{COMMONS_BASE}/thumb/{digest[0]}/{digest[:2]}/{encoded}/"
        f"{size}px-{encoded}.png"
    )


def read_chunks(data: bytes):
    pos = 8  # skip PNG signature
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        ctype = data[pos : pos + 4]
        pos += 4
        chunk_data = data[pos : pos + length]
        pos += length
        crc = data[pos : pos + 4]
        pos += 4
        yield ctype, chunk_data
        if ctype == b"IEND":
            break


def decode_png_rgba(data: bytes) -> Tuple[int, int, List[List[int]]]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file")
    width = height = None
    blocks: List[bytes] = []
    for ctype, chunk_data in read_chunks(data):
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type != 6:
                raise ValueError("PNG must be 8-bit RGBA")
        elif ctype == b"IDAT":
            blocks.append(chunk_data)

    if width is None or height is None:
        raise ValueError("PNG missing IHDR chunk")

    raw = zlib.decompress(b"".join(blocks))
    stride = width * BPP
    rows: List[List[int]] = []
    prev = [0] * stride

    def paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    idx = 0
    for _ in range(height):
        filter_type = raw[idx]
        idx += 1
        row = [0] * stride
        if filter_type == 0:
            row = list(raw[idx : idx + stride])
        elif filter_type == 1:
            for x in range(stride):
                left = row[x - BPP] if x >= BPP else 0
                row[x] = (raw[idx + x] + left) & 0xFF
        elif filter_type == 2:
            for x in range(stride):
                up = prev[x]
                row[x] = (raw[idx + x] + up) & 0xFF
        elif filter_type == 3:
            for x in range(stride):
                left = row[x - BPP] if x >= BPP else 0
                up = prev[x]
                row[x] = (raw[idx + x] + ((left + up) >> 1)) & 0xFF
        elif filter_type == 4:
            for x in range(stride):
                left = row[x - BPP] if x >= BPP else 0
                up = prev[x]
                up_left = prev[x - BPP] if x >= BPP else 0
                row[x] = (raw[idx + x] + paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter {filter_type}")
        rows.append(row)
        prev = row
        idx += stride

    return width, height, rows


def crop_alpha(
    width: int, height: int, rows: List[List[int]]
) -> Tuple[int, int, List[List[int]]]:
    top, bottom = height, -1
    left, right = width, -1

    for y in range(height):
        row = rows[y]
        for x in range(width):
            if row[x * BPP + 3] > 0:
                top = min(top, y)
                bottom = max(bottom, y)
                left = min(left, x)
                right = max(right, x)

    if bottom < top or right < left:
        return width, height, rows

    cropped = [
        row[left * BPP : (right + 1) * BPP] for row in rows[top : bottom + 1]
    ]
    return right - left + 1, bottom - top + 1, cropped


def resize_nearest(
    width: int, height: int, rows: List[List[int]], size: int
) -> Tuple[int, int, List[List[int]]]:
    if width == size and height == size:
        return width, height, rows

    new_rows: List[List[int]] = []
    for ny in range(size):
        src_y = min(height - 1, int(ny * height / size))
        src_row = rows[src_y]
        new_row = [0] * (size * BPP)
        for nx in range(size):
            src_x = min(width - 1, int(nx * width / size))
            src_idx = src_x * BPP
            dst_idx = nx * BPP
            new_row[dst_idx : dst_idx + BPP] = src_row[src_idx : src_idx + BPP]
        new_rows.append(new_row)
    return size, size, new_rows


def flatten_background(rows: List[List[int]], bg=(0, 0, 0)) -> None:
    br, bgc, bb = bg
    for row in rows:
        for idx in range(0, len(row), BPP):
            r, g, b, a = row[idx : idx + BPP]
            if a < 255:
                r = (r * a + br * (255 - a)) // 255
                g = (g * a + bgc * (255 - a)) // 255
                b = (b * a + bb * (255 - a)) // 255
            row[idx] = r
            row[idx + 1] = g
            row[idx + 2] = b
            row[idx + 3] = 255


def encode_png(width: int, height: int, rows: List[List[int]]) -> bytes:
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Generate NYC Subway route icons.")
    parser.add_argument(
        "route",
        nargs="?",
        default="M",
        help="Route identifier (e.g., F, M, 7, SIR). Default: M.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=1024,
        help="Output size in pixels (square). Default: 1024.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to the raw PNG (downloaded from Wikimedia). Default: icons/<ROUTE>.png.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path. Default: icons/<ROUTE>_black.png within the repo.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    route = args.route.upper()
    size = args.size
    input_path = args.input or (PROJECT_ROOT / "icons" / f"{route}.png")
    output_path = args.output or (PROJECT_ROOT / "icons" / f"{route}_black.png")

    if not input_path.exists():
        url = build_download_url(route, size)
        print(f"❌ Raw icon not found: {input_path}")
        print("   Download it from the following link (save as the missing path):")
        print(f"   {url}")
        return 1

    print(f"⚙️  Processing {input_path}...")
    png_bytes = input_path.read_bytes()
    width, height, rows = decode_png_rgba(png_bytes)
    width, height, rows = crop_alpha(width, height, rows)
    width, height, rows = resize_nearest(width, height, rows, size)
    flatten_background(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(encode_png(width, height, rows))
    print(f"✅ Saved {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
