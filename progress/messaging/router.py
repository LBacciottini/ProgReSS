"""
This module contains aservice that routes classical messages incoming and outgoing from the device.
It listens to all classical ports and routes messages to the correct inner layer.
If the message is meant for another device, it is routed to the correct output port.
"""

import netsquid as ns
from progress.messaging.messages import ClassicalRoutingTableMessage
from progress.pqnet.messages import InterModuleMessage, ReplaceDAGMessage
from progress import progress_logging as log


class MessageRoutingService(ns.protocols.NodeProtocol):
    r"""
    A service that routes classical messages incoming and outgoing from the device.
    It listens to all classical port inputs and routes messages depending on their destination:
        - If the message is meant for another device, it is routed to the correct output port.
        - If the message is meant for the device, it is handled by the service and delivered to the correct
          layer of the device architecture (either Link or NET layers in the current version of ProgReSS).

    Parameters
    ----------
    name : str
        The name of the protocol.
    node : :class:`netsquid.nodes.Node`
        The node that the protocol is running on.
    """

    def __init__(self, name, node):
        super().__init__(name=name, node=node)
        self._routing_table = None

    def _handle_message(self, message):
        r"""
        Handle a message that is meant to be routed between devices.
        """
        if message.destination_device != self.node.device_id:
            self._route_message_out(message)
            return
        if isinstance(message, InterModuleMessage):
            req = self.node.net_manager.req_message(message)
            self.node.net_manager.put(req)
        elif isinstance(message, ReplaceDAGMessage):
            log.info(f"Received new DAG", self.node.device_id)
            req = self.node.net_manager.req_message(message)
            self.node.net_manager.put(req)
        elif isinstance(message, ClassicalRoutingTableMessage):
            self._handle_routing_table(message)

    def _handle_routing_table(self, message):
        r"""
        Handle a message that contains a routing table.
        """
        log.info(f"Received routing table", self.node.device_id)
        if not isinstance(message, ClassicalRoutingTableMessage):
            raise TypeError("Message is not a routing table message")
        if message.destination_device != self.node.device_id:
            self._route_message_out(message)
        else:
            self._routing_table = message.routing_table

    def _route_message_out(self, message):
        out_qnic = self._routing_table[message.destination_device]
        self.node.ports[f"c_{out_qnic}"].tx_output(message)

    def _get_ev_expr(self):
        ev_expr = self.await_port_input(self.node.ports[f"controller"])
        for i in range(self.node.num_cnics):
            ev_expr |= self.await_port_input(self.node.ports[f"c_{i}"])

        return ev_expr

    def _get_triggered_ports(self, ev_expr):
        triggered_ports = []
        for i in range(self.node.num_cnics - 1, -1, -1):
            if ev_expr.second_term.value:
                triggered_ports.append(f"c_{i}")
            ev_expr = ev_expr.first_term
        if ev_expr.value:
            triggered_ports.append("controller")
        return triggered_ports

    def run(self):
        r"""
        References
        ----------

        See :meth:`netsquid.protocols.Protocol.run`.
        """
        while True:
            if self.node.dag is None:
                ev_expr = yield self._get_ev_expr()
                triggered_ports = self._get_triggered_ports(ev_expr)
            else:
                ev_expr = yield self._get_ev_expr() |\
                    self.await_port_output(self.node.dag.wrapping_node.ports["messages"])
                if ev_expr.second_term.value:
                    while len(self.node.dag.wrapping_node.ports["messages"].output_queue) > 0:
                        message = self.node.dag.wrapping_node.ports["messages"].rx_output()
                        self._handle_message(message)
                triggered_ports = self._get_triggered_ports(ev_expr.first_term)

            for port in triggered_ports:
                while len(self.node.ports[port].input_queue) > 0:
                    message = self.node.ports[port].rx_input()
                    self._handle_message(message)
