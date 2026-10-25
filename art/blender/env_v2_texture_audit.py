"""Read-only image measurements; does not alter generated raster assets."""
import bpy
import numpy as np
import json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art/generated/env-v2/textures'
rows = []
for name in ('meadow_albedo_v1.png', 'wood_albedo_v1.png'):
    path = OUT / name
    img = bpy.data.images.load(str(path), check_existing=False)
    width, height = img.size
    px = np.empty(width * height * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(height, width, 4)[..., :3]
    axes = {}
    for axis, label in ((1, 'left_right'), (0, 'bottom_top')):
        jump = np.mean(np.abs(np.take(px, 0, axis=axis) - np.take(px, -1, axis=axis)))
        ordinary = np.mean(np.abs(np.diff(px, axis=axis)), axis=(1, 2) if axis == 0 else (0, 2))
        axes[label] = {
            'wrap_mean_abs_jump': float(jump),
            'ordinary_adjacent_edge_mean': float(np.mean(ordinary)),
            'ordinary_adjacent_edge_p95': float(np.percentile(ordinary, 95)),
            'wrap_to_mean_ratio': float(jump / max(float(np.mean(ordinary)), 1e-8)),
        }
    rows.append({'file': name, 'width': width, 'height': height,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'blender_buffer_rgb_mean': px.mean(axis=(0,1)).tolist(), 'edges': axes})
    bpy.data.images.remove(img)
(OUT / 'texture-audit.json').write_text(json.dumps({
    'scope': 'Original generated candidates only; read-only Blender float pixel buffers. No reference-game bitmap processed.',
    'interpretation': 'Edge jump ratios are diagnostics, not a visual pass or proof of seamless tiling. Original image sizes are measured, not requested sizes.',
    'assets': rows,
}, indent=2), encoding='utf-8')
print(json.dumps(rows))
