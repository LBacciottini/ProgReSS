import math

import netsquid as ns

from sdqn.examples.fish_network.controller import DummyController
from sdqn.examples.fish_network.metrics_collector import TokenUtilizationMetricsCollector, FidelityMetricsCollector, \
    CumulativeMetricsCollector
from sdqn.hardware.llps.mps import optimistic_parameters_v3, MPSProtocol
from sdqn.hardware.mps_connection import MPSConnection

from sdqn.device import QNetworkDevice


def get_topology(avg_scenario_period=0.5, controller_dist=15, out_of_band=False):
    r"""
    Get the topology of the network.
    """
    qproc_params = {
        "coherence_time": 5 * 1e6,
        "one_qbit_noise": None, 
        "two_qbit_noise": None,
        "two_qbit_p_err": 0.0000000000005,
        "meas_p_err": 0.,
        "instr_duration": 1.
    }
    
    end_node_0 = QNetworkDevice(device_id=0, num_qnics=1, num_cnics=1, num_qbits_qnic=100,
                                qproc_params=qproc_params)
    end_node_1 = QNetworkDevice(device_id=1, num_qnics=1, num_cnics=1, num_qbits_qnic=100,
                                qproc_params=qproc_params)

    rep_2 = QNetworkDevice(device_id=2, num_qnics=4, num_cnics=4, num_qbits_qnic=100,
                           qproc_params=qproc_params)
    rep_3 = QNetworkDevice(device_id=3, num_qnics=2, num_cnics=2, num_qbits_qnic=100,
                           qproc_params=qproc_params)
    rep_4 = QNetworkDevice(device_id=4, num_qnics=2, num_cnics=2, num_qbits_qnic=100,
                           qproc_params=qproc_params)
    rep_5 = QNetworkDevice(device_id=5, num_qnics=3, num_cnics=3, num_qbits_qnic=100,
                           qproc_params=qproc_params)

    end_node_6 = QNetworkDevice(device_id=6, num_qnics=1, num_cnics=1, num_qbits_qnic=100,
                                qproc_params=qproc_params)

    # create the network
    network = ns.nodes.Network("Fish Network")

    # add the nodes to the network
    network.add_nodes([end_node_0, end_node_1, rep_2, rep_3, rep_4, rep_5, end_node_6])
    
    # get the mps connection parameters
    L_att = 22
    link_length = 15  # km
    p_photon = optimistic_parameters_v3["p_photon"]
    p_bsa = optimistic_parameters_v3["p_bsa"]
    p_left = math.e ** (-link_length / (2 * L_att)) * p_photon * p_bsa
    
    mps_conn_params = {
        "p_left": p_left,
        "p_mid": optimistic_parameters_v3["p_mid"], 
        "num_positions": optimistic_parameters_v3["N_value"],
        "t_clock": optimistic_parameters_v3["t_clock"]
    }

    mps_conn_params_5_6 = mps_conn_params.copy()
    mps_conn_params_5_6["p_left"] = math.e ** (-link_length / (4 * L_att)) * p_photon * p_bsa

    # add the edges to the network
    delay = 1e9*link_length/2e5
    network.add_connection(node1=end_node_0, node2=rep_2, port_name_node1="q_0", port_name_node2="q_0",
                           connection=MPSConnection(name="MPS_CONN_0_2", length=link_length, **mps_conn_params))
    network.add_connection(node1=end_node_0, node2=rep_2, port_name_node1="c_0", port_name_node2="c_0",
                           bidirectional=True, delay=delay, label="CONN_0_2")

    network.add_connection(node1=end_node_1, node2=rep_2, port_name_node1="q_0", port_name_node2="q_1",
                            connection=MPSConnection(name="MPS_CONN_1_2", length=link_length, **mps_conn_params))
    network.add_connection(node1=end_node_1, node2=rep_2, port_name_node1="c_0", port_name_node2="c_1",
                            bidirectional=True, delay=delay, label="CONN_1_2")

    network.add_connection(node1=rep_2, node2=rep_3, port_name_node1="q_2", port_name_node2="q_0",
                            connection=MPSConnection(name="MPS_CONN_2_3", length=link_length, **mps_conn_params))
    network.add_connection(node1=rep_2, node2=rep_3, port_name_node1="c_2", port_name_node2="c_0",
                            bidirectional=True, delay=delay, label="CONN_2_3")

    network.add_connection(node1=rep_2, node2=rep_4, port_name_node1="q_3", port_name_node2="q_0",
                            connection=MPSConnection(name="MPS_CONN_2_4", length=link_length, **mps_conn_params))
    network.add_connection(node1=rep_2, node2=rep_4, port_name_node1="c_3", port_name_node2="c_0",
                            bidirectional=True, delay=delay, label="CONN_2_4")

    network.add_connection(node1=rep_3, node2=rep_5, port_name_node1="q_1", port_name_node2="q_1",
                            connection=MPSConnection(name="MPS_CONN_3_5", length=link_length, **mps_conn_params))
    network.add_connection(node1=rep_3, node2=rep_5, port_name_node1="c_1", port_name_node2="c_1",
                            bidirectional=True, delay=delay, label="CONN_3_5")

    network.add_connection(node1=rep_4, node2=rep_5, port_name_node1="q_1", port_name_node2="q_2",
                            connection=MPSConnection(name="MPS_CONN_4_5", length=link_length, **mps_conn_params))
    network.add_connection(node1=rep_4, node2=rep_5, port_name_node1="c_1", port_name_node2="c_2",
                            bidirectional=True, delay=delay, label="CONN_4_5")

    network.add_connection(node1=rep_5, node2=end_node_6, port_name_node1="q_0", port_name_node2="q_0",
                            connection=MPSConnection(name="MPS_CONN_5_6", length=link_length/2, **mps_conn_params_5_6))
    network.add_connection(node1=rep_5, node2=end_node_6, port_name_node1="c_0", port_name_node2="c_0",
                            bidirectional=True, delay=delay/2, label="CONN_5_6")

    # add link layer protocols
    end_node_0_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=end_node_0.qhardware,
                    other_node_info=(2, "qnic0"), name="mps0")
    ]
    for i, llp in enumerate(end_node_0_llps):
        end_node_0.qhardware.subscribe_llp(i, llp)
        llp.start()

    end_node_1_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=end_node_1.qhardware,
                    other_node_info=(2, "qnic1"), name="mps0")
    ]
    for i, llp in enumerate(end_node_1_llps):
        end_node_1.qhardware.subscribe_llp(i, llp)
        llp.start()

    rep_2_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=rep_2.qhardware,
                    other_node_info=(0, "qnic0"), name="mps0"),
        MPSProtocol(num_positions=100, qnic="qnic1", node=rep_2.qhardware,
                    other_node_info=(1, "qnic0"), name="mps1"),
        MPSProtocol(num_positions=100, qnic="qnic2", node=rep_2.qhardware,
                    other_node_info=(3, "qnic0"), name="mps2"),
        MPSProtocol(num_positions=100, qnic="qnic3", node=rep_2.qhardware,
                    other_node_info=(4, "qnic0"), name="mps3")
    ]
    for i, llp in enumerate(rep_2_llps):
        rep_2.qhardware.subscribe_llp(i, llp)
        llp.start()

    rep_3_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=rep_3.qhardware,
                    other_node_info=(2, "qnic2"), name="mps0"),
        MPSProtocol(num_positions=100, qnic="qnic1", node=rep_3.qhardware,
                    other_node_info=(5, "qnic1"), name="mps1")
    ]
    for i, llp in enumerate(rep_3_llps):
        rep_3.qhardware.subscribe_llp(i, llp)
        llp.start()

    rep_4_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=rep_4.qhardware,
                    other_node_info=(2, "qnic3"), name="mps0"),
        MPSProtocol(num_positions=100, qnic="qnic1", node=rep_4.qhardware,
                    other_node_info=(5, "qnic2"), name="mps1")
    ]
    for i, llp in enumerate(rep_4_llps):
        rep_4.qhardware.subscribe_llp(i, llp)
        llp.start()

    rep_5_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=rep_5.qhardware,
                    other_node_info=(6, "qnic0"), name="mps0"),
        MPSProtocol(num_positions=100, qnic="qnic1", node=rep_5.qhardware,
                    other_node_info=(3, "qnic1"), name="mps1"),
        MPSProtocol(num_positions=100, qnic="qnic2", node=rep_5.qhardware,
                    other_node_info=(4, "qnic1"), name="mps2")
    ]
    for i, llp in enumerate(rep_5_llps):
        rep_5.qhardware.subscribe_llp(i, llp)
        llp.start()

    end_node_6_llps = [
        MPSProtocol(num_positions=100, qnic="qnic0", node=end_node_6.qhardware,
                    other_node_info=(5, "qnic0"), name="mps0")
    ]
    for i, llp in enumerate(end_node_6_llps):
        end_node_6.qhardware.subscribe_llp(i, llp)
        llp.start()

    # add the controller
    controller = DummyController(avg_scenario_period=avg_scenario_period)
    network.add_node(controller)

    # connect the controller to all nodes of the network
    nodes = [
        end_node_0,
        end_node_1,
        rep_2,
        rep_3,
        rep_4,
        rep_5,
        end_node_6
    ]

    if out_of_band:
        base_delay = 1e9*controller_dist/2e5
        for i in range(len(nodes)):
            network.add_connection(node1=controller, node2=nodes[i], port_name_node1=f"dev_{i}", port_name_node2="controller",
                                    bidirectional=True, delay=base_delay*(i+1))
    else:
        controller_delay = 1e9*controller_dist/2e5
        for i, node in enumerate(nodes):
            network.add_connection(node1=controller, node2=node, port_name_node1=f"dev_{i}", port_name_node2="controller",
                                    bidirectional=True, delay=controller_delay)

    controller.start()

    data_collector = TokenUtilizationMetricsCollector()
    fid_collector = FidelityMetricsCollector(node_a=6, node_b=0)
    agg_collector = CumulativeMetricsCollector(node_a=6, node_b=0)

    return network, data_collector, fid_collector, agg_collector

