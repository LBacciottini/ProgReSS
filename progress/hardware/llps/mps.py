"""
This module implements the Midpoint source (MPS) Link Layer protocol.
It also provides a :class:`~progress.mps.protocols.mps_protocol.MPSSourceProtocol` which is a
:class:`netsquid.protocols.nodeprotocols.NodeProtocol` determining the behavior of the Entangled Photon Source (EPS)
in the middle of the physical link between the two nodes.
"""

from netsquid.components import Message, SourceStatus
from netsquid.protocols.nodeprotocols import NodeProtocol
import progress.progress_logging as qilog
import netsquid as ns

__all__ = ["MPSProtocol", "MPSSourceProtocol"]

from progress.hardware.llps.llp import LinkProtocol


class MPSProtocol(LinkProtocol):
    r"""
    This protocol simulates the Midpoint source (MPS) protocol on the link interface of a node.
    An independent instance of this protocols must be started on a node for each link on which MPS protocols is
    activated.

    Parameters
    ----------
    qnic : str
        The port name on which the protocol will run.
    num_positions : int
        The number of qubits available for the link layer protocol.
    node : :class:`~qi_simulation.repeater.Repeater` or None, optional
        The node on which this protocols will run. If `None`, it must be set before starting the protocol and the
        link layer protocol must be manually subscribed to the node through the method
        :meth:`~qi_simulation.repeater.Repeater.subscribe_link_protocol`.
    other_node_info : tuple or None, optional
        A two-elements tuple where the first is the neighbor node id (int), and the second is the name of its attached
        interface (str). This info is used to generate a :class:`~qi_simulation.sockets.SocketDescriptor` from each
        qubit. If None, it must be set before the protocol is started.
    name : str, optional
        The name of the instance, defaults to the class name.
    """

    def __init__(self, num_positions, qnic, node=None, other_node_info=None, name=None):
        self._qubits_status = None

        self._alert_shown = False

        self._started_message_displayed = False

        super().__init__(num_positions, qnic, node, other_node_info, name)

    def start(self):
        """Start this protocol on a specified link of this node.

        References
        ----------

        See :meth:`netsquid.protocols.Protocol.start` for more information.
        """
        self._qubits_status = [None for _ in range(self._num_positions)]
        super().start()

    def _allocate_qubit(self, idx):
        if self._qubits_status[idx] is not None:
            qilog.warning(f"Repeater tried to allocate non-empty position {idx}.",
                          repeater_id=self.node.supercomponent.device_id, protocol=self.name)

        # count how many qubits are allocated
        allocated = 0
        for q in self._qubits_status:
            if q is not None:
                allocated += 1
        if allocated == self._num_positions:
            qilog.warning(f"Attention. All qubits on interface {self._qnic} are allocated.",
                          repeater_id=self.node.supercomponent.device_id, protocol=self.name)
            return None
        elif not self._alert_shown and allocated > 4*self._num_positions/5:
            qilog.warning(f"More than 4/5 of the qubits on interface {self._qnic} are allocated. Possible"
                          f" Bottleneck.",
                          repeater_id=self.node.supercomponent.device_id, protocol=self.name)
            self._alert_shown = True
        self._qubits_status[idx] = ns.sim_time()

    def _deallocate_qubit(self, idx):
        if self._qubits_status[idx] is None:
            qilog.warning(f"Repeater tried to deallocate empty position {idx}.",
                          repeater_id=self.node.supercomponent.device_id, protocol=self.name)
        self._qubits_status[idx] = None

    def run(self):
        r"""
        References
        ----------

        See :meth:`netsquid.protocols.Protocol.run`.
        """

        port = self.node.ports[self._qnic]

        # init phase
        init_res = InitMPSMessage()
        port.tx_output(init_res)
        while True:
            wait_msg = self.await_port_input(self.node.ports[self._qnic])
            wait_timer = self.await_timer(duration=100000)
            ev_expr = yield wait_msg | wait_timer
            if ev_expr.first_term.value:
                qilog.info(f"MPS Protocol on interface {self._qnic} has started.",
                           repeater_id=self.node.supercomponent.device_id, protocol=self.name)
                self._handle_incoming_qubit(ev_expr.first_term)
                break
            else:  # the timer triggered, we send the init again
                # qilog.info(f"triggering on {self._interface}")
                init_res = InitMPSMessage()
                port.tx_output(init_res)
        # end of init phase

        wait_msg = self.await_port_input(self.node.ports[self._qnic])
        while True:
            ev_expr = yield wait_msg
            self._handle_incoming_qubit(ev_expr)

    def _handle_incoming_qubit(self, event_expr):
        """
        In this high level abstraction of MPS protocol, the entangling source pre-computes which qubit pairs
        will make it to the destination and only sends those pairs. This method handles the incoming qubit pairs from
        the source.
        """
        msg = self.node.ports[self._qnic].rx_input(event=event_expr.triggered_events[0])
        qubit = msg.items[0]
        idx = msg.meta["position"]

        """
        # DEBUG
        counter = 0
        for qubit_status in self._qubits_status:
            if qubit_status is None:
                counter += 1
        """
        if idx is not None:
            """
            # DEBUG
            if (self.node.ID == 0 or self.node.ID == 1) and self._interface == "q0":
                qilog.debug(f"Entanglement generated on link {self._interface} at position {idx}."
                              f"There are {counter}/{self._num_positions} free qubits on this interface.",
                           repeater_id=self.node.ID, protocol=self.name)
            """

            if idx == -1:
                # Then this is just a notification that no pair was generated in the last round. Ignore it.
                """
                qilog.debug(f"No pair in last round on link {self._link_index}",
                           repeater_id=self.node.ID, protocol=self.name)
                """
                return

            self._allocate_qubit(idx)
            self.node.qmemory.put(qubit, self.node.map_info_to_qubit(self._qnic, idx))

            # we create a socket for the qubit and we deliver to the stack engine:
            self.deliver_new_socket(idx=idx)

    def free(self, request):
        idx = request.idx

        self._deallocate_qubit(idx)
        self.node.ports[self._qnic].tx_output(FreeQubitMessage(position=idx))

        # qilog.debug(f"Qubit {idx} freed on link {self._interface}", repeater_id=self.node.ID, protocol=self.name)

        """ No one uses this response, so we can ignore it.
        res = res_free(content="Done")
        self.send_response(res)
        """

    def _handle_stop_generation(self, _):
        msg = StopGenerationMessage()
        self.node.ports[self._qnic].tx_output(msg)

    def _handle_resume_generation(self, _):
        msg = ResumeGenerationMessage()
        self._qubits_status = [None for _ in range(self._num_positions)]
        self.node.ports[self._qnic].tx_output(msg)


