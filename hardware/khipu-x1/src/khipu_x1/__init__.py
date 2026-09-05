"""KHIPU-X1 wave-1 software reference.

This package is a deterministic CPU reference for the draft KIDS v0.1
contract. It is not FPGA execution and it makes no performance claim.
"""

from .kids import Descriptor, KhipuValidationError, Opcode
from .receipt import ReceiptChain
from .simulator import ExecutionResult, KhipuExecutionError, KhipuSimulator, array_commitment

__all__ = [
    "Descriptor",
    "ExecutionResult",
    "KhipuExecutionError",
    "KhipuSimulator",
    "KhipuValidationError",
    "Opcode",
    "ReceiptChain",
    "array_commitment",
]
