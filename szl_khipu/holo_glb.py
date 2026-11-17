#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
"""Standard-library glTF 2.0 (GLB) writer for holographic research scenes.

Emissive PBR materials, indexed tube / sphere / box geometry and hard budgets.
Rendered in the browser by Gradio's built-in Model3D viewer; no JavaScript,
CDN, GPU or third-party Python dependency is authored here.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from array import array

MAX_VERTICES = 600_000
MAX_BYTES = 24_000_000


class HoloHold(ValueError):
    """Geometry budget or validity refusal."""


def _unit(v):
    d = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if d <= 1e-12:
        return None
    return (v[0] / d, v[1] / d, v[2] / d)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


class Scene:
    def __init__(self, generator: str):
        self.generator = generator
        self.materials: list[dict] = []
        self._mat_index: dict[tuple, int] = {}
        self.groups: dict[int, tuple[array, array, list[int]]] = {}
        self.vertex_count = 0

    # -- materials -----------------------------------------------------
    def material(self, name: str, rgb, *, glow: float = 0.35, metallic: float = 0.25,
                 roughness: float = 0.42, alpha: float = 1.0) -> int:
        rgb = tuple(min(1.0, max(0.0, float(c))) for c in rgb)
        key = (name, rgb, round(glow, 3), round(metallic, 3), round(roughness, 3), round(alpha, 3))
        if key in self._mat_index:
            return self._mat_index[key]
        mat = {
            "name": name,
            "pbrMetallicRoughness": {"baseColorFactor": [*rgb, alpha],
                                     "metallicFactor": metallic, "roughnessFactor": roughness},
            "emissiveFactor": [c * glow for c in rgb],
            "doubleSided": True,
        }
        if alpha < 1.0:
            mat["alphaMode"] = "BLEND"
        self.materials.append(mat)
        self._mat_index[key] = len(self.materials) - 1
        return len(self.materials) - 1

    def _group(self, mat: int):
        if mat not in self.groups:
            self.groups[mat] = (array("f"), array("f"), [])
        return self.groups[mat]

    def _budget(self, add: int):
        self.vertex_count += add
        if self.vertex_count > MAX_VERTICES:
            raise HoloHold("VERTEX_BUDGET")

    # -- primitives ----------------------------------------------------
    def tube(self, points, radius: float, mat: int, sides: int = 8):
        pts = [tuple(float(c) for c in p) for p in points]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) < 2 or not 0 < radius <= 1.0 or not 3 <= sides <= 24:
            raise HoloHold("TUBE_INVALID")
        if not all(math.isfinite(c) for p in pts for c in p):
            raise HoloHold("NONFINITE_GEOMETRY")
        self._budget(len(pts) * sides)
        verts, norms, tris = self._group(mat)
        start = len(verts) // 3
        prev_u = None
        for i, c in enumerate(pts):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, len(pts) - 1)]
            t = _unit((b[0] - a[0], b[1] - a[1], b[2] - a[2])) or (1.0, 0.0, 0.0)
            ref = prev_u if prev_u is not None else ((0.0, 1.0, 0.0) if abs(t[1]) < 0.9 else (1.0, 0.0, 0.0))
            u = _unit(_cross(t, _cross(ref, t))) if prev_u is not None else _unit(_cross(t, ref))
            if u is None:
                u = _unit(_cross(t, (0.0, 0.0, 1.0))) or (1.0, 0.0, 0.0)
            v = _cross(t, u)
            prev_u = u
            for j in range(sides):
                ang = 2 * math.pi * j / sides
                n = (math.cos(ang) * u[0] + math.sin(ang) * v[0],
                     math.cos(ang) * u[1] + math.sin(ang) * v[1],
                     math.cos(ang) * u[2] + math.sin(ang) * v[2])
                verts.extend((c[0] + radius * n[0], c[1] + radius * n[1], c[2] + radius * n[2]))
                norms.extend(n)
        for i in range(len(pts) - 1):
            for j in range(sides):
                a0 = start + i * sides + j
                a1 = start + i * sides + (j + 1) % sides
                b0 = a0 + sides
                b1 = a1 + sides
                tris.extend((a0, b0, a1, a1, b0, b1))

    def sphere(self, center, radius: float, mat: int, rings: int = 6, segments: int = 10):
        if not 0 < radius <= 2.0:
            raise HoloHold("SPHERE_INVALID")
        cx, cy, cz = (float(c) for c in center)
        self._budget((rings + 1) * (segments + 1))
        verts, norms, tris = self._group(mat)
        start = len(verts) // 3
        for r in range(rings + 1):
            phi = math.pi * r / rings
            for s in range(segments + 1):
                th = 2 * math.pi * s / segments
                n = (math.sin(phi) * math.cos(th), math.cos(phi), math.sin(phi) * math.sin(th))
                verts.extend((cx + radius * n[0], cy + radius * n[1], cz + radius * n[2]))
                norms.extend(n)
        for r in range(rings):
            for s in range(segments):
                a0 = start + r * (segments + 1) + s
                b0 = a0 + segments + 1
                tris.extend((a0, b0, a0 + 1, a0 + 1, b0, b0 + 1))

    def box(self, center, size, mat: int):
        cx, cy, cz = (float(c) for c in center)
        hx, hy, hz = (float(s) / 2 for s in size)
        if min(hx, hy, hz) <= 0:
            raise HoloHold("BOX_INVALID")
        self._budget(24)
        verts, norms, tris = self._group(mat)
        faces = [((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
                 ((0, 1, 0), (0, 0, 1), (1, 0, 0)), ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
                 ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (0, 1, 0), (1, 0, 0))]
        for n, u, v in faces:
            start = len(verts) // 3
            for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                p = [n[k] * (hx, hy, hz)[k] + su * u[k] * (hx, hy, hz)[k] + sv * v[k] * (hx, hy, hz)[k] for k in range(3)]
                verts.extend((cx + p[0], cy + p[1], cz + p[2]))
                norms.extend(n)
            tris.extend((start, start + 1, start + 2, start, start + 2, start + 3))

    # -- serialization -------------------------------------------------
    def glb(self) -> bytes:
        if not self.groups:
            raise HoloHold("EMPTY_SCENE")
        binary = bytearray()
        views, accessors, primitives = [], [], []

        def add_view(data: bytes, target: int) -> int:
            while len(binary) % 4:
                binary.append(0)
            views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data), "target": target})
            binary.extend(data)
            return len(views) - 1

        def le(arr: array) -> bytes:
            if sys.byteorder != "little":
                arr = array(arr.typecode, arr)
                arr.byteswap()
            return arr.tobytes()

        for mat in sorted(self.groups):
            verts, norms, tris = self.groups[mat]
            count = len(verts) // 3
            if count == 0 or not tris or max(tris) >= count:
                raise HoloHold("MESH_INDEX_INVALID")
            xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
            pv = add_view(le(verts), 34962)
            nv = add_view(le(norms), 34962)
            big = count > 65535
            iv = add_view(le(array("I" if big else "H", tris)), 34963)
            accessors.append({"bufferView": pv, "componentType": 5126, "count": count, "type": "VEC3",
                              "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]})
            accessors.append({"bufferView": nv, "componentType": 5126, "count": count, "type": "VEC3"})
            accessors.append({"bufferView": iv, "componentType": 5125 if big else 5123,
                              "count": len(tris), "type": "SCALAR"})
            primitives.append({"attributes": {"POSITION": len(accessors) - 3, "NORMAL": len(accessors) - 2},
                               "indices": len(accessors) - 1, "material": mat, "mode": 4})
        while len(binary) % 4:
            binary.append(0)
        manifest = {"asset": {"version": "2.0", "generator": self.generator},
                    "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
                    "meshes": [{"primitives": primitives}], "materials": self.materials,
                    "buffers": [{"byteLength": len(binary)}], "bufferViews": views,
                    "accessors": accessors}
        header = json.dumps(manifest, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        header += b" " * (-len(header) % 4)
        total = 12 + 8 + len(header) + 8 + len(binary)
        if total > MAX_BYTES:
            raise HoloHold("GLB_BYTE_BUDGET")
        return (struct.pack("<4sII", b"glTF", 2, total)
                + struct.pack("<I4s", len(header), b"JSON") + header
                + struct.pack("<I4s", len(binary), b"BIN\0") + bytes(binary))


def parse_glb(data: bytes) -> dict:
    """Structural readback used by tests and the app's pre-serve check."""
    if len(data) < 28:
        raise HoloHold("GLB_TRUNCATED")
    magic, version, total = struct.unpack("<4sII", data[:12])
    if magic != b"glTF" or version != 2 or total != len(data):
        raise HoloHold("GLB_HEADER_INVALID")
    jlen, jtype = struct.unpack("<I4s", data[12:20])
    if jtype != b"JSON":
        raise HoloHold("GLB_JSON_CHUNK_MISSING")
    manifest = json.loads(data[20:20 + jlen])
    blen, btype = struct.unpack("<I4s", data[20 + jlen:28 + jlen])
    if btype != b"BIN\0" or manifest["buffers"][0]["byteLength"] != blen:
        raise HoloHold("GLB_BIN_CHUNK_INVALID")
    for view in manifest["bufferViews"]:
        if view["byteOffset"] + view["byteLength"] > blen:
            raise HoloHold("GLB_VIEW_OUT_OF_RANGE")
    return manifest