class MPSSourceProtocol(NodeProtocol):
    r"""
    This protocol is run at the mid-point source of a link and is used to handle 'Reset Qubit' messages.
    """
    _num_positions = None

    def __init__(self, node, name=None):
        super().__init__(node=node, name=name)

    def start(self):
        r"""
        References
        ----------

        See :meth:`netsquid.protocols.Protocol.start`.
        """
        super().start()

    def run(self):
        # at the beginning we send the init message:
        init_msg = InitMPSMessage()
        self.node.ports["c0"].tx_output(init_msg)
        self.node.ports["c1"].tx_output(init_msg)

        # and we wait for the init messages to be received by both sides:
        received = None

        while True:
            wait_msg = self.await_port_input(self.node.ports["c0"]) | self.await_port_input(self.node.ports["c1"])
            ev_expr = yield wait_msg
            if ev_expr.first_term.value and received is None:
                msg = self.node.ports["c0"].rx_input(event=ev_expr.triggered_events[0])
                if isinstance(msg, InitMPSMessage):
                    received = "c0"
            elif ev_expr.second_term.value and received is None:
                msg = self.node.ports["c1"].rx_input(event=ev_expr.triggered_events[0])
                if isinstance(msg, InitMPSMessage):
                    received = "c1"
            elif ev_expr.first_term.value and received == "c1":
                msg = self.node.ports["c0"].rx_input(event=ev_expr.triggered_events[0])
                if isinstance(msg, InitMPSMessage):
                    t_link = (ns.sim_time() - msg.items[0]) * 2
                    self.node.init_source(t_link)
                    break
            elif ev_expr.second_term.value and received == "c0":
                msg = self.node.ports["c1"].rx_input(event=ev_expr.triggered_events[0])
                if isinstance(msg, InitMPSMessage):
                    t_link = (ns.sim_time() - msg.items[0]) * 2
                    self.node.init_source(t_link)
                    break

        # now we can start the source:
        self.node.start()

        while True:
            wait_msg = self.await_port_input(self.node.ports["c0"]) | self.await_port_input(self.node.ports["c1"])
            ev_expr = yield wait_msg

            if ev_expr.first_term.value:
                while len(self.node.ports["c0"].input_queue) > 0:
                    msg = self.node.ports["c0"].rx_input()
                    if isinstance(msg, FreeQubitMessage):
                        position = msg.items[0]
                        if self.node.pos_status_list[position] == "busy":
                            self.node.pos_status_list[position] = "free_left"
                        elif self.node.pos_status_list[position] == "free_right":
                            self.node.pos_status_list[position] = "free"
                    elif isinstance(msg, StopGenerationMessage):
                        self.node.stop()
                    elif isinstance(msg, ResumeGenerationMessage):
                        if self.node.status == SourceStatus.OFF:
                            self.node.reset(and_restart=True)

            if ev_expr.second_term.value:
                while len(self.node.ports["c1"].input_queue) > 0:
                    msg = self.node.ports["c1"].rx_input()
                    if isinstance(msg, FreeQubitMessage):
                        position = msg.items[0]
                        if self.node.pos_status_list[position] == "busy":
                            self.node.pos_status_list[position] = "free_right"
                        elif self.node.pos_status_list[position] == "free_left":
                            self.node.pos_status_list[position] = "free"

                    elif isinstance(msg, StopGenerationMessage):
                        self.node.stop()
                    elif isinstance(msg, ResumeGenerationMessage):
                        if self.node.status == SourceStatus.OFF:
                            self.node.reset(and_restart=True)


