"""
This sub-package contains an implementation of the Quantum Hardware Abstraction Layer (QHAL),
which is the level that standardizes the interface between the quantum hardware and the NET level.
"""

from progress.abstraction.qhal import QHAL

__all__ = ["QHAL"]