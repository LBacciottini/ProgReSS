"""This module implements a Connection with a source in the middle
used to enable Midpoint source protocol between two nodes.
"""

from netsquid.components import QuantumChannel, FibreDelayModel, ClassicalChannel
from netsquid.nodes import Connection

__all__ = ["MPSConnection"]

from progress.hardware.ep_source import MPSSourceNode


class MPSConnection(Connection):
    r"""A quantum connection using a :class:`~qi_simulation.mps.components.ep_source.MPSSourceNode` in the middle.
    It implements a high level simulation of the Midpoint source link layer protocols between the two nodes at the
    edges of this connection. The qubits received through this connection are ready-to-use entangled pairs.

    The entangled pairs are in Bell state :math:`\vert \beta_{00}\rangle` and the source is placed in the middle.
    Two fiber channels connect the source output ports to A and B.

    Parameters
    ----------
    name : str
        The name of this connection
    length : int, float
        The total length of the connection. Each fiber channel is ``length/2`` long.
    p_left : float
        The probability of successfully latching the emitted qubit on the left with the components on that side.
        It should keep into account the loss probability on the link and the probability of failure at the components,
        which is due to frequency conversion and partial BSA in the case of standard MS,
        or due to imperfect nDPD and absorption in the case of AFC-enhanced MS.
    p_right : float, optional
        The probability of successfully latching the emitted qubit on the right with the components on that side.
        If ``None``, it is set equal to ``p_left``. Defaults to ``None``.
    p_mid : float, optional
        The probability that the midpoint entangled pair source successfully emits a pair at a given clock cycle.
        Defaults to 1.
    num_positions : int, optional
        The number of modes of the repeaters' quantum memories attached to the link. Defaults to 1.
    t_clock : int or float, optional
        The clock period of the MS protocols. Defaults to 1. [ns]
    """
    def __init__(self, name, length, p_left, p_right=None, p_mid=1., num_positions=1, t_clock=1):
        super().__init__(name)

        models = {"delay_model": FibreDelayModel()}

        qchannel_a = QuantumChannel("QChannelA", models=models, length=length/2)
        qchannel_b = QuantumChannel("QChannelB", models=models, length=length/2)

        cchannel_a = ClassicalChannel("CChannelA", length=0, models=models)
        cchannel_b = ClassicalChannel("CChannelB", length=0, models=models)

        qsource = MPSSourceNode(f"{name}_src", p_left, p_right, num_positions, p_mid, t_clock)
        self.add_subcomponent(qchannel_a)
        self.add_subcomponent(qchannel_b)
        self.add_subcomponent(cchannel_a)
        self.add_subcomponent(cchannel_b)
        self.add_subcomponent(qsource, "qsource")
        qchannel_a.ports["recv"].forward_output(self.port_A)
        qchannel_b.ports["recv"].forward_output(self.port_B)
        self.port_A.forward_input(cchannel_a.ports["send"])
        self.port_B.forward_input(cchannel_b.ports["send"])
        qsource.ports["c0"].connect(cchannel_a.ports["recv"])
        qsource.ports["c1"].connect(cchannel_b.ports["recv"])
        qsource.ports["qout0"].connect(qchannel_a.ports["send"])
        qsource.ports["qout1"].connect(qchannel_b.ports["send"])

    def start(self):
        """
        Sets the status of the inner source to INTERNAL so that it starts producing entanglement.
        """
        self.subcomponents["qsource"].start()

    def stop(self):
        """
        Sets the status of the inner source to OFF so that it stops producing entanglement.
        """
        self.subcomponents["qsource"].stop()

    def reset(self, and_restart=True):
        """
        Reset the status of the inner source. Should be called while the inner source is OFF.

        Parameters
        ----------
        and_restart : bool, optional
            If True, also restarts the inner source, i.e. it sets its status to INTERNAL. Defaults to True.
        """
        self.subcomponents["qsource"].reset(and_restart=and_restart)