class StopGenerationMessage(Message):
    """
    This message is sent by repeaters to notify the MPS source that it has to stop generating entanglement.
    """

    header = "MPS SOURCE STOP GENERATION"

    def __init__(self):
        super().__init__(items=["Stop"], header=self.header)


class ResumeGenerationMessage(Message):
    """
    This message is sent by repeaters to notify the MPS source that it has to resume generating entanglement.
    """

    header = "MPS SOURCE RESUME GENERATION"

    def __init__(self):
        super().__init__(items=["Resume"], header=self.header)


class FreeQubitMessage(Message):
    """
    This message is sent by a components to notify the MPS source that a position is now free on that end.
    """

    header = "MPS FREE QUBIT"

    def __init__(self, position):
        super().__init__(items=[position], header=self.header + " " + str(position))


class InitMPSMessage(Message):
    """
    This message is sent by the MPS source to initialize MPS on components nodes.
    """

    header = "MPS INIT"

    def __init__(self):
        # Add here more parameters if needed
        super().__init__(items=[ns.sim_time()], header=self.header)


# parameters set to comply with simulations in https://arxiv.org/abs/1910.08227v2
optimistic_parameters_v1 = {"p_mid": 1, "t_clock": 10, "N_value": 100, "p_photon": 0.9, "p_bsa": 0.53}
optimistic_parameters_v2 = {"p_mid": 0.5, "t_clock": 10, "N_value": 100, "p_photon": 0.9, "p_bsa": 0.53}
optimistic_parameters_v3 = {"p_mid": 0.02, "t_clock": 10, "N_value": 100, "p_photon": 0.9, "p_bsa": 0.53}
