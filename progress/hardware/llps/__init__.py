"""
This package contains an abstract class for Link Layer Protocols that can be instantiated to create custom protocols.
It also provides a ready-to-use protocol called :class:`~progress.llps.mps.MPSProtocol`
which is the default protocol used by quantum network devices.
"""

from progress.hardware.llps.llp import LinkProtocol
from progress.hardware.llps.mps import MPSProtocol

__all__ = ["LinkProtocol", "MPSProtocol"]
