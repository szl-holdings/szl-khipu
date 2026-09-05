"""KHIPU-X1 FPGA-first accelerator software reference.

The package provides deterministic CPU reference behavior, graph lowering,
package verification and an RC1 authorization emulator. It is not FPGA or ASIC
execution and it makes no performance, energy or physical-outcome claim.
"""

from .graph import (
    BufferSpec,
    GraphNode,
    GraphPlan,
    GraphValidationError,
    LoweringResult,
    lower_graph,
)
from .kids import Descriptor, KhipuValidationError, Opcode
from .package import KhipuPackageError, PackageReport, build_package, verify_package
from .rc1 import (
    AuthorizationDecision,
    AuthorizationEnvelope,
    RC1Emulator,
    RC1Mode,
    descriptor_stream_digest,
    issue_hmac_authorization,
)
from .receipt import ReceiptChain
from .simulator import ExecutionResult, KhipuExecutionError, KhipuSimulator, array_commitment
from .source_lock import SourceLockError, load_source_lock, validate_source_lock

__all__ = [
    "AuthorizationDecision",
    "AuthorizationEnvelope",
    "BufferSpec",
    "Descriptor",
    "ExecutionResult",
    "GraphNode",
    "GraphPlan",
    "GraphValidationError",
    "KhipuExecutionError",
    "KhipuPackageError",
    "KhipuSimulator",
    "KhipuValidationError",
    "LoweringResult",
    "Opcode",
    "PackageReport",
    "RC1Emulator",
    "RC1Mode",
    "ReceiptChain",
    "SourceLockError",
    "array_commitment",
    "build_package",
    "descriptor_stream_digest",
    "issue_hmac_authorization",
    "load_source_lock",
    "lower_graph",
    "validate_source_lock",
    "verify_package",
]
