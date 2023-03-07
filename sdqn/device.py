import netsquid as ns

from sdqn.abstraction.qhal import QHAL
from sdqn.hardware.qhardware import QHardware
from sdqn.messaging.router import MessageRoutingService
from sdqn.progress.net_manager import NetManagerProtocol


class QNetworkDevice(ns.nodes.Node):

    def __init__(self, device_id, num_qnics, num_cnics, num_qbits_qnic, qproc_params=None):
        ports = [f"q_{i}" for i in range(num_qnics)] + [f"c_{i}" for i in range(num_cnics)] + ["controller"]
        super().__init__(name=f"device_{device_id}", port_names=ports, ID=device_id)
        self.device_id = device_id
        self.num_qnics = num_qnics
        self.num_cnics = num_cnics

        # create the quantum hardware
        self.qhardware = QHardware(name=f"qhardware_{device_id}", num_qnics=num_qnics, num_qbits_qnic=num_qbits_qnic,
                                   qproc_params=qproc_params)
        self.add_subcomponent(self.qhardware, name="qhardware")
        # connect the quantum hardware to the node ports
        for i in range(num_qnics):
            self.ports[f"q_{i}"].forward_input(self.qhardware.ports[f"qnic{i}"])
            self.qhardware.ports[f"qnic{i}"].forward_output(self.ports[f"q_{i}"])

        # create the QHAL
        self.qhal = QHAL(device_id=device_id, name=f"qhal_{device_id}", qhardware=self.qhardware)
        self.add_subcomponent(self.qhal, name="qhal")
        # connect the QHAL to the qhardware ports
        self.qhal.ports["new_entanglement"].connect(self.qhardware.ports["new_entanglements"])
        self.qhal.ports["q_ops"].connect(self.qhardware.ports["q_ops"])

        # create the net level
        self.dag = None
        self.net_manager = NetManagerProtocol(name=f"net_manager_{device_id}", node=self)
        self.net_manager.start()
        self.current_topology_id = 0

        # create the message router
        self.message_router = MessageRoutingService(name=f"message_router_{device_id}", node=self)
        self.message_router.start()