# ----------------------------------------------------------------------
# Scene builders
# ----------------------------------------------------------------------

HOLO_CYAN = (0.33, 0.93, 1.0)
HOLO_GOLD = (1.0, 0.78, 0.33)
HOLO_CORAL = (1.0, 0.42, 0.45)
HOLO_VIOLET = (0.66, 0.55, 1.0)
HOLO_STEEL = (0.45, 0.58, 0.72)
RELATION_RGB = {"R1": HOLO_GOLD, "R2": HOLO_CYAN, "R3": HOLO_CORAL, "R4": HOLO_VIOLET}


def torus_knot_points(a: int, b: int, count: int = 480, R: float = 2.1, r: float = 0.78,
                      center=(0.0, 0.0, 0.0)):
    """T(a, b): winds a times around the core and b times through the hole."""
    cx, cy, cz = center
    pts = []
    for i in range(count + 1):
        t = 2 * math.pi * i / count
        rr = R + r * math.cos(a * t)
        pts.append((cx + rr * math.cos(b * t), cy + rr * math.sin(b * t), cz + r * math.sin(a * t)))
    return pts


def hjo_scene(a: int, b: int, gaps, covers, rows, profile) -> bytes:
    """Torus knot T(a,b) + gap-poset Hasse lattice + one cylindric partition."""
    s = Scene("szl.khipu.hjo-loom.glb/v1")
    knot = s.material("torus-knot-T(a,b)", HOLO_CYAN, glow=0.75, metallic=0.4, roughness=0.25)
    ring = s.material("torus-guide", HOLO_STEEL, glow=0.25, alpha=0.55)
    node = s.material("gap-node", HOLO_GOLD, glow=0.8)
    edge = s.material("cover-edge", HOLO_VIOLET, glow=0.6)
    cube = s.material("cylinder-cell", HOLO_CORAL, glow=0.45, roughness=0.5)
    axis = s.material("cylinder-axis", HOLO_STEEL, glow=0.3, alpha=0.6)
    s.tube(torus_knot_points(a, b, center=(-4.2, 0.0, 0.0)), 0.085, knot, 10)
    for k in range(0, 360, 30):
        th = math.radians(k)
        s.tube([(-4.2 + (2.1 + 0.78 * math.cos(u)) * math.cos(th), (2.1 + 0.78 * math.cos(u)) * math.sin(th),
                 0.78 * math.sin(u)) for u in [2 * math.pi * j / 32 for j in range(33)]],
               0.012, ring, 5)
    # Hasse diagram of the gap poset: height = gap value, spread by residue mod a.
    pos = {}
    fmax = max(gaps) if gaps else 1
    for g in gaps:
        lane = (g % a) - (a - 1) / 2
        pos[g] = (lane * 0.62, -2.4 + 4.8 * g / max(1, fmax), 0.0)
        s.sphere(pos[g], 0.16, node)
    for g, h in covers:
        s.tube([pos[g], pos[h]], 0.025, edge, 6)
    # Cylindric partition: row i wraps at angle 2*pi*i/a, columns along the axis
    # shifted by the profile, cell height = entry (stacked cubes).
    cx = 4.6
    s.tube([(cx, -3.0, 0.0), (cx, 3.0, 0.0)], 0.035, axis, 8)
    offset = 0
    for i, row in enumerate(rows):
        th = 2 * math.pi * i / max(1, len(rows))
        for j, val in enumerate(row[:14]):
            y = -2.6 + 0.42 * (j + offset)
            for k in range(min(int(val), 8)):
                rad = 0.7 + 0.36 * k
                s.box((cx + rad * math.cos(th), y, rad * math.sin(th)), (0.32, 0.36, 0.32), cube)
        offset += profile[i] if i < len(profile) else 0
    return s.glb()


