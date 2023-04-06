"""
This module contains the Quantum Hardware Abstraction Layer implementation.
"""

import collections
from collections import namedtuple

import netsquid as ns

from progress.hardware.llps.llp import LinkProtocol
from progress.hardware.qhardware import QuantumOperationsService
from progress.sockets import Token, TokenMessage
import progress.progress_logging as log

__all__ = ["QHAL", "EntanglementHandlerProtocol", "TokenOperationsService"]


class QHAL(ns.nodes.Node):
    r"""
    The Quantum Hardware Abstraction Layer of an SDQN device.

    Parameters
    ----------
    device_id : int
        The ID of the SDQN device (parent node)
    name : str
        The name of this node.
    qhardware : :class:`~progress.hardware.qhardware.QHardware`
        A reference to the QHardware placed in the same device (for easy access to its services).

    Attributes
    ----------
    qhardware : :class:`~progress.hardware.qhardware.QHardware`
        A reference to the quantum hardware placed in the same device.
    token_api_service : :class:`~progress.hardware.qhardware.QuantumOperationsService`
        The token operations service of the QHardware. It is used to request quantum operations with a
        hardware-independent interface.
    entanglement_handler : :class:`~progress.abstraction.qhal.EntanglementHandlerProtocol`
        The entanglement handler protocol of this QHAL. It is responsible for processing signals
        sent by the link layer protocols and allocating tokens in the queues for the NET layer.
    token_out_ports : list[:class:`netsquid.components.Port`]
        A shortcut to the output ports of this module. Each port is used to send tokens to the NET layer from a
        specific QNIC queue. The index of the port in the list is the index of the QNIC it is connected to.
    socket_table : collections.deque
        A table that keeps track of all tokens currently allocated. The table is implemented as a deque with a fixed
        size.

    Notes
    -----

    Ports:
        - "q_ops" (input): The port on which the Physical layer sends responses and outcomes for quantum operations.
        - "new_entanglement" (input): The port on which the link layer protocols send signals about new entanglement.
        - "tokens_ops" (input): The port on which the NET layer sends requests for token operations.
        - "token_out_{i}" (output): The port on which the QHAL sends tokens to the NET layer. The index of the port
          is the index of the QNIC token queue it is connected to.
    """

    def __init__(self, device_id, name, qhardware):
        ports = ["q_ops", "new_entanglement", "tokens_ops"]
        ports += [f"token_out_{i}" for i in range(qhardware.num_qnics)]
        super().__init__(name=name, port_names=ports)
        self.token_out_ports = [self.ports[f"token_out_{i}"] for i in range(qhardware.num_qnics)]

        self.qhardware = qhardware
        r"""
        A reference to the quantum hardware (:class:`~progress.hardware.QHardware`) placed in the same device.
        """

        self._device_id = device_id

        self.socket_table = collections.deque(maxlen=qhardware.num_qnics*qhardware.num_qbits_qnic)

        self.token_api_service = TokenOperationsService(self, name=f"token_api_service_{self._device_id}")
        self.entanglement_handler = EntanglementHandlerProtocol(self, name=f"entanglement_handler_{self._device_id}")

        self._start()

    def _start(self):
        """
        Start the QHAL inner protocols.
        """
        self.token_api_service.start()
        self.entanglement_handler.start()

    def stop_entanglement(self, qnic):
        """
        Stop the generation of entanglement in the given qnic.

        Parameters
        ----------
        qnic : int
            The qnic to stop the generation of entanglement.
        """
        self.qhardware.get_subscribed_llp(qnic).put(LinkProtocol.req_stop_generation())

    def resume_entanglement(self, qnic):
        """
        Resume the generation of entanglement in the given qnic.

        Parameters
        ----------
        qnic : int
            The qnic to resume the generation of entanglement.
        """
        self.qhardware.get_subscribed_llp(qnic).put(LinkProtocol.req_resume_generation())


