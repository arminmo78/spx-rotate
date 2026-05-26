#!/usr/bin/env python3
"""Generate simple SVG-based PNG icons for the PWA."""
import base64, struct, zlib

def create_png(size):
    """Create a minimal PNG icon programmatically."""
    # Simple dark background with green chart symbol
    img = []
    for y in range(size):
        row = []
        for x in range(size):
            # Background
            r, g, b, a = 10, 10, 15, 255
            # Border ring
            cx, cy = size//2, size//2
            dist = ((x-cx)**2 + (y-cy)**2) ** 0.5
            radius = size//2 - 2
            if dist > radius:
                a = 0
            elif dist > radius - size//16:
                r,g,b = 0, 180, 100
            else:
                # Inner chart bars
                bar_w = size // 8
                for i, (bx, bh, bc) in enumerate([
                    (1, 0.3, (255,69,58)),
                    (2, 0.5, (255,149,0)),
                    (3, 0.65, (255,217,61)),
                    (4, 0.55, (255,217,61)),
                    (5, 0.8, (0,255,135)),
                    (6, 1.0, (0,255,135)),
                ]):
                    bx_start = int(size * 0.1) + i * bar_w
                    bx_end = bx_start + bar_w - 2
                    by_start = int(cy - radius * 0.7 * bh)
                    by_end = int(cy + radius * 0.5)
                    if bx_start <= x < bx_end and by_start <= y <= by_end:
                        r,g,b = bc
            row.extend([r,g,b,a])
        img.append(bytes(row))

    def png_chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    raw = b''
    for row in img:
        raw += b'\x00' + row
    compressed = zlib.compress(raw, 9)

    png = b'\x89PNG\r\n\x1a\n'
    png += png_chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
    png += png_chunk(b'IDAT', compressed)
    png += png_chunk(b'IEND', b'')
    return png

for sz in [192, 512]:
    with open(f'/home/claude/spx-pwa/icon-{sz}.png', 'wb') as f:
        f.write(create_png(sz))
    print(f'Generated icon-{sz}.png')
