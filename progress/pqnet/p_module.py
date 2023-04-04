"""
This module contains the base class for all progress modules.
"""

from abc import ABC, abstractmethod
from collections import namedtuple
import progress.progress_logging as log
import progress.pqnet.messages as messages

import netsquid as ns

from progress.sockets import TokenTable, TokenMessage

__all__ = ["Module", "ModuleBehavior", "ProcessingModuleBehavior", "SchedulingModuleBehavior"]


class Module(ns.nodes.Node):
    r"""
    This class is the base class for all progress modules. It is a node acting as a wrapper for its inner
    behavior, which is implemented in a class that inherits from :class:`~progress.pqnet.p_module.ModuleBehavior`.

    Parameters
    ----------
    module_id : int
        The id of the module.
    device_id : int
        The id of the device that the module is running on.
    name : str
        The name of the module.
    num_input : int
        The number of input ports.
    num_output : int
        The number of output ports.
    qhal : :class:`~progress.pqnet.qhal.QHAL` or None, optional
        A reference to the QHAL running on the device. If `None`, the QHAL must be set before starting the module.
    """

    def __init__(self, module_id, device_id, name, num_input, num_output, qhal=None):

        ports = ["in{}".format(i) for i in range(num_input)] + ["out{}".format(i) for i in range(num_output)]
        ports += ["messages"]
        super().__init__(name=name, port_names=ports)

        self.module_id = module_id
        """The id of the module."""
        self.device_id = device_id
        """The id of the device that the module is running on."""
        self.qhal = qhal
        """A reference to the QHAL running on the device."""
        self.behavior = None
        """The behavior of the module."""
        self.environment = ModuleEnvironment(self)
        """The environment of the module. It is used to trigger events on the module behavior when needed."""
        self.num_input = num_input
        """The number of input ports."""
        self.num_output = num_output
        """The number of output ports."""

        # the token table to store and manage owned tokens
        self.token_table = TokenTable()
        """The token table to store and manage owned tokens."""

    def start(self):
        """
        Start the module behavior. Should be called after the qhal and behavior have been set.
        """
        if self.qhal is None or self.behavior is None:
            raise ValueError("The qhal and behavior must be set before starting the module.")
        self.behavior.start()
        self.environment.start()

    def stop(self):
        """
        Stop the module behavior.
        """
        self.behavior.stop()
        self.environment.stop()