class EntanglementHandlerProtocol(ns.protocols.NodeProtocol):
    def __init__(self, node, name=None):
        if name is None:
            name = "Entanglement Handler"
        super().__init__(node=node, name=name)

    def run(self):
        while True:
            yield self.await_port_input(self.node.ports["new_entanglement"])
            # catch the entanglement info and create the socket
            while len(self.node.ports["new_entanglement"].input_queue) > 0:
                msg = self.node.ports["new_entanglement"].rx_input()
                if len(msg.items) != 2:
                    raise ValueError(f"The new entanglement message {msg} should have two items.")
                local_end = msg.items[0]
                other_end = msg.items[1]

                self.node.socket_table.append(local_end)
                if len(self.node.socket_table) == self.node.socket_table.maxlen:
                    log.warning(f"Socket table of Device {self.node.supercomponent.device_id} is full.")

                # generate a token
                coherence_time = self.node.qhardware.qproc_coherence_time
                if coherence_time is not None:
                    token = Token(socket=local_end, other_end=other_end, pct=ns.sim_time() + coherence_time,
                                  purified=0, additional_info={}, current_state=0)
                else:
                    token = Token(socket=local_end, other_end=other_end, pct=0,
                                  purified=0, additional_info={}, current_state=0)
                tkn_msg = TokenMessage(token=token)

                # if there is no dag we free the token
                if self.node.supercomponent.dag is None:
                    self.node.token_api_service.put(TokenOperationsService.req_free(token=token))
                    continue

                # send the token out for processing
                self.node.token_out_ports[int(local_end.qnic[4:])].tx_output(tkn_msg)


