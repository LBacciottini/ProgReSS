r"""
This module contains an abstract class for a generic link protocol in our architecture. The class sums up the
core services that a link layer protocol must provide to the :class:`~progress.components.stack_engine.StackEngine`
and to the upper layers in general.
"""

from abc import ABC, abstractmethod
from collections import namedtuple

import netsquid as ns
from netsquid.protocols.serviceprotocol import ServiceProtocol


__all__ = ['LinkProtocol']

from progress.sockets import Socket


class LinkProtocol(ABC, ServiceProtocol):
    r"""
    This class is an abstract class for a generic link protocol in our architecture. The class sums up the core
    services that a link layer protocol must provide to the QHAL and to net in general.
    When a new entangled pair is generated, the link protocol signals the event to the QHAL, which will handle the new
    resource.
    Each link protocol usually depends on the hardware it is running on, also involving the connection to the other
    node (e.g. BMS connection, EPS in the middle, etc.).

    Parameters
    ----------
    qnic : str
        The port name on which the protocol will run.
    num_positions : int
        The number of qubits available for the link layer protocol.
    node : :class:`~progress.repeater.Repeater` or None, optional
        The node on which this protocols will run. If `None`, it must be set before starting the protocol and the
        link layer protocol must be manually subscribed to the node through the method
        :meth:`~progress.repeater.Repeater.subscribe_link_protocol`.
    other_node_info : tuple or None, optional
        A two-elements tuple where the first is the neighbor node id (int), and the second is the name of its attached
        interface (str). This info is used to generate a :class:`~progress.sockets.Token` from each
        qubit. If `None`, it must be set before the protocol is started.
    name : str, optional
        The name of the instance, defaults to the class name.

    Notes
    ------
    Link protocols also act as a service to the physical service. It supports three request types:

    1. :class:`~progress.mps.protocols.mps_protocol.req_reset`
        Free a qubit for a new entanglement.
    2. :class:`~progress.mps.protocols.mps_protocol.req_stop_generation`
        Stop the mid-point entangling source. If already stopped, it has no effect.
    3. :class:`~progress.mps.protocols.mps_protocol.req_resume_generation`
        Resume the mid-point entangling source. All allocated qubits are considered released. If already active,
        it has no effect
    """

    req_free = namedtuple("req_free", ["idx"])
    r"""
    This request type is used to free a qubit which can now be used for a new link layer entanglement.
    Parameters:

    1. idx (int)
        The index of the qubit to free.
    """

    req_stop_generation = namedtuple("request_stop_generation", [])
    r"""
    Request this protocol to stop the mid point entangling source. It can be resumed by this protocol or the link
    protocol at the other end of the link by using a
    :class:`~progress.mps.protocols.mps_protocol.req_stop_generation` request.
    If the protocol is already stopped, this request has no effect.
    """

    req_resume_generation = namedtuple("request_resume_generation", [])
    r"""
    Request this protocol to resume the mid point entangling source. If the source is not stopped, this request has no
    effect.
    """

    def __init__(self, num_positions, qnic, node=None, other_node_info=None, name=None):
        r"""
        Initialize the link protocol.
        """
        super().__init__(node=node, name=name)

        self.register_request(self.req_free, self.free)
        self.register_request(self.req_stop_generation, self._handle_stop_generation)
        self.register_request(self.req_resume_generation, self._handle_resume_generation)


        self._num_positions = num_positions
        self._qnic = qnic

        self.other_node_info = other_node_info

    @property
    def interface(self):
        r"""
        The interface on which the protocol runs.
        """
        return self._qnic

    @abstractmethod
    def _handle_stop_generation(self, request):
        r"""
        This method is called when upper layers want to stop entanglement generation.
        """
        pass

    @abstractmethod
    def _handle_resume_generation(self, request):
        r"""
        This method is called when upper layers want to resume entanglement generation.
        """
        pass

    @abstractmethod
    def free(self, request):
        r"""
        This method is called when upper layers want to free a qubit for a new entanglement.
        """
        pass

    def deliver_new_socket(self, idx):
        r"""
        This method must be called by implementations of this abstract class when a new entangled pair is generated.
        It signals the new entanglement generation

        Parameters
        ----------
        idx : int
            The index of the qubit on the link protocol interface.
        """

        # send a message out of the "new_entanglements port of the node"
        # To describe the entanglement, we directly use two sockets
        local_end = Socket(self.node.supercomponent.device_id, self._qnic, idx)
        other_end = Socket(self.other_node_info[0], self.other_node_info[1], idx)
        self.node.ports["new_entanglements"].tx_output(ns.components.Message(items=[local_end, other_end]))








