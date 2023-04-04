r"""
This sub-package provides implements the PQ-NET framework that is used to implement the programmable
NET layer of ProgReSS. See :mod:`progress.pqnet.repository` for some ready-to-use modules that can be used
in custom DAGs.
"""

from progress.pqnet.dag import DAGFactory
from progress.pqnet.p_module import ModuleBehavior, ProcessingModuleBehavior, SchedulingModuleBehavior

_all_ = ["DAGFactory", "ModuleBehavior", "ProcessingModuleBehavior", "SchedulingModuleBehavior"]
