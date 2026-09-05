"""Small deterministic graph IR and KIDS v0.1 lowering.

The compiler surface is intentionally narrow. It proves descriptor generation,
shape/dtype validation and stable graph commitments; it is not an optimizing
compiler and it does not claim FPGA execution.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .kids import Descriptor, KhipuValidationError, Opcode, canonical_json_bytes

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_ALLOWED_DTYPES = {"int8", "int32", "float16", "float32", "float64"}
_LOWERABLE_OPS = {
    Opcode.NOP,
    Opcode.GEMM_INT8,
    Opcode.RMSNORM,
    Opcode.SHA3_COMMIT,
    Opcode.BARRIER,
}


class GraphValidationError(ValueError):
    """Raised when a graph cannot be lowered without ambiguity."""


@dataclass(frozen=True)
class BufferSpec:
    name: str
    shape: tuple[int, ...]
    dtype: str

    def validate(self) -> None:
        if not _NAME.fullmatch(self.name):
            raise GraphValidationError(f"invalid buffer name: {self.name!r}")
        if not self.shape or any(not isinstance(dim, int) or dim <= 0 for dim in self.shape):
            raise GraphValidationError(f"buffer {self.name} has an invalid shape")
        if self.dtype not in _ALLOWED_DTYPES:
            raise GraphValidationError(f"buffer {self.name} has unsupported dtype {self.dtype}")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {"name": self.name, "shape": list(self.shape), "dtype": self.dtype}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BufferSpec":
        try:
            spec = cls(
                name=str(value["name"]),
                shape=tuple(int(dim) for dim in value["shape"]),
                dtype=str(value["dtype"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GraphValidationError(f"invalid buffer declaration: {exc}") from exc
        spec.validate()
        return spec


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    opcode: Opcode
    inputs: tuple[str, ...] = field(default_factory=tuple)
    output: str | None = None
    attrs: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _NAME.fullmatch(self.node_id):
            raise GraphValidationError(f"invalid node id: {self.node_id!r}")
        for name in self.inputs:
            if not _NAME.fullmatch(name):
                raise GraphValidationError(f"node {self.node_id} has invalid input name")
        if self.output is not None and not _NAME.fullmatch(self.output):
            raise GraphValidationError(f"node {self.node_id} has invalid output name")
        try:
            canonical_json_bytes(dict(self.attrs))
        except (TypeError, ValueError, KhipuValidationError) as exc:
            raise GraphValidationError(f"node {self.node_id} has invalid attrs: {exc}") from exc

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.node_id,
            "op": self.opcode.value,
            "inputs": list(self.inputs),
            "output": self.output,
            "attrs": dict(self.attrs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GraphNode":
        try:
            node = cls(
                node_id=str(value["id"]),
                opcode=Opcode(str(value["op"])),
                inputs=tuple(str(name) for name in value.get("inputs", [])),
                output=None if value.get("output") is None else str(value["output"]),
                attrs=dict(value.get("attrs", {})),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GraphValidationError(f"invalid graph node: {exc}") from exc
        node.validate()
        return node


@dataclass(frozen=True)
class GraphPlan:
    name: str
    inputs: tuple[BufferSpec, ...]
    nodes: tuple[GraphNode, ...]
    outputs: tuple[str, ...]
    version: str = "0.1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "inputs": [spec.as_dict() for spec in self.inputs],
            "nodes": [node.as_dict() for node in self.nodes],
            "outputs": list(self.outputs),
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.as_dict())).hexdigest()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GraphPlan":
        try:
            plan = cls(
                version=str(value.get("version", "0.1")),
                name=str(value["name"]),
                inputs=tuple(BufferSpec.from_dict(item) for item in value.get("inputs", [])),
                nodes=tuple(GraphNode.from_dict(item) for item in value.get("nodes", [])),
                outputs=tuple(str(name) for name in value.get("outputs", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GraphValidationError(f"invalid graph: {exc}") from exc
        if plan.version != "0.1":
            raise GraphValidationError(f"unsupported graph version: {plan.version}")
        if not _NAME.fullmatch(plan.name):
            raise GraphValidationError(f"invalid graph name: {plan.name!r}")
        if not plan.nodes:
            raise GraphValidationError("graph must contain at least one node")
        return plan


@dataclass(frozen=True)
class LoweringResult:
    graph_digest: str
    descriptors: tuple[Descriptor, ...]
    buffers: Mapping[str, BufferSpec]

    def as_dict(self) -> dict[str, Any]:
        return {
            "graph_digest": self.graph_digest,
            "descriptors": [descriptor.as_dict() for descriptor in self.descriptors],
            "buffers": {
                name: spec.as_dict() for name, spec in sorted(self.buffers.items())
            },
        }


def _infer_node(node: GraphNode, buffers: Mapping[str, BufferSpec]) -> BufferSpec | None:
    missing = [name for name in node.inputs if name not in buffers]
    if missing:
        raise GraphValidationError(f"node {node.node_id} references undefined inputs: {missing}")

    if node.opcode is Opcode.GEMM_INT8:
        if len(node.inputs) != 2 or node.output is None:
            raise GraphValidationError(f"node {node.node_id}: GEMM_INT8 requires 2 inputs/output")
        left, right = (buffers[name] for name in node.inputs)
        if left.dtype != "int8" or right.dtype != "int8":
            raise GraphValidationError(f"node {node.node_id}: GEMM_INT8 inputs must be int8")
        if len(left.shape) < 2 or len(right.shape) != 2 or left.shape[-1] != right.shape[0]:
            raise GraphValidationError(f"node {node.node_id}: GEMM_INT8 shape mismatch")
        out_dtype = "float32" if "scale" in node.attrs else "int32"
        return BufferSpec(node.output, left.shape[:-1] + (right.shape[1],), out_dtype)

    if node.opcode is Opcode.RMSNORM:
        if len(node.inputs) not in {1, 2} or node.output is None:
            raise GraphValidationError(f"node {node.node_id}: RMSNORM requires data, optional weight, output")
        data = buffers[node.inputs[0]]
        if data.dtype not in {"float16", "float32", "float64", "int32"}:
            raise GraphValidationError(f"node {node.node_id}: RMSNORM data dtype unsupported")
        if len(node.inputs) == 2:
            weight = buffers[node.inputs[1]]
            if len(weight.shape) != 1 or weight.shape[0] != data.shape[-1]:
                raise GraphValidationError(f"node {node.node_id}: RMSNORM weight shape mismatch")
            if weight.dtype not in {"float16", "float32", "float64"}:
                raise GraphValidationError(f"node {node.node_id}: RMSNORM weight must be floating point")
        eps = float(node.attrs.get("eps", 1e-6))
        if not (eps > 0.0):
            raise GraphValidationError(f"node {node.node_id}: eps must be positive")
        return BufferSpec(node.output, data.shape, "float32")

    if node.opcode is Opcode.SHA3_COMMIT:
        if len(node.inputs) != 1 or node.output is not None:
            raise GraphValidationError(f"node {node.node_id}: SHA3_COMMIT takes 1 input and no output")
        return None

    if node.opcode in {Opcode.NOP, Opcode.BARRIER}:
        if node.inputs or node.output is not None:
            raise GraphValidationError(f"node {node.node_id}: {node.opcode.value} takes no buffers")
        return None

    raise GraphValidationError(f"node {node.node_id}: opcode {node.opcode.value} is not lowerable")


def lower_graph(
    plan: GraphPlan,
    *,
    model_digest: str,
    policy_digest: str,
    start_sequence: int = 1,
    start_nonce: int = 1,
) -> LoweringResult:
    if plan.version != "0.1":
        raise GraphValidationError(f"unsupported graph version: {plan.version}")
    if not _NAME.fullmatch(plan.name):
        raise GraphValidationError(f"invalid graph name: {plan.name!r}")
    if not plan.nodes:
        raise GraphValidationError("graph must contain at least one node")
    if any(not _NAME.fullmatch(name) for name in plan.outputs):
        raise GraphValidationError("graph output names must be bounded identifiers")
    if start_sequence < 0 or start_nonce < 0:
        raise GraphValidationError("sequence and nonce starts must be non-negative")

    buffers: dict[str, BufferSpec] = {}
    for spec in plan.inputs:
        spec.validate()
        if spec.name in buffers:
            raise GraphValidationError(f"duplicate input buffer: {spec.name}")
        buffers[spec.name] = spec

    seen_nodes: set[str] = set()
    descriptors: list[Descriptor] = []
    for offset, node in enumerate(plan.nodes):
        node.validate()
        if node.node_id in seen_nodes:
            raise GraphValidationError(f"duplicate node id: {node.node_id}")
        seen_nodes.add(node.node_id)
        if node.opcode not in _LOWERABLE_OPS:
            raise GraphValidationError(f"node {node.node_id}: opcode is reserved or unsupported")
        if node.output is not None and node.output in buffers:
            raise GraphValidationError(f"node {node.node_id}: output {node.output} already exists")
        inferred = _infer_node(node, buffers)
        if inferred is not None:
            inferred.validate()
            buffers[inferred.name] = inferred
        descriptor = Descriptor(
            sequence=start_sequence + offset,
            nonce=start_nonce + offset,
            opcode=node.opcode,
            model_digest=model_digest,
            policy_digest=policy_digest,
            inputs=node.inputs,
            output=node.output,
            attrs={**dict(node.attrs), "graph_node_id": node.node_id, "graph_digest": plan.digest},
        )
        descriptor.validate()
        descriptors.append(descriptor)

    if not plan.outputs:
        raise GraphValidationError("graph must declare at least one output")
    missing_outputs = [name for name in plan.outputs if name not in buffers]
    if missing_outputs:
        raise GraphValidationError(f"graph declares undefined outputs: {missing_outputs}")

    return LoweringResult(plan.digest, tuple(descriptors), dict(buffers))