class ModuleBehavior(ns.protocols.ServiceProtocol, ABC):
    """
    This class is the base class for all module behaviors. It follows an event-driven approach, where the
    behavior is triggered by events. Such events are listed as the abstract methods of this class.

    Parameters
    ----------
    node : :class:`~progress.pqnet.p_module.Module`
        The module that this behavior is associated with.
    qnic : int or None, optional
        If not `None`, the module will take as input tokens directly from that qnic's token queue on its first input
        port. Defaults to `None`.
    name : str or None, optional
        The name of the behavior. If `None`, a default name is used. Defaults to `None`.
    """

    req_handle_message = namedtuple("req_handle_message", ["sender", "message"])
    req_handle_response = namedtuple("req_handle_response", ["response", "request"])
    req_handle_new_token = namedtuple("req_handle_new_token", ["token"])
    req_handle_collect_garbage = namedtuple("req_handle_collect_garbage", [])

    GARBAGE_COLLECTOR_PERIOD = 0.5  # ms

    def __init__(self, node, qnic=None, name=None):
        if name is None:
            name = "ModuleBehaviorProtocol for {}".format(node.name)
        super().__init__(node=node, name=name)
        self.register_request(self.req_handle_message, self.handle_message)
        self.register_request(self.req_handle_response, self.handle_response)
        self.register_request(self.req_handle_new_token, self.handle_new_token)
        self.register_request(self.req_handle_collect_garbage, self._collect_garbage)
        self.qnic = qnic

        self.last_garbage_collection = ns.sim_time()


    @abstractmethod
    def handle_message(self, request):
        r"""
        This method is called when a classical message is received from another remote module.

        Parameters
        ----------
        request : :class:`~progress.pqnet.p_module.ModuleBehavior.req_handle_message`
            The request containing the message to handle.
        """
        pass

    @abstractmethod
    def handle_response(self, request):
        r"""
        This method is called when a response to a previous request is received from the qhal.

        Parameters
        ----------
        request : :class:`~progress.pqnet.p_module.ModuleBehavior.req_handle_response`
            The request containing the QHAL response to handle. The response contains the outcome and the originating
            request piggybacked.
        """
        pass

    @abstractmethod
    def handle_new_token(self, request):
        r"""
        This method is called when a new token is received as input.

        Parameters
        ----------
        request : :class:`~progress.pqnet.p_module.ModuleBehavior.req_handle_new_token`
            The request containing the new token to handle.
        """
        pass

    def send_message(self, message, dest_device, dest_module_id):
        r"""
        Send a classical message to another module.

        Parameters
        ----------
        message : :class:`~ns.components.Message`
            The message to send.
        dest_device : int
            The device ID of the destination device.
        dest_module_id : int
            The module ID of the destination module.
        """
        wrapper = messages.InterModuleMessage(sender_device=self.node.device_id, sender_id=self.node.module_id,
                                              destination_device=dest_device, destination_id=dest_module_id,
                                              inner_message=message, topology_id=self.node.supercomponent.supercomponent.current_topology_id)
        self.node.ports["messages"].tx_output(wrapper)

    def token_is_present(self, token):
        r"""
        Check if a token is mapped to a physical qubit.

        Parameters
        ----------
        token : :class:`~progress.sockets.Token`
            The token to check.

        Returns
        -------
        bool
            `True` if the token is mapped to a physical qubit, `False` otherwise.
        """
        return self.node.qhal.token_api_service.token_has_socket(token, raise_error=False)

    def free_token(self, token):
        r"""
        This method is called when a token is no longer needed and can be freed (together with the physical qubit).

        Parameters
        ----------
        token : :class:`~progress.pqnet.kernel.p_token.Token`
            The token to free.
        """

        # if the token is stored in the token table, remove it
        self.node.token_table.pop_token(token.socket, raise_error=False)

        if self.token_is_present(token):
            req = self.node.qhal.token_api_service.req_free(token)
            self.node.qhal.token_api_service.put(req)
        else:
            log.warning(f"tried to free a token that is not present: {token}", repeater_id=self.node.device_id,
                        protocol=self.node.name)
            # log.warning(str(self.node.qhal.socket_table))

    def _collect_garbage(self, _):
        r"""
        This method is called periodically to collect garbage from the token table. Garbage are tokens that is expired
        (each token has an expiration time given by hardware parameters)
        """
        self.last_garbage_collection = ns.sim_time()
        to_remove = self.node.token_table.collect_garbage(current_time=ns.sim_time())
        for token in to_remove:
            self.free_token(token)

    def terminate(self):
        r"""
        Clean up actions before terminating.
        """
        # free all tokens
        for token in self.node.token_table.get_snapshot():
            self.free_token(token)

    def start_entanglement_generation(self, qnic):
        r"""
        Start the entanglement generation process on the given qnic.

        Parameters
        ----------
        qnic : int
            The qnic to start (or resume) the entanglement generation process on.
        """
        self.node.qhal.resume_entanglement(qnic)

    def stop_entanglement_generation(self, qnic):
        r"""
        Stop the entanglement generation process on the given qnic.

        Parameters
        ----------
        qnic : int
            The qnic to stop the entanglement generation process on.
        """
        self.node.qhal.stop_entanglement(qnic)


class ProcessingModuleBehavior(ModuleBehavior, ABC):
    r"""
    This class is extended by those module behaviors that perform some local quantum operations on the input tokens.
    Processing modules can have either zero or one output ports, otherwise an exception is raised.
    """

    def __init__(self, node, qnic=None, name=None):
        super().__init__(node=node, qnic=qnic, name=name)
        assert self.node.num_output <= 1, "Processing modules must have exactly zero or one output"

    def promote_token(self, token):
        r"""
        Send out a token out from the output port (to the next module).

        Parameters
        ----------
        token : :class:`~progress.pqnet.kernel.p_token.Token`
            The token to promote.
        """
        # pop the token from the token table
        self.node.token_table.pop_token(token.socket, raise_error=False)

        if self.node.num_output == 1:
            self.node.ports["out0"].tx_output(TokenMessage(token=token))
        else:
            raise ValueError("Cannot promote a token from a module with no output")

    def dejmps_tokens(self, token_a, token_b, role):
        r"""
        Apply DEJMPS entanglement distillation (the quantum circuit part) on two tokens.

        Parameters
        ----------
        token_a : :class:`~progress.pqnet.kernel.p_token.Token`
            The token to distill.
        token_b : :class:`~progress.pqnet.kernel.p_token.Token`
            The second token as distillation ancilla.
        role : str
            The role of the module in the distillation process. Must be one of "A", "B". It determines the
            initial rotation of the protocol. If the role is "A", the initial rotation is :math:`\pi/2`, otherwise
            it is :math:`-\pi/2`.

        References
        ----------
        .. [1] https://arxiv.org/abs/quant-ph/9604039
        """
        req = self.node.qhal.token_api_service.req_dejmps(self.node.module_id, token_a, token_b, role=role)
        self.node.qhal.token_api_service.put(req)
        """
        # DEBUG
        log.info(f"distilling {token_a} and {token_b}", repeater_id=self.node.device_id, protocol=self.name)
        """

    def swap_tokens(self, token_a, token_b):
        r"""
        Swap two tokens.

        Parameters
        ----------
        token_a : :class:`~progress.pqnet.kernel.p_token.Token`
            The first token to swap.
        token_b : :class:`~progress.pqnet.kernel.p_token.Token`
            The second token to swap.
        """
        req = self.node.qhal.token_api_service.req_swap(self.node.module_id, token_a, token_b)
        self.node.qhal.token_api_service.put(req)

    def correct_token(self, token):
        r"""
        Apply the correction circuit to a token to bring it back to :math:`\vert \phi^+ \rangle` Bell state from
        another Bell state which is specified inside the token information.

        Parameters
        ----------
        token : :class:`~progress.pqnet.kernel.p_token.Token`
            The token to correct.
        """
        req = self.node.qhal.token_api_service.req_correct(self.node.module_id, token)
        self.node.qhal.token_api_service.put(req)

    def apply_qcircuit(self, tokens, qcircuit):
        r"""
        Apply a custom quantum circuit to a token.

        Parameters
        ----------
        tokens : list of :class:`~progress.pqnet.kernel.p_token.Token`
            The tokens to apply the circuit to.
        qcircuit : :class:`~netsquid.components.qprogram.QuantumProgram`
            The quantum circuit to apply.
        """
        req = self.node.qhal.token_api_service.req_apply_qcircuit(self.node.module_id, tokens, qcircuit)
        self.node.qhal.token_api_service.put(req)


