"""
This module contains the manager for the NET layer. It is responsible for handling controller messages and
maintaining the DAG.
"""
from collections import namedtuple

import netsquid as ns

from sdqn.messaging.messages import ClassicalRoutingTableMessage
from sdqn.progress.messages import InterModuleMessage, ReplaceDAGMessage


class NetManagerProtocol(ns.protocols.ServiceProtocol):

    req_message = namedtuple("req_message", ["message"])
    """
    Request to handle a ProgReSS message.
    """

    def __init__(self, name, node):
        super().__init__(name=name, node=node)
        self.register_request(self.req_message, self._handle_message)
        self.entanglement_started = False

    def _handle_message(self, request):
        message = request.message
        if isinstance(message, InterModuleMessage):
            # retrieve the DAG of the node and inject the message
            dag = self.node.dag
            if dag is None or self.node.current_topology_id != message.topology_id:
                # if the topology id of the message does not match the current topology id, ignore the message
                return
            dag.wrapping_node.ports["messages"].tx_input(message)
        elif isinstance(message, ReplaceDAGMessage):
            # replace the DAG of the node

            if self.node.dag is not None:
                self.node.dag.terminate()
                self.node.dag.remove()
            self.node.dag = message.dag_factory.create_dag()
            self.node.dag.set_qhal(self.node.qhal)

            # connect the new DAG to the qhal
            self.node.add_subcomponent(self.node.dag.wrapping_node, name="dag")
            for i in range(self.node.qhardware.num_qnics):
                self.node.qhal.ports[f"token_out_{i}"].connect(self.node.dag.wrapping_node.ports[f"token_in_{i}"])
            self.node.qhal.ports["tokens_ops"].connect(self.node.dag.wrapping_node.ports["tokens_ops_in"])

            self.node.dag.start()
            self.node.current_topology_id = message.topology_id

            # by default, also start the entanglement generation on all links (only the first time)
            # TODO: this should be specified in the ReplaceDAGMessage
            if not self.entanglement_started:
                for i in range(self.node.qhardware.num_qnics):
                    self.node.qhal.resume_entanglement(qnic=i)
                self.entanglement_started = True



