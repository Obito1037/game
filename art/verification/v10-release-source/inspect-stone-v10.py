"""Read-only PNG statistics. Does not transform or rewrite the generated image."""
from pathlib import Path
import hashlib, json, struct, zlib
import numpy as np

root = Path(__file__).resolve().parents[1]
folder = root / 'art/generated/stone-v10'
raw = (folder / 'stone-base-v1.png').read_bytes()
assert raw[:8] == b'\x89PNG\r\n\x1a\n'
offset, compressed = 8, bytearray()
while offset < len(raw):
    size = struct.unpack('>I', raw[offset:offset+4])[0]
    tag, block = raw[offset+4:offset+8], raw[offset+8:offset+8+size]
    if tag == b'IHDR':
        width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', block)
    elif tag == b'IDAT': compressed.extend(block)
    offset += size + 12
assert depth == 8 and color in (2, 6) and interlace == 0
channels = 3 if color == 2 else 4
stride = width * channels
decoded = zlib.decompress(compressed)
rows, previous, cursor = [], bytearray(stride), 0
for _ in range(height):
    mode = decoded[cursor]
    row = bytearray(decoded[cursor+1:cursor+1+stride])
    cursor += stride + 1
    for x in range(stride):
        a = row[x-channels] if x >= channels else 0
        b = previous[x]
        c = previous[x-channels] if x >= channels else 0
        if mode == 1: predictor = a
        elif mode == 2: predictor = b
        elif mode == 3: predictor = (a+b)//2
        elif mode == 4:
            p = a+b-c
            pa,pb,pc = abs(p-a),abs(p-b),abs(p-c)
            predictor = a if pa <= pb and pa <= pc else b if pb <= pc else c
        else:
            assert mode == 0
            predictor = 0
        row[x] = (row[x] + predictor) & 255
    rows.append(bytes(row)); previous = row
pixels = np.frombuffer(b''.join(rows), dtype=np.uint8).reshape(height,width,channels)
srgb = pixels[:,:,:3].astype(np.float64)/255
linear = np.where(srgb <= .04045, srgb/12.92, ((srgb+.055)/1.055)**2.4)
luminance = linear @ np.array([.2126,.7152,.0722])
report = {
    'source': 'Built-in image_gen; new original bitmap, no reference image supplied',
    'mode': 'built-in', 'originalFile': 'stone-base-v1.png', 'promptFile': 'prompt.txt',
    'sha256': hashlib.sha256(raw).hexdigest().upper(),
    'width': width, 'height': height, 'channels': channels, 'bytes': len(raw),
    'measurement': 'All source PNG pixels, IEC sRGB transfer decoded to linear RGB; image not modified.',
    'meanSRGB': srgb.mean(axis=(0,1)).tolist(),
    'meanLinearRGB': linear.mean(axis=(0,1)).tolist(),
    'meanLinearLuminance': float(luminance.mean()),
    'linearLuminancePercentiles_1_5_50_95_99': np.percentile(luminance,[1,5,50,95,99]).tolist(),
    'limits': ['AI-generated color texture, not a calibrated scan or measured PBR material.',
               'Shallow fissure shading is present in the generated image.',
               'Requested tileability is not a verified seamless edge guarantee.',
               'Runtime relief derived from luminance is an artistic approximation.'],
    'status': 'Candidate: requires in-game material comparison before production adoption.'
}
(folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
