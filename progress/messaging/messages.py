"""
This module contains network messages that are used in ProgReSS, like classical routing messages.
Note: Not used in the current version of ProgReSS
"""

import netsquid as ns


class ClassicalRoutingTableMessage(ns.components.Message):
    """
    This message encapsulates a classical routing table shaped as a dictionary indexed by host IDs.

    Parameters
    ----------
    dest_device : int
        The ID of the device that the routing table is for.
    routing_table : dict[int, int]
        The routing table.
    """

    def __init__(self, dest_device, routing_table):
        super().__init__(items=[dest_device, routing_table], header=f"CLASSICAL ROUTING TABLE to {dest_device}")

    @property
    def routing_table(self):
        return self.items[1]

    @property
    def destination_device(self):
        return self.items[0]
