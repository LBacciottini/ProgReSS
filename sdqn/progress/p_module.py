from abc import ABC, abstractmethod
from collections import namedtuple
import sdqn.sdqn_logging as log
import sdqn.progress.messages as messages

import netsquid as ns

from sdqn.sockets import TokenTable, TokenMessage


class Module(ns.nodes.Node):

    def __init__(self, module_id, device_id, name, num_input, num_output, qhal=None):

        ports = ["in{}".format(i) for i in range(num_input)] + ["out{}".format(i) for i in range(num_output)]
        ports += ["messages"]
        super().__init__(name=name, port_names=ports)

        self.module_id = module_id
        self.device_id = device_id
        self.qhal = qhal
        self.behavior = None
        self.environment = ModuleEnvironment(self)
        self.num_input = num_input
        self.num_output = num_output

        # the token table to store and manage owned tokens
        self.token_table = TokenTable()

    def start(self):
        if self.qhal is None or self.behavior is None:
            raise ValueError("The qhal and behavior must be set before starting the module.")
        self.behavior.start()
        self.environment.start()

    def stop(self):
        self.behavior.stop()
        self.environment.stop()


class ModuleBehavior(ns.protocols.ServiceProtocol, ABC):

    req_handle_message = namedtuple("req_handle_message", ["sender", "message"])
    req_handle_response = namedtuple("req_handle_response", ["response", "request"])
    req_handle_new_token = namedtuple("req_handle_new_token", ["token"])

    def __init__(self, node, qnic=None, name=None):
        if name is None:
            name = "ModuleBehaviorProtocol for {}".format(node.name)
        super().__init__(node=node, name=name)
        self.register_request(self.req_handle_message, self.handle_message)
        self.register_request(self.req_handle_response, self.handle_response)
        self.register_request(self.req_handle_new_token, self.handle_new_token)
        self.qnic = qnic


    @abstractmethod
    def handle_message(self, request):
        r"""
        This method is called when a classical message is received from another remote module.

        Parameters
        ----------
        request : :class:`~sdqn.progress.kernel.p_module.ModuleBehavior.req_handle_message`
            The request containing the message to handle.
        """
        pass

    @abstractmethod
    def handle_response(self, request):
        r"""
        This method is called when a response to a previous request is received from the qhal.
        Parameters
        ----------
        request : :class:`~sdqn.progress.kernel.p_module.ModuleBehavior.req_handle_response`
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
        request : :class:`~sdqn.progress.kernel.p_module.ModuleBehavior.req_handle_new_token`
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
        return self.node.qhal.token_api_service.token_has_socket(token, raise_error=False)

    def free_token(self, token):
        r"""
        This method is called when a token is no longer needed and can be freed.

        Parameters
        ----------
        token : :class:`~sdqn.progress.kernel.p_token.Token`
            The token to free.
        """
        if self.token_is_present(token):
            req = self.node.qhal.token_api_service.req_free(token)
            self.node.qhal.token_api_service.put(req)
        else:
            log.warning(f"tried to free a token that is not present: {token}", repeater_id=self.node.device_id,
                        protocol=self.node.name)

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
    This class is extended by those modules that perform some local quantum operations on the input tokens.
    """

    def __init__(self, node, qnic=None, name=None):
        super().__init__(node=node, qnic=qnic, name=name)
        assert self.node.num_output <= 1, "Processing modules must have exactly zero or one output"

    def promote_token(self, token):
        r"""
        Send out a token to the next module.

        Parameters
        ----------
        token : :class:`~sdqn.progress.kernel.p_token.Token`
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
        token_a : :class:`~sdqn.progress.kernel.p_token.Token`
            The token to distill.
        token_b : :class:`~sdqn.progress.kernel.p_token.Token`
            The second token as ancilla.
        role : str
            The role of the module in the distillation process. Must be one of "A", "B". It determines the
            initial rotation of the protocol.
        """
        req = self.node.qhal.token_api_service.req_dejmps(self.node.module_id, token_a, token_b, role=role)
        self.node.qhal.token_api_service.put(req)

    def swap_tokens(self, token_a, token_b):
        r"""
        Swap two tokens.

        Parameters
        ----------
        token_a : :class:`~sdqn.progress.kernel.p_token.Token`
            The first token to swap.
        token_b : :class:`~sdqn.progress.kernel.p_token.Token`
            The second token to swap.
        """
        req = self.node.qhal.token_api_service.req_swap(self.node.module_id, token_a, token_b)
        self.node.qhal.token_api_service.put(req)

    def correct_token(self, token):
        r"""
        Apply the correction circuit to a token to bring it back to |phi+> Bell state.

        Parameters
        ----------
        token : :class:`~sdqn.progress.kernel.p_token.Token`
            The token to correct.
        """
        req = self.node.qhal.token_api_service.req_correct(self.node.module_id, token)
        self.node.qhal.token_api_service.put(req)

    def apply_qcircuit(self, tokens, qcircuit):
        r"""
        Apply a quantum circuit to a token.

        Parameters
        ----------
        tokens : list of :class:`~sdqn.progress.kernel.p_token.Token`
            The tokens to apply the circuit to.
        qcircuit : :class:`~netsquid.components.qprogram.QuantumProgram`
            The quantum circuit to apply.
        """
        req = self.node.qhal.token_api_service.req_apply_qcircuit(self.node.module_id, tokens, qcircuit)
        self.node.qhal.token_api_service.put(req)


class SchedulingModuleBehavior(ModuleBehavior, ABC):
    r"""
    This class represents modules that perform scheduling and routing operations on the input tokens.
    """

    def __init__(self, node, qnic=None, name=None):
        super().__init__(node=node, qnic=qnic, name=name)

    def promote_token(self, token, output_port=0):
        r"""
        Send out a token from a specific port.

        Parameters
        ----------
        token : :class:`~sdqn.progress.kernel.p_token.Token`
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
    - calling behavior handlers
    """

    def __init__(self, node, name=None):
        if name is None:
            name = "ModuleEnvironment for {}".format(node.name)
        super().__init__(node=node, name=name)

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
        while True:
            # wait for a message on any input port (tokens or messages)
            ev_expr = yield self._get_wait_ev_expr()
            port_names = self._get_triggered_ports(ev_expr)
            for port_name in port_names:
                if port_name == "messages":
                    self._handle_message()
                else:
                    self._handle_new_token(port_name)

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