def khipu_scene(prims: dict, *, show_relations: bool = True) -> bytes:
    """Render OKR-derived primitives (positions, recorded colours, knot types)."""
    s = Scene("szl.khipu.okr-twin.glb/v1")
    mats: dict[tuple, int] = {}

    def mat_for(rgb, role):
        key = (tuple(round(float(c), 3) for c in rgb), role)
        if key not in mats:
            glow = 0.55 if role == "primary" else 0.32
            mats[key] = s.material(f"cord-{role}", key[0], glow=glow, roughness=0.6, metallic=0.1)
        return mats[key]

    for t in prims.get("tubes", []):
        r = {"primary": 0.07, "top": 0.03, "pendant": 0.026, "subsidiary": 0.02}.get(t.get("role"), 0.022)
        s.tube(t["points"], float(t.get("radius") or r), mat_for(t.get("rgb") or HOLO_STEEL, t.get("role", "cord")), 6)
    knot_mats = {
        "S": s.material("knot-single", (0.95, 0.95, 1.0), glow=0.9),
        "L": s.material("knot-long", HOLO_GOLD, glow=0.85),
        "E": s.material("knot-figure-eight", HOLO_CORAL, glow=0.85),
        "?": s.material("knot-other", HOLO_VIOLET, glow=0.7),
    }
    for k in prims.get("knots", []):
        kind = str(k.get("type") or "?")[:1]
        m = knot_mats.get(kind, knot_mats["?"])
        x, y, z = k["pos"]
        if kind == "L":
            turns = int(k.get("turns") or 2)
            length = 0.05 + 0.025 * min(turns, 9)
            s.tube([(x, y + length / 2, z), (x, y - length / 2, z)], 0.045, m, 8)
        elif kind == "E":
            s.sphere((x, y + 0.03, z), 0.04, m, 4, 8)
            s.sphere((x, y - 0.03, z), 0.04, m, 4, 8)
        else:
            s.sphere((x, y, z), 0.045, m, 4, 8)
    if show_relations:
        for arc in prims.get("arcs", []):
            rgb = RELATION_RGB.get(arc.get("relation"), HOLO_VIOLET)
            s.tube(arc["points"], 0.014, s.material(f"relation-{arc.get('relation')}", rgb, glow=1.0), 5)
    return s.glb()
