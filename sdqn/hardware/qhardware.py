"""
This module contains the model of the QHardware of the SDQN architecture.
"""

from collections import namedtuple, deque

import netsquid as ns
import math

from sdqn.hardware.llps.llp import LinkProtocol
import sdqn.sdqn_logging as log

__all__ = ['get_processor', 'QHardware', 'QuantumOperationsService']

INSTR_Rx = ns.components.IGate("Rx_gate", ns.qubits.operators.create_rotation_op(math.pi / 2, (1, 0, 0)))
"""
Pi/2 rotation around the x-axis
"""

INSTR_RxC = ns.components.IGate("RxC_gate", ns.qubits.operators.create_rotation_op(math.pi / 2, (1, 0, 0), conjugate=True))
"""
-Pi/2 rotation around the x-axis
"""


def get_processor(num_positions, coherence_time=None, one_qbit_noise=None, two_qbit_noise=None,
                  two_qbit_p_err=0.005, meas_p_err=0., instr_duration=0.):
    r"""Get an operational quantum processor

    Parameters
    -----------
    num_positions : int
        The number of qubits in the quantum memory of this processor.
    coherence_time : int or None, optional
        The coherence time of the quantum memory. It is the time after which the fidelity of the qubit state
          drops more than 5%. [ns]
    one_qbit_noise : :class:`netsquid.models.model.Model`, None, optional
        The noise model of one qubit instructions of this processor.
    two_qbit_noise : :class:`netsquid.models.model.Model`, None, optional
        The noise model of two qubit instructions of this processor.
    two_qbit_p_err : float, optional
        The probability of error of two qubit instructions of this processor. The error means that the instruction
        depolarizes the qubits.
        If `two_qbit_noise` is not None, this parameter is ignored.
    meas_p_err : float, optional
        The probability of error of CBS measurement instruction of this processor. The error means that the instruction
        depolarizes the qubit right before the measurement.
    instr_duration : float, optional
        The duration of each instruction of this processor. Defaults to 0. [ns]

    Returns
    -------
    :class:`netsquid.components.qprocessor.QuantumProcessor`
        The quantum processor, ready to use.
    """

    if two_qbit_noise is None:
        two_qbit_noise = ns.components.DepolarNoiseModel(depolar_rate=two_qbit_p_err, time_independent=True)

    meas_noise = ns.components.DepolarNoiseModel(depolar_rate=meas_p_err, time_independent=True)

    phys_instructions = [
        ns.components.PhysicalInstruction(ns.components.INSTR_X, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
        ns.components.PhysicalInstruction(ns.components.INSTR_Z, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
        ns.components.PhysicalInstruction(ns.components.INSTR_CX, duration=instr_duration, parallel=True,
                                          q_noise_model=two_qbit_noise),
        ns.components.PhysicalInstruction(ns.components.INSTR_H, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
        ns.components.PhysicalInstruction(ns.components.INSTR_INIT, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
        ns.components.PhysicalInstruction(ns.components.INSTR_MEASURE_BELL, duration=instr_duration,parallel=True,
                            q_noise_model=two_qbit_noise, apply_q_noise_after=False),
        ns.components.PhysicalInstruction(ns.components.INSTR_MEASURE, duration=instr_duration, parallel=True,
                            q_noise_model=meas_noise, apply_q_noise_after=False),
        ns.components.PhysicalInstruction(ns.components.INSTR_ROT_Y, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
        ns.components.PhysicalInstruction(INSTR_Rx, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
        ns.components.PhysicalInstruction(INSTR_RxC, duration=instr_duration, parallel=True,
                                          q_noise_model=one_qbit_noise),
    ]

    if coherence_time is None:
        qproc = ns.components.QuantumProcessor(name="QuantumProcessor",
                                               num_positions=num_positions,
                                               phys_instructions=phys_instructions)
    else:
        # Used to apply an initial imperfection to the qubits (F_0 =~ 0.98)
        models = {'qin_noise_model': ns.components.DepolarNoiseModel(depolar_rate=0.03,
                                                                     time_independent=True)}

        mem_noise_model = ns.components.DephaseNoiseModel(dephase_rate=-math.log(0.98)*1e9 / coherence_time)
        # mem_noise_model = DephaseNoiseModel(dephase_rate=10.0)

        qproc = ns.components.QuantumProcessor(name="QuantumProcessor",
                                               num_positions=num_positions,
                                               mem_noise_models=[mem_noise_model] * num_positions,
                                               phys_instructions=phys_instructions)
        qproc.models['qin_noise_model'] = models['qin_noise_model']

    return qproc


class QHardware(ns.nodes.Node):
    r"""
    This node contains the quantum hardware of a Quantum Internet node, including the quantum processor and the QNICS.

    Parameters
    ----------
    name : str
        The name of this Repeater
    num_qnics : int, optional
        The number of QNICS of this device. Defaults to 2.
    num_qbits_qnic : int, optional
        The number of physical qubits assigned to each QNIC of this device. Defaults to 1.
    qproc_params : dict, optional
        The parameters of the quantum processor of this device. See :func:`~sdqn.hardware.qhardware.get_processor`
        for details. If `None`, a default processor is created. Defaults to `None`. The field `num_positions` can be
        omitted, as it is set to `num_qnics * num_qbits_qnic`.

    Notes
    ------
    Ports:

    1. qnic{0..[num_qnics-1]}
        The QNICS of this device.
    3. q_ops
        Used to request quantum operations to the quantum processor.
    4. new_entanglements
        Used to signal to the outside that a new entangled qubit is available.
    """
    
    def __init__(self, name, num_qnics=2, num_qbits_qnic=1, qproc_params=None):
        ports = ["qnic{}".format(i) for i in range(num_qnics)] + ["q_ops", "new_entanglements"]
        super().__init__(name=name, port_names=ports)
        self.qproc_params = qproc_params
        self.num_qnics = num_qnics
        self.num_qbits_qnic = num_qbits_qnic

        self.qproc_coherence_time = None
        if self.qproc_params is not None:
            self.qproc_coherence_time = self.qproc_params.get('coherence_time', None)

        self._llp_subscriptions = [None for _ in range(num_qnics)]

        if qproc_params is None:
            qproc_params = {}

        qproc_params['num_positions'] = num_qnics * num_qbits_qnic

        self.qmemory = get_processor(**qproc_params)

        self._qops_service = QuantumOperationsService(name="qops_service", node=self)
        self._qops_service.start()

    def put_qop(self, request):
        """
        Submit a quantum operation request. The response is sent through the port "q_ops" of the node.

        Parameters
        ----------
        request: namedtuple
            The request to be submitted. See :class:`~sdqn.hardware.qhardware.QuantumOperationRequest` for details.
        """
        self._qops_service.put(request)

    def get_subscribed_llp(self, qnic):
        r"""
        Returns the Link Layer protocol subscribed to the given QNIC.

        Parameters
        ----------
        qnic : int or str
            The QNIC to get the subscribed link protocol from. Can be either the qnic's name or its index.

        Returns
        -------
        :class:`~sdqn.hardware.llps.llp.LinkProtocol` or None
        """

        # get the qnic as an integer
        if not isinstance(qnic, int):
            qnic = int(qnic[4:])

        return self._llp_subscriptions[qnic]

    def subscribe_llp(self, qnic, llp):
        r"""
        Subscribe a link layer protocol to the given QNIC.

        Parameters
        ----------
        qnic : int or str
            The QNIC to subscribe the link protocol to. Can be either the qnic's name or its index.

        llp : :class:`~sdqn.hardware.llps.llp.LinkProtocol
            The link layer protocol to subscribe.
        """

        # get the qnic as an integer
        if not isinstance(qnic, int):
            qnic = int(qnic[4:])

        self._llp_subscriptions[qnic] = llp

    def map_info_to_qubit(self, qnic, idx):
        """
        Maps the qnic and the index of the qubit to the position in the quantum processor.
        """
        if isinstance(qnic, int):
            return qnic * self.num_qbits_qnic + idx
        elif isinstance(qnic, str):
            return int(qnic[4:]) * self.num_qbits_qnic + idx
        else:
            raise ValueError("The qnic must be either an integer or a string.")


class QuantumOperationsService(ns.protocols.ServiceProtocol):
    r"""
    This protocol is used to request quantum operations to the quantum processor.
    It sends the measurement outcomes (if present) out from the port `q_ops`.

    Parameters
    ----------
    node : :class:`~netsquid.node.Node`
        The component to which the service is attached.
    name : str or None, optional
        The name of the service, for labelling purposes. Defaults to `None`.
    """

    req_free = namedtuple("req_free", ["qnic", "idx"])
    """
    Request to free a qubit from the quantum processor at a specified position.
    
    Parameters:
        qnic (int or str): The qnic to which the qubit is assigned.
        idx (int): The index of the qubit relative to the qnic.
    """

    req_swap = namedtuple("req_swap", ["id", "qnic1", "idx1", "qnic2", "idx2"])
    """
    Request to perform entanglement swapping on two qubits in the quantum processor.
    
    Parameters:
        id (int): The id of the request.
        qnic1 (int or str): The qnic to which the first qubit is assigned.
        idx1 (int): The index of the first qubit relative to the qnic.
        qnic2 (int or str): The qnic to which the second qubit is assigned.
        idx2 (int): The index of the second qubit relative to the qnic.
    """

    req_dejmps = namedtuple("req_purify", ["id", "qnic1", "idx1", "qnic2", "idx2", "role"])
    """
    Request to perform DEJMPS distillation on two qubits in the quantum processor. The first one is the one distilled,
    the second one is used as ancilla. The "role" field is used to determine which rotation to apply (pi/2 or -pi/2),
    and can assume two values, either 'A' (pi/2) or 'B' (-pi/2).
    
    Parameters:
        id (int): The id of the request.
        qnic1 (int or str): The qnic to which the first qubit is assigned.
        idx1 (int): The index of the first qubit relative to the qnic.
        qnic2 (int or str): The qnic to which the second qubit is assigned.
        idx2 (int): The index of the second qubit relative to the qnic.
        role (str): The role of this device in the distillation. Can be either 'A' or 'B'.
    """

    req_correct = namedtuple("req_correct", ["id", "qnic1", "idx1", "cur_state"])
    r"""
    Request to correct a qubit in the quantum processor. The qubit is in the state specified by `cur_state`, which is
    an integer between 0 and 3 indicating the Bell state. The qubit is corrected to the Bell state
    :math:`\vert \beta_{00} \rangle`.
    
    Parameters:
        id (int): The id of the request.
        qnic1 (int or str): The qnic to which the qubit is assigned.
        idx1 (int): The index of the qubit relative to the qnic.
        cur_state (int): The current state of the qubit. Can be either 0, 1, 2 or 3.
    """

    req_qcirc = namedtuple("req_qcirc", ["id", "qubits_map", "qcirc"])
    """
    Request to perform a generic quantum circuit on a set of qubits in the quantum processor.
    When the circuit is executed, the measurement outcomes are sent out from the port `q_ops`.
    
    Parameters:
        id (int): The id of the request.
        qubits_map (list of tuples): A list of tuples, each one containing the qnic and the index of the qubit
            relative to the qnic.
        qcirc (QuantumProgram): The quantum program to execute.
    """

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
        self.send_signal(self._new_req_signal)
        return kwargs

    def run(self):
        r"""Wait for a new request signal, then run the requests one by one.

        Assumes request handlers are generators and not functions.

        References
        -----------

        See :meth:`~netsquid.protocols.Protocol.run`.
        """
        while True:
            yield self.await_signal(self, self._new_req_signal)
            while len(self.queue) > 0:
                start_time, (handler_id, request, kwargs) = self.queue.popleft()
                if start_time > ns.sim_time():
                    yield self.await_timer(end_time=start_time)
                func = self.request_handlers[handler_id]
                args = request
                gen = func(args, **kwargs)
                if gen is not None:
                    yield from gen

    class CorrectProgram(ns.components.QuantumProgram):
        """Quantum processor program that applies corrections to restore the |beta00> state."""
        default_num_qubits = 1
        curr_state = 0

        def set_corrections(self, current_state):
            self.curr_state = current_state

        def program(self):
            q1, = self.get_qubit_indices(1)
            if self.curr_state == 1 or self.curr_state == 3:
                self.apply(ns.components.instructions.INSTR_X, q1)
            if self.curr_state == 2 or self.curr_state == 3:
                self.apply(ns.components.instructions.INSTR_Z, q1)
            yield self.run()

    def free(self, qnic, idx):
        r"""
        Free the qubit on the given socket.

        Parameters
        ----------
        qnic : str
            The qnic identifier.
        idx : int
            The index of the qubit on the qnic.
        """

        """
        # DEBUG
        log.info("Freeing qubit on qnic %s, index %d" % (qnic, idx),
                 repeater_id=self.node.supercomponent.device_id,
                 protocol="QHardware")
        """
        link_protocol = self.node.get_subscribed_llp(qnic)
        if link_protocol is None:
            raise ValueError("No link protocol subscribed to the given qnic.")
        request = LinkProtocol.req_free(idx=idx)
        link_protocol.put(request)
        """
        response = self.res_free('Done')
        self.send_response(response)
        """

    def _handle_free(self, request):
        r"""
        Handle a free request.
        """
        self.free(request.qnic, request.idx)

    def _handle_qcirc(self, request):
        r"""
        Handle a quantum circuit request.
        """
        positions = [self.node.map_info_to_qubit(qnic, idx) for qnic, idx in request.qubits_map]
        qcirc = request.qcirc
        self.qproc.execute_program(program=qcirc, qubit_mapping=positions, error_on_fail=True)
        yield self.await_program(processor=self.qproc)
        out = qcirc.output

        if out is None or len(out) == 0:
            self.send_response('Done', name=request.id)
        else:
            self.send_response(out, name=request.id)

    def _handle_correct(self, request):
        cur_state = request.cur_state
        positions = [self.node.map_info_to_qubit(request.qnic1, request.idx1)]
        self.correct_program.set_corrections(cur_state)
        self.qproc.execute_program(program=self.correct_program, qubit_mapping=positions, error_on_fail=True)
        yield self.await_program(processor=self.qproc)

        self.send_response('Done', name=request.id)

    @staticmethod
    def _setup_dejmps_program(conj_rotation):
        """
        Set up the DEJMPS quantum program.
        Parameters
        ----------
        conj_rotation : bool
            Whether to apply the conjugate of the rotation.

        Returns
        -------
        dejmp_program : :class:`~netsquid.programs.Program`
        """
        INSTR_ROT = INSTR_Rx if not conj_rotation else INSTR_RxC
        prog = ns.components.QuantumProgram(num_qubits=2)
        q1, q2 = prog.get_qubit_indices(2)
        prog.apply(INSTR_ROT, [q1])
        prog.apply(INSTR_ROT, [q2])
        prog.apply(ns.components.instructions.INSTR_CX, [q1, q2])
        prog.apply(ns.components.instructions.INSTR_MEASURE, q2, output_key="m", inplace=False)
        return prog

    def _handle_dejmps(self, request):
        r"""
        Handle a DEJMPS distillation request. It automatically frees measured qubit at the end.
        """
        role = request.role
        if role == 'A':
            # pi/2 rotation
            prog = self._setup_dejmps_program(conj_rotation=False)
        elif role == 'B':
            # -pi/2 rotation
            prog = self._setup_dejmps_program(conj_rotation=True)
        else:
            raise ValueError("The role must be either 'A' or 'B'.")
        positions = [self.node.map_info_to_qubit(qnic, idx)
                     for qnic, idx in [(request.qnic1, request.idx1), (request.qnic2, request.idx2)]]
        self.qproc.execute_program(program=prog, qubit_mapping=positions, error_on_fail=True)
        yield self.await_program(processor=self.qproc)

        outcome = prog.output["m"][0]

        # free the ancilla
        self.free(request.qnic2, request.idx2)

        self.send_response(outcome, name=request.id)

    def _handle_swap(self, request):

        positions = [self.node.map_info_to_qubit(qnic, idx)
                     for qnic, idx in [(request.qnic1, request.idx1), (request.qnic2, request.idx2)]]
        self.qproc.execute_program(program=self._es_program, qubit_mapping=positions, error_on_fail=True)
        yield self.await_program(processor=self.qproc)

        bell_result, = self._es_program.output["m"]

        # free the swapped qubits
        self.free(request.qnic1, request.idx1)
        self.free(request.qnic2, request.idx2)

        self.send_response(bell_result, name=request.id)

    def send_response(self, response, name=None):
        r"""
        Sends a response to the port `q_ops`.
        """
        header = "Q OP RESP"
        if name is not None:
            header += " REQ " + str(name)
        msg = ns.components.Message(header=header, items=[name, response])
        self.node.ports['q_ops'].tx_output(msg)

    def __init__(self, node, name=None):
        if name is None:
            name = "Quantum Operations Service"
        super().__init__(node=node, name=name)

        # We will use a queue for requests
        self.queue = deque()
        self._new_req_signal = "New request in queue"
        self.add_signal(self._new_req_signal)
        self._create_id = 0

        self.qproc = self.node.qmemory

        # save the entanglement swapping program
        self._es_program = ns.components.QuantumProgram(num_qubits=2)
        q1, q2 = self._es_program.get_qubit_indices(num_qubits=2)
        self._es_program.apply(ns.components.instructions.INSTR_MEASURE_BELL, [q1, q2], output_key="m", inplace=False)

        self.correct_program = self.CorrectProgram()

        self.register_request(self.req_free, self._handle_free)
        self.register_request(self.req_qcirc, self._handle_qcirc)
        self.register_request(self.req_correct, self._handle_correct)
        self.register_request(self.req_dejmps, self._handle_dejmps)
        self.register_request(self.req_swap, self._handle_swap)
