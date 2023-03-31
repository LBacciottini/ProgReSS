"""
This package models the Physical layer of the quantum network: the hardware, the links, the qubits, the qnic, etc.
It also models the quantum Link Layer protocols to be installed on each qnic of the devices.
"""

from progress.hardware.mps_connection import MPSConnection
from progress.hardware.qhardware import QHardware

__all__ = ["MPSConnection", "QHardware"]


