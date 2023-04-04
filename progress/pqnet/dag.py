import netsquid as ns
import networkx as nx

from progress.pqnet.p_module import Module
from progress.pqnet.messages import InterModuleMessage
import progress.progress_logging as log


class DAG:
    r"""
    This class is a representation of a Directed Acyclic Graph (DAG), where each node is assigned with an instance of
    the class :class:`~progress.pqnet.kernel.p_module.Module`. The DAG is used to represent the input/output
    relationship between modules, that determines the order in which the modules process the tokens.

    Parameters
    ----------
    nodes : dict[str, :class:`~progress.pqnet.kernel.p_module.Module`]
        A dictionary that maps the name of each node to its corresponding module.
    edges : list[tuple[str, str]]
        A list of tuples, where each tuple represents an edge in the DAG. The order of the tuple is important,
        as it determines the direction of the edge.

    Attributes
    ----------
    wrapping_node : :class:`netsquid.nodes.Node`
        A :class:`netsquid.nodes.Node` that wraps the DAG. This node is used to connect the DAG to the rest of the
        components of the quantum network device.

    Notes
    -----
    The Ports of the wrapping node are:
        - "token_in_[0..roots]": The input port for tokens from the i-th QNIC. Tokens are delivered to the i-th root of
            the DAG. The i-th root is the i-th node in `nodes` that has no predecessors.
        - "messages": The input/output port for classical messages.
        - "tokens_ops_in": The input port for responses from the quantum hardware for operations on the tokens.
    """

    def __init__(self, nodes, edges):
        self._graph = nx.DiGraph()
        self._graph.add_nodes_from(nodes.keys())
        self._graph.add_edges_from(edges)
        self._nodes = nodes

        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("The graph is not a DAG.")

        # save the roots of the dag
        self._roots = []
        for node in self._graph.nodes:
            if len(list(self._graph.predecessors(node))) == 0:
                self._roots.append(node)

        # add a wrapper node to the dag and add the ports
        self.wrapping_node = ns.nodes.Node(name="DAG")
        r"""
        A :class:`netsquid.nodes.Node` that wraps the DAG. This node is used to connect the DAG to the rest of the
        components of the device.
        
        Notes
        -----
        The ports of this node are:
        1. token_in_[0..roots]: The input port for tokens of the i-th root of the DAG.
            The i-th root is the i-th node in `nodes` that has no predecessors.
        2. messages: The input/output port for classical messages.
        3. tokens_ops_in: The input port for responses from the quantum hardware for operations on the tokens.
        """

        self.wrapping_node.add_ports([f"token_in_{i}" for i in range(len(self._roots))] +
                                     ["messages", "tokens_ops_in"])

        # connect the ports of the modules
        ports_used = {}
        for node in self._graph.nodes:
            ports_used[node] = (0, 0)
            self.wrapping_node.add_subcomponent(component=self._nodes[node], name=node)
        for edge in edges:
            source = edge[0]
            destination = edge[1]
            self._nodes[source].ports[f"out{ports_used[source][0]}"].connect(
                self._nodes[destination].ports[f"in{ports_used[destination][1]}"]
            )
            ports_used[source] = (ports_used[source][0] + 1, ports_used[source][1])
            ports_used[destination] = (ports_used[destination][0], ports_used[destination][1] + 1)

        # create a switch and connect it to the "messages" port of each module
        self._switch = DAGMessagesSwitch(dag=self)
        self.wrapping_node.add_subcomponent(component=self._switch, name="switch")
        for i, node in enumerate(self._nodes.keys()):
            self._nodes[node].ports["messages"].connect(self._switch.ports[f"module_{i}"])

        # forward input and output ports to the switch
        self.wrapping_node.ports["messages"].forward_input(self._switch.ports["ext"])
        self._switch.ports["ext"].forward_output(self.wrapping_node.ports["messages"])
        self.wrapping_node.ports["tokens_ops_in"].forward_input(self._switch.ports["qhal_responses"])

        # finally, forward input tokens to roots of the dag depending on their qnic attribute
        for root in self._roots:
            qnic = self._nodes[root].behavior.qnic
            if qnic is None:
                raise ValueError(f"Module {root} is a root of the DAG but has no qnic attribute.")
            self.wrapping_node.ports[f"token_in_{qnic}"].forward_input(self._nodes[root].ports["in0"])

    def set_qhal(self, qhal):
        r"""
        Set the QHAL instance on all modules.

        Parameters
        ----------
        qhal : :class:`~progress.pqnet.kernel.qhal.QHAL`
        """
        for node in self._nodes.values():
            node.qhal = qhal

    def start(self):
        r"""
        Start all modules.
        """
        for node in self._nodes.values():
            node.start()

    def get_nodes(self):
        r"""
        Get a list of the nodes of the DAG, where each element is the module identifier.

        Returns
        -------
        list[str]
        """
        return list(self._nodes.keys())

    def get_dag_node(self):
        r"""
        Get the netsquid node that wraps the DAG.

        Returns
        -------
        :class:`~netsquid.nodes.node.Node`
        """
        return self.wrapping_node

    def terminate(self):
        r"""
        Terminate all modules.
        """
        for node in self._nodes.values():
            node.stop()
            node.behavior.terminate()

    def remove(self):
        r"""
        Remove all modules.
        """
        for node in self._nodes.values():
            self.wrapping_node.rem_subcomponent(node)
            for port in node.ports.values():
                port.disconnect()
        self._switch.remove()
        self.wrapping_node.remove()
        for port in self.wrapping_node.ports.values():
            port.disconnect()


