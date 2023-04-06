import netsquid as ns

from progress.abstraction.qhal import QHAL
from progress.hardware.qhardware import QHardware
from progress.messaging.router import MessageRoutingService
from progress.pqnet.net_manager import NetManagerProtocol


class QNetworkDevice(ns.nodes.Node):
    r"""
    A quantum network device that can be used as a programmable repeater or end node of the network.

    Parameters
    ----------
    device_id : int
        The ID of the device. Should be unique in the network.
    num_qnics : int
        The number of QNICs.
    num_cnics : int
        The number of classical NICs.
    num_qbits_qnic : int
        The number of memory qubits allocated to each QNIC.
    qproc_params : dict[str, any] or None, optional
        The parameters of the quantum processor of this device. See :func:`~progress.hardware.qhardware.get_processor`
        for details. If `None`, a default processor is created. Defaults to `None`. The field `num_positions` can be
        omitted, as it is set to `num_qnics * num_qbits_qnic`.

    Attributes
    ----------
    device_id : int
        The ID of the device.
    num_qnics : int
        The number of QNICs of this device.
    num_cnics : int
        The number of classical NICs of this device.
    qhardware : :class:`~progress.hardware.qhardware.QHardware`
        The quantum hardware of this device.
    qhal : :class:`~progress.abstraction.qhal.QHAL`
        The QHAL of this device.
    net_manager : :class:`~progress.pqnet.net_manager.NetManagerProtocol`
        The NET manager installed on this device.
    message_router : :class:`~progress.messaging.router.MessageRoutingService`
        The message router installed on this device.

    Notes
    -----
    The device architecture is composed of the following layers (bottom-up):
        - Physical layer: The quantum hardware (quantum memory, processor, QNICs, etc.)
        - Link Layer Protocols: The classical control protocols to generate robust entanglement over each QNIC.
        - Quantum Hardware Abstraction Layer: The QHAL (see :class:`~progress.abstraction.qhal.QHAL`). It abstracts the
          quantum hardware resources and provides a unified interface for the NET layer.
        - NET layer: The NET layer is responsible for processing link-generated entanglement and delivering long-range
          entanglement to the applications. We implemented the NET layer as a programmable framework called PQ-NET
          (see :class:`~progress.pqnet.__init__`).

    Ports:
        - q_{i}: The i-th QNIC of this device.
        - c_{i}: The i-th classical NIC of this device.
        - controller: The controller port of this device. It is used for controller-device communication.
    """

    def __init__(self, device_id, num_qnics, num_cnics, num_qbits_qnic, qproc_params=None):
        ports = [f"q_{i}" for i in range(num_qnics)] + [f"c_{i}" for i in range(num_cnics)] + ["controller"]
        super().__init__(name=f"device_{device_id}", port_names=ports, ID=device_id)
        self.device_id = device_id
        self.num_qnics = num_qnics
        self.num_cnics = num_cnics

        # create the quantum hardware
        self.qhardware = QHardware(name=f"qhardware_{device_id}", num_qnics=num_qnics, num_qbits_qnic=num_qbits_qnic,
                                   qproc_params=qproc_params)
        #"""The quantum hardware of this device."""
        self.add_subcomponent(self.qhardware, name="qhardware")
        # connect the quantum hardware to the node ports
        for i in range(num_qnics):
            self.ports[f"q_{i}"].forward_input(self.qhardware.ports[f"qnic{i}"])
            self.qhardware.ports[f"qnic{i}"].forward_output(self.ports[f"q_{i}"])

        # create the QHAL
        self.qhal = QHAL(device_id=device_id, name=f"qhal_{device_id}", qhardware=self.qhardware)
        #"""The QHAL of this device."""
        self.add_subcomponent(self.qhal, name="qhal")
        # connect the QHAL to the qhardware ports
        self.qhal.ports["new_entanglement"].connect(self.qhardware.ports["new_entanglements"])
        self.qhal.ports["q_ops"].connect(self.qhardware.ports["q_ops"])

        # create the pqnet level
        self.dag = None
        #"""The current DAG of the device (PQ-NET)."""
        self.net_manager = NetManagerProtocol(name=f"net_manager_{device_id}", node=self)
        #"""The NET manager of this device. It handles classical messages and responses from the quantum hardware and
        #    delivers them to the destination module inside the DAG.
        #"""
        self.net_manager.start()
        self.current_topology_id = 0

        # create the message router
        self.message_router = MessageRoutingService(name=f"message_router_{device_id}", node=self)
        #"""
        #The message router of this device. It handles all classical messages and routes them inside and outside of
        #the device.
        #"""
        self.message_router.start()
