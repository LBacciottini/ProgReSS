"""
This module contains the messages that are used at the NET level for module-to-module communication and for
controller-device communication.
"""

import netsquid as ns

__all__ = ["InterModuleMessage", "ReplaceDAGMessage"]


class InterModuleMessage(ns.components.Message):
    """
    A message that is used to communicate between modules.
    """

    base_header = "INTER MODULE MESSAGE"

    def __init__(self, sender_device, sender_id, destination_device, destination_id, inner_message, topology_id=0):
        super().__init__(items=[sender_device, sender_id, destination_device, destination_id, inner_message,topology_id],
                         header=f"{self.base_header} {sender_id} {destination_id}")

    @property
    def sender_device(self):
        """
        The id of device that sent the message.

        Returns
        -------
        int
        """
        return self.items[0]

    @property
    def sender_id(self):
        """
        The id of the module that sent the message.

        Returns
        -------
        int
        """
        return self.items[1]

    @property
    def destination_device(self):
        """
        The id of the device that the message is intended for.

        Returns
        -------
        int
        """
        return self.items[2]

    @property
    def destination_id(self):
        """
        The id of the module that the message is intended for.

        Returns
        -------
        int
        """
        return self.items[3]

    @property
    def inner_message(self):
        r"""
        The message that is being sent.

        Returns
        -------
        :class:`netsquid.components.Message`
        """
        return self.items[4]

    @property
    def topology_id(self):
        """
        The current topology id of the network. If it does not match the current topology id of the device,
        the message is discarded. This is used to prevent messages from being sent to device that are not yet
        up to date with the current topology (they must receive a new DAG).

        Returns
        -------
        int
        """
        return self.items[-1]


class ReplaceDAGMessage(ns.components.Message):
    """
    A message used by the controller to update the DAG of a device
    """

    base_header = "REPLACE DAG MESSAGE"

    def __init__(self, destination_device, dag_factory, topology_id=0):
        super().__init__(items=[destination_device, dag_factory,
                                topology_id], header=f"{self.base_header} to {destination_device}")

    @property
    def destination_device(self):
        """
        The id of the device that the message is intended for.

        Returns
        -------
        int
        """
        return self.items[0]

    @property
    def dag_factory(self):
        r"""
        The DAG factory that is used to create the new DAG.

        Returns
        -------
        :class:`~progress.topology.dag.DAGFactory`
        """
        return self.items[1]

    @property
    def topology_id(self):
        """
        The new topology id of the network.

        Returns
        -------
        int
        """
        return self.items[-1]
