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
from .quantization import (
    Int8QuantizedTensor,
    QuantizationError,
    dequantize_symmetric_int8,
    quantize_symmetric_int8,
    tensor_sha256,
)
from .rc1 import (
    AuthorizationDecision,
    AuthorizationEnvelope,
    RC1Emulator,
    RC1Mode,
    descriptor_stream_digest,
    issue_hmac_authorization,
)
from .receipt import ReceiptChain
from .safetensors_inventory import (
    ModelWeightInventory,
    SafetensorsFileInventory,
    SafetensorsInventoryError,
    TensorInventory,
    compare_inventory_to_spec,
    inventory_local_model,
    inventory_safetensors_file,
    inventory_sharded_model,
)
from .simulator import ExecutionResult, KhipuExecutionError, KhipuSimulator, array_commitment
from .source_lock import SourceLockError, load_source_lock, validate_source_lock
from .transformer import (
    TargetBudget,
    TransformerImportError,
    TransformerReadinessReport,
    TransformerSpec,
    assess_target_budget,
    build_projection_probe_graph,
    inspect_transformer_config,
)
from .wire import (
    BATCH_HEADER_SIZE,
    DESCRIPTOR_SIZE,
    WireBatch,
    WireDescriptor,
    WireFlags,
    WireFormatError,
    WireOpcode,
    decode_batch,
    decode_descriptor,
    encode_batch,
    encode_descriptor,
    opcode_code,
)

__all__ = [
    "BATCH_HEADER_SIZE",
    "AuthorizationDecision",
    "AuthorizationEnvelope",
    "BufferSpec",
    "DESCRIPTOR_SIZE",
    "Descriptor",
    "ExecutionResult",
    "GraphNode",
    "GraphPlan",
    "GraphValidationError",
    "Int8QuantizedTensor",
    "KhipuExecutionError",
    "KhipuPackageError",
    "KhipuSimulator",
    "KhipuValidationError",
    "LoweringResult",
    "ModelWeightInventory",
    "Opcode",
    "PackageReport",
    "QuantizationError",
    "RC1Emulator",
    "RC1Mode",
    "ReceiptChain",
    "SafetensorsFileInventory",
    "SafetensorsInventoryError",
    "SourceLockError",
    "TargetBudget",
    "TensorInventory",
    "TransformerImportError",
    "TransformerReadinessReport",
    "TransformerSpec",
    "WireBatch",
    "WireDescriptor",
    "WireFlags",
    "WireFormatError",
    "WireOpcode",
    "array_commitment",
    "assess_target_budget",
    "build_package",
    "build_projection_probe_graph",
    "compare_inventory_to_spec",
    "decode_batch",
    "decode_descriptor",
    "dequantize_symmetric_int8",
    "descriptor_stream_digest",
    "encode_batch",
    "encode_descriptor",
    "inspect_transformer_config",
    "inventory_local_model",
    "inventory_safetensors_file",
    "inventory_sharded_model",
    "issue_hmac_authorization",
    "load_source_lock",
    "opcode_code",
    "quantize_symmetric_int8",
    "lower_graph",
    "tensor_sha256",
    "validate_source_lock",
    "verify_package",
]