class DAGFactory:
    r"""
    This class is a factory that creates a DAG from a list of edges and a dictionary of
    :class:`~progress.pqnet.kernel.p_module.ModuleBehavior` classes.

    Parameters
        ----------
        edges : list[tuple[str, str]]
            A list of tuples, where each tuple represents an edge in the DAG. The order of the tuple is important,
            as it determines the direction of the edge.
        module_behaviors : dict[str, tuple(:class:`~progress.pqnet.kernel.p_module.ModuleBehavior.class`, dict)]
            A dictionary mapping the name of each module to a tuple of the module behavior class and a dictionary
            of the parameters to pass to the constructor of the module class. The dictionary must have keys that are
            numerical strings, so that they can be used to derive the module id. Roots of the DAG must have the optional
            integer parameter `"qnic"` to link them to the specific token queue from the QHAL.
    """

    def __init__(self, edges, module_behaviors, device_id):
        self._edges = edges
        self._module_behaviors = module_behaviors
        self._module_params = {}
        # infer the number of input and output ports for each module
        for node in self._module_behaviors.keys():
            num_input = 0
            num_output = 0

            if "qnic" in self._module_behaviors[node][1].keys():
                num_input += 1

            for edge in edges:
                if edge[1] == node:
                    num_input += 1
                if edge[0] == node:
                    num_output += 1
            self._module_params[node] = {}
            self._module_params[node]["num_input"] = num_input
            self._module_params[node]["num_output"] = num_output
            self._module_params[node]["device_id"] = device_id
            self._module_params[node]["name"] = "Module " + node
            self._module_params[node]["module_id"] = int(node)

    def create_dag(self):
        r"""
        Create a DAG.

        Returns
        -------
        :class:`~progress.pqnet.kernel.dag.DAG`
        """
        modules = {}
        for node in self._module_behaviors.keys():
            modules[node] = Module(**self._module_params[node])
            self._module_behaviors[node][1]["node"] = modules[node]
            behavior = self._module_behaviors[node][0](**self._module_behaviors[node][1])
            modules[node].behavior = behavior
        return DAG(modules.copy(), self._edges.copy())


class DAGMessagesSwitch(ns.components.Switch):
    r"""
    This class abstracts a virtual switch that routes incoming messages to the correct module in the DAG
    using `module_id` as routing key. It also acts as a multiplexer for all outgoing messages from
    bricks in the DAG.

    Parameters
    -----------
    dag : :class:`~progress.pqnet.kernel.dag.DAG`
        The DAG that the switch is associated with.
    name : str or None, optional
        The name of the switch instance. If `None`, a default name is used. Defaults to `None`.
    """

    def __init__(self, dag, name=None):
        r"""
        Initialize the switch.
        """

        port_names = [f"module_{i}" for i in range(len(dag.get_nodes()))] + ["ext", "qhal_responses"]

        mux = {}

        if name is None:
            name = "DAGSwitch"

        # The multiplexing part is already initialized
        for i in range(len(dag.get_nodes())):
            mux[port_names[i]] = "ext"

        # Routing table:
        routing_table = {}
        for node in dag.get_nodes():
            routing_table[int(node)] = port_names[int(node)]

        super().__init__(name=name, port_names=port_names, properties={"mux_table": mux,
                                                                       "routing_table": routing_table})

    def routing_table(self, input_port, message) -> [(ns.components.Message, str)]:
        r"""
        See :class:`~netsquid.components.switch.Switch` for more information.
        """
        if input_port == "ext":
            if isinstance(message, InterModuleMessage):
                if message.destination_id not in self.properties["routing_table"]:
                    log.warning(f"No entry for module {message.destination_id} in the DAG")
                    return []
                return [(message, self.properties["routing_table"][message.destination_id])]
        elif input_port == "qhal_responses":  # message is a response from the QHAL
            return [(message, self.properties["routing_table"][message.items[2].id])]
        else:
            return [(message, self.properties["mux_table"][input_port])]
