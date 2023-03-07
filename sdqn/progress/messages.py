import netsquid as ns


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
        return self.items[0]

    @property
    def sender_id(self):
        return self.items[1]

    @property
    def destination_device(self):
        return self.items[2]

    @property
    def destination_id(self):
        return self.items[3]

    @property
    def inner_message(self):
        return self.items[4]

    @property
    def topology_id(self):
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
        return self.items[0]

    @property
    def dag_factory(self):
        return self.items[1]

    @property
    def topology_id(self):
        return self.items[-1]