class TokenOperationsService(ns.protocols.ServiceProtocol):
    r"""
    The Token Operations Service is a service protocol that handles the requests for token operations.
    An instance is automatically loaded in each QHAL node.

    Notes
    -----
    The requests types exposed by this service (see Attributes) are very important as they compose the unified interface
    for hardware-independent quantum operations.

    Attributes
    ----------
    req_free : collections.namedtuple
        Request to free a token from memory. See :meth:`~progress.abstraction.qhal.TokenOperationsService.req_free`.
    req_swap : collections.namedtuple
        Request to perform entanglement swapping on two tokens.
        See :meth:`~progress.abstraction.qhal.TokenOperationsService.req_swap`.
    req_dejmps : collections.namedtuple
        Request to perform de-JMPs on a token. See :meth:`~progress.abstraction.qhal.TokenOperationsService.req_dejmps`.
    req_qcirc : collections.namedtuple
        Request to perform quantum circuit operations on a token.
        See :meth:`~progress.abstraction.qhal.TokenOperationsService.req_qcirc`.

    Parameters
    ----------
        node : :class:`~progress.abstraction.qhal.QHAL`
            The QHAL node.
        name : str or None, optional
            The name of the service protocol. If `None`, the name will be set to "Token Operations Service".
    """

    req_free = namedtuple("req_free", ["token"])
    """
    Request to free a token from memory.

    Parameters:
        token (:class:`~progress.sockets.Token`): The token to free.
    """

    req_swap = namedtuple("req_swap", ["id", "token1", "token2"])
    """
    Request to perform entanglement swapping on two tokens.

    Parameters:
        id (int): The ID of the requesting module.
        token1 (:class:`~progress.sockets.Token`): The first token to swap.
        token2 (:class:`~progress.sockets.Token`): The second token to swap.
    """

    req_dejmps = namedtuple("req_purify", ["id", "token1", "token2", "role"])
    """
    Request to perform DEJMPS distillation on two tokens. The first one is the one distilled,
    the second one is used as ancilla. The "role" field is used to determine which rotation to apply (pi/2 or -pi/2),
    and can assume two values, either 'A' (pi/2) or 'B' (-pi/2).

    Parameters:
        id (int): The id of the requesting module.
        token1 (:class:`~progress.sockets.Token`): The first token to distill.
        token2 (:class:`~progress.sockets.Token`): The second token to distill.
        role (str): The role of this device in the distillation. Can be either 'A' or 'B'.
    """

    req_correct = namedtuple("req_correct", ["id", "token"])
    r"""
    Request to correct a token. The token is in a custom Bell state, which is
    represented by an integer between 0 and 3. The token is corrected to the Bell state
    :math:`\vert \beta_{00} \rangle`.

    Parameters:
        id (int): The id of the requesting module.
        token (:class:`~progress.sockets.Token`): The token to correct.
    """

    req_qcirc = namedtuple("req_qcirc", ["id", "tokens", "qcirc"])
    """
    Request to perform a generic quantum circuit on a list of tokens.
    When the circuit is executed, the measurement outcomes are sent out from the port `tokens_ops`.
    If some tokens are measures, they have to be freed afterwards with a `req_free` request.

    Parameters:
        id (int): The id of the requesting module.
        tokens (list of :class:`~progress.sockets.Token`): The list of tokens in input to the quantum operation.
        qcirc (:class:`netsquid.components.qprocessor.QuantumProgram`): The quantum program to execute.
    """

    def token_has_socket(self, token, raise_error=True):
        r"""
        Check if a token is present in the socket table of the QHAL.

        Parameters
        ----------
        token : :class:`~sdqn.sockets.Token`
            The token to check.
        raise_error : bool
            If True, raise an error if the token is not present in the socket table. Default is True.

        Returns
        -------
        bool
            True if the token is present in the socket table, False otherwise.
            Only significant if `raise_error` is False.
        """

        if token.socket in self.node.socket_table:
            return True
        elif raise_error:
            raise ValueError(f"The token {token} is not present in the socket table of the QHAL.")
        return False

    def free(self, token):
        r"""
        Free a token from memory. Also free the physical qubit.

        Parameters
        ----------
        token : :class:`~sdqn.sockets.Token`
            The token to free.
        """

        # DEBUG
        """
        # check consistency
        if len(self.node.socket_table) >= self.node.socket_table.maxlen * 4 / 5:
            consistency = self._check_consistency()
            if consistency != 0:
                log.warning(f"Consistency check failed with code {consistency}.", repeater_id=self.node.supercomponent.device_id)
        """
        self.node.qhardware.put_qop(QuantumOperationsService.req_free(token.socket.qnic, token.socket.idx))
        # remove the token from the socket table
        self.node.socket_table.remove(token.socket)

        """ DEBUG
        if len(self.node.socket_table) >= self.node.socket_table.maxlen*4/5:
            log.warning(f"The socket table has {len(self.node.socket_table)} sockets out "
                        f"of {self.node.socket_table.maxlen}.", repeater_id=self.node.supercomponent.device_id)
        """

    def _handle_free(self, request):
        self.free(request.token)

    def _handle_swap(self, request):
        token_a = request.token1
        token_b = request.token2

        q_request = QuantumOperationsService.req_swap(request.id, token_a.socket.qnic, token_a.socket.idx,
                                                      token_b.socket.qnic, token_b.socket.idx)
        self.node.qhardware.put_qop(q_request)

        # wait for the result
        yield self.await_port_input(self.node.ports["q_ops"])
        msg = self.node.ports["q_ops"].rx_input()
        assert msg.items[0] == request.id
        self.send_response(response=msg.items[1], name=request.id, request=request)

        # remove the tokens from the socket table
        self.node.socket_table.remove(token_a.socket)
        self.node.socket_table.remove(token_b.socket)

    def _handle_dejmps(self, request):
        token_a = request.token1
        token_b = request.token2

        q_request = QuantumOperationsService.req_dejmps(request.id, token_a.socket.qnic, token_a.socket.idx,
                                                        token_b.socket.qnic, token_b.socket.idx, request.role)
        self.node.qhardware.put_qop(q_request)

        # wait for the result
        yield self.await_port_input(self.node.ports["q_ops"])
        msg = self.node.ports["q_ops"].rx_input()
        assert msg.items[0] == request.id
        self.send_response(response=msg.items[1], name=request.id, request=request)

        # remove the ancilla from the socket table
        self.node.socket_table.remove(token_b.socket)

    def _handle_correct(self, request):
        token = request.token

        q_request = QuantumOperationsService.req_correct(request.id, token.socket.qnic, token.socket.idx)
        self.node.qhardware.put_qop(q_request)

        # wait for the result
        yield self.await_port_input(self.node.ports["q_ops"])
        msg = self.node.ports["q_ops"].rx_input()
        assert msg.items[0] == request.id
        self.send_response(response=msg.items[1], name=request.id, request=request)

    def _handle_qcirc(self, request):
        tokens = request.tokens

        q_request = QuantumOperationsService.req_qcirc(request.id, [(t.socket.qnic, t.socket.idx) for t in tokens],
                                                       request.qcirc)
        self.node.qhardware.put_qop(q_request)

        # wait for the result
        yield self.await_port_input(self.node.ports["q_ops"])
        msg = self.node.ports["q_ops"].rx_input()
        assert msg.items[0] == request.id, f"Received message with id {msg.items[0]} but expected {request.id}"
        self.send_response(response=msg.items[1], name=request.id, request=request)

    def _check_consistency(self):
        """
        Debug function to check if the socket table is consistent with the qhardware: it checks that the number of
        sockets in the socket table is equal to the number of qubits allocated in the link layer protocols
        subscribed to the qhardware.

        Returns
        -------
        int
            The difference between the number of sockets in the socket table and the number of qubits allocated in the
            link layer protocols.
        """

        # get the number of qubits allocated in the link layer protocols
        num_qubits = 0
        for qnic in range(self.node.qhardware.num_qnics):
            llp = self.node.qhardware.get_subscribed_llp(qnic)
            # count the number of non None elements in llp._qubits_status
            num_qubits += len([x for x in llp._qubits_status if x is not None])

        if len(self.node.socket_table) != num_qubits:
            log.warning(f"The socket table has {len(self.node.socket_table)} sockets but the qhardware has "
                      f"{num_qubits} qubits allocated in the link layer protocols.")
        return len(self.node.socket_table) - num_qubits


    def send_response(self, response, name=None, request=None):
        r"""
        Sends a response to the port `tokens_ops`.
        """
        header = "TOKEN OPS RESPONSE"
        if name is not None:
            header += " REQ " + str(name)
        msg = ns.components.Message(header=header, items=[name, response, request])
        self.node.ports['tokens_ops'].tx_output(msg)

    def __init__(self, node, name=None):
        if name is None:
            name = "Token Operations Service"
        super().__init__(node=node, name=name)

        # We will use a queue for requests
        self.queue = collections.deque()
        self._new_req_signal = "New request in queue"
        self.add_signal(self._new_req_signal)
        self._create_id = 0

        self.register_request(self.req_free, self._handle_free)
        self.register_request(self.req_qcirc, self._handle_qcirc)
        self.register_request(self.req_correct, self._handle_correct)
        self.register_request(self.req_dejmps, self._handle_dejmps)
        self.register_request(self.req_swap, self._handle_swap)

    def handle_request(self, request, identifier, start_time=None, **kwargs):
        r"""Schedule the request on the queue.

        Parameters
        ----------
        request :
            The object representing the request.
        identifier : str
            The identifier for this request.
        start_time : float, optional
            The time at which the request can be executed. Default current simulation time. [ns]
        kwargs : dict, optional
            Additional arguments which can be set by the service.

        Returns
        -------
        dict
            The dictionary with additional arguments.

        Notes
        -----
        This method is called after
        :meth:`~netsquid.protocols.serviceprotocol.ServiceProtocol.put` which
        does the type checking etc.

        """
        if start_time is None:
            start_time = ns.sim_time()
        self.queue.append((start_time, (identifier, request, kwargs)))

        """
        # DEBUG
        # check that the queue is not longer than 20 requests
        if len(self.queue) > 20:
            log.warning(f"Queue of requests for {self.name} has {len(self.queue)} requests: {self.queue}. ", repeater_id=self.node.supercomponent.device_id)
        """
        self.send_signal(self._new_req_signal)
        return kwargs

    def run(self):
        r"""Wait for a new request signal, then run the requests one by one.

        Assumes request handlers are generators and not functions.

        References
        ----------

        See :meth:`netsquid.protocols.Protocol.run`.
        """
        while True:
            yield self.await_signal(self, self._new_req_signal)
            # log.warning(f"Hey, you, you are finally awake! The queue has {len(self.queue)} requests!", repeater_id=self.node.supercomponent.device_id)
            while len(self.queue) > 0:
                start_time, (handler_id, request, kwargs) = self.queue.popleft()
                if start_time > ns.sim_time():
                    yield self.await_timer(end_time=start_time)
                func = self.request_handlers[handler_id]
                args = request
                gen = func(args, **kwargs)
                if gen is not None:
                    yield from gen