class SchedulingModuleBehavior(ModuleBehavior, ABC):
    r"""
    This class is extended by module behaviors that perform scheduling and routing operations on the input tokens.
    """

    def __init__(self, node, qnic=None, name=None):
        super().__init__(node=node, qnic=qnic, name=name)

    def promote_token(self, token, output_port=0):
        r"""
        Send out a token from a specified port.

        Parameters
        ----------
        token : :class:`~progress.pqnet.kernel.p_token.Token`
            The token to promote.
        output_port : int, optional
            The index of the output port to use. Defaults to 0.
        """

        # pop the token from the token table
        self.node.token_table.pop_token(token.socket, raise_error=False)

        if self.node.num_output > output_port:
            self.node.ports[f"out{output_port}"].tx_output(TokenMessage(token))
        else:
            raise ValueError("Cannot promote a token from a non-existing output port")


class ModuleEnvironment(ns.protocols.NodeProtocol):
    r"""
    This is the environment for the module. It is responsible for
        - receiving messages from the module
        - sending messages out of the module
        - calling behavior handlers (i.e. triggering its events)
    """

    GARBAGE_COLLECTION_PERIOD = .2  # ms
    """
    The period of garbage collection in ms.
    """

    def __init__(self, node, name=None):
        if name is None:
            name = "ModuleEnvironment for {}".format(node.name)
        super().__init__(node=node, name=name)
        self.next_garbage_collection = ns.sim_time() + self.GARBAGE_COLLECTION_PERIOD*1e6

    def _get_wait_ev_expr(self):
        ev_expr = self.await_port_input(self.node.ports["messages"])
        for i in range(self.node.num_input):
            ev_expr |= self.await_port_input(self.node.ports["in{}".format(i)])
        return ev_expr

    def _get_triggered_ports(self, ev_expr):
        port_names = []
        for i in range(self.node.num_input - 1, -1, -1):
            if ev_expr.second_term.value:
                port_names.append("in{}".format(i))
            ev_expr = ev_expr.first_term
        if ev_expr.value:
            port_names.append("messages")
        return port_names

    def run(self):
        r"""
        References
        ----------

        See :meth:`netsquid.protocols.Protocol.run`.
        """
        while True:
            # wait for a message on any input port (tokens or messages)
            ev_expr = yield self._get_wait_ev_expr() | self.await_timer(end_time=self.next_garbage_collection)
            if ev_expr.first_term.value:
                port_names = self._get_triggered_ports(ev_expr.first_term)
                for port_name in port_names:
                    if port_name == "messages":
                        self._handle_message()
                    else:
                        self._handle_new_token(port_name)
            else:
                self._handle_collect_garbage()

    def _handle_message(self):
        while len(self.node.ports["messages"].input_queue) > 0:
            msg = self.node.ports["messages"].rx_input()
            if isinstance(msg, messages.InterModuleMessage):
                req = ModuleBehavior.req_handle_message(sender=(msg.sender_device, msg.sender_id),
                                                        message=msg.inner_message)
            else:  # response from the QHAL
                req = ModuleBehavior.req_handle_response(response=msg.items[1], request=msg.items[2])
            self.node.behavior.put(req)

    def _handle_new_token(self, port_name):
        while len(self.node.ports[port_name].input_queue) > 0:
            msg = self.node.ports[port_name].rx_input()
            if not isinstance(msg, TokenMessage):
                raise ValueError(f"Received a message {msg} on the token input port that is not a token message")
            token = msg.token
            req = ModuleBehavior.req_handle_new_token(token=token)
            self.node.behavior.put(req)

    def _handle_collect_garbage(self):
        req = ModuleBehavior.req_handle_collect_garbage()
        self.node.behavior.put(req)
        self.next_garbage_collection = ns.sim_time() + self.GARBAGE_COLLECTION_PERIOD*1e6
