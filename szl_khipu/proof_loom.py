"""Pure Python, bounded GLB proof-loom research scene and exact finite witness.

No web, model, history, native code, GPU or serializer dependencies. Viewer is
Gradio's built-in Model3D, which necessarily renders 3-D in the browser.
These are MODERN mathematical illustrations, not archaeological transcriptions.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

SCHEMA = "szl.khipu.proof-loom/v1"
MAX_N = 128
CURVES = ((2, 3), (3, 4), (3, 5), (3, 7))
_LOCK = threading.Lock()
_OUTPUT_DIR: Path | None = None
# Retain the handle for process-lifetime use; TemporaryDirectory removes files
# on normal interpreter shutdown. Gradio handles request-cache expiry separately.
_OUTPUT_TEMP: tempfile.TemporaryDirectory[str] | None = None


class EvidenceHold(ValueError):
    """Fail-closed input or identity mismatch."""


def _inputs(n: int, identity: str, curve: tuple[int, int]):
    if type(n) is not int or not 0 <= n <= MAX_N:
        raise EvidenceHold("FINITE_BOUND_INVALID")
    if identity not in ("RR1", "RR2"):
        raise EvidenceHold("IDENTITY_INVALID")
    if type(curve) is not tuple or curve not in CURVES:
        raise EvidenceHold("CURVE_NOT_PRESET")


@lru_cache(maxsize=None)
def _gap(n: int, smallest: int) -> int:
    if n == 0:
        return 1
    if n < smallest:
        return 0
    return _gap(n, smallest + 1) + _gap(n - smallest, smallest + 2)


def _residue(n: int, residues: tuple[int, int]) -> int:
    ways = [1] + [0] * n
    for k in range(1, n + 1):
        if k % 5 in residues:
            for j in range(k, n + 1):
                ways[j] += ways[j - k]
    return ways[-1]


def witness(n: int = 18, identity: str = "RR1", curve: tuple[int, int] = (2, 3)) -> dict:
    _inputs(n, identity, curve)
    minimum, residues = (1, (1, 4)) if identity == "RR1" else (2, (2, 3))
    gap, modular = _gap(n, minimum), _residue(n, residues)
    if gap != modular:
        raise EvidenceHold("FINITE_IDENTITY_MISMATCH")
    digits = [[exp, int(d)] for exp, d in enumerate(str(gap)[::-1]) if d != "0"]
    record = {
        "schema": SCHEMA,
        "identity": identity,
        "n": n,
        "gap_count": gap,
        "residue_count": modular,
        "residue_classes_mod_5": list(residues),
        "digital_cord": {"present": True, "place_values": digits[::-1]},
        "curve_preset": list(curve),
        "curve_semantics": "TORUS_KNOT_GEOMETRY_ILLUSTRATION_ONLY",
        "historical_claim": "NOT_ESTABLISHED",
        "infinite_identity_proved_here": False,
        "external_hjo_lean_replayed": False,
        "trained_model_used": False,
        "model_qualification": "NOT_ASSESSED",
        "signature_verified": False,
        "source": "https://github.com/AxiomMath/HJO",
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return {**record, "sha256": hashlib.sha256(b"szl-khipu-proofloom-v1\0" + raw).hexdigest()}


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def _unit(a):
    d = math.sqrt(sum(v*v for v in a))
    if d <= 1e-12:
        raise EvidenceHold("DEGENERATE_GEOMETRY")
    return tuple(v/d for v in a)


class _Mesh:
    def __init__(self):
        self.groups = {}  # material -> vertices, normals, triangles

    def tube(self, points: list[tuple[float, float, float]], radius: float, material: int, sides: int = 8):
        if not 0 < radius <= .2 or not 3 <= sides <= 16 or len(points) < 2:
            raise EvidenceHold("GEOMETRY_LIMIT")
        verts, normals, triangles = self.groups.setdefault(material, ([], [], []))
        start = len(verts)
        for i, center in enumerate(points):
            edge = tuple(points[min(i+1, len(points)-1)][k] - points[max(i-1, 0)][k] for k in range(3))
            tangent = _unit(edge)
            ref = (0., 1., 0.) if abs(tangent[2]) > .9 else (0., 0., 1.)
            u = _unit(_cross(tangent, ref))
            v = _cross(tangent, u)
            for j in range(sides):
                t = 2*math.pi*j/sides
                normal = tuple(math.cos(t)*u[k]+math.sin(t)*v[k] for k in range(3))
                verts.append(tuple(center[k]+radius*normal[k] for k in range(3)))
                normals.append(normal)
        for i in range(len(points)-1):
            for j in range(sides):
                a = start+i*sides+j
                b = start+i*sides+(j+1)%sides
                c = start+(i+1)*sides+j
                d = start+(i+1)*sides+(j+1)%sides
                triangles.extend((a, c, b, b, c, d))


def _curve_points(a: int, b: int, count: int = 352):
    # The (a,b) torus-knot link is a geometric research illustration.
    result = []
    for i in range(count + 1):
        t = 2*math.pi*i/count
        ring = 1.16 + .41*math.cos(b*t)
        result.append((-3.25 + ring*math.cos(a*t), .08 + ring*math.sin(a*t), .41*math.sin(b*t)))
    return result


def _scene(record: dict) -> _Mesh:
    a, b = record["curve_preset"]
    mesh = _Mesh()
    mesh.tube(_curve_points(a, b), .063, 0, 10)
    # Clear spatial partition prevents implying a historic knot == torus knot.
    mesh.tube([(0, -1.95, -1.6), (0, 1.96, -1.6)], .018, 3, 6)
    mesh.tube([(1.0, 1.48, 0), (5.18, 1.48, 0)], .06, 1)
    mesh.tube([(1.0, 1.42, 0), (1.0, 1.6, 0)], .07, 1)
    mesh.tube([(5.18, 1.42, 0), (5.18, 1.6, 0)], .07, 1)
    digits = record["digital_cord"]["place_values"]
    # At least one strand for zero; zero is a recorded value, not missing.
    if not digits:
        digits = [[0, 0]]
    if len(digits) > 10:
        raise EvidenceHold("DIGIT_BUDGET")
    for idx, (exp, digit) in enumerate(digits):
        x = 1.32 + idx*.45
        end = -1.32
        mesh.tube([(x, 1.44, 0), (x, end, .0)], .026, 1)
        # Each knot on a digital strand counts one unit of that decimal digit.
        for knot in range(digit):
            y = .98 - knot*.19
            mesh.tube([
                (x+.12*math.cos(t), y+.063*math.sin(t), .06*math.sin(2*t))
                for t in [2*math.pi*k/48 for k in range(49)]
            ], .024, 2, 7)
        # One place marker per position, regardless of whether value is zero.
        mesh.tube([(x-.08, -1.34, 0), (x+.08, -1.34, 0)], .034, 3, 6)
    # Reference rings and research-only ornament, independent of counted knots.
    for radius in (1.67, 1.84):
        mesh.tube([(-3.25+radius*math.cos(i*2*math.pi/96),
                    .08+radius*math.sin(i*2*math.pi/96), -1.15)
                   for i in range(97)], .013, 3, 5)
    return mesh


def _make_glb(mesh: _Mesh) -> bytes:
    """Generate standards-compliant GLB 2.0 with indexed normals and PBR materials."""
    binary = bytearray()
    views, accessors, primitives = [], [], []
    materials = [
        {"name": "math-torus-cyan", "pbrMetallicRoughness": {"baseColorFactor": [.08,.86,1,1], "metallicFactor": .35, "roughnessFactor": .31}, "emissiveFactor": [.03,.41,.56], "doubleSided": True},
        {"name": "modern-cord-gold", "pbrMetallicRoughness": {"baseColorFactor": [.98,.69,.25,1], "metallicFactor": .31, "roughnessFactor": .46}, "emissiveFactor": [.28,.13,.02], "doubleSided": True},
        {"name": "decimal-knot-coral", "pbrMetallicRoughness": {"baseColorFactor": [1,.27,.38,1], "metallicFactor": .11, "roughnessFactor": .38}, "emissiveFactor": [.32,.04,.08], "doubleSided": True},
        {"name": "separator-silver", "pbrMetallicRoughness": {"baseColorFactor": [.37,.5,.65,1], "metallicFactor": .32, "roughnessFactor": .45}, "emissiveFactor": [.07,.11,.16], "doubleSided": True},
    ]

    def add_view(data: bytes, target: int):
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(data)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        return len(views)-1

    for material, (vertices, normals, indices) in sorted(mesh.groups.items()):
        if len(vertices) > 65000 or not indices or max(indices) >= len(vertices):
            raise EvidenceHold("MESH_BUDGET")
        pos = [x for point in vertices for x in point]
        normal = [x for point in normals for x in point]
        if not all(math.isfinite(x) for x in pos+normal):
            raise EvidenceHold("NONFINITE_MESH")
        pv = add_view(struct.pack('<'+'f'*len(pos), *pos), 34962)
        nv = add_view(struct.pack('<'+'f'*len(normal), *normal), 34962)
        iv = add_view(struct.pack('<'+'H'*len(indices), *indices), 34963)
        accessors.append({"bufferView": pv, "componentType": 5126, "count": len(vertices), "type": "VEC3", "min": [min(v[k] for v in vertices) for k in range(3)], "max": [max(v[k] for v in vertices) for k in range(3)]})
        position_idx = len(accessors)-1
        accessors.append({"bufferView": nv, "componentType": 5126, "count": len(vertices), "type": "VEC3"})
        normals_idx = len(accessors)-1
        accessors.append({"bufferView": iv, "componentType": 5123, "count": len(indices), "type": "SCALAR"})
        indices_idx = len(accessors)-1
        primitives.append({"attributes": {"POSITION": position_idx, "NORMAL": normals_idx}, "indices": indices_idx, "material": material, "mode": 4})
    while len(binary)%4:
        binary.append(0)
    manifest = {"asset": {"version": "2.0", "generator": SCHEMA},
                "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
                "meshes": [{"primitives": primitives}], "materials": materials,
                "buffers": [{"byteLength": len(binary)}], "bufferViews": views,
                "accessors": accessors}
    header = json.dumps(manifest, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    header += b' ' * (-len(header)%4)
    total = 12 + 8 + len(header) + 8 + len(binary)
    if total > 3_000_000:
        raise EvidenceHold("GLB_BYTE_BUDGET")
    return struct.pack('<4sII', b'glTF', 2, total) + struct.pack('<I4s', len(header), b'JSON') + header + struct.pack('<I4s', len(binary), b'BIN\0') + bytes(binary)


def _directory() -> Path:
    global _OUTPUT_DIR, _OUTPUT_TEMP
    if _OUTPUT_DIR is None:
        _OUTPUT_TEMP = tempfile.TemporaryDirectory(prefix="szl-proof-loom-")
        _OUTPUT_DIR = Path(_OUTPUT_TEMP.name)
    return _OUTPUT_DIR


@lru_cache(maxsize=48)
def _render_cached(n: int, identity: str, curve: tuple[int, int]) -> tuple[str, dict]:
    record = witness(n, identity, curve)
    glb = _make_glb(_scene(record))
    filename = "proof-loom-" + record["sha256"][:20] + ".glb"
    root = _directory()
    dest = root / filename
    if dest.exists():
        if dest.read_bytes() != glb:
            raise EvidenceHold("RENDER_FILE_CONFLICT")
    else:
        temp = root / (filename + ".tmp")
        with temp.open('xb') as stream:
            stream.write(glb)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, dest)
    return str(dest), record, hashlib.sha256(glb).hexdigest()


def render(n: int = 18, identity: str = "RR1", curve: tuple[int, int] = (2, 3)) -> tuple[str, dict]:
    """Thread-safe bounded scene render; only ephemeral locally generated GLB files."""
    _inputs(n, identity, curve)
    with _LOCK:
        path, record, expected_hash = _render_cached(n, identity, curve)
        target = Path(path)
        if target.is_symlink() or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
            raise EvidenceHold("RENDER_READBACK_MISMATCH")
        return path, record


def panel(n: int = 18, identity: str = "RR1", curve: str = "2,3") -> tuple[str, str]:
    import html
    presets = {f"{a},{b}": (a, b) for a, b in CURVES}
    if curve not in presets:
        raise EvidenceHold("CURVE_NOT_PRESET")
    if type(n) is float and math.isfinite(n) and n.is_integer():
        n = int(n)
    file, record = render(n, identity, presets[curve])
    digest = html.escape(record['sha256'])
    count = record['gap_count']
    return (file,
        f'<div class="receipt"><b>FINITE MATCH</b> · {record["identity"]} · '
        f'n={n} · {count:,} partitions · check {digest[:16]}…</div>'
        '<p><b>Left:</b> mathematical torus-knot geometry. '
        '<b>Right:</b> a modern decimal cord diagram. '
        'The scene does not reconstruct archaeological khipus or prove the infinite identity. '
        'Model quality, signer, and HJO Lean replay: <b>NOT ASSESSED</b>.</p>'
        '<p><a href="https://github.com/AxiomMath/HJO" target="_blank" rel="noopener">'
        'External mathematical proof</a> · '
        '<a href="https://github.com/khipulab/open-khipu-repository" target="_blank" rel="noopener">'
        'Historical source archive</a></p>')
