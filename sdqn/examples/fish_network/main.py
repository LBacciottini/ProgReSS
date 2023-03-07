import logging

import netsquid as ns

from sdqn.examples.fish_network.topology import get_topology
import sdqn.sdqn_logging as log

# the main function
if __name__ == '__main__':
    ns.set_qstate_formalism(ns.QFormalism.DM)
    log.log_to_console(level=logging.INFO)
    ns.set_random_state(seed=53)
    network, data_collector = get_topology(avg_scenario_period=0.124)
    stats = ns.sim_run(end_time=100000000)
    print('Stats are: ', data_collector.get_counts())
    print(stats)