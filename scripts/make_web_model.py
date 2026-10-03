#!/usr/bin/env python3
"""Turn a big STL (e.g. a CT-derived chondrocranium) into a small file the
3D viewer on the site can load quickly (assets/js/model-viewer.js).

    pip install trimesh fast-simplification
    python scripts/make_web_model.py path/to/skull.stl assets/models/name.bin

What it does: cuts the mesh down to about 48,000 triangles (plenty for a
smooth skull on screen), then stores it compactly: vertex positions rounded
onto a 65,536-step grid inside the model's bounding box, plus the triangle
list. A 15 MB STL comes out around half a megabyte. Units are kept (the
viewer shows models that share a figure at the same scale).

File layout (little-endian):
  4 bytes  "TMSH"
  uint32   version (1)
  uint32   number of vertices
  uint32   number of triangle indices (3 per triangle)
  6 x f32  bounding box min xyz, max xyz
  uint16   x, y, z per vertex, quantized within the bounding box
  uint16 or uint32 indices (uint16 when there are fewer than 65,536 vertices)
"""
import struct
import sys

import numpy as np
import trimesh
import fast_simplification

TARGET_FACES = 48000


def main(src, dst, target=TARGET_FACES):
    mesh = trimesh.load(src, force="mesh")
    faces = len(mesh.faces)
    if faces > target:
        v, f = fast_simplification.simplify(
            mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
            target_reduction=1 - target / faces)
        mesh = trimesh.Trimesh(v, f, process=True)
    v = mesh.vertices.astype(np.float64)
    f = mesh.faces.astype(np.int64)
    lo, hi = v.min(0), v.max(0)
    span = np.where(hi - lo > 0, hi - lo, 1)
    q = np.round((v - lo) / span * 65535).astype("<u2")
    idx = f.reshape(-1)
    idx_bytes = idx.astype("<u2" if len(v) < 65536 else "<u4").tobytes()
    with open(dst, "wb") as out:
        out.write(b"TMSH")
        out.write(struct.pack("<III", 1, len(v), len(idx)))
        out.write(struct.pack("<6f", *lo, *hi))
        out.write(q.tobytes())
        out.write(idx_bytes)
    print(f"{dst}: {len(mesh.faces)} triangles, {len(v)} vertices, "
          f"bbox {np.round(lo, 2)} to {np.round(hi, 2)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else TARGET_FACES)
